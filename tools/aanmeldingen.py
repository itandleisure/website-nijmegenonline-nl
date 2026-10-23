"""Haalt goedgekeurde aanmeldingen (evenementen, bedrijven en nieuwsberichten) op uit het Google Apps Script en zet
ze in de data.

Zo werkt de flow (zie ook tools/google-formulier/Code.gs):
1. Iemand meldt een evenement of bedrijf aan op de site; dat komt in de Google Sheet en in een mail aan de redactie.
2. De redactie klikt in die mail op "Akkoord" (of zet "Akkoord" in de kolom Status).
3. Elk uur draait dit script (.github/workflows/aanmeldingen.yml): het haalt de goedgekeurde aanmeldingen op,
   zet evenementen in data/evenementen.json (foto in assets/uploads/aangemeld/) en bedrijven in
   data/bedrijven-aangemeld.json (voor de bedrijvengids) en nieuwsberichten in data/nieuws.json (foto ook in
   assets/uploads/aangemeld/), en meldt ze terug zodat de status "Gepubliceerd" wordt en de inzender een mail krijgt.
   Daarna bouwen tools/agenda.py, tools/bedrijvengids.py, tools/nieuws.py en tools/build.py de site opnieuw.
   Nieuwsberichten komen niet via een formulier maar per mail binnen: zie tools/nieuws_ophalen.py.

Gebruik: python tools/aanmeldingen.py [--test bestand.json]   (--test: lijst uit een bestand, niets terugmelden)
"""
import base64
import datetime
import html
import io
import json
import pathlib
import re
import sys
import time
import unicodedata
import urllib.parse
import urllib.request
import zoneinfo

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from paginas import GOOGLE_FORM_URL  # noqa: E402
from import_wordpress import SITE  # noqa: E402
import nieuws  # noqa: E402

VERWERKT = ROOT / "data" / "aanmeldingen-verwerkt.txt"
FOTOMAP = "assets/uploads/aangemeld"


def slug(tekst):
    tekst = unicodedata.normalize("NFKD", tekst).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", tekst).strip("-")[:80].strip("-") or "evenement"


def ophalen(url):
    with urllib.request.urlopen(url, timeout=120) as r:
        return json.loads(r.read().decode("utf-8"))


def bewaar_foto(foto, naam):
    """Foto (base64) als webp van maximaal 1200 px breed; geeft het pad terug."""
    from PIL import Image
    im = Image.open(io.BytesIO(base64.b64decode(foto["data"])))
    im = im.convert("RGB")
    if im.width > 1200:
        im = im.resize((1200, round(im.height * 1200 / im.width)))
    pad = "%s/%s.webp" % (FOTOMAP, naam)
    (ROOT / FOTOMAP).mkdir(parents=True, exist_ok=True)
    im.save(ROOT / pad, quality=82)
    return pad


def alinea(tekst):
    delen = [d.strip() for d in re.split(r"\n\s*\n", tekst.replace("\r", "")) if d.strip()]
    return "\n".join("<p>%s</p>" % html.escape(d).replace("\n", "<br>") for d in delen)


def nieuws_html(tekst):
    """Tekst van de beoordeelpagina naar HTML: alinea's gescheiden door een lege regel, een regel die met ## begint
    wordt een tussenkop, de eerste alinea de vetgedrukte intro (zoals de berichten op WordPress) en links klikbaar."""
    def opmaak(t):
        t = html.escape(t).replace("\n", "<br>")
        return re.sub(r"(https?://[^\s<]+[^\s<.,;:)])", r'<a href="\1">\1</a>', t)
    uit, intro = [], True
    for blok in re.split(r"\n\s*\n", tekst.replace("\r", "").strip()):
        regels = blok.strip().split("\n")
        if regels[0].startswith("#"):
            uit.append("<h2>%s</h2>" % opmaak(regels.pop(0).lstrip("#").strip()))
        rest = "\n".join(regels).strip()
        if rest:
            uit.append("<p><strong>%s</strong></p>" % opmaak(rest) if intro else "<p>%s</p>" % opmaak(rest))
            intro = False
    return "\n".join(uit)


def nieuwsbericht(a, berichten):
    titel = (a.get("titel") or "").strip()
    tekst = nieuws_html(a.get("omschrijving") or "")
    if not titel or not tekst:
        raise ValueError("titel of tekst ontbreekt")
    bestaand = {b["slug"] for b in berichten}
    basis = slug(titel)
    s, n = basis, 2
    while s in bestaand:
        s, n = "%s-%d" % (basis, n), n + 1
    foto = bewaar_foto(a["foto"], "nieuws-" + s) if a.get("foto") else ""
    nu = datetime.datetime.now(zoneinfo.ZoneInfo("Europe/Amsterdam")).strftime("%Y-%m-%dT%H:%M:%S")
    return {
        "slug": s,
        "titel": titel,
        "seo_titel": titel,
        "beschrijving": (a.get("samenvatting") or "").strip(),
        "datum": nu,
        "gewijzigd": nu,
        "foto": "%s/%s" % (SITE, foto) if foto else "",
        "bijschrift": (a.get("bijschrift") or "").strip() if foto else "",
        "tekst": tekst,
        "aanmelding": a["id"],
    }


def tijd(waarde):
    m = re.match(r"(\d{1,2})[:.](\d{2})", waarde or "")
    return "%02d:%s" % (int(m.group(1)), m.group(2)) if m else ""


def postcode(tekst):
    """'6511ab' wordt '6511 AB'; Duitse (5 cijfers) en andere postcodes blijven zoals ze zijn."""
    tekst = tekst.strip().upper()
    m = re.match(r"^(\d{4})\s*([A-Z]{2})$", tekst)
    return "%s %s" % m.groups() if m else tekst


def naam_sleutel(naam):
    """Naam zonder kleine verschillen: 'Café het Haantje' en "Cafe 't Haantje" worden allebei 'haantje'."""
    naam = unicodedata.normalize("NFKD", naam).encode("ascii", "ignore").decode().lower()
    naam = re.sub(r"['`]", "", naam)
    woorden = [w for w in re.split(r"[^a-z0-9]+", naam) if w and w not in ("cafe", "het", "t", "de", "the")]
    return "".join(woorden)


def adres_sleutel(adres):
    """Straat en huisnummer zonder postcode, plaats en leestekens: 'Daalseweg 19, 6521 GH Nijmegen' wordt 'daalseweg19'."""
    return re.sub(r"[^a-z0-9]", "", adres.split(",")[0].lower())


def kies_aanbieder(a, evenementen, aanbieders):
    """De aanbieder die de redactie op de beoordeelpagina koos; anders een bestaande met (bijna) dezelfde naam
    of hetzelfde adres; anders een nieuwe op naam van de locatie."""
    keuze = (a.get("aanbieder") or "").strip()
    locatie = a.get("locatie", "").strip()
    if keuze in aanbieders:
        return keuze
    if keuze != "nieuw":
        sleutel = naam_sleutel(locatie)
        gevonden = next((k for k, v in aanbieders.items() if sleutel and naam_sleutel(v["naam"]) == sleutel), None)
        if not gevonden and a.get("adres"):
            straat = adres_sleutel(a["adres"])
            gevonden = next((e["aanbieder"] for e in reversed(evenementen)
                             if e.get("aanbieder") in aanbieders and e["adres"] and adres_sleutel(e["adres"]) == straat), None)
        if gevonden:
            return gevonden
    if not locatie:
        return ""
    s, n = slug(locatie), 2
    while s in aanbieders:
        s, n = "%s-%d" % (slug(locatie), n), n + 1
    return s


def vul_adressen(aanbieders, evenementen):
    """Zet bij elke aanbieder het bekende adres, voor de beoordeelpagina. Voorkeur: met postcode, dan met
    huisnummer, dan het laatste evenement."""
    for k, v in aanbieders.items():
        adressen = [e["adres"] for e in evenementen if e.get("aanbieder") == k and e.get("adres")]
        if adressen:
            v["adres"] = max(reversed(adressen), key=lambda x: (bool(re.search(r"\b(\d{4} ?[A-Z]{2}|\d{5})\b", x)),
                                                                   bool(re.search(r"\d", x))))
        else:
            v.pop("adres", None)


def evenement(a, evenementen, aanbieders):
    datum = (a.get("datum") or "")[:10]
    if not re.match(r"\d{4}-\d{2}-\d{2}$", datum):
        raise ValueError("geen geldige datum: %r" % a.get("datum"))
    einddatum = (a.get("einddatum") or "")[:10]
    if not re.match(r"\d{4}-\d{2}-\d{2}$", einddatum) or einddatum < datum:
        einddatum = datum
    begin, eind = tijd(a.get("starttijd")), tijd(a.get("eindtijd"))
    bestaand = {e["slug"] for e in evenementen} | set((ROOT / "data" / "evenementen-verwijderd.txt").read_text().split())
    basis = slug(a["titel"])
    s, n = basis, 2
    while s in bestaand:
        s, n = "%s-%d" % (basis, n), n + 1
    locatie = a.get("locatie", "").strip()
    aanbieder = kies_aanbieder(a, evenementen, aanbieders)
    if aanbieder in aanbieders:
        locatie = aanbieders[aanbieder]["naam"]   # de bekende schrijfwijze
    elif aanbieder:
        aanbieders[aanbieder] = {"naam": locatie}
    plaats = " ".join(x for x in (postcode(a.get("postcode", "")), a.get("plaats", "").strip()) if x)
    adres = ", ".join(x for x in (a.get("adres", "").strip(), plaats) if x) or next(
        (e["adres"] for e in reversed(evenementen) if e.get("aanbieder") == aanbieder and e["adres"]), "")
    site = a.get("site", "").strip()
    if site and not re.match(r"https?://", site):
        site = "https://" + site
    foto = bewaar_foto(a["foto"], s) if a.get("foto") else ""
    return {
        "slug": s,
        "titel": a["titel"].strip(),
        "start": "%sT%s" % (datum, begin) if begin else datum,
        "eind": "%sT%s" % (einddatum, eind) if eind else einddatum,
        "locatie": locatie,
        "adres": adres,
        "afbeelding": "%s/%s" % (SITE, foto) if foto else "",
        "alt": a["titel"].strip() if foto else "",
        "uitgelicht": False,
        "aanbieder": aanbieder or "",
        "link": "",
        "terugkerend": False,
        "gepubliceerd": (a.get("ontvangen") or "")[:10],
        "tekst": alinea(a.get("omschrijving", "")),
        "aanmelding": a["id"],
        "website": site if re.match(r"https?://[^\s/]+\.[^\s]+$", site) else "",
        "contactmail": a.get("evenementmail", "").strip(),
        "telefoon": a.get("evenementtelefoon", "").strip(),
    }


def main(test=None):
    if not GOOGLE_FORM_URL:
        print("GOOGLE_FORM_URL is leeg, niets op te halen")
        return
    lijst = json.load(open(test)) if test else ophalen(GOOGLE_FORM_URL + "?actie=lijst")
    verwerkt = set(VERWERKT.read_text().split()) if VERWERKT.exists() else set()
    evenementen = json.load(open(ROOT / "data" / "evenementen.json", encoding="utf-8"))
    aanbieders = json.load(open(ROOT / "data" / "aanbieders.json", encoding="utf-8"))
    bedrijven_pad = ROOT / "data" / "bedrijven-aangemeld.json"
    bedrijven = json.load(open(bedrijven_pad, encoding="utf-8")) if bedrijven_pad.exists() else []
    wijzigingen_pad = ROOT / "data" / "bedrijvengids-wijzigingen.json"
    wijzigingen = json.load(open(wijzigingen_pad, encoding="utf-8")) if wijzigingen_pad.exists() else {}
    berichten = nieuws.laad()
    nieuw, terugmelden = [], []
    for a in lijst.get("evenement", []):
        if a["id"] not in verwerkt:
            try:
                e = evenement(a, evenementen, aanbieders)
            except Exception as fout:  # één kapotte aanmelding mag de rest niet tegenhouden
                print("Evenement %s overgeslagen: %s" % (a.get("id"), fout))
                continue
            evenementen.append(e)
            nieuw.append("evenement %s" % e["slug"])
            verwerkt.add(a["id"])
        # Met de link naar de eventpagina, die gaat in de mail aan de inzender
        slug_ = next((e["slug"] for e in evenementen if e.get("aanmelding") == a["id"]), "")
        if a.get("gepubliceerd"):
            terugmelden.append(a["gepubliceerd"] + ("&url=" + urllib.parse.quote("%s/events/%s/" % (SITE, slug_), safe="") if slug_ else ""))
    for a in lijst.get("bedrijf", []):
        if a["id"] not in verwerkt:
            b = {k: v for k, v in a.items() if k not in ("foto", "gepubliceerd")}
            if a.get("foto"):
                b["foto"] = bewaar_foto(a["foto"], "bedrijf-" + slug(a.get("bedrijf", a["id"])))
            if a.get("vermelding"):
                # Dit is mijn bedrijf: de redactie keurde de wijziging goed; tools/bedrijvengids.py past hem toe
                b["goedgekeurd"] = time.strftime("%Y-%m-%d")
                wijzigingen[a["vermelding"]] = b
                nieuw.append("wijziging bedrijf %s" % a["vermelding"])
            else:
                bedrijven.append(b)
                nieuw.append("bedrijf %s" % a.get("bedrijf"))
            verwerkt.add(a["id"])
        url = "%s/bedrijvengids/%s/" % (SITE, a["vermelding"]) if a.get("vermelding") else ""
        terugmelden.append(a.get("gepubliceerd") and a["gepubliceerd"] + ("&url=" + urllib.parse.quote(url, safe="") if url else ""))
    nieuwe_berichten = False
    for a in lijst.get("nieuws", []):
        if a["id"] not in verwerkt:
            try:
                b = nieuwsbericht(a, berichten)
            except Exception as fout:  # één kapot bericht mag de rest niet tegenhouden
                print("Nieuwsbericht %s overgeslagen: %s" % (a.get("id"), fout))
                continue
            berichten.append(b)
            nieuwe_berichten = True
            nieuw.append("nieuws %s" % b["slug"])
            verwerkt.add(a["id"])
        slug_ = next((b["slug"] for b in berichten if b.get("aanmelding") == a["id"]), "")
        if a.get("gepubliceerd"):
            terugmelden.append(a["gepubliceerd"] + ("&url=" + urllib.parse.quote("%s/nieuwsoverzicht/%s/" % (SITE, slug_), safe="") if slug_ else ""))
    if nieuwe_berichten:
        nieuws.bewaar(berichten)
    if nieuw:
        evenementen.sort(key=lambda e: (e["start"], e["slug"]))
        vul_adressen(aanbieders, evenementen)
        (ROOT / "data" / "evenementen.json").write_text(json.dumps(evenementen, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        (ROOT / "data" / "aanbieders.json").write_text(json.dumps(dict(sorted(aanbieders.items())), ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        if bedrijven:
            bedrijven_pad.write_text(json.dumps(bedrijven, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        if wijzigingen:
            wijzigingen_pad.write_text(json.dumps(wijzigingen, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        VERWERKT.write_text("\n".join(sorted(verwerkt)) + "\n")
    # De workflow meldt pas terug na een geslaagde commit; mislukt die, dan komt de aanmelding de volgende keer terug
    if not test:
        open(ROOT / ".terugmelden", "w").write("\n".join(u for u in terugmelden if u))
    print("Aanmeldingen: %d nieuw%s" % (len(nieuw), "".join("\n  " + n for n in nieuw)))


if __name__ == "__main__":
    main(sys.argv[sys.argv.index("--test") + 1] if "--test" in sys.argv else None)
