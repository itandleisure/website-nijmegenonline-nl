"""Maakt het overzicht van alle restaurants voor de gids /thema/restaurants-in-nijmegen-restaurant/.

De gids bundelde alleen artikelen. Wie op "restaurant nijmegen" zoekt, wil een lijst met restaurants. Dit script zet de
restaurants uit data/bedrijvengids.json (categorie restaurant, gids + overig) op een rij: per keuken, per buurt en van
A tot Z. Elke naam linkt naar de bedrijfspagina, elke keuken naar de gids over die keuken.

Het blok komt in data/gidsblokken/restaurants.html. import_wordpress.gids_pagina() zet het in de gids als die in
data/gidsen.json een veld "blok" heeft. Daarna: python tools/gidsen_bouwen.py /thema/restaurants-in-nijmegen-restaurant/
en python tools/build.py.

Gebruik: python tools/restaurantoverzicht.py
"""
import html
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
SITE = "https://www.nijmegenonline.nl"
DOEL = ROOT / "data" / "gidsblokken" / "restaurants.html"
PAGINA = "/thema/restaurants-in-nijmegen-restaurant/"
R = "../../"  # van /thema/<gids>/ naar de hoofdmap

# Keuken uit de bedrijvengids -> (kop, korte tekst, gids over die keuken)
KEUKENS = [
    ("Italiaans", "Italiaanse restaurants", "Pasta, pizza uit de houtoven en antipasti. Italiaans is de grootste keuken van Nijmegen.",
     "culinair-genieten-in-italiaanse-sfeer-probeer-deze-restaurants-in-nijmegen"),
    ("Japans", "Japanse restaurants en sushi", "Sushi aan tafel, all you can eat in rondes of ramen.",
     "sushi-in-nijmegen-afhalen-bezorgen-of-aan-tafel"),
    ("Aziatisch", "Aziatische restaurants", "Wok, dim sum en gerechten uit heel Azië onder één dak.",
     "geniet-van-deze-aziatische-hoogstandjes-in-nijmegen"),
    ("Chinees", "Chinese restaurants", "Van de klassieke Chinees-Indische kaart tot authentiek Chinees.",
     "chinees-in-nijmegen-afhalen-of-uit-eten"),
    ("Thais", "Thaise restaurants", "Curry's, pad thai en soepen met citroengras.",
     "thais-eten-in-nijmegen-onze-top-3-thaise-restaurants"),
    ("Indonesisch", "Indonesische restaurants", "Rijsttafel, rendang en saté.",
     "indonesisch-eten-in-nijmegen-rijsttafel"),
    ("Vietnamees", "Vietnamese en Koreaanse restaurants", "Pho, banh mi en Koreaanse barbecue.",
     "surinaams-vietnamees-en-koreaans-eten-in-nijmegen"),
    ("Indiaas", "Indiase restaurants", "Curry's, tandoori en veel vegetarische gerechten.",
     "indias-culinaire-parels-toprestaurants-in-nijmegen"),
    ("Turks", "Turkse restaurants", "Grill, meze en pide.",
     "heerlijke-turkse-specialiteiten-in-nijmegen"),
    ("Midden-Oosters", "Libanese en Midden-Oosterse restaurants", "Mezze, falafel en gerechten van de grill.",
     "op-zoek-naar-een-nieuwe-culinaire-belevenis-probeer-libanees-eten-in-nijmegen"),
    ("Grieks", "Griekse restaurants", "Gyros, souvlaki en meze, vaak met een ouzo van het huis.",
     "op-culinaire-ontdekkingsreis-probeer-deze-griekse-restaurants-in-nijmegen"),
    ("Spaans", "Spaanse restaurants en tapas", "Tapas om te delen, paella en Spaanse wijn.",
     "tapas-in-nijmegen-onze-3-favorieten"),
    ("Mediterraan", "Mediterrane restaurants", "Gerechten uit de landen rond de Middellandse Zee.", None),
    ("Frans", "Franse restaurants", "Klassieke Franse keuken en fine dining.",
     "ontdek-de-franse-keuken-in-nijmegen"),
    ("Mexicaans", "Mexicaanse restaurants", "Taco's, burrito's en margarita's.",
     "mexicaans-genieten-in-nijmegen-dit-zijn-de-beste-adresjes"),
    ("Steakhouse", "Steakhouses en burgers", "Steaks, spareribs en burgers.",
     "steak-spareribs-en-burgers-in-nijmegen"),
    ("Hollands", "Hollandse restaurants", "Stamppot, schnitzels en de Hollandse pot.",
     "geniet-van-de-hollandse-pot-in-deze-nederlandse-restaurants-in-nijmegen"),
    ("Surinaams", "Surinaamse en Caribische restaurants", "Roti, broodje pom en moksi meti.",
     "surinaams-vietnamees-en-koreaans-eten-in-nijmegen"),
    ("Vegetarisch", "Vegetarische en vegan restaurants", "Restaurants waar groente de hoofdrol speelt.",
     "waar-kun-je-het-best-vegan-uit-eten-in-nijmegen"),
    ("Internationaal", "Internationale keuken en brasserieën", "Een kaart met gerechten uit verschillende keukens. Fijn als niet iedereen hetzelfde wil.",
     "de-10-beste-restaurants-in-nijmegen-centrum"),
]
# Keukens die samen onder één kop vallen
SAMEN = {"Burgers": "Steakhouse", "Amerikaans": "Steakhouse", "Koreaans": "Vietnamees", "Caribisch": "Surinaams",
         "Europees": "Internationaal", "Marokkaans": "Midden-Oosters", "Afghaans": "Midden-Oosters",
         "Pannenkoeken": "Hollands", "Vis": "Hollands"}

# Eerste vier cijfers van de postcode -> buurt
BUURTEN = [
    ("bottendaal", "Bottendaal en Altrade", "Achter het station en richting het Kronenburgerpark. Rustiger dan de binnenstad, met een paar echte buurtrestaurants.", ["6512"]),
    ("oost", "Nijmegen-Oost", "De Groesbeekseweg, Berg en Dalseweg en Sint Annastraat. Veel kleine restaurants en eetcafés waar vooral Nijmegenaren zelf komen.", ["6515", "6521", "6522", "6523", "6524"]),
    ("zuid", "Nijmegen-Zuid en de campus", "Rond het Goffertpark, de Hatertseweg en de Radboud-campus in Heyendaal.", ["6525", "6531", "6532", "6533", "6534"]),
    ("hatert-dukenburg", "Hatert, Dukenburg en Lindenholt", "Vooral bij de winkelcentra Hatert, Meijhorst, Zwanenveld en Leuvensbroek.", ["6535", "6536", "6537", "6538", "6546"]),
    ("west", "Nijmegen-West", "Hees, Neerbosch, de Wolfskuil en het Waalfront.", ["6541", "6542", "6543", "6544", "6545"]),
    ("noord", "Lent en Oosterhout", "Aan de overkant van de Waal, vaak met uitzicht op de rivier of de stad.", ["6663", "6664", "6665", "6666", "6678", "6681"]),
]


# Opmaak alleen voor deze pagina, zodat site.css (en de versie in elke pagina) niet hoeft te veranderen
STIJL = ("<style>.resto-lijst{list-style:none;padding:0;margin:8px 0 20px;columns:2 240px;column-gap:24px}"
         ".resto-lijst li{break-inside:avoid;padding:6px 0;border-bottom:1px solid #eee}"
         ".resto__straat{color:#666;font-size:.9em}.resto__aantal{color:#888;font-weight:normal;font-size:.85em}"
         ".resto-alles summary{cursor:pointer;font-weight:600;padding:10px 0;min-height:44px}</style>")


def esc(s):
    return html.escape(s or "", quote=True)


def straat(adres):
    """Hoogstraat 3 -> Hoogstraat (zonder huisnummer, voor een korte regel)."""
    return re.sub(r"\s+\d.*$", "", (adres or "").strip())


def restaurants():
    d = json.loads((ROOT / "data" / "bedrijvengids.json").read_text(encoding="utf-8"))
    alle, gezien = [], set()
    for e in d["restaurant"]["gids"] + d["restaurant"]["overig"]:
        slug = e.get("slug")
        if not slug or slug in gezien or not (ROOT / "bedrijvengids" / slug / "index.html").is_file():
            continue
        gezien.add(slug)
        keukens = [k.strip() for k in (e.get("keuken") or "").split(";") if k.strip()]
        keukens = [SAMEN.get(k, k) for k in keukens]
        if not keukens and e.get("in_gids", True) is not False:
            # Bedrijven met een eigen tekst: keuken uit de subcategorieën of de tekst halen
            tekst = (e.get("tekst", "") + " " + " ".join(e.get("categorieen", []))).lower()
            for woord, k in (("indiaas", "Indiaas"), ("italiaans", "Italiaans"), ("steak", "Steakhouse"), ("pizzeria", "Italiaans")):
                if woord in tekst:
                    keukens = [k]
                    break
        alle.append({"slug": slug, "naam": e["naam"].strip(), "adres": (e.get("adres") or "").strip(),
                     "pc": (e.get("postcode") or "")[:4], "plaats": (e.get("plaats") or "").strip(), "keukens": keukens})
    alle.sort(key=lambda x: x["naam"].lower().lstrip("'’ "))
    return alle


def h1(slug):
    """Kop van een artikel, als ankertekst voor de link ernaartoe."""
    m = re.search(r"<h1[^>]*>(.*?)</h1>", (ROOT / slug / "index.html").read_text(encoding="utf-8"), re.S)
    return html.unescape(re.sub(r"<[^>]+>", "", m.group(1))).strip() if m else slug


def link(r, met_straat=True):
    s = '<a href="%sbedrijvengids/%s/">%s</a>' % (R, r["slug"], esc(r["naam"]))
    if met_straat and r["adres"]:
        s += ' <span class="resto__straat">%s</span>' % esc(straat(r["adres"]))
    return s


def lijst(rs, met_straat=True):
    return '<ul class="resto-lijst">%s</ul>' % "".join("<li>%s</li>" % link(r, met_straat) for r in rs)


def buurt_van(r):
    if r["pc"] == "6511" or (not r["pc"] and r["plaats"] in ("Nijmegen", "")):
        return "binnenstad"
    for code, _, _, pcs in BUURTEN:
        if r["pc"] in pcs:
            return code
    if r["plaats"] in ("Lent", "Oosterhout"):
        return "noord"
    return "omgeving"


def maak():
    alle = restaurants()
    n = len(alle)
    binnen = [r for r in alle if buurt_van(r) == "binnenstad"]
    waalkade = [r for r in binnen if re.match(r"(Waalkade|Lage Markt|Veerkade|Steiger|Ubbergseveldweg)", r["adres"])]
    out = []
    out.append('<!-- Gemaakt door tools/restaurantoverzicht.py, niet met de hand aanpassen -->')
    out.append(STIJL)
    out.append('<section class="gids-sectie" id="restaurants-per-keuken">')
    out.append("  <h2>Restaurants in Nijmegen per keuken</h2>")
    out.append('  <div class="inhoud-tekst"><p>In onze bedrijvengids staan %d restaurants in Nijmegen. Hieronder staan ze per keuken, met de straat erbij. '
               'Klik op een naam voor het adres, de openingstijden en de website. Bij elke keuken staat ook onze gids met de adressen die wij aanraden.</p></div>' % n)
    for code, kop, tekst, gids in KEUKENS:
        rs = [r for r in alle if code in r["keukens"]]
        if len(rs) < 2:
            continue
        anker = "keuken-" + re.sub(r"[^a-z]+", "-", code.lower()).strip("-")
        out.append('  <h3 id="%s">%s <span class="resto__aantal">(%d)</span></h3>' % (anker, esc(kop), len(rs)))
        meer = (' Onze tips: <a href="%s%s/">%s</a>.' % (R, gids, esc(h1(gids)))) if gids else ""
        out.append("  <p>%s%s</p>" % (esc(tekst), meer))
        out.append("  " + lijst(rs))
    out.append("</section>")

    out.append('<section class="gids-sectie" id="restaurants-per-buurt">')
    out.append("  <h2>Restaurants per buurt</h2>")
    out.append('  <div class="inhoud-tekst"><p>De meeste restaurants zitten in de binnenstad: %d van de %d. Woon je in een wijk, of wil je juist '
               'buiten de drukte eten? Dan staan hieronder de restaurants per stadsdeel.</p></div>' % (len(binnen), n))
    out.append('  <h3 id="buurt-binnenstad">Binnenstad <span class="resto__aantal">(%d)</span></h3>' % len(binnen))
    out.append('  <p>Rond de Grote Markt, de Lange Hezelstraat, de Molenstraat, het Kelfkensbos en Plein 1944. In de '
               '<a href="%sde-10-beste-restaurants-in-nijmegen-centrum/">10 beste restaurants in het centrum</a> staan onze favorieten. '
               'Alle restaurants in de binnenstad staan hierboven per keuken en hieronder van A tot Z.</p>' % R)
    if waalkade:
        out.append('  <h3 id="buurt-waalkade">Aan de Waalkade <span class="resto__aantal">(%d)</span></h3>' % len(waalkade))
        out.append('  <p>Eten met uitzicht op de Waal en de Waalbrug. In de zomer zitten de terrassen hier vol. Meer over de kade lees je op '
                   '<a href="%swaalkade-nijmegen/">de Waalkade in Nijmegen</a>.</p>' % R)
        out.append("  " + lijst(waalkade))
    for code, kop, tekst, _ in BUURTEN:
        rs = [r for r in alle if buurt_van(r) == code]
        if not rs:
            continue
        out.append('  <h3 id="buurt-%s">%s <span class="resto__aantal">(%d)</span></h3>' % (code, esc(kop), len(rs)))
        out.append("  <p>%s</p>" % esc(tekst))
        out.append("  " + lijst(rs))
    out.append("</section>")

    out.append('<section class="gids-sectie" id="alle-restaurants">')
    out.append("  <h2>Alle restaurants in Nijmegen van A tot Z</h2>")
    out.append('  <div class="inhoud-tekst"><p>Zoek je een bepaald restaurant? Hier staan ze allemaal. Op de kaart zie je ze in de '
               '<a href="%sbedrijvengids-categorie/restaurant/">bedrijvengids bij Restaurants</a>.</p></div>' % R)
    out.append('  <details class="resto-alles"><summary>Toon alle %d restaurants</summary>' % n)
    out.append("  " + lijst(alle))
    out.append("  </details>")
    out.append("</section>")

    ld = {"@context": "https://schema.org", "@type": "ItemList", "name": "Restaurants in Nijmegen", "url": SITE + PAGINA,
          "numberOfItems": n, "itemListElement": [
              {"@type": "ListItem", "position": i + 1, "name": r["naam"], "url": "%s/bedrijvengids/%s/" % (SITE, r["slug"])}
              for i, r in enumerate(alle)]}
    out.append('<script type="application/ld+json">%s</script>' % json.dumps(ld, ensure_ascii=False))
    DOEL.parent.mkdir(parents=True, exist_ok=True)
    DOEL.write_text("\n".join(out) + "\n", encoding="utf-8")
    met_keuken = sum(1 for r in alle if r["keukens"])
    print("Gemaakt: %s (%d restaurants, %d met keuken, %d binnenstad)" % (DOEL.relative_to(ROOT), n, met_keuken, len(binnen)))
    return n


if __name__ == "__main__":
    maak()
