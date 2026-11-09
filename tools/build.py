"""Zet de gedeelde onderdelen uit partials/ in alle pagina's en maakt links intern.

1. Elke pagina markeert waar een onderdeel komt met
       <!-- zijbalk --> ... <!-- /zijbalk -->
   Alles daartussen wordt vervangen door partials/zijbalk.html (idem header, footer).
   {{root}} in een partial wordt het relatieve pad naar de hoofdmap ("./", "../", ...).
2. Links naar www.nijmegenonline.nl/<pad>/ worden relatief als die pagina al in deze repo staat,
   zodat de testsite op zichzelf werkt. Links naar pagina's die nog niet gebouwd zijn blijven
   naar de huidige site wijzen; die staan in het overzicht aan het eind.
3. Afbeeldingen van www.nijmegenonline.nl/wp-content/uploads/ wijzen naar de eigen webp-versie in
   assets/uploads/ als tools/afbeeldingen.py die heeft gemaakt (src relatief, og:image absoluut).
4. sitemap.xml met alle pagina's die geïndexeerd mogen worden (geen doorverwijzingen), met de
   echte URL's en de datum van de laatste wijziging.
5. Zet data-pagefind-body en een soort-filter op <main>, zodat Pagefind (zoeken/) alleen echte pagina's
   indexeert en niet de doorverwijzingen. De index zelf bouwt tools/zoekindex.py.
6. Geeft kaartfoto's zonder alt-tekst (<img alt=""> in een link) de titel van die kaart als alt-tekst.
7. Zet partials/analytics.html (Google Analytics) vlak voor </head> in elke pagina; de code zelf laadt
   alleen op www.nijmegenonline.nl, dus de testsite telt niet mee.
   statistiek/ (interne, afgeschermde pagina) blijft helemaal buiten stap 1-7.
8. Live (met --live, of vanzelf zodra het bestand CNAME bestaat): testbalk en noindex eruit, robots.txt open voor
   zoekmachines en 404.html zonder het pad van de testsite (zie LIVEGANG.md). Door de CNAME-controle blijft de site
   live als de nachtelijke scripts pagina's opnieuw maken.
9. Houdt de <title> op hoogstens 70 tekens (Bing meldt langere titels als fout): eerst valt " | NijmegenOnline" weg,
   dan wordt ingekort tot het eerste deel voor " | " (minstens 30 tekens), en anders op een woordgrens met "…".
   og:title en de kop op de pagina blijven de volledige titel houden.
10. tools/vindbaar.py: "Bijgewerkt op" en "In het kort" op de gidsen, organisatiegegevens op de homepage en llms.txt.
11. Meldt aan het eind indexeerbare pagina's met meer of minder dan één <title> of <h1>, of zonder meta description.

Gebruik: python tools/build.py [--live]
"""
import collections
import html as html_lib
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import vindbaar  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
PARTIALS = ROOT / "partials"
SITE = "https://www.nijmegenonline.nl"
UPLOAD = re.compile(r'(src="|srcset=")?https?://(?:www\.)?nijmegenonline\.nl/wp-content/uploads/([^"\'\s)]+?)\.(?:png|jpe?g|gif|webp)', re.I)
MAIN = re.compile(r"<main\b(?![^>]*data-pagefind-body)([^>]*)>")
# soort per eerste deel van het pad, voor het filter op de zoekpagina; de rest is "Artikelen"
SOORTEN = {
    "bedrijvengids": "Bedrijvengids", "bedrijvengids-categorie": "Bedrijvengids", "overzicht": "Bedrijvengids",
    "events": "Agenda", "event-location": "Agenda", "jaarlijkse-evenementen": "Agenda", "agenda": "Agenda",
    "nijmegen-evenementen-overzicht": "Agenda", "nieuwsoverzicht": "Nieuws", "vacatures": "Vacatures",
    "thema": "Gidsen",
}
KAART = re.compile(r'(<a\b[^>]*>)(.*?)</a>')
TITEL = re.compile(r"<(?:strong|h[2-4])\b[^>]*>(.*?)</(?:strong|h[2-4])>", re.S)
TITLE = re.compile(r"<title>(.*?)</title>", re.S)
MAX_TITEL = 70
LOSSE_WOORDEN = {"de", "het", "een", "en", "of", "met", "op", "van", "voor", "naar", "in", "aan", "bij", "uit", "te",
                 "door", "om", "over", "tot", "na", "tijdens", "onder", "als", "dat", "die", "is", "zijn", "wordt", "the", "and", "of", "w/"}
LINK = re.compile(r'(<a\b[^>]*?\bhref=")https?://(?:www\.)?nijmegenonline\.nl(/[^"#?]*)([^"]*")')


def root_prefix(page):
    depth = len(page.relative_to(ROOT).parts) - 1
    return "../" * depth or "./"


def pages():
    for page in sorted(ROOT.rglob("index.html")):
        if any(part.startswith(".") or part in ("partials", "tools", "node_modules") for part in page.relative_to(ROOT).parts):
            continue
        yield page


def bestaat(pad):
    pad = pad.strip("/")
    return (ROOT / pad / "index.html").is_file() if pad else True


def doorverwijzingen():
    """Vaste 301's uit _redirects (zonder * of :), zodat een link naar een oud adres meteen naar het eindadres gaat."""
    kaart = {}
    pad = ROOT / "_redirects"
    for regel in pad.read_text(encoding="utf-8").splitlines() if pad.exists() else []:
        delen = regel.split()
        if len(delen) >= 2 and delen[0].startswith("/") and not any(t in delen[0] for t in "*:") and delen[1].startswith("/"):
            kaart.setdefault(delen[0], delen[1])
    return kaart


def eindadres(pad, kaart):
    for _ in range(10):
        volgende = kaart.get(pad.rstrip("/") + "/")
        if not volgende or not bestaat(volgende):
            break
        pad = volgende
    return pad


def ongebruikte_doorverwijzingen_weg():
    """Haalt de regels van oude adressen zonder backlinks of bezoekers uit _redirects (data/doorverwijzingen-ongebruikt.txt),
    zodat het aantal onder de limiet van Cloudflare Pages blijft. Hun doorstuurpagina in de repo blijft bestaan."""
    lijst, pad = ROOT / "data" / "doorverwijzingen-ongebruikt.txt", ROOT / "_redirects"
    if not (lijst.exists() and pad.exists()):
        return
    weg = {r.strip() for r in lijst.read_text(encoding="utf-8").splitlines() if r.startswith("/")}
    regels = pad.read_text(encoding="utf-8").splitlines()
    over = [r for r in regels if not (r.startswith("/") and r.split()[0] in weg)]
    if len(over) != len(regels):
        pad.write_text("\n".join(over) + "\n", encoding="utf-8")
    print("_redirects: %d doorverwijzingen" % sum(r.startswith("/") for r in over))


def main(live=False):
    partials = {p.stem: p.read_text(encoding="utf-8").rstrip("\n") for p in PARTIALS.glob("*.html")}
    kaart = doorverwijzingen()
    extern = collections.Counter()
    for page in pages():
        if page.parent.name == "statistiek":  # interne pagina: geen menu, analytics of zoekindex
            continue
        html = page.read_text(encoding="utf-8")
        nieuw = html
        root = root_prefix(page)
        if "<!-- analytics -->" not in nieuw:
            nieuw = re.sub(r"\n([ \t]*)</head>", r"\n\1  <!-- analytics --><!-- /analytics -->\n\1</head>", nieuw, count=1)
        for naam, inhoud in partials.items():
            blok = inhoud.replace("{{root}}", root)
            patroon = re.compile(r"([ \t]*)<!-- %s -->.*?<!-- /%s -->" % (naam, naam), re.S)

            def vervang(m, blok=blok, naam=naam):
                insprong = m.group(1)
                regels = "\n".join(insprong + r if r else r for r in blok.split("\n"))
                return "%s<!-- %s -->\n%s\n%s<!-- /%s -->" % (insprong, naam, regels, insprong, naam)

            nieuw = patroon.sub(vervang, nieuw)

        def intern(m):
            pad = eindadres(m.group(2), kaart)
            if bestaat(pad):
                doel = root + pad.strip("/") + ("/" if pad.strip("/") else "")
                return m.group(1) + (doel or "./") + m.group(3)
            extern[pad] += 1
            return m.group(0)

        regels = []
        for regel in nieuw.split("\n"):
            # de testbalk verwijst bewust naar de echte pagina
            regels.append(regel if 'class="testbalk"' in regel else LINK.sub(intern, regel))
        nieuw = "\n".join(regels)

        def afbeelding(m):
            lokaal = "assets/uploads/%s.webp" % m.group(2)
            if not (ROOT / lokaal).is_file():
                return m.group(0)
            return (m.group(1) + root + lokaal) if m.group(1) else "%s/%s" % (SITE, lokaal)

        nieuw = UPLOAD.sub(afbeelding, nieuw)

        nieuw = KAART.sub(alt_tekst, nieuw)
        nieuw = TITLE.sub(korte_titel, nieuw, count=1)
        nieuw = zoekbaar(page, nieuw)

        if live:
            nieuw = re.sub(r'\n[ \t]*<div class="testbalk">.*?</div>\n', "\n", nieuw)
            nieuw = re.sub(r'\n[ \t]*<meta name="robots" content="noindex, nofollow">', "", nieuw)

        if nieuw != html:
            page.write_text(nieuw, encoding="utf-8")

    vindbaar.main()
    sitemap(live)
    seo_controle()
    ongebruikte_doorverwijzingen_weg()

    if live:
        pagina = ROOT / "404.html"
        pagina.write_text(pagina.read_text(encoding="utf-8").replace("/website-nijmegenonline-nl/", "/")
                          .replace(" in de testomgeving", ""), encoding="utf-8")
        (ROOT / "robots.txt").write_text("User-agent: *\nAllow: /\nDisallow: /statistiek/\n\nSitemap: %s/sitemap.xml\n" % SITE, encoding="utf-8")
        print("Live-versie gemaakt: testbalk en noindex verwijderd, robots.txt open.")

    if extern:
        print("Nog naar de huidige site (%d pagina's nog niet gebouwd):" % len(extern))
        for pad, n in extern.most_common():
            print("  %4dx %s" % (n, pad))


def korte_titel(m):
    """Stap 9: een <title> van meer dan MAX_TITEL tekens inkorten (lengte geteld zonder HTML-entiteiten)."""
    titel = m.group(1).strip()
    if len(html_lib.unescape(titel)) <= MAX_TITEL:
        return m.group(0)
    kort = html_lib.unescape(titel)
    for staart in (" | NijmegenOnline", " - NijmegenOnline", " – NijmegenOnline"):
        if kort.endswith(staart):
            kort = kort[: -len(staart)].rstrip()
    if len(kort) > MAX_TITEL:
        for scheiding in (" | ",):
            deel = kort.split(scheiding)[0].strip()
            if 30 <= len(deel) <= MAX_TITEL:
                kort = deel
                break
    if len(kort) > MAX_TITEL:
        woorden = kort[: MAX_TITEL - 1].rsplit(" ", 1)[0].split(" ")
        while len(woorden) > 1 and (woorden[-1].lower() in LOSSE_WOORDEN or woorden[-1] in "-–|•&:"):
            woorden.pop()
        kort = " ".join(woorden).rstrip(" ,;:") + "…"
    return "<title>%s</title>" % html_lib.escape(kort, quote=False)


def seo_controle():
    """Stap 10: telt per indexeerbare pagina (de pagina's in sitemap.xml) <title>, <h1> en meta description."""
    fouten = []
    for loc in re.findall(r"<loc>%s/([^<]*)</loc>" % re.escape(SITE), (ROOT / "sitemap.xml").read_text(encoding="utf-8")):
        page = ROOT / loc / "index.html"
        if not page.is_file():
            continue
        html = page.read_text(encoding="utf-8")
        titels, koppen = len(re.findall(r"<title[\s>]", html, re.I)), len(re.findall(r"<h1[\s>]", html, re.I))
        if titels != 1 or koppen != 1 or '<meta name="description"' not in html:
            fouten.append("  /%s: %d title, %d h1%s" % (loc, titels, koppen, "" if '<meta name="description"' in html else ", geen description"))
    if fouten:
        print("SEO-controle: %d pagina's met een afwijkende title, h1 of description:" % len(fouten))
        print("\n".join(fouten[:50]))


def alt_tekst(m):
    """Lege alt in een kaartlink wordt de titel van de kaart (<strong> of kop, anders de linktekst)."""
    if 'alt=""' not in m.group(2):
        return m.group(0)
    t = TITEL.search(m.group(2))
    tekst = re.sub(r"<[^>]+>", " ", t.group(1) if t else m.group(2))
    tekst = re.sub(r"\s+", " ", tekst).strip().replace('"', "&quot;")
    return m.group(1) + m.group(2).replace('alt=""', 'alt="%s"' % tekst) + "</a>" if tekst else m.group(0)


def zoekbaar(page, html):
    """Markeert <main> voor Pagefind; doorverwijzingen en de zoekpagina zelf blijven erbuiten.
    Bedrijven die nog niet in Google mogen (noindex, nog geen eigen tekst) zijn wel vindbaar op de site."""
    delen = page.parent.relative_to(ROOT).parts
    if 'http-equiv="refresh"' in html or delen[:1] == ("zoeken",):
        return html
    soort = SOORTEN.get(delen[0], "Artikelen") if delen else "Artikelen"
    return MAIN.sub(r'<main\1 data-pagefind-body data-pagefind-filter="soort:%s">' % soort, html, count=1)


def sitemap(live):
    regels = []
    for page in pages():
        html = page.read_text(encoding="utf-8")
        if '<meta name="robots" content="noindex">' in html:  # doorverwijzing
            continue
        if page.parent.name == "zoeken":
            continue
        m = re.search(r'<link rel="canonical" href="([^"]+)"', html)
        pad = page.parent.relative_to(ROOT).as_posix()
        url = m.group(1) if m else SITE + ("/" if pad == "." else "/%s/" % pad)
        if not url.startswith(SITE):
            continue
        d = re.search(r'"dateModified": "(\d{4}-\d{2}-\d{2})', html)
        regels.append("  <url><loc>%s</loc>%s</url>" % (url, "<lastmod>%s</lastmod>" % d.group(1) if d else ""))
    (ROOT / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n'
                                      '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n%s\n</urlset>\n'
                                      % "\n".join(sorted(set(regels))), encoding="utf-8")
    print("sitemap.xml: %d pagina's" % len(set(regels)))


if __name__ == "__main__":
    main(live="--live" in sys.argv or (ROOT / "CNAME").exists())
