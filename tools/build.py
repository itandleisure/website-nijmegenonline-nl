"""Zet de gedeelde onderdelen uit partials/ in alle pagina's.

Elke pagina markeert waar een onderdeel komt met
    <!-- zijbalk --> ... <!-- /zijbalk -->
Alles daartussen wordt vervangen door partials/zijbalk.html.
{{root}} in een partial wordt het relatieve pad naar de hoofdmap ("./", "../", ...).

Gebruik: python tools/build.py
"""
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
PARTIALS = ROOT / "partials"


def root_prefix(page):
    depth = len(page.relative_to(ROOT).parts) - 1
    return "../" * depth or "./"


def main():
    partials = {p.stem: p.read_text(encoding="utf-8").rstrip("\n") for p in PARTIALS.glob("*.html")}
    for page in sorted(ROOT.rglob("index.html")):
        if any(part.startswith(".") or part in ("partials", "tools") for part in page.relative_to(ROOT).parts):
            continue
        html = page.read_text(encoding="utf-8")
        nieuw = html
        for naam, inhoud in partials.items():
            blok = inhoud.replace("{{root}}", root_prefix(page))
            patroon = re.compile(r"([ \t]*)<!-- %s -->.*?<!-- /%s -->" % (naam, naam), re.S)

            def vervang(m, blok=blok, naam=naam):
                insprong = m.group(1)
                regels = "\n".join(insprong + r if r else r for r in blok.split("\n"))
                return "%s<!-- %s -->\n%s\n%s<!-- /%s -->" % (insprong, naam, regels, insprong, naam)

            nieuw = patroon.sub(vervang, nieuw)
        if nieuw != html:
            page.write_text(nieuw, encoding="utf-8")
            print("bijgewerkt:", page.relative_to(ROOT))


if __name__ == "__main__":
    main()
