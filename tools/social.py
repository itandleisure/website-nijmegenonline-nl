"""Elke dag een post op Facebook en Instagram, helemaal vanuit de site. Draait via .github/workflows/social.yml.

Afgesproken met Frans (02-11-2026): route A uit het voorstel (eigen Action, Claude schrijft, Meta API plaatst),
1 post per dag, nog geen advertentiebudget, betaalde partners en uitgelichte evenementen gaan voor gratis content.
Instellingen (aan/uit, controleperiode, hoe vaak partners) staan in data/social-instellingen.json.

Stappen:
  python tools/social.py voorbereiden [--datum 2026-11-03]
      Kiest de post van de dag, maakt de beelden (assets/social/, jpg 1080 x 1350, story 1080 x 1920), laat Claude de
      tekst schrijven (zonder ANTHROPIC_API_KEY een vaste tekst) en zet alles in data/social-gepland.json. Bouwt ook
      /social/, de pagina voor de link in de Instagram-bio. Daarna: python tools/build.py (header en footer).
  python tools/social.py melden
      Alleen in de controleperiode: zet de post van vandaag in een GitHub-issue. Sluit Frans dat issue, dan wordt de
      post overgeslagen; doet hij niets, dan gaat hij gewoon online.
  python tools/social.py plaatsen
      Plaatst de post van vandaag via de Meta Graph API op de Facebookpagina en Instagram, plus een Instagram-story
      voor een uitgelicht evenement op de dag zelf. Haalt posts over evenementen weg die van de site zijn verwijderd.
      Vraagt META_TOKEN (systeemgebruiker- of paginatoken) en optioneel META_PAGE_ID; zie docs/social-media-koppelen.md.
  python tools/social.py voorbeeld --datum 2026-11-03 --dagen 7 [--map /pad]
      Een week vooruit kijken: maakt beelden en teksten in een losse map met een index.html, zonder iets te bewaren
      of te plaatsen.

Wat er per dag komt (zie kies()):
  1. Betaald gaat voor: een uitgelicht evenement (klant, promotiepakket) 1 tot 9 dagen voor de datum, en partners en
     hoofdpartners volgens partner_elke_dagen. Hoogstens betaald_per_week in 7 dagen, behalve een evenement dat
     vandaag zijn laatste kans heeft. Op maandag en donderdag (de agenda-carrousels) alleen als het niet kan wachten.
     Betaalde posts beginnen met "Advertentie" (Reclamecode Social Media).
  2. Anders het weekschema: ma deze week in Nijmegen (carrousel), di nieuws, wo gids of artikel, do dit weekend
     (carrousel), vr gids of artikel (seizoen eerst), za vandaag in Nijmegen (carrousel), zo nieuws. Lukt een soort
     niet (te weinig evenementen, geen vers nieuws), dan de volgende.
  In de carrousels staan uitgelichte evenementen vooraan.
"""
import datetime
import html
import json
import os
import pathlib
import re
import shutil
import sys
import time
import zoneinfo

from PIL import Image, ImageDraw, ImageFont, ImageOps

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from agenda import DAGEN, MAANDEN, dag, lokaal, wanneer  # noqa: E402
from import_wordpress import ROOT, SITE, VOET, esc, kop, samenvatting  # noqa: E402
from nieuwsbrief import basis, nieuw_genoeg  # noqa: E402
import nieuws  # noqa: E402

AMSTERDAM = zoneinfo.ZoneInfo("Europe/Amsterdam")
DATA = ROOT / "data"
INSTELLINGEN = DATA / "social-instellingen.json"
GEPLAATST = DATA / "social-geplaatst.json"
GEPLAND = DATA / "social-gepland.json"
BEELDEN = ROOT / "assets" / "social"
PAGINA = "social"
BEWAAR_BEELDEN = 45   # dagen; daarna mogen de jpg's weg (Facebook en Instagram hebben hun eigen kopie)
MODEL = os.environ.get("MODEL_SOCIAL") or "claude-sonnet-5-5"
GRAPH = "https://graph.facebook.com/v23.0"

DONKERBLAUW = (18, 73, 124)
GROEN = (83, 156, 32)
BLAUW = (64, 143, 198)
LICHT = (214, 228, 240)
BREED, HOOG, STORY_HOOG = 1080, 1350, 1920

SCHEMA = {0: ["week", "nieuws", "gids"], 1: ["nieuws", "gids"], 2: ["gids", "nieuws"], 3: ["weekend", "nieuws", "gids"],
          4: ["gids", "nieuws"], 5: ["vandaag", "nieuws", "gids"], 6: ["nieuws", "gids"]}
CARROUSEL_DAGEN = {0, 3}
VOORBLAD = ["assets/img/standaard/nijmegen-skyline-waalkade.webp", "assets/img/standaard/nijmegen-waal-zonsondergang.webp",
            "assets/img/standaard/nijmegen-skyline-stevenskerk.webp"]


# ---------------------------------------------------------------- data

def lees(pad, standaard):
    return json.load(open(pad, encoding="utf-8")) if pad.is_file() else standaard


def schrijf(pad, data):
    pad.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def instellingen():
    return lees(INSTELLINGEN, {})


def geplaatst():
    return lees(GEPLAATST, [])


def laatst_geplaatst(log, sleutel):
    """Datum waarop deze sleutel (evenement:slug, bedrijf:slug, pagina:/url/, nieuws:slug) het laatst online kwam."""
    data = [p["datum"] for p in log if p.get("status") == "geplaatst" and sleutel in p.get("sleutels", [])]
    return datetime.date.fromisoformat(max(data)) if data else None


def laatst_betaald(log, sleutel):
    data = [p["datum"] for p in log if p.get("status") == "geplaatst" and p.get("betaald") and sleutel in p.get("sleutels", [])]
    return datetime.date.fromisoformat(max(data)) if data else None


MAX_VERGROTING = 2.3   # een foto die meer vergroot moet worden om het fotovlak (1080 x 880) te vullen, wordt korrelig


def eigen_foto(url):
    """Pad naar de eigen webp/jpg in de repo, of None (dan geen post: Instagram wil altijd een beeld).
    Standaardfoto's en te kleine of te smalle foto's tellen niet mee."""
    if not url:
        return None
    if url.startswith("/"):
        url = SITE + url
    pad = lokaal(url)
    if not pad:
        m = re.match(r"https?://(?:www\.)?nijmegenonline\.nl/(assets/.+)$", url)
        pad = m.group(1) if m and (ROOT / m.group(1)).is_file() else None
    if not pad or "/standaard/" in pad:
        return None
    with Image.open(ROOT / pad) as img:
        return pad if max(BREED / img.width, (HOOG - 470) / img.height) <= MAX_VERGROTING else None


def evenementen():
    return json.load(open(DATA / "evenementen.json", encoding="utf-8"))


def kort(e, vandaag):
    """'za 8 nov, 20.30 uur', 'nu, t/m zo 9 nov' of '8 t/m 9 nov'."""
    s, t = dag(e, "start"), dag(e, "eind")

    def d(x):
        return "%s %d %s" % (DAGEN[x.weekday()][:2], x.day, MAANDEN[x.month - 1][:3])
    if s == t:
        tijd = e["start"][11:16].replace(":", ".") if "T" in e["start"] else ""
        return d(s) + (", %s uur" % tijd if tijd else "")
    if s <= vandaag:
        return "nu, t/m %s" % d(t)
    return "%s t/m %s" % (d(s), d(t))


def pagina_info(url):
    """Titel, beschrijving en eigen foto van een pagina op de site, uit de og-tags."""
    pad = ROOT / url.strip("/") / "index.html"
    if not pad.is_file():
        return None
    bron = pad.read_text(encoding="utf-8")
    if 'http-equiv="refresh"' in bron:
        return None

    def meta(naam):
        m = re.search(r'<meta property="og:%s" content="([^"]*)"' % naam, bron)
        return html.unescape(m.group(1)) if m else ""
    foto = eigen_foto(meta("image"))
    if not meta("title") or not foto:
        return None
    return {"titel": meta("title"), "beschrijving": meta("description"), "foto": foto}


def bedrijven():
    """slug -> bedrijf uit de bedrijvengids (een bedrijf staat soms in meer categorieën)."""
    uit = {}
    for cat, v in json.load(open(DATA / "bedrijvengids.json", encoding="utf-8")).items():
        for b in (v.get("gids", []) if isinstance(v, dict) else []):
            uit.setdefault(b["slug"], dict(b, categorie=cat))
    return uit


def instagram_naam(url):
    m = re.match(r"https?://(?:www\.)?instagram\.com/([A-Za-z0-9_.]+)/?", url or "")
    return m.group(1) if m and m.group(1) not in ("p", "reel", "explore") else None


# ---------------------------------------------------------------- kiezen

def kandidaat_evenement(e, url, vandaag, betaald):
    w = wanneer(e)
    return {"soort": "evenement", "betaald": betaald, "sleutels": ["evenement:" + e["slug"]], "titel": e["titel"],
            "link": "%s/events/%s/" % (url, e["slug"]), "label": "UITGELICHT" if betaald else "AGENDA",
            "items": [{"titel": e["titel"], "sub": "%s · %s" % (kort(e, vandaag), e["locatie"]), "foto": eigen_foto(e["afbeelding"])}],
            "feiten": ["📅 %s" % (w[0].upper() + w[1:]), "📍 %s" % ", ".join(x for x in (e["locatie"], e.get("adres", "")) if x)],
            "bron": {"titel": e["titel"], "wanneer": w, "locatie": e["locatie"], "omschrijving": samenvatting(e["tekst"], 900)}}


def story_vandaag(vandaag, log):
    """Een uitgelicht evenement dat vandaag begint krijgt een Instagram-story (los van de post van de dag)."""
    al = {p.get("story_sleutel") for p in log if p.get("story_id")}
    for e in sorted(evenementen(), key=lambda e: (e["start"], e["slug"])):
        if e.get("uitgelicht") and dag(e, "start") == vandaag and eigen_foto(e["afbeelding"]) and "story:" + e["slug"] not in al:
            return e
    return None


def betaalde_kandidaten(vandaag, log, inst, url):
    """Betaalde posts die nu aan de beurt zijn, met hun laatste dag: [(laatste_dag, kandidaat)]."""
    uit = []
    vooraf, minimaal = inst.get("evenement_dagen_vooraf", [9, 1])
    for e in evenementen():
        if not e.get("uitgelicht") or dag(e, "eind") < vandaag or not eigen_foto(e["afbeelding"]):
            continue
        if laatst_betaald(log, "evenement:" + e["slug"]):
            continue
        s = dag(e, "start")
        if s > vandaag + datetime.timedelta(days=vooraf):
            continue
        # te laat aangemeld of al begonnen (lang lopend): zo snel mogelijk
        laatste = max(vandaag, s - datetime.timedelta(days=minimaal))
        uit.append((laatste, kandidaat_evenement(e, url, vandaag, True)))

    pakketten = lees(DATA / "bedrijvengids-pakketten.json", {})
    gids = bedrijven()
    for slug, p in sorted(pakketten.items()):
        if slug.startswith("_") or not isinstance(p, dict):
            continue
        elke = inst.get("partner_elke_dagen", {}).get(p.get("pakket"), 0)
        if not elke or p.get("betaald_tot", "") < vandaag.isoformat() or slug not in gids:
            continue
        laatst = laatst_betaald(log, "bedrijf:" + slug)
        if laatst and (vandaag - laatst).days < elke:
            continue
        b = gids[slug]
        foto = next((f for f in [*(p.get("fotos") or []), b.get("foto")] if eigen_foto(f)), None)
        if not foto:
            print("social: %s heeft geen eigen foto, sla over" % slug)
            continue
        actie = p.get("actie") if p.get("actie", {}).get("tot", "9999") >= vandaag.isoformat() else None
        feiten = ["📍 %s" % ", ".join(x for x in (b.get("adres"), b.get("plaats")) if x)]
        if actie:
            feiten.insert(0, "🎁 %s" % actie["tekst"])
        uit.append((vandaag + datetime.timedelta(days=14), {
            "soort": "partner", "betaald": True, "sleutels": ["bedrijf:" + slug], "titel": b["naam"],
            "link": "%s/bedrijvengids/%s/" % (url, slug), "label": "PARTNER",
            "items": [{"titel": b["naam"], "sub": ", ".join(x for x in (b.get("adres"), b.get("plaats")) if x),
                       "foto": eigen_foto(foto)}],
            "feiten": feiten, "instagram_naam": instagram_naam(b.get("instagram")),
            "bron": {"naam": b["naam"], "plaats": b.get("plaats"), "beschrijving": b.get("beschrijving", ""),
                     "tekst": samenvatting(b.get("tekst", ""), 900), "actie": actie["tekst"] if actie else ""}}))
    return sorted(uit, key=lambda x: (x[0], x[1]["sleutels"]))


def carrousel(soort, van, tot, vandaag, log, url):
    gekozen = []
    for e in evenementen():
        if dag(e, "start") > tot or dag(e, "eind") < van or not nieuw_genoeg(e, van) or not eigen_foto(e["afbeelding"]):
            continue
        recent = laatst_geplaatst(log, "evenement:" + e["slug"])
        # uitgelicht eerst, maar wat de afgelopen dagen al langskwam achteraan (anders steeds hetzelfde evenement)
        gekozen.append((bool(recent and (vandaag - recent).days < 4), not e.get("uitgelicht"), e["start"], e["slug"], e))
    gekozen = [x[-1] for x in sorted(gekozen)[:5]]
    if len(gekozen) < 3:
        return None
    koppen = {"week": ("Deze week in Nijmegen", "%d t/m %d %s" % (van.day, tot.day, MAANDEN[tot.month - 1])),
              "weekend": ("Dit weekend in Nijmegen", "%d t/m %d %s" % (van.day, tot.day, MAANDEN[tot.month - 1])),
              "vandaag": ("Vandaag in Nijmegen", "%s %d %s" % (DAGEN[van.weekday()], van.day, MAANDEN[van.month - 1]))}
    titel, periode = koppen[soort]
    return {"soort": soort, "betaald": False, "sleutels": ["evenement:" + e["slug"] for e in gekozen], "titel": titel,
            "periode": periode, "link": "%s/nijmegen-evenementen-overzicht/" % url, "label": "AGENDA",
            "items": [{"titel": e["titel"], "sub": "%s · %s" % (kort(e, vandaag), e["locatie"]), "foto": eigen_foto(e["afbeelding"]),
                       "uitgelicht": bool(e.get("uitgelicht"))} for e in gekozen],
            "feiten": ["• %s (%s, %s)" % (e["titel"], kort(e, vandaag), e["locatie"]) for e in gekozen],
            "bron": {"soort": titel, "periode": periode,
                     "evenementen": [{"titel": e["titel"], "wanneer": kort(e, vandaag), "locatie": e["locatie"],
                                      "omschrijving": samenvatting(e["tekst"], 250)} for e in gekozen]}}


def nieuws_kandidaat(vandaag, log, url):
    for b in sorted(nieuws.laad(), key=lambda b: b["datum"], reverse=True):
        datum = datetime.date.fromisoformat(b["datum"][:10])
        if (vandaag - datum).days > 4:
            break
        if datum > vandaag or laatst_geplaatst(log, "nieuws:" + b["slug"]) or not eigen_foto(b.get("foto")):
            continue
        return {"soort": "nieuws", "betaald": False, "sleutels": ["nieuws:" + b["slug"]], "titel": b["titel"],
                "link": "%s/nieuwsoverzicht/%s/" % (url, b["slug"]), "label": "NIEUWS",
                "items": [{"titel": b["titel"], "sub": "", "foto": eigen_foto(b["foto"])}], "feiten": [],
                "bron": {"titel": b["titel"], "samenvatting": b.get("beschrijving", ""), "tekst": samenvatting(b["tekst"], 1200)}}
    return None


def gids_kandidaat(vandaag, log, inst, url):
    """Seizoenspagina eerst, dan gidsen en artikelen met het meeste verkeer die een jaar niet geplaatst zijn."""
    import csv
    seizoen = [(u, 0) for u, maanden in inst.get("seizoen", {}).items() if vandaag.month in maanden]
    pool = [(g["url"], 500) for g in json.load(open(DATA / "gidsen.json", encoding="utf-8"))]
    for r in csv.DictReader(open(DATA / "indeling-artikelen.csv", encoding="utf-8"), delimiter=";"):
        if r["nieuwe_rubriek"] != "Partnerbijdragen":   # betaalde artikelen niet als gewone tip
            pool.append((r["url"], int(r["verkeer"] or 0)))
    pool.sort(key=lambda x: -x[1])
    for lijst, wacht in ((seizoen, 21), (pool, 365)):
        for u, _ in lijst:
            laatst = laatst_geplaatst(log, "pagina:" + u)
            if laatst and (vandaag - laatst).days < wacht:
                continue
            info = pagina_info(u)
            if not info:
                continue
            titel = re.sub(r"\s*\|\s*NijmegenOnline$", "", info["titel"])
            return {"soort": "gids", "betaald": False, "sleutels": ["pagina:" + u], "titel": titel, "link": url + u,
                    "label": "TIP", "items": [{"titel": titel, "sub": "", "foto": info["foto"]}], "feiten": [],
                    "bron": {"titel": titel, "beschrijving": info["beschrijving"],
                             "tekst": samenvatting((ROOT / u.strip("/") / "index.html").read_text(encoding="utf-8"), 1200)}}
    return None


def kies(vandaag, log, inst, url):
    """De post van vandaag: betaald eerst (met grenzen), anders het weekschema."""
    week_geleden = (vandaag - datetime.timedelta(days=6)).isoformat()
    betaald_deze_week = sum(1 for p in log if p.get("status") == "geplaatst" and p.get("betaald") and p["datum"] >= week_geleden)
    for laatste, k in betaalde_kandidaten(vandaag, log, inst, url):
        moet = laatste <= vandaag
        if not moet and (betaald_deze_week >= inst.get("betaald_per_week", 3) or vandaag.weekday() in CARROUSEL_DAGEN):
            continue
        return k

    maandag = vandaag - datetime.timedelta(days=vandaag.weekday())
    for soort in SCHEMA[vandaag.weekday()]:
        if soort == "week":
            k = carrousel("week", vandaag, maandag + datetime.timedelta(days=6), vandaag, log, url)
        elif soort == "weekend":
            k = carrousel("weekend", maandag + datetime.timedelta(days=4), maandag + datetime.timedelta(days=6), vandaag, log, url)
        elif soort == "vandaag":
            k = carrousel("vandaag", vandaag, vandaag, vandaag, log, url)
        elif soort == "nieuws":
            k = nieuws_kandidaat(vandaag, log, url)
        else:
            k = gids_kandidaat(vandaag, log, inst, url)
        if k:
            return k
    return None


# ---------------------------------------------------------------- beelden

def lettertype(grootte, gewicht="Bold"):
    f = ImageFont.truetype(str(ROOT / "assets" / "fonts" / "raleway-latin.woff2"), grootte)
    f.set_variation_by_name(gewicht)
    return f


def regels(teken, tekst, font, breedte, maximum):
    woorden, uit, regel = tekst.split(), [], ""
    for w in woorden:
        probeer = (regel + " " + w).strip()
        if teken.textlength(probeer, font=font) <= breedte:
            regel = probeer
        else:
            if regel:
                uit.append(regel)
            regel = w
    if regel:
        uit.append(regel)
    if len(uit) > maximum:
        uit = uit[:maximum]
        while uit[-1] and teken.textlength(uit[-1] + "…", font=font) > breedte:
            uit[-1] = uit[-1].rsplit(" ", 1)[0] if " " in uit[-1] else uit[-1][:-1]
        uit[-1] += "…"
    return uit


def passend(teken, tekst, breedte, groottes, maximum):
    """Grootste lettergrootte waarbij de titel in maximum regels past."""
    for g in groottes:
        f = lettertype(g)
        r = regels(teken, tekst, f, breedte, 99)
        if len(r) <= maximum:
            return f, r
    f = lettertype(groottes[-1])
    return f, regels(teken, tekst, f, breedte, maximum)


def logo(hoogte):
    img = Image.open(ROOT / "assets" / "img" / "logo-nijmegenonline-wit.png").convert("RGBA")
    return img.resize((round(img.width * hoogte / img.height), hoogte), Image.LANCZOS)


def label_tekst(teken, xy, tekst, kleur):
    f = lettertype(30, "ExtraBold")
    x, y = xy
    w = teken.textlength(tekst, font=f)
    teken.rounded_rectangle((x, y, x + w + 40, y + 52), radius=26, fill=kleur)
    teken.text((x + 20, y + 26), tekst, font=f, fill="white", anchor="lm")


def beeld(item, doel, label, hoogte=HOOG, nummer=None, kop=None):
    """Foto boven, donkerblauw vlak met titel en datum eronder, logo rechtsonder."""
    vlak = 470 if hoogte == HOOG else 700
    groot = 1 if hoogte == HOOG else 1.3   # story: groter, want hij staat schermvullend
    foto = Image.open(ROOT / item["foto"]).convert("RGB")
    canvas = Image.new("RGB", (BREED, hoogte), DONKERBLAUW)
    canvas.paste(ImageOps.fit(foto, (BREED, hoogte - vlak), Image.LANCZOS, centering=(0.5, 0.4)), (0, 0))
    teken = ImageDraw.Draw(canvas)
    marge, y = 64, hoogte - vlak + 48
    if kop:
        # voorblad van een carrousel: grote kop, de periode eronder
        label_tekst(teken, (marge, y), label, GROEN)
        f, r = passend(teken, kop, BREED - 2 * marge, [80, 72, 64], 2)
        y += 84
        for regel in r:
            teken.text((marge, y), regel, font=f, fill="white")
            y += round(f.size * 1.15)
        teken.text((marge, y + 10), item["sub"], font=lettertype(42, "SemiBold"), fill=LICHT)
        teken.text((marge, hoogte - 48), "Swipe voor de tips  »", font=lettertype(34, "Bold"), fill="white", anchor="ls")
    else:
        label_tekst(teken, (marge, y), ("%d  %s" % (nummer, label)) if nummer else label, GROEN if label != "PARTNER" else BLAUW)
        y += 84
        f, r = passend(teken, item["titel"], BREED - 2 * marge, [round(g * groot) for g in (68, 60, 52, 46)], 3)
        for regel in r:
            teken.text((marge, y), regel, font=f, fill="white")
            y += round(f.size * 1.18)
        if item.get("sub"):
            sub = lettertype(round(38 * groot), "SemiBold")
            for regel in regels(teken, item["sub"], sub, BREED - 2 * marge - 230, 2):   # 230: ruimte voor het logo
                teken.text((marge, y + 12), regel, font=sub, fill=LICHT)
                y += round(48 * groot)
    lg = logo(64)
    canvas.paste(lg, (BREED - marge - lg.width, hoogte - 40 - lg.height), lg)
    doel.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(doel, "JPEG", quality=86, optimize=True, progressive=True)
    return doel.relative_to(ROOT).as_posix() if doel.is_relative_to(ROOT) else str(doel)


def maak_beelden(k, map_, naam):
    paden = []
    if len(k["items"]) > 1:
        # voorblad met een vaste stadsfoto, zodat de eerste foto niet twee keer achter elkaar komt
        voorblad = {"titel": k["titel"], "sub": k["periode"], "foto": VOORBLAD[datetime.date.fromisoformat(naam[:10]).toordinal() % len(VOORBLAD)
                                                                             if re.match(r"\d{4}-\d\d-\d\d", naam) else 0]}
        paden.append(beeld(voorblad, map_ / ("%s-0.jpg" % naam), k["label"], kop=k["titel"]))
        for i, item in enumerate(k["items"], 1):
            paden.append(beeld(item, map_ / ("%s-%d.jpg" % (naam, i)), "UITGELICHT" if item.get("uitgelicht") else k["label"], nummer=i))
    else:
        paden.append(beeld(k["items"][0], map_ / ("%s-1.jpg" % naam), k["label"]))
    return paden


def maak_story(e, map_, naam, vandaag):
    item = {"titel": e["titel"], "sub": "%s · %s" % (kort(e, vandaag), e["locatie"]), "foto": eigen_foto(e["afbeelding"])}
    return beeld(item, map_ / ("%s-story.jpg" % naam), "VANDAAG", hoogte=STORY_HOOG)


# ---------------------------------------------------------------- tekst

SYSTEEM = """Je schrijft de tekst bij een post op de Facebook- en Instagrampagina van NijmegenOnline, de stadsgids van
Nijmegen (agenda, nieuws, tips, bedrijvengids). Lezers zijn inwoners en bezoekers van Nijmegen en omgeving.

Schrijf in het Nederlands, informeel (je/jij), warm en lokaal, zonder overdrijving of clickbait. 2 tot 4 korte zinnen,
hoogstens 450 tekens. Begin met een zin die nieuwsgierig maakt. Hoogstens 2 emoji, of geen.

Strikte regels:
- Gebruik alleen feiten uit de gegevens hieronder. Verzin niets: geen prijzen, tijden, namen, superlatieven als
  "de beste" of beloften die er niet staan.
- Noem geen datum, tijd, adres of link: die zet het script er zelf onder.
- Geen hashtags in de tekst; geef die apart (2 of 3, kleine letters, zonder #, passend bij het onderwerp, niet
  "nijmegen" of "nijmegenonline": die staan er al).
- Bij een advertentie (betaald: ja) schrijf je neutraal en eerlijk over het bedrijf of evenement, niet als eigen
  aanbeveling van de redactie.
- Bij een carrousel met meerdere evenementen schrijf je alleen een inleiding; de lijst zet het script eronder."""

TEKST_SCHEMA = {"type": "object", "additionalProperties": False, "required": ["tekst", "hashtags"],
                "properties": {"tekst": {"type": "string"}, "hashtags": {"type": "array", "items": {"type": "string"}}}}

SJABLONEN = {"week": "Zin om er deze week op uit te gaan? Dit staat er in Nijmegen en omgeving op de agenda.",
             "weekend": "Nog geen plannen voor het weekend? Een paar tips uit onze agenda.",
             "vandaag": "Vandaag in Nijmegen en omgeving, voor wie nog iets leuks zoekt."}


def getallen(tekst):
    return set(re.findall(r"\d+", tekst))


def controleer(tekst, bron):
    """Geeft een reden als de tekst niet door de controle komt, anders None."""
    if not 40 <= len(tekst) <= 600:
        return "lengte %d" % len(tekst)
    if re.search(r"https?://|www\.|\.nl\b|#\w", tekst):
        return "link of hashtag in de tekst"
    vreemd = getallen(tekst) - getallen(json.dumps(bron, ensure_ascii=False))
    if vreemd:
        return "getallen die niet in de bron staan: %s" % ", ".join(sorted(vreemd))
    return None


def sjabloon(k):
    if k["soort"] in SJABLONEN:
        return SJABLONEN[k["soort"]]
    b = k["bron"]
    tekst = b.get("samenvatting") or b.get("beschrijving") or b.get("omschrijving") or b.get("tekst") or k["titel"]
    return samenvatting("<p>%s</p>" % esc(tekst), 300)


def schrijf_tekst(k):
    """(tekst, hashtags, door) met Claude, of met een vaste tekst als Claude er niet is of de controle faalt."""
    sleutel = os.environ.get("ANTHROPIC_API_KEY")
    if sleutel:
        import anthropic
        client = anthropic.Anthropic()
        bericht = "Soort post: %s\nBetaald: %s\n\nGegevens:\n%s" % (
            k["soort"], "ja" if k["betaald"] else "nee", json.dumps(k["bron"], ensure_ascii=False, indent=1))
        for poging in range(2):
            try:
                r = client.messages.create(
                    model=MODEL, max_tokens=1500,
                    system=[{"type": "text", "text": SYSTEEM, "cache_control": {"type": "ephemeral"}}],
                    messages=[{"role": "user", "content": bericht}],
                    output_config={"effort": "low", "format": {"type": "json_schema", "schema": TEKST_SCHEMA}})
                uit = json.loads(next(b.text for b in r.content if b.type == "text"))
            except Exception as fout:   # noqa: BLE001  Claude is een extraatje: zonder gaat de post gewoon door
                print("social: Claude gaf een fout (%s), vaste tekst" % fout)
                break
            reden = controleer(uit["tekst"].strip(), k["bron"])
            if not reden:
                tags = [re.sub(r"[^a-z0-9]", "", t.lower()) for t in uit.get("hashtags", [])]
                return uit["tekst"].strip(), [t for t in tags if 2 < len(t) <= 25][:3], "claude"
            print("social: tekst afgekeurd (%s)%s" % (reden, ", nog een keer" if poging == 0 else ", vaste tekst"))
            bericht += "\n\nJe vorige tekst werd afgekeurd: %s. Houd je aan de regels." % reden
    return sjabloon(k), [], "sjabloon"


def bijschriften(k, tekst, tags, inst):
    kop = "Advertentie\n\n" if k["betaald"] else ""
    feiten = "\n".join(k["feiten"])
    fb = kop + tekst + ("\n\n" + feiten if feiten else "") + "\n\n👉 " + k["link"]
    naam = "\n\n📸 @%s" % k["instagram_naam"] if k.get("instagram_naam") else ""
    alle = list(dict.fromkeys(inst.get("hashtags", []) + tags))
    ig = (kop + tekst + ("\n\n" + feiten if feiten else "") + naam + "\n\nMeer info via de link in onze bio."
          + "\n\n" + " ".join("#" + t for t in alle))
    return fb, ig[:2200]


# ---------------------------------------------------------------- voorbereiden

def plan_maken(vandaag, log, inst, url, map_, naam):
    k = kies(vandaag, log, inst, url)
    if not k:
        return None
    beelden = maak_beelden(k, map_, naam)
    tekst, tags, door = schrijf_tekst(k)
    fb, ig = bijschriften(k, tekst, tags, inst)
    plan = {"datum": vandaag.isoformat(), "soort": k["soort"], "betaald": k["betaald"], "sleutels": k["sleutels"],
            "titel": k["titel"], "link": k["link"], "beelden": beelden, "story": None, "facebook": fb, "instagram": ig,
            "tekst_door": door, "status": "gepland"}
    e = story_vandaag(vandaag, log)
    if e:
        plan["story"], plan["story_sleutel"] = maak_story(e, map_, naam, vandaag), "story:" + e["slug"]
    return plan


def voorbereiden(vandaag):
    inst, log = instellingen(), geplaatst()
    url = basis()
    gepland = lees(GEPLAND, {})
    if gepland.get(vandaag.isoformat(), {}).get("status") == "geplaatst":
        print("social: post van %s staat al online" % vandaag)
        return
    plan = plan_maken(vandaag, log, inst, url, BEELDEN, vandaag.isoformat())
    grens = (vandaag - datetime.timedelta(days=14)).isoformat()
    gepland = {d: p for d, p in gepland.items() if d >= grens}
    if plan:
        gepland[vandaag.isoformat()] = plan
        print("social: %s, %s: %s (%s, tekst door %s)" % (vandaag, plan["soort"], plan["titel"],
                                                          "betaald" if plan["betaald"] else "gratis", plan["tekst_door"]))
    else:
        print("social: niets te posten op %s" % vandaag)
    schrijf(GEPLAND, gepland)
    opruimen(vandaag, gepland)
    linkpagina(vandaag, log, gepland)


def opruimen(vandaag, gepland):
    houden = {b for p in gepland.values() for b in p.get("beelden", []) + [p.get("story")] if b}
    houden |= {b for p in geplaatst()[-30:] for b in p.get("beelden", [])}
    grens = vandaag - datetime.timedelta(days=BEWAAR_BEELDEN)
    for f in BEELDEN.glob("*.jpg") if BEELDEN.is_dir() else []:
        try:
            datum = datetime.date.fromisoformat(f.name[:10])
        except ValueError:
            continue
        if datum < grens and f.relative_to(ROOT).as_posix() not in houden:
            f.unlink()


def linkpagina(vandaag, log, gepland):
    """/social/: de link in de Instagram-bio, met de posts van de afgelopen weken."""
    posts = [p for p in log if p.get("status") == "geplaatst"]
    vandaag_plan = gepland.get(vandaag.isoformat())
    if vandaag_plan and vandaag_plan["status"] == "gepland":
        posts.append(vandaag_plan)
    posts = sorted(posts, key=lambda p: p["datum"], reverse=True)[:18]
    kaarten = []
    for p in posts:
        d = datetime.date.fromisoformat(p["datum"])
        link = p["link"].replace(basis(), "").replace(SITE, "")
        kaarten.append('          <article class="kaart"><a href="..%s"><img src="../%s" alt="%s" loading="lazy">'
                       '<div class="kaart__tekst"><div class="label">%s%d %s</div><h3>%s</h3></div></a></article>'
                       % (esc(link), esc(p["beelden"][0]), esc(p["titel"]), "Advertentie · " if p.get("betaald") else "",
                          d.day, MAANDEN[d.month - 1], esc(p["titel"])))
    inhoud = """
  <main class="artikel-wrap">
    <div class="container">
      <div class="kruimelpad"><a href="../">Home</a> › Social media</div>
      <header class="rubriek-kop">
        <h1>Van onze Facebook en Instagram</h1>
        <p>Hier vind je de links uit onze posts op Instagram en Facebook. Meer te doen? Kijk in de <a href="../nijmegen-evenementen-overzicht/">agenda</a> of lees het
        <a href="../nieuwsberichten/">nieuws</a>.</p>
      </header>
      <section class="gids-sectie">
        <div class="raster">
%s
        </div>
      </section>
    </div>
  </main>
""" % "\n".join(kaarten)
    pagina = kop("Van onze Facebook en Instagram", "De links uit de posts van NijmegenOnline op Facebook en Instagram: "
                 "agenda, nieuws en tips voor Nijmegen.", SITE + "/social/", "../",
                 # wisselt elke dag en heeft geen eigen inhoud: niet in Google en niet in de sitemap
                 extra='\n  <meta name="robots" content="noindex">') + inhoud + VOET
    (ROOT / PAGINA).mkdir(exist_ok=True)
    (ROOT / PAGINA / "index.html").write_text(pagina, encoding="utf-8")


# ---------------------------------------------------------------- GitHub-issue (controleperiode)

def github(methode, pad, data=None):
    import requests
    r = requests.request(methode, "https://api.github.com/repos/%s%s" % (os.environ["GITHUB_REPOSITORY"], pad),
                         headers={"Authorization": "Bearer " + os.environ["GITHUB_TOKEN"],
                                  "Accept": "application/vnd.github+json"}, json=data, timeout=30)
    r.raise_for_status()
    return r.json() if r.text else {}


def in_controle(inst, log):
    return sum(1 for p in log if p.get("status") == "geplaatst") < inst.get("controle_posts", 0)


def melden(vandaag):
    inst, log = instellingen(), geplaatst()
    gepland = lees(GEPLAND, {})
    plan = gepland.get(vandaag.isoformat())
    if not inst.get("aan") or not plan or plan["status"] != "gepland" or not in_controle(inst, log) or plan.get("issue"):
        return
    if not os.environ.get("GITHUB_TOKEN"):
        print("social: geen GITHUB_TOKEN, geen issue")
        return
    ruw = "https://raw.githubusercontent.com/%s/main/" % os.environ["GITHUB_REPOSITORY"]
    plaatjes = " ".join('<img src="%s%s" width="220">' % (ruw, b) for b in plan["beelden"])
    tekst = ("@itandleisure, dit gaat vandaag rond het middaguur op Facebook en Instagram%s.\n\n"
             "**Niets doen = plaatsen.** Wil je deze post niet? Sluit dit issue, dan wordt hij overgeslagen.\n\n%s\n\n"
             "### Facebook\n\n```text\n%s\n```\n\n### Instagram\n\n```text\n%s\n```\n\n"
             "_Controleperiode: nog %d posts met een issue (instelling controle_posts in data/social-instellingen.json)._"
             % (" (betaald)" if plan["betaald"] else "", plaatjes, plan["facebook"], plan["instagram"],
                inst.get("controle_posts", 0) - sum(1 for p in log if p.get("status") == "geplaatst")))
    issue = github("POST", "/issues", {"title": "Social %s: %s" % (vandaag, plan["titel"]), "body": tekst})
    plan["issue"] = issue["number"]
    schrijf(GEPLAND, gepland)
    print("social: issue #%d gemaakt" % issue["number"])


# ---------------------------------------------------------------- plaatsen (Meta Graph API)

class Meta:
    def __init__(self):
        import requests
        self.s = requests.Session()
        token = os.environ["META_TOKEN"]
        pagina = os.environ.get("META_PAGE_ID")
        if not pagina:
            paginas = self.vraag("GET", "/me/accounts", access_token=token, fields="id,name").get("data", [])
            pagina = paginas[0]["id"] if paginas else self.vraag("GET", "/me", access_token=token, fields="id")["id"]
        info = self.vraag("GET", "/" + pagina, access_token=token, fields="access_token,instagram_business_account,name")
        self.pagina = pagina
        self.token = info.get("access_token", token)
        self.ig = (info.get("instagram_business_account") or {}).get("id")
        print("social: pagina %s, Instagram %s" % (info.get("name", pagina), self.ig or "niet gekoppeld"))

    def vraag(self, methode, pad, **params):
        r = self.s.request(methode, GRAPH + pad, data=params if methode != "GET" else None,
                           params=params if methode == "GET" else None, timeout=60)
        if r.status_code >= 400:
            raise RuntimeError("Meta %s %s: %s" % (methode, pad, r.text[:500]))
        return r.json()

    def facebook(self, beelden, tekst):
        if len(beelden) == 1:
            r = self.vraag("POST", "/%s/photos" % self.pagina, url=beelden[0], caption=tekst, access_token=self.token)
            return r.get("post_id") or r["id"]
        media = [self.vraag("POST", "/%s/photos" % self.pagina, url=b, published="false", access_token=self.token)["id"]
                 for b in beelden]
        params = {"message": tekst, "access_token": self.token}
        for i, m in enumerate(media):
            params["attached_media[%d]" % i] = json.dumps({"media_fbid": m})
        return self.vraag("POST", "/%s/feed" % self.pagina, **params)["id"]

    def wacht(self, container):
        for _ in range(30):
            status = self.vraag("GET", "/" + container, fields="status_code", access_token=self.token).get("status_code")
            if status == "FINISHED":
                return
            if status in ("ERROR", "EXPIRED"):
                raise RuntimeError("Instagram kon het beeld niet verwerken (%s)" % status)
            time.sleep(5)
        raise RuntimeError("Instagram bleef bezig met verwerken")

    def instagram(self, beelden, tekst, story=False):
        if story:
            c = self.vraag("POST", "/%s/media" % self.ig, image_url=beelden[0], media_type="STORIES", access_token=self.token)["id"]
        elif len(beelden) == 1:
            c = self.vraag("POST", "/%s/media" % self.ig, image_url=beelden[0], caption=tekst, access_token=self.token)["id"]
        else:
            kinderen = [self.vraag("POST", "/%s/media" % self.ig, image_url=b, is_carousel_item="true",
                                   access_token=self.token)["id"] for b in beelden]
            for kind in kinderen:
                self.wacht(kind)
            c = self.vraag("POST", "/%s/media" % self.ig, media_type="CAROUSEL", children=",".join(kinderen), caption=tekst,
                           access_token=self.token)["id"]
        self.wacht(c)
        media = self.vraag("POST", "/%s/media_publish" % self.ig, creation_id=c, access_token=self.token)["id"]
        link = self.vraag("GET", "/" + media, fields="permalink", access_token=self.token).get("permalink")
        return media, link

    def verwijder(self, id_):
        self.vraag("DELETE", "/" + id_, access_token=self.token)


def bereikbaar(url):
    import requests
    for _ in range(20):
        try:
            if requests.head(url, timeout=20).status_code == 200:
                return True
        except requests.RequestException:
            pass
        time.sleep(30)
    return False


def plaatsen(vandaag):
    inst, log = instellingen(), geplaatst()
    gepland = lees(GEPLAND, {})
    plan = gepland.get(vandaag.isoformat())
    if not os.environ.get("META_TOKEN"):
        if not inst.get("aan"):
            print("social: staat uit (aan: false in data/social-instellingen.json)")
            return
        print("::error::Het secret META_TOKEN ontbreekt, zie docs/social-media-koppelen.md")
        sys.exit(1)
    meta = Meta()   # ook als hij uit staat: zo test je de koppeling met Run workflow > plaatsen
    if not inst.get("aan"):
        print("social: koppeling werkt, maar plaatsen staat uit (aan: false in data/social-instellingen.json)")
        return
    if not meta.ig and inst.get("instagram", True):
        print("::warning::Geen Instagram-bedrijfsaccount gekoppeld aan de Facebookpagina; alleen Facebook")
    weghalen(meta, log)
    if not plan or plan["status"] != "gepland":
        print("social: geen post klaar voor %s" % vandaag)
        schrijf(GEPLAATST, log)
        return
    if plan.get("issue") and os.environ.get("GITHUB_TOKEN"):
        issue = github("GET", "/issues/%d" % plan["issue"])
        if issue["state"] == "closed":
            plan["status"] = "overgeslagen"
            print("social: issue #%d is gesloten, post overgeslagen" % plan["issue"])
            schrijf(GEPLAND, gepland)
            return
    elif in_controle(inst, log):
        print("social: controleperiode maar geen issue gevonden, voor de zekerheid niet geplaatst")
        return
    url = basis()
    beelden = ["%s/%s" % (url, b) for b in plan["beelden"]]
    if not all(bereikbaar(b) for b in beelden):
        raise SystemExit("social: beelden nog niet online op %s" % url)
    fouten = []
    if inst.get("facebook", True):
        try:
            plan["facebook_id"] = meta.facebook(beelden, plan["facebook"])
        except RuntimeError as fout:
            fouten.append(str(fout))
    if inst.get("instagram", True) and meta.ig:
        try:
            plan["instagram_id"], plan["instagram_link"] = meta.instagram(beelden, plan["instagram"])
            if plan.get("story") and bereikbaar("%s/%s" % (url, plan["story"])):
                plan["story_id"] = meta.instagram(["%s/%s" % (url, plan["story"])], "", story=True)[0]
        except RuntimeError as fout:
            fouten.append(str(fout))
    plan["status"] = "geplaatst" if (plan.get("facebook_id") or plan.get("instagram_id")) else "fout"
    plan["fouten"] = fouten
    log.append({k: plan.get(k) for k in ("datum", "soort", "betaald", "sleutels", "titel", "link", "beelden", "tekst_door",
                                         "facebook_id", "instagram_id", "instagram_link", "story_sleutel", "story_id",
                                         "status")})
    schrijf(GEPLAATST, log)
    schrijf(GEPLAND, gepland)
    if plan.get("issue") and os.environ.get("GITHUB_TOKEN"):
        regels_ = ["Geplaatst."] if plan["status"] == "geplaatst" else ["Plaatsen mislukt."]
        if plan.get("facebook_id"):
            regels_.append("- Facebook: https://www.facebook.com/%s" % plan["facebook_id"])
        if plan.get("instagram_link"):
            regels_.append("- Instagram: %s" % plan["instagram_link"])
        regels_ += ["- Fout: %s" % f for f in fouten]
        github("POST", "/issues/%d/comments" % plan["issue"], {"body": "\n".join(regels_)})
        if plan["status"] == "geplaatst":
            github("PATCH", "/issues/%d" % plan["issue"], {"state": "closed", "state_reason": "completed"})
    print("social: %s, %s" % (plan["status"], "; ".join(fouten) or "geen fouten"))
    if fouten:
        sys.exit(1)


def weghalen(meta, log):
    """Posts over een evenement dat van de site is gehaald (data/evenementen-verwijderd.txt) ook offline halen."""
    pad = DATA / "evenementen-verwijderd.txt"
    weg = set(pad.read_text(encoding="utf-8").split()) if pad.is_file() else set()
    for p in log:
        if p.get("status") != "geplaatst" or p.get("verwijderd") or p.get("soort") != "evenement":
            continue
        slug = p["sleutels"][0].split(":", 1)[1]
        if slug not in weg:
            continue
        for veld in ("facebook_id", "instagram_id", "story_id"):
            if p.get(veld):
                try:
                    meta.verwijder(p[veld])
                except RuntimeError as fout:
                    print("::warning::%s niet verwijderd (%s), haal hem met de hand weg" % (veld, fout))
        p["verwijderd"] = datetime.date.today().isoformat()
        print("social: post over %s weggehaald (evenement verwijderd)" % slug)


# ---------------------------------------------------------------- voorbeeld

def voorbeeld(van, dagen, map_):
    """Een paar dagen vooruit, alsof elke post geplaatst wordt; niets wordt bewaard."""
    inst, log = instellingen(), [dict(p) for p in geplaatst()]
    url = basis()
    if map_.exists():
        shutil.rmtree(map_)
    map_.mkdir(parents=True)
    blokken = []
    for i in range(dagen):
        d = van + datetime.timedelta(days=i)
        plan = plan_maken(d, log, inst, url, map_, d.isoformat())
        if not plan:
            blokken.append("<h2>%s %s</h2><p>Niets te posten.</p>" % (DAGEN[d.weekday()], d))
            continue
        plan["status"], plan["story_id"] = "geplaatst", "voorbeeld" if plan["story"] else None
        log.append(plan)
        plaatjes = "".join('<img src="%s">' % pathlib.Path(b).name for b in plan["beelden"] + ([plan["story"]] if plan["story"] else []))
        blokken.append('<h2>%s %d %s: %s%s</h2><div class="beelden">%s</div><div class="teksten"><div><h3>Facebook</h3><pre>%s</pre></div>'
                       '<div><h3>Instagram</h3><pre>%s</pre></div></div><p class="klein">tekst door %s</p>'
                       % (DAGEN[d.weekday()].capitalize(), d.day, MAANDEN[d.month - 1], esc(plan["soort"]),
                          " (betaald)" if plan["betaald"] else "", plaatjes, esc(plan["facebook"]), esc(plan["instagram"]),
                          plan["tekst_door"]))
    (map_ / "index.html").write_text(
        "<!doctype html><meta charset='utf-8'><title>Voorbeeld social media</title><style>body{font-family:system-ui;"
        "max-width:1100px;margin:2em auto;padding:0 1em}.beelden{display:flex;gap:8px;overflow-x:auto}.beelden img{height:340px}"
        ".teksten{display:grid;grid-template-columns:1fr 1fr;gap:16px}pre{white-space:pre-wrap;background:#f3f5f7;padding:12px;"
        "font-family:inherit}.klein{color:#666;font-size:.85em}h2{margin-top:2.5em}</style><h1>Voorbeeld: %d dagen vanaf %s</h1>%s"
        % (dagen, van, "".join(blokken)), encoding="utf-8")
    print("social: voorbeeld in %s" % map_)


if __name__ == "__main__":
    args = sys.argv[1:]
    stap = args[0] if args else ""
    datum = (datetime.date.fromisoformat(args[args.index("--datum") + 1]) if "--datum" in args
             else datetime.datetime.now(AMSTERDAM).date())
    if stap == "voorbereiden":
        voorbereiden(datum)
    elif stap == "melden":
        melden(datum)
    elif stap == "plaatsen":
        plaatsen(datum)
    elif stap == "voorbeeld":
        aantal = int(args[args.index("--dagen") + 1]) if "--dagen" in args else 7
        doel = pathlib.Path(args[args.index("--map") + 1]) if "--map" in args else ROOT / "_voorbeeld-social"
        voorbeeld(datum, aantal, doel.resolve())
    else:
        print(__doc__)
        sys.exit(2)
