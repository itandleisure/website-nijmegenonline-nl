"""Bezoekersrubrieken: /zien-en-doen/ en /plan-je-bezoek/.

Twee overzichtspagina's voor bezoekers van buiten de stad, zoals de vaste rubrieken van Visit Nijmegen en Regio Arnhem.
Ze bundelen pagina's die al op de site staan. De indeling staat in data/bezoekers.json: per pagina groepen met kaarten.
Een kaart naar een eigen pagina krijgt vanzelf de titel, omschrijving en foto van die pagina (h1, meta description,
og:image). Bij een externe link (bijv. Visit Nijmegen) staan titel en tekst in het json-bestand. Een kaart naar een pagina
die niet (meer) bestaat of een doorverwijzing is geworden, slaat het script over en meldt het.

Gebruik: python tools/bezoekers.py   (daarna tools/build.py en tools/zoekindex.py)
"""
import html
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from import_wordpress import SITE, VOET, esc, kop  # noqa: E402

DATA = json.load(open(ROOT / "data" / "bezoekers.json", encoding="utf-8"))


def meta(s, naam):
    m = re.search(r'<meta (?:name|property)="%s" content="([^"]*)"' % re.escape(naam), s)
    return html.unescape(m.group(1)) if m else ""


def eigen_pagina(pad):
    """Titel, omschrijving en foto van een pagina op deze site, of None als die er niet is of doorverwijst."""
    bestand = ROOT / pad.split("#")[0].strip("/") / "index.html"
    if not bestand.is_file():
        return None
    s = bestand.read_text(encoding="utf-8")
    if 'http-equiv="refresh"' in s:
        return None
    h1 = re.search(r"<h1[^>]*>(.*?)</h1>", s, re.S)
    titel = html.unescape(re.sub(r"<[^>]+>", "", h1.group(1))).strip() if h1 else meta(s, "og:title")
    foto = meta(s, "og:image")
    if foto.startswith(SITE + "/assets/uploads/"):
        foto = foto[len(SITE) + 1:]   # eigen foto: relatief, zodat de testsite hem ook toont
    elif "/assets/img/logo" in foto:
        foto = ""
    return {"titel": titel, "tekst": meta(s, "description"), "foto": foto}


def kaart(k, root):
    if k.get("extern"):
        href, info, doel = k["extern"], {"titel": k["titel"], "tekst": k["tekst"], "foto": ""}, ' rel="noopener" target="_blank"'
    else:
        info = eigen_pagina(k["pad"])
        if info is None:
            print("Overgeslagen, bestaat niet of is een doorverwijzing:", k["pad"])
            return ""
        info.update({x: k[x] for x in ("titel", "tekst") if k.get(x)})
        href, doel = root + k["pad"].lstrip("/"), ""
    tekst = info["tekst"]
    if len(tekst) > 150:
        tekst = tekst[:147].rsplit(" ", 1)[0] + "…"
    img = '<img src="%s%s" alt="" loading="lazy">' % (root, esc(info["foto"])) if info["foto"] else ""
    meer = "Naar %s" % k.get("bron", "de site") if k.get("extern") else "Lees meer"
    return ('          <a class="gidskaart" href="%s"%s>%s<div class="gidskaart__tekst">'
            '<h3>%s</h3><p>%s</p><span class="gidskaart__meer">%s <span aria-hidden="true">→</span></span></div></a>'
            % (esc(href), doel, img, esc(info["titel"]), esc(tekst), meer))


def pagina(p):
    root = "../"
    canonical = "%s/%s/" % (SITE, p["slug"])
    eerste = next((eigen_pagina(k["pad"]) for g in p["groepen"] for k in g["kaarten"] if k.get("pad") and eigen_pagina(k["pad"])), None)
    ld = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "Home", "item": SITE + "/"},
        {"@type": "ListItem", "position": 2, "name": p["naam"], "item": canonical}]}
    extra = '\n  <script type="application/ld+json">%s</script>' % json.dumps(ld, ensure_ascii=False)
    foto = SITE + "/" + eerste["foto"] if eerste and eerste["foto"] else None
    out = [kop(p["titel"], p["omschrijving"], canonical, root, foto, extra)]
    out.append('  <main class="artikel-wrap">\n    <div class="container">')
    out.append('      <div class="kruimelpad"><a href="../">Home</a> › %s</div>' % esc(p["naam"]))
    out.append('      <header class="rubriek-kop">\n        <h1>%s</h1>\n        <p>%s</p>\n      </header>' % (esc(p["kop"]), esc(p["intro"])))
    out.append('      <nav class="gidsen-filter" aria-label="Op deze pagina">')
    for g in p["groepen"]:
        out.append('        <a class="knop-link" href="#%s">%s</a>' % (g["id"], esc(g["naam"])))
    out.append("      </nav>")
    for g in p["groepen"]:
        out.append('      <section class="bezoekers-groep" id="%s">\n        <h2>%s</h2>' % (g["id"], esc(g["naam"])))
        if g.get("intro"):
            out.append("        <p>%s</p>" % esc(g["intro"]))
        out.append('        <div class="gidsen-raster">')
        out += [x for x in (kaart(k, root) for k in g["kaarten"]) if x]
        out.append("        </div>\n      </section>")
    out.append('      <div class="partner-slider" data-plaatsing="blog"></div>')
    out.append("    </div>\n  </main>")
    out.append(VOET)
    return "\n".join(out)


def main():
    for p in DATA:
        d = ROOT / p["slug"]
        d.mkdir(exist_ok=True)
        (d / "index.html").write_text(pagina(p), encoding="utf-8")
        print("Gemaakt:", p["slug"] + "/")


if __name__ == "__main__":
    main()
