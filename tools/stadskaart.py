"""Kaart van de stad: /kaart-nijmegen/.

Een kaart voor bezoekers met bezienswaardigheden, parken, parkeergarages, musea, podia en hotels, met knoppen om groepen
aan en uit te zetten. Gebruikt dezelfde kaart als de bedrijvengids (assets/js/kaart.js, Leaflet met OpenStreetMap).
Bezienswaardigheden, parken en parkeergarages staan hieronder (coördinaten uit OpenStreetMap, november 2026); musea,
podia en hotels komen uit de bedrijvengids (data/bedrijvengids.json), zodat nieuwe bedrijven vanzelf op de kaart komen.

Gebruik: python tools/stadskaart.py   (daarna tools/build.py en tools/zoekindex.py)
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from import_wordpress import SITE, VOET, esc, kop  # noqa: E402
import gidsiconen  # noqa: E402
from bedrijvengids import LEAFLET, adresregel  # noqa: E402

SLUG = "kaart-nijmegen"

# Eigen iconen (lijnen, 24x24, net als tools/gidsiconen.py)
ICONEN = {
    "bezienswaardigheid": '<path d="M12 3l2.6 5.6 6 .7-4.5 4.1 1.2 6L12 16.4 6.7 19.4l1.2-6L3.4 9.3l6-.7z"/>',
    "park": '<path d="M12 22v-6M7 16h10l-3-4h2l-4-5-4 5h2z"/><path d="M12 7V3"/>',
    "parkeren": '<rect x="4" y="3" width="16" height="18" rx="3"/><path d="M10 17V7h3a3 3 0 0 1 0 6h-3"/>',
    "station": '<rect x="6" y="3" width="12" height="14" rx="3"/><path d="M6 11h12M9 21l1.5-4M15 21l-1.5-4M9 14h.01M15 14h.01"/>',
}

# (naam, lat, lon, pagina op de site, korte regel)
EIGEN = {
    "Bezienswaardigheden": [
        ("Valkhof", 51.847794, 5.870265, "/valkhof-nijmegen/", "Valkhofpark met de Sint-Nicolaaskapel en de Barbarossaruïne", "bezienswaardigheid"),
        ("Stevenskerk", 51.847988, 5.862781, "/stevenskerk-nijmegen/", "Grote of Sint-Stevenskerk", "bezienswaardigheid"),
        ("Grote Markt", 51.847372, 5.864194, "/markten-nijmegen/", "Het plein in het hart van de oude stad, met de weekmarkt", "bezienswaardigheid"),
        ("Waalkade", 51.849962, 5.863691, "/waalkade-nijmegen/", "Terrassen, Velorama en De Bastei aan de Waal", "bezienswaardigheid"),
        ("Waalbrug", 51.851512, 5.871186, "/verhaal-van-nijmegen/#oorlog", "De brug uit 1936, bekend van Market Garden", "bezienswaardigheid"),
        ("Lange Hezelstraat", 51.848480, 5.856172, "/thema/winkelen-in-nijmegen/", "Oude winkelstraat met speciaalzaken", "bezienswaardigheid"),
        ("Snelbinder", 51.853658, 5.857566, "/routes-nijmegen/#stad", "Fietsbrug naast de spoorbrug over de Waal", "bezienswaardigheid"),
    ],
    "Parken en natuur": [
        ("Kronenburgerpark", 51.846373, 5.857490, "/kronenburgerpark-nijmegen/", "Stadspark met de Kruittoren", "park"),
        ("Hunnerpark", 51.847126, 5.872083, "/valkhof-nijmegen/", "Park bij de Waalbrug", "park"),
        ("Goffertpark", 51.824041, 5.835671, "/goffertpark-nijmegen/", "Groot park met openluchttheater", "park"),
        ("Museumpark Orientalis", 51.817392, 5.895929, "/museumpark-orientalis/", "Openluchtmuseum in Heilig Landstichting", "park"),
        ("Heumensoord", 51.797577, 5.866299, "/heumensoord/", "Bos en heide ten zuiden van de stad", "park"),
    ],
    "Parkeren en station": [
        ("Station Nijmegen", 51.843136, 5.853091, "/station-nijmegen/", "Stationsplein", "station"),
        ("Parkeergarage Keizer Karel", 51.842400, 5.856341, "/parkeergarage-keizer-karel-nijmegen/", "Bij het Keizer Karelplein", "parkeren"),
        ("Parkeergarage Mariënburg", 51.844500, 5.866800, "/parkeergarage-marienburg-nijmegen/", "Midden in het centrum, bij LUX", "parkeren"),
        ("Parkeergarage Eiermarkt", 51.847548, 5.866871, "/parkeergarage-eiermarkt-nijmegen/", "Bij de Grote Markt", "parkeren"),
        ("Parkeergarage Kelfkensbos", 51.846546, 5.870101, "/parkeergarage-kelfkensbos-nijmegen/", "Bij het Valkhof", "parkeren"),
    ],
}

# Groepen uit de bedrijvengids: (naam op de kaart, categorieën)
GIDS = [("Musea", ["musea"]), ("Theater, muziek en film", ["podia", "bioscoop"]), ("Overnachten", ["hotel"])]


def punten(root):
    groepen, lijst = [], []
    for groep, rijen in EIGEN.items():
        groepen.append(groep)
        lijst += [[naam, lat, lon, root + pad.lstrip("/"), regel, groep, cat] for naam, lat, lon, pad, regel, cat in rijen]
    gids = json.load(open(ROOT / "data" / "bedrijvengids.json", encoding="utf-8"))
    gezien = set()
    for groep, cats in GIDS:
        n = 0
        for cat in cats:
            for b in gids.get(cat, {}).get("gids", []) + gids.get(cat, {}).get("overig", []):
                if not b.get("lat") or b["slug"] in gezien:
                    continue
                lat, lon = round(float(b["lat"]), 6), round(float(b["lon"]), 6)
                if not (51.74 < lat < 51.90 and 5.70 < lon < 6.00):   # alleen Nijmegen en de directe omgeving
                    continue
                gezien.add(b["slug"])
                lijst.append([b["naam"], lat, lon, "%sbedrijvengids/%s/" % (root, b["slug"]), adresregel(b), groep, cat])
                n += 1
        if n:
            groepen.append(groep)
    return groepen, lijst


def pagina():
    root = "../"
    canonical = "%s/%s/" % (SITE, SLUG)
    groepen, lijst = punten(root)
    iconen = dict(ICONEN)
    iconen.update({c: gidsiconen.inhoud(c) for _, cats in GIDS for c in cats})
    eerste = {g: (lijst[[p[5] for p in lijst].index(g)][6]) for g in groepen}
    iconen.update({"groep:" + g: iconen.get(eerste[g]) or gidsiconen.STANDAARD for g in groepen})
    data = json.dumps({"groepen": groepen, "punten": lijst, "iconen": iconen, "allesAan": True}, ensure_ascii=False).replace("</", "<\\/")
    ld = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "Home", "item": SITE + "/"},
        {"@type": "ListItem", "position": 2, "name": "Plan je bezoek", "item": SITE + "/plan-je-bezoek/"},
        {"@type": "ListItem", "position": 3, "name": "Kaart", "item": canonical}]}
    extra = LEAFLET + '\n  <script type="application/ld+json">%s</script>' % json.dumps(ld, ensure_ascii=False)
    out = [kop("Kaart van Nijmegen: bezienswaardigheden, musea en parkeren",
               "Kaart van Nijmegen voor bezoekers: bezienswaardigheden, parken, musea, theaters, hotels, parkeergarages en het station.",
               canonical, root, None, extra)]
    out.append('  <main class="artikel-wrap">\n    <div class="container">')
    out.append('      <div class="kruimelpad"><a href="../">Home</a> › <a href="../plan-je-bezoek/">Plan je bezoek</a> › Kaart</div>')
    out.append('      <header class="rubriek-kop">\n        <h1>Kaart van Nijmegen</h1>\n'
               '        <p>Alles wat je als bezoeker wilt vinden op één kaart: bezienswaardigheden, parken, musea, theaters, hotels, '
               'parkeergarages en het station. Zet met de knoppen groepen aan of uit en klik op een punt voor meer informatie.</p>\n      </header>')
    out.append('      <div id="kaartgroepen" class="kaartgroepen"></div>')
    out.append('      <div id="gidskaart" class="gidskaart stadskaart" role="region" aria-label="Kaart van Nijmegen"></div>')
    out.append('      <script type="application/json" id="kaartdata">%s</script>' % data)
    out.append('      <script src="../assets/js/kaart.js?v=11" defer></script>')
    # Ook zonder kaart (of met een schermlezer) bruikbaar: dezelfde plekken als lijst
    out.append('      <section class="stadskaart-lijst">\n        <h2>Alle plekken op de kaart</h2>')
    for g in groepen:
        out.append('        <h3>%s</h3>\n        <ul>%s</ul>' % (esc(g), "".join(
            '<li><a href="%s">%s</a> <span>%s</span></li>' % (esc(p[3]), esc(p[0]), esc(p[4])) for p in lijst if p[5] == g)))
    out.append("      </section>")
    out.append("    </div>\n  </main>")
    out.append(VOET)
    return "\n".join(out)


def main():
    d = ROOT / SLUG
    d.mkdir(exist_ok=True)
    (d / "index.html").write_text(pagina(), encoding="utf-8")
    print("Gemaakt: %s/" % SLUG)


if __name__ == "__main__":
    main()
