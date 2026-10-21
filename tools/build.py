"""Zet de gedeelde onderdelen uit partials/ in alle pagina's en maakt links intern.

1. Elke pagina markeert waar een onderdeel komt met
       <!-- zijbalk --> ... <!-- /zijbalk -->
   Alles daartussen wordt vervangen door partials/zijbalk.html (idem header, footer).
   {{root}} in een partial wordt het relatieve pad naar de hoofdmap ("./", "../", ...).
2. Links naar www.nijmegenonline.nl/<pad>/ worden relatief als die pagina al in deze repo staat,
   zodat de testsite op zichzelf werkt. Links naar pagina's die nog niet gebouwd zijn blijven
   naar de huidige site wijzen; die staan in het overzicht aan het eind.
3. Met --live: testbalk en noindex eruit en robots.txt open voor zoekmachines (zie LIVEGANG.md).

Gebruik: python tools/build.py [--live]
"""
import collections
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
PARTIALS = ROOT / "partials"
SITE = "https://www.nijmegenonline.nl"
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


def main(live=False):
    partials = {p.stem: p.read_text(encoding="utf-8").rstrip("\n") for p in PARTIALS.glob("*.html")}
    extern = collections.Counter()
    for page in pages():
        html = page.read_text(encoding="utf-8")
        nieuw = html
        root = root_prefix(page)
        for naam, inhoud in partials.items():
            blok = inhoud.replace("{{root}}", root)
            patroon = re.compile(r"([ \t]*)<!-- %s -->.*?<!-- /%s -->" % (naam, naam), re.S)

            def vervang(m, blok=blok, naam=naam):
                insprong = m.group(1)
                regels = "\n".join(insprong + r if r else r for r in blok.split("\n"))
                return "%s<!-- %s -->\n%s\n%s<!-- /%s -->" % (insprong, naam, regels, insprong, naam)

            nieuw = patroon.sub(vervang, nieuw)

        def intern(m):
            pad = m.group(2)
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

        if live:
            nieuw = re.sub(r'\n[ \t]*<div class="testbalk">.*?</div>\n', "\n", nieuw)
            nieuw = re.sub(r'\n[ \t]*<meta name="robots" content="noindex, nofollow">', "", nieuw)

        if nieuw != html:
            page.write_text(nieuw, encoding="utf-8")

    if live:
        (ROOT / "robots.txt").write_text("User-agent: *\nAllow: /\n\nSitemap: %s/sitemap.xml\n" % SITE, encoding="utf-8")
        print("Live-versie gemaakt: testbalk en noindex verwijderd, robots.txt open.")

    if extern:
        print("Nog naar de huidige site (%d pagina's nog niet gebouwd):" % len(extern))
        for pad, n in extern.most_common():
            print("  %4dx %s" % (n, pad))


if __name__ == "__main__":
    main(live="--live" in sys.argv)
