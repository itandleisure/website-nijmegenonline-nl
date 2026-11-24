"""Bedrijven die in de tekst van een artikel of gids genoemd worden, linken naar hun pagina in de bedrijvengids
(vraag Frans, 24-11-2026: "Eetbar MikMak" in /hapje-eten-en-drinken-in-nijmegen/ moet doorklikken naar
/bedrijvengids/eetbar-mikmak/).

Welke naam naar welk bedrijf gaat, staat in data/artikel-bedrijflinks.json:

    {"hapje-eten-en-drinken-in-nijmegen": {"Eetbar MikMak": "eetbar-mikmak", "De Bruijn": "de-bruijn-lunchen-op-de-markt"},
     "thema/museums-nijmegen": {"Valkhof Museum": "valkhof-museum"},
     "markten-nijmegen": {"Woensdag": ""}}

- De sleutel links is de map van de pagina (een artikel, of thema/<gids>). Rechts staat de map van het bedrijf in
  /bedrijvengids/. Een lege waarde ("") betekent: bewust niet linken (bijvoorbeeld "Woensdag" is hier een dag, geen
  bedrijf). Zo stelt --voorstellen hem niet opnieuw voor.
- Alleen de eerste keer dat de naam in de tekst staat wordt een link, zoals een redacteur dat ook zou doen. Een
  vermelding in een tussenkop wordt alleen gebruikt als de naam verder nergens in de tekst staat.
- Hoofdletters, spaties en de soort apostrof (’ of ') maken niet uit: "Café T’ Haantje" vindt ook "café t' haantje".
- Er komt alleen een link als de bedrijfspagina bestaat en geen doorverwijzing is, en als het artikel nog niet naar
  dat bedrijf linkt (in de tekst of met een kaartje). Bestaande links blijven zoals ze zijn.
- tools/build.py haalt elke pagina hier doorheen, dus de links blijven staan als een artikel of gids opnieuw wordt
  gemaakt (tools/import_wordpress.py). Een link weghalen: zet de waarde op "" en draai build.py; de link verdwijnt dan
  ook uit de pagina.

Gebruik:
    python tools/bedrijflinks.py                 links zetten in alle pagina's en melden wat niet lukte
    python tools/bedrijflinks.py --voorstellen   lijst met bedrijfsnamen in artikelen die nog niet in het bestand staan:
                                                 docs/bedrijflinks-voorstellen.md (om na te kijken en over te nemen)
"""
import collections
import functools
import html as html_lib
import json
import pathlib
import re
import sys
import unicodedata

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "artikel-bedrijflinks.json"
VERMELDINGEN = ROOT / "data" / "bedrijvengids-vermeldingen.json"
VOORSTELLEN = ROOT / "docs" / "bedrijflinks-voorstellen.md"
KLASSE = "bedrijflink"

DELEN = re.compile(r"(<!--.*?-->|<[^>]*>)", re.S)
TAG = re.compile(r"<(/?)([a-zA-Z][\w-]*)")
# in deze elementen nooit een link zetten
OVERSLAAN = {"a", "script", "style", "code", "pre", "textarea", "button", "select", "option", "svg", "noscript",
             "template", "title", "h1", "figcaption", "label"}
KOPPEN = {"h2", "h3", "h4", "h5", "h6"}
LEEG = {"br", "img", "hr", "input", "meta", "link", "source", "wbr", "col", "area", "base", "embed", "param", "track"}
APOSTROF = r"(?:['’‘`´]|&#0?39;|&#821[67];|&rsquo;|&lsquo;|&apos;)"
EN = r"(?:&amp;|&#0?38;|&)"
LINK_OUD = re.compile(r'<a class="%s" href="[^"]*">(.*?)</a>' % KLASSE, re.S)


@functools.lru_cache(maxsize=1)
def koppelingen():
    if not DATA.exists():
        return {}
    return json.loads(DATA.read_text(encoding="utf-8"))


@functools.lru_cache(maxsize=None)
def bedrijf_bestaat(sleutel):
    pad = ROOT / "bedrijvengids" / sleutel / "index.html"
    return pad.is_file() and 'http-equiv="refresh"' not in pad.read_text(encoding="utf-8")[:3000]


def patroon(naam):
    """Regex voor een naam in HTML-tekst: hoofdletters, witruimte en apostrof maken niet uit."""
    stukken = []
    for teken in naam.strip():
        if teken in "'’‘`´":
            stukken.append(APOSTROF + "?")
        elif teken == "&":
            stukken.append(EN)
        elif teken.isspace():
            if not stukken or stukken[-1] != r"(?:\s|&nbsp;|&#160;)+":
                stukken.append(r"(?:\s|&nbsp;|&#160;)+")
        else:
            stukken.append(re.escape(teken))
    return re.compile(r"(?<![\w&])" + "".join(stukken) + r"(?![\w])", re.I)


def tekstgebied(html):
    """Begin en eind van de lopende tekst: vanaf de eerste <div class="inhoud-tekst"> tot het gidstip of </article>."""
    begin = html.find('<div class="inhoud-tekst')
    if begin < 0:
        return None
    eind = min([i for i in (html.find("<!-- gidstip -->", begin), html.find("</article>", begin)) if i > 0] or [len(html)])
    return begin, eind


def zet_link(stuk, naam, href):
    """Zet in een stuk HTML de eerste vermelding van naam om in een link. Geeft (nieuw stuk, gelukt) terug."""
    delen = DELEN.split(stuk)
    open_ = []  # stapel open elementen
    kandidaten = []  # (in_kop, index in delen, match)
    regex = patroon(naam)
    for i, deel in enumerate(delen):
        if i % 2:  # tag of commentaar
            m = TAG.match(deel)
            if not m or deel.startswith("<!--"):
                continue
            naam_tag = m.group(2).lower()
            if naam_tag in LEEG or deel.endswith("/>"):
                continue
            if m.group(1):
                if naam_tag in open_:
                    while open_ and open_.pop() != naam_tag:
                        pass
            else:
                open_.append(naam_tag)
            continue
        if not deel.strip() or any(t in OVERSLAAN for t in open_):
            continue
        m = regex.search(deel)
        if m:
            kandidaten.append((any(t in KOPPEN for t in open_), i, m))
            if not kandidaten[-1][0]:
                break
    if not kandidaten:
        return stuk, False
    kandidaten.sort(key=lambda k: (k[0], k[1]))
    _, i, m = kandidaten[0]
    deel = delen[i]
    delen[i] = '%s<a class="%s" href="%s">%s</a>%s' % (deel[:m.start()], KLASSE, href, m.group(0), deel[m.end():])
    return "".join(delen), True


def koppel(pagina, html, root):
    """Zet de bedrijfslinks uit data/artikel-bedrijflinks.json in één pagina. pagina: map ten opzichte van de hoofdmap,
    zoals "hapje-eten-en-drinken-in-nijmegen" of "thema/museums-nijmegen". Geeft (nieuwe html, [niet gevonden namen])."""
    lijst = koppelingen().get(pagina)
    gebied = tekstgebied(html)
    if gebied is None:
        return html, []
    begin, eind = gebied
    stuk = html[begin:eind]
    # eerst onze eigen links weghalen, zodat een gewijzigde of geschrapte koppeling ook uit de pagina verdwijnt
    stuk = LINK_OUD.sub(lambda m: m.group(1), stuk)
    niet_gevonden = []
    for naam, sleutel in (lijst or {}).items():
        if not sleutel or not bedrijf_bestaat(sleutel):
            if sleutel:
                niet_gevonden.append("%s (bedrijfspagina %s bestaat niet)" % (naam, sleutel))
            continue
        if re.search(r'href="[^"]*bedrijvengids/%s/"' % re.escape(sleutel), stuk):
            continue  # het artikel linkt al naar dit bedrijf
        stuk, gelukt = zet_link(stuk, naam, "%sbedrijvengids/%s/" % (root, sleutel))
        if not gelukt:
            niet_gevonden.append(naam)
    return html[:begin] + stuk + html[eind:], niet_gevonden


def paginas():
    """Alle artikelen en gidsen met lopende tekst: (map, pad)."""
    from genoemd import GEEN_ARTIKEL
    for pad in sorted(ROOT.glob("*/index.html")):
        if pad.parent.name not in GEEN_ARTIKEL and not pad.parent.name.startswith("."):
            yield pad.parent.name, pad
    for pad in sorted(ROOT.glob("thema/*/index.html")):
        yield "thema/" + pad.parent.name, pad


def main():
    teller, missers = collections.Counter(), []
    for map_, pad in paginas():
        html = pad.read_text(encoding="utf-8")
        if 'http-equiv="refresh"' in html:
            continue
        nieuw, niet = koppel(map_, html, "../" * map_.count("/") + "../")
        missers += ["%s: %s" % (map_, n) for n in niet]
        if nieuw != html:
            pad.write_text(nieuw, encoding="utf-8")
            teller["paginas"] += 1
        teller["links"] += nieuw.count('class="%s"' % KLASSE)
    print("bedrijflinks: %d links naar de bedrijvengids, %d pagina's bijgewerkt" % (teller["links"], teller["paginas"]))
    for regel in missers:
        print("  niet gevonden:", regel)
    for map_ in koppelingen():
        if not (ROOT / map_ / "index.html").is_file():
            print("  pagina bestaat niet:", map_)


# ---------------------------------------------------------------- voorstellen voor nieuwe artikelen

def norm(s):
    s = html_lib.unescape(re.sub(r"<[^>]+>", " ", s))
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"[’'`]", "", s)
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


VOORVOEGSELS = {"de", "het", "t", "the", "restaurant", "cafe", "eetcafe", "hotel", "brasserie", "lunchroom", "bistro",
                "grandcafe", "bar", "eetbar", "pizzeria", "trattoria", "salon", "kapsalon"}


def kern(n):
    """Naam zonder lidwoord of soort ervoor en plaatsnaam erachter: "cafe t haantje" -> "haantje"."""
    w = n.split()
    while len(w) > 1 and w[0] in VOORVOEGSELS:
        w = w[1:]
    while len(w) > 1 and w[-1] in ("nijmegen", "wijchen", "lent", "bv"):
        w = w[:-1]
    return " ".join(w)


def voorstellen():
    gids = json.loads(VERMELDINGEN.read_text(encoding="utf-8"))
    index, volledig = collections.defaultdict(set), collections.defaultdict(set)
    for sleutel, v in gids.items():
        n = norm(v["bedrijf"])
        index[n].add(sleutel)
        index[kern(n)].add(sleutel)
        volledig[n].add(sleutel)
    bekend = {(p, norm(n)) for p, namen in koppelingen().items() for n in namen}
    regels = []
    for map_, pad in paginas():
        html = pad.read_text(encoding="utf-8")
        gebied = tekstgebied(html)
        if 'http-equiv="refresh"' in html or not gebied:
            continue
        stuk = html[gebied[0]:gebied[1]]
        al = set(re.findall(r"bedrijvengids/([a-z0-9-]+)/", stuk)) | set(koppelingen().get(map_, {}).values())
        stuk = re.sub(r"<a\b.*?</a>", " ", stuk, flags=re.S)  # tekst die al een link is telt niet mee
        tekst = " %s " % norm(stuk)
        gezien = {}
        # 1. namen met nadruk (vet, tussenkop, opsomming): ook een kortere vorm ("De Bruijn")
        for m in re.finditer(r"<(strong|b|h[2-4]|li)\b[^>]*>(.*?)</\1>", stuk, re.S):
            ruw = html_lib.unescape(re.sub(r"<[^>]+>", "", m.group(2))).strip()
            for deel in {ruw, re.split(r"[:–—|(]| - ", ruw)[0]}:
                deel = re.sub(r"^[\s·•–-]*\d*[.)]?\s*", "", deel).strip()
                n = norm(deel)
                if len(n) < 4 or n in gezien:
                    continue
                treffers = index.get(n) or index.get(kern(n))
                if not treffers and len(kern(n)) >= 5:
                    treffers = {s for s, v in gids.items() if (kern(norm(v["bedrijf"])) + " ").startswith(kern(n) + " ")}
                    treffers = treffers if len(treffers) <= 3 else set()
                if treffers:
                    gezien[n] = (deel, treffers)
        # 2. volledige namen van minstens twee woorden in de lopende tekst
        for n, treffers in volledig.items():
            if n in gezien or len(kern(n).split()) < 2 or " %s " % n not in tekst:
                continue
            gezien[n] = (n, treffers)
        for n, (deel, treffers) in gezien.items():
            if (map_, n) in bekend or treffers & al:
                continue
            if any(n != m and " %s " % n in " %s " % m for m in gezien):
                continue  # al onderdeel van een langere naam
            opties = ", ".join("`%s` (%s, %s)" % (s, gids[s]["bedrijf"], gids[s]["categorie"]) for s in sorted(treffers))
            regels.append("| %s | %s | %s |" % (map_, deel.replace("|", "/"), opties))
    VOORSTELLEN.parent.mkdir(exist_ok=True)
    VOORSTELLEN.write_text(
        "# Bedrijfsnamen in artikelen die nog niet gelinkt zijn\n\n"
        "Gemaakt door `python tools/bedrijflinks.py --voorstellen`. Klopt een voorstel, zet het dan in "
        "`data/artikel-bedrijflinks.json` (naam zoals in de tekst, met de sleutel van het bedrijf). Klopt het niet, zet "
        "de naam erin met een lege sleutel (\"\"), dan komt hij hier niet meer terug.\n\n"
        "| Pagina | Naam in de tekst | Bedrijf in de gids |\n|---|---|---|\n" + "\n".join(regels) + "\n",
        encoding="utf-8")
    print("bedrijflinks: %d voorstellen in %s" % (len(regels), VOORSTELLEN.relative_to(ROOT)))


if __name__ == "__main__":
    sys.path.insert(0, str(ROOT / "tools"))
    voorstellen() if "--voorstellen" in sys.argv else main()
