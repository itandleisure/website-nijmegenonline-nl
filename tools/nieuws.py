"""Bouwt de nieuwspagina's uit data/nieuws.json.

- /nieuwsoverzicht/<slug>/   een pagina per bericht (zelfde URL als op WordPress)
- /nieuwsberichten/          overzicht, nieuwste eerst (/nieuwsoverzicht/ verwijst hierheen)
- homepage                   de drie nieuwste berichten tussen <!-- nieuws --> en <!-- /nieuws -->

data/nieuws.json komt uit tools/import_nieuws.py (de berichten van WordPress) en groeit met de berichten die de
redactie via nieuws@nijmegenonline.nl en de Google Sheet goedkeurt (tools/aanmeldingen.py). Daarna nog
python tools/build.py voor header, footer, zijbalk en de webp-afbeeldingen.

Gebruik: python tools/nieuws.py
"""
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from import_wordpress import (DOORVERWIJZING, ROOT, SITE, VOET, datum_nl, esc, goede_alt, kop,  # noqa: E402
                              samenvatting)

OVERZICHT = "nieuwsberichten"
DATA = ROOT / "data" / "nieuws.json"


def laad():
    return json.load(open(DATA, encoding="utf-8"))


def bewaar(berichten):
    berichten.sort(key=lambda b: (b["datum"], b["slug"]), reverse=True)
    DATA.write_text(json.dumps(berichten, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def foto_src(b, root):
    """Een eigen foto (www.nijmegenonline.nl/assets/...) relatief, zodat hij ook op de testsite werkt.
    Foto's van wp-content zet tools/build.py om naar de webp in assets/uploads/."""
    if b["foto"].startswith(SITE + "/assets/"):
        return root + b["foto"][len(SITE) + 1:]
    return b["foto"]


def zonder_dubbele_foto(b):
    """De uitgelichte foto staat vaak ook als eerste afbeelding in de tekst."""
    if not b["foto"]:
        return b["tekst"]
    basis = re.sub(r"\.\w+$", "", b["foto"].rsplit("/", 1)[-1])
    m = re.search(r'(<p>\s*)?<img[^>]+src="[^"]*/%s(?:-\d+x\d+)?\.\w+"[^>]*/?>(\s*</p>)?' % re.escape(basis), b["tekst"])
    return b["tekst"][:m.start()] + b["tekst"][m.end():] if m else b["tekst"]


def nieuwskaart(b, root):
    img = '<img src="%s" alt="" loading="lazy">' % esc(foto_src(b, root)) if b["foto"] else ""
    return ('<article class="kaart"><a href="%snieuwsoverzicht/%s/">%s<div class="kaart__tekst"><div class="label">%s</div>'
            "<h3>%s</h3></div></a></article>" % (root, b["slug"], img, esc(datum_nl(b["datum"])), esc(b["titel"])))


def bericht_pagina(b, nieuwer, ouder):
    root = "../../"
    canonical = "%s/nieuwsoverzicht/%s/" % (SITE, b["slug"])
    tekst = zonder_dubbele_foto(b)
    beschrijving = b["beschrijving"] or samenvatting(tekst)
    ld = [{"@context": "https://schema.org", "@type": "NewsArticle", "headline": b["titel"], "url": canonical,
           "datePublished": b["datum"], "dateModified": b["gewijzigd"], "description": beschrijving,
           "publisher": {"@type": "Organization", "name": "NijmegenOnline", "url": SITE + "/"}},
          {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
              {"@type": "ListItem", "position": 1, "name": "Home", "item": SITE + "/"},
              {"@type": "ListItem", "position": 2, "name": "Nieuws", "item": "%s/%s/" % (SITE, OVERZICHT)},
              {"@type": "ListItem", "position": 3, "name": b["titel"], "item": canonical}]}]
    if b["foto"]:
        ld[0]["image"] = b["foto"]
    extra = "".join('\n  <script type="application/ld+json">%s</script>' % json.dumps(x, ensure_ascii=False) for x in ld)
    out = [kop(b["seo_titel"], beschrijving, canonical, root, b["foto"] or None, extra)]
    out.append('  <main class="artikel-wrap">\n    <div class="container">\n      <div class="artikel-layout">\n      <article class="artikel nieuwsbericht">')
    out.append('        <div class="kruimelpad"><a href="%s">Home</a> › <a href="%s/%s/">Nieuws</a> › %s</div>'
               % (root, SITE, OVERZICHT, esc(b["titel"])))
    out.append('        <p class="gidslabel">Nieuws · <time datetime="%s">%s</time></p>' % (b["datum"][:10], datum_nl(b["datum"])))
    out.append("        <h1>%s</h1>" % esc(b["titel"]))
    if b["foto"]:
        bijschrift = "<figcaption>%s</figcaption>" % esc(b["bijschrift"]) if b.get("bijschrift") else ""
        out.append('        <figure><img src="%s" alt="%s">%s</figure>'
                   % (esc(foto_src(b, root)), esc(goede_alt("", b["foto"], b["titel"])), bijschrift))
    out.append('        <div class="partner-slider" data-plaatsing="blog"></div>')
    out.append('        <div class="inhoud-tekst">\n%s\n        </div>' % tekst)
    nav = []
    if ouder:
        nav.append('<a class="vorige" href="../%s/"><span>Vorig bericht</span>%s</a>' % (ouder["slug"], esc(ouder["titel"])))
    if nieuwer:
        nav.append('<a class="volgende" href="../%s/"><span>Volgend bericht</span>%s</a>' % (nieuwer["slug"], esc(nieuwer["titel"])))
    if nav:
        out.append('        <nav class="bericht-nav">%s</nav>' % "".join(nav))
    out.append('        <p class="gids-verder"><a href="%s/%s/">Al het nieuws</a> · <a href="%s/nijmegen-evenementen-overzicht/">Agenda</a></p>'
               % (SITE, OVERZICHT, SITE))
    out.append("      </article>\n\n      <!-- zijbalk --><!-- /zijbalk -->\n      </div>\n    </div>\n  </main>")
    out.append(VOET)
    return "\n".join(out)


def overzicht(berichten):
    root = "../"
    canonical = "%s/%s/" % (SITE, OVERZICHT)
    out = [kop("Nieuws uit Nijmegen", "Ontdek de laatste nieuwsberichten uit Nijmegen: blijf op de hoogte van lokale actualiteiten, "
               "evenementen, politiek en cultuur in de regio.", canonical, root, next((b["foto"] for b in berichten if b["foto"]), None))]
    out.append('  <main class="artikel-wrap">\n    <div class="container">')
    out.append('      <div class="kruimelpad"><a href="../">Home</a> › Nieuws</div>')
    out.append('      <header class="rubriek-kop">\n        <h1>Nieuws uit Nijmegen</h1>\n'
               '        <p>Nieuws over evenementen, cultuur en wat er speelt in Nijmegen en de regio. '
               'Zoek je iets om te doen? Kijk dan in de <a href="%s/nijmegen-evenementen-overzicht/">agenda</a>.</p>\n      </header>' % SITE)
    jaar = None
    for b in berichten:
        if b["datum"][:4] != jaar:
            if jaar:
                out.append("        </div>\n      </section>")
            jaar = b["datum"][:4]
            out.append('      <section class="gids-sectie">\n        <h2>%s</h2>\n        <div class="raster">' % jaar)
        out.append("          " + nieuwskaart(b, root))
    if jaar:
        out.append("        </div>\n      </section>")
    out.append('      <div class="partner-slider" data-plaatsing="blog"></div>')
    out.append("    </div>\n  </main>")
    out.append(VOET)
    return "\n".join(out)


def main():
    berichten = sorted(laad(), key=lambda b: (b["datum"], b["slug"]), reverse=True)
    for n, b in enumerate(berichten):
        d = ROOT / "nieuwsoverzicht" / b["slug"]
        d.mkdir(parents=True, exist_ok=True)
        nieuwer = berichten[n - 1] if n > 0 else None
        ouder = berichten[n + 1] if n + 1 < len(berichten) else None
        (d / "index.html").write_text(bericht_pagina(b, nieuwer, ouder), encoding="utf-8")
    (ROOT / OVERZICHT).mkdir(exist_ok=True)
    (ROOT / OVERZICHT / "index.html").write_text(overzicht(berichten), encoding="utf-8")
    stub = DOORVERWIJZING % {"titel": "Nieuws uit Nijmegen", "url": "%s/%s/" % (SITE, OVERZICHT), "pad": "../%s/" % OVERZICHT}
    (ROOT / "nieuwsoverzicht" / "index.html").write_text(stub.replace("Dit artikel is samengevoegd met", "Bekijk"), encoding="utf-8")

    home = ROOT / "index.html"
    blok = "\n".join(["        <div class=\"raster\">"] + ["          " + nieuwskaart(b, "./") for b in berichten[:3]] +
                     ["        </div>", '        <p class="gids-verder"><a href="%s/%s/">Al het nieuws</a></p>' % (SITE, OVERZICHT)])
    t = home.read_text(encoding="utf-8")
    t, n = re.subn(r"([ \t]*)<!-- nieuws -->.*?<!-- /nieuws -->",
                   lambda m: "%s<!-- nieuws -->\n%s\n%s<!-- /nieuws -->" % (m.group(1), blok, m.group(1)), t, flags=re.S)
    if not n:
        raise SystemExit("Markering <!-- nieuws --> ontbreekt in index.html")
    home.write_text(t, encoding="utf-8")
    print("%d nieuwsberichten, %s t/m %s" % (len(berichten), berichten[-1]["datum"][:10], berichten[0]["datum"][:10]))


if __name__ == "__main__":
    main()
