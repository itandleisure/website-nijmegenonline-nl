"""Alles aan het bedrijf en de plaats koppelen (besluit Frans, 2-11-2026).

- Bedrijf: de sleutel uit de bedrijvengids (/bedrijvengids/<sleutel>/) is de basis. Een evenement wijst ernaar met
  "bedrijf" (of via zijn aanbieder: "bedrijf" in data/aanbieders.json), een nieuwsbericht met "bedrijven". De
  bedrijfspagina toont dan de komende evenementen en het nieuws; de evenement- en nieuwspagina's krijgen een kaartje
  "Over <bedrijf>".
- Plaats: elk evenement en elke aanbieder heeft een plaats (Nijmegen, Wijchen, Kleef, ...). Staat die er niet bij, dan
  haalt plaats_van() hem uit het adres (plaatsnaam of postcode). De plaatspagina's in /bestemmingen/ tonen de agenda
  van hun plaats (tools/agenda.py), en het agenda-overzicht kan op plaats filteren.
"""
import json
import pathlib
import re
import unicodedata

from import_wordpress import SITE, esc

ROOT = pathlib.Path(__file__).resolve().parent.parent
VERMELDINGEN = ROOT / "data" / "bedrijvengids-vermeldingen.json"
ZOEKLIJST = ROOT / "data" / "bedrijven-zoek.json"

# Plaats -> (bestemmingspagina of None, andere schrijfwijzen). De naam is zoals hij op de site staat.
# Dorpen horen bij de pagina van hun gemeente (Malden bij Heumen, Beek bij Berg en Dal).
PLAATSEN = {
    "Nijmegen": (None, ["Nimwegen", "Lent", "Hatert", "Dukenburg", "Lindenholt", "Oosterhout"]),
    "Wijchen": ("wijchen", ["Alverna", "Batenburg", "Bergharen", "Hernen", "Balgoij", "Niftrik", "Woezik"]),
    "Beuningen": ("beuningen", ["Weurt", "Ewijk", "Winssen"]),
    "Groesbeek": ("groesbeek", ["Breedeweg", "De Horst", "Heilig Landstichting"]),
    "Berg en Dal": ("berg-en-dal", ["Beek", "Ubbergen", "Ooij", "Persingen", "Leuth", "Kekerdom", "Millingen aan de Rijn",
                                    "Millingen"]),
    "Heumen": ("heumen", ["Malden", "Overasselt", "Nederasselt", "Molenhoek"]),
    "Mook": ("mook", ["Plasmolen", "Middelaar", "Mook en Middelaar"]),
    "Gennep": ("gennep", ["Milsbeek", "Ottersum", "Ven-Zelderheide"]),
    "Kleef": ("kleve", ["Kleve", "Cleve", "Materborn", "Kellen", "Donsbrüggen"]),
    "Kranenburg": ("kranenburg", ["Zyfflich", "Nütterden", "Frasselt", "Wyler"]),
    "Goch": ("goch", ["Pfalzdorf", "Asperden", "Hommersum"]),
    "Elst": (None, []),
    "Bemmel": (None, []),
    "Druten": (None, []),
    "Arnhem": (None, []),
    "Cuijk": (None, []),
}
# Postcodes (eerste vier cijfers, of vijf in Duitsland) als de plaatsnaam niet in het adres staat
POSTCODES = [((6500, 6546), "Nijmegen"), ((6550, 6551), "Beuningen"), ((6560, 6564), "Groesbeek"),
             ((6566, 6578), "Berg en Dal"), ((6580, 6584), "Heumen"), ((6585, 6586), "Mook"), ((6590, 6598), "Gennep"),
             ((6600, 6605), "Wijchen"), ((6611, 6612), "Heumen"), ((6613, 6617), "Wijchen"), ((6640, 6645), "Beuningen"),
             ((6650, 6659), "Druten"), ((6660, 6662), "Elst"), ((6663, 6666), "Nijmegen"), ((6678, 6678), "Nijmegen"),
             ((6680, 6689), "Bemmel"), ((6800, 6846), "Arnhem")]
DUITS = {"47533": "Kleef", "47559": "Kranenburg", "47574": "Goch"}


def _sleutel(tekst):
    tekst = unicodedata.normalize("NFKD", tekst or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", tekst).strip()


_NAMEN = sorted(((_sleutel(n), plaats) for plaats, (_, andere) in PLAATSEN.items() for n in [plaats] + andere),
                key=lambda x: -len(x[0]))


def plaats_naam(tekst):
    """'kleve' of 'Malden' -> 'Kleef' / 'Heumen'; onbekend -> ''."""
    s = _sleutel(tekst)
    return next((p for n, p in _NAMEN if s == n), "")


def plaats_van(adres):
    """De plaats uit een adres: eerst een plaatsnaam (achteraan het eerst), dan de postcode. Onbekend: ''."""
    s = " %s " % _sleutel(adres)
    # De plaatsnaam die het laatst in het adres staat ("Nijmeegsebaan 1, Groesbeek": niet Nijmegen)
    beste, plek = "", -1
    for naam, plaats in _NAMEN:
        i = s.rfind(" %s " % naam)
        if i > plek:
            beste, plek = plaats, i
    if beste:
        return beste
    m = re.search(r"\b(\d{4})\s?[A-Za-z]{2}\b", adres or "")
    if m:
        pc = int(m.group(1))
        return next((p for (van, tot), p in POSTCODES if van <= pc <= tot), "")
    m = re.search(r"\b(?:D-)?(\d{5})\b", adres or "")
    return DUITS.get(m.group(1), "") if m else ""


def bestemming(plaats):
    """Slug van de plaatspagina in /bestemmingen/, of None."""
    return PLAATSEN.get(plaats, (None, []))[0]


def laad_vermeldingen():
    return json.loads(VERMELDINGEN.read_text(encoding="utf-8")) if VERMELDINGEN.exists() else {}


def zoeklijst(vermeldingen):
    """Klein bestand voor het zoekveld "Zoek je bedrijf" in de formulieren en op de beoordeelpagina:
    [sleutel, naam, adres, postcode, plaats, website, categorie] per bedrijf, op naam gesorteerd."""
    rijen = [[s, v["bedrijf"], v.get("adres", ""), v.get("postcode", ""), v.get("plaats", ""), v.get("site", ""),
              v.get("categorie", "")] for s, v in vermeldingen.items()]
    return sorted(rijen, key=lambda r: (_sleutel(r[1]), r[0]))


def schrijf_zoeklijst(vermeldingen):
    ZOEKLIJST.write_text(json.dumps(zoeklijst(vermeldingen), ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")


def bedrijf_van_evenement(e, aanbieders):
    """De bedrijfssleutel van een evenement: eigen veld, anders die van de aanbieder."""
    return e.get("bedrijf") or aanbieders.get(e.get("aanbieder") or "", {}).get("bedrijf") or ""


def plaats_van_evenement(e, aanbieders):
    """Eigen veld, anders uit het adres, anders die van de aanbieder, anders uit de naam van de locatie (Kleve centrum),
    anders Nijmegen."""
    a = aanbieders.get(e.get("aanbieder") or "", {})
    return (plaats_naam(e.get("plaats") or "") or e.get("plaats") or plaats_van(e.get("adres") or "")
            or a.get("plaats") or plaats_van(a.get("adres") or "") or plaats_van(e.get("locatie") or "")
            or plaats_van(a.get("naam") or "") or "Nijmegen")


def foto_src(foto, root):
    """Een foto van de eigen site relatief maken, zodat hij ook op de testsite werkt."""
    if foto.startswith(SITE + "/assets/"):
        return root + foto[len(SITE) + 1:]
    return foto


def over_bedrijf(slug, v, root, kop_="h2"):
    """Kaartje "Over <bedrijf>" onder een evenement, nieuwsbericht of vacature, met een link naar de bedrijfspagina."""
    foto = '<img src="%s" alt="" loading="lazy">' % esc(foto_src(v["foto"], root)) if v.get("foto") else ""
    regel = " · ".join(x for x in (v.get("categorie", ""), v.get("plaats", "")) if x)
    return ('        <section class="over-bedrijf">\n          <%s>Over %s</%s>\n'
            '          <a class="over-bedrijf__kaart" href="%sbedrijvengids/%s/">%s<span><strong>%s</strong>%s'
            '<span class="over-bedrijf__meer">Bekijk de bedrijfspagina</span></span></a>\n        </section>'
            % (kop_, esc(v["bedrijf"]), kop_, root, slug, foto, esc(v["bedrijf"]),
               '<span class="over-bedrijf__regel">%s</span>' % esc(regel) if regel else ""))


def organisatie_ld(slug, v):
    """schema.org Organization voor organizer (evenement), about (nieuws) en hiringOrganization (vacature)."""
    uit = {"@type": "Organization", "name": v["bedrijf"], "url": "%s/bedrijvengids/%s/" % (SITE, slug)}
    if v.get("site"):
        uit["sameAs"] = v["site"]
    return uit
