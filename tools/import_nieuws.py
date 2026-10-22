"""Zet de nieuwsberichten (WP News and Widget Pro, post type "news") om naar statische pagina's.

Datum, uitgelichte afbeelding en Rank Math-titel komen uit de XML-export (bron/wp-xml/nieuws.xml), de tekst
uit de HTML van de live pagina (bron/nieuws-html/<slug>.html), want in de XML staat nog ruwe WordPress-tekst
met shortcodes. Resultaat:

- /nieuwsoverzicht/<slug>/   een pagina per bericht (zelfde URL als op WordPress)
- /nieuwsberichten/          overzicht, nieuwste eerst (/nieuwsoverzicht/ verwijst hierheen)
- homepage                   de drie nieuwste berichten tussen <!-- nieuws --> en <!-- /nieuws -->

Gebruik: python tools/import_nieuws.py [/mnt/project-files/bron]
"""
import datetime
import html
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from import_wordpress import (DOORVERWIJZING, ROOT, SITE, VOET, datum_nl, esc, goede_alt, kop,  # noqa: E402
                              samenvatting, schoon)

OVERZICHT = "nieuwsberichten"


def veld(item, tag):
    m = re.search(r"<%s>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</%s>" % (tag, tag), item, re.S)
    return m.group(1) if m else ""


def meta(item, sleutel):
    m = re.search(r"<wp:meta_key><!\[CDATA\[%s\]\]></wp:meta_key>\s*<wp:meta_value><!\[CDATA\[(.*?)\]\]></wp:meta_value>"
                  % re.escape(sleutel), item, re.S)
    return m.group(1) if m else ""


def tekst_uit_html(pad, titel):
    t = pad.read_text(encoding="utf-8")
    begin = re.search(r'<div class="entry-content single-page">', t)
    eind = t.find('<div class="blog-share', begin.end())
    inhoud = t[begin.end():eind]
    # Lazy loading van WordPress: de echte afbeelding staat in data-src
    inhoud = re.sub(r'\ssrc="data:image/svg\+xml[^"]*"', "", inhoud)
    inhoud = re.sub(r"\sdata-src=", " src=", inhoud)
    inhoud = re.sub(r'\sdata-(?:srcset|sizes)="[^"]*"', "", inhoud)
    inhoud = schoon(inhoud, set(), "../../", False, titel).strip()
    # De titel staat nog eens als kop bovenaan
    kop_ = re.match(r"<h[1-6][^>]*>(.*?)</h[1-6]>\s*", inhoud, re.S)
    if kop_ and gelijk(kop_.group(1), titel):
        inhoud = inhoud[kop_.end():]
    return inhoud.strip()


def gelijk(a, b):
    def norm(s):
        return re.sub(r"\W+", "", html.unescape(re.sub(r"<[^>]+>", "", s))).lower()
    return norm(a) == norm(b)


def lees(bron):
    xml = (bron / "wp-xml" / "nieuws.xml").read_text(encoding="utf-8")
    items = xml.split("<item>")[1:]
    bijlagen = {veld(i, "wp:post_id"): veld(i, "wp:attachment_url") for i in items
                if "<wp:post_type><![CDATA[attachment]]>" in i}
    berichten = []
    for i in items:
        if "<wp:post_type><![CDATA[news]]>" not in i or veld(i, "wp:status") != "publish":
            continue
        slug = veld(i, "wp:post_name")
        titel = html.unescape(veld(i, "title")).strip()
        pagina = bron / "nieuws-html" / ("%s.html" % slug)
        if not pagina.is_file():
            print("Geen HTML voor %s, overgeslagen" % slug)
            continue
        tekst = tekst_uit_html(pagina, titel)
        foto = bijlagen.get(meta(i, "_thumbnail_id"), "")
        if not foto:
            m = re.search(r'<img[^>]+src="([^"]+)"', tekst)
            foto = re.sub(r"-\d+x\d+(\.\w+)$", r"\1", m.group(1)) if m else ""
        berichten.append({
            "slug": slug,
            "titel": titel,
            "seo_titel": html.unescape(meta(i, "rank_math_title")).replace("%title%", titel).strip() or titel,
            "beschrijving": html.unescape(meta(i, "rank_math_description")).strip(),
            "datum": veld(i, "wp:post_date").replace(" ", "T"),
            "gewijzigd": veld(i, "wp:post_modified").replace(" ", "T"),
            "foto": foto,
            "tekst": tekst,
        })
    return sorted(berichten, key=lambda b: b["datum"], reverse=True)


def zonder_dubbele_foto(b):
    """De uitgelichte foto staat vaak ook als eerste afbeelding in de tekst."""
    if not b["foto"]:
        return b["tekst"]
    basis = re.sub(r"\.\w+$", "", b["foto"].rsplit("/", 1)[-1])
    m = re.search(r'(<p>\s*)?<img[^>]+src="[^"]*/%s(?:-\d+x\d+)?\.\w+"[^>]*/?>(\s*</p>)?' % re.escape(basis), b["tekst"])
    return b["tekst"][:m.start()] + b["tekst"][m.end():] if m else b["tekst"]


def nieuwskaart(b, root):
    img = '<img src="%s" alt="" loading="lazy">' % esc(b["foto"]) if b["foto"] else ""
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
        out.append('        <figure><img src="%s" alt="%s"></figure>' % (esc(b["foto"]), esc(goede_alt("", b["foto"], b["titel"]))))
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


def main(bron):
    bron = pathlib.Path(bron)
    berichten = lees(bron)
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
    main(sys.argv[1] if len(sys.argv) > 1 else "/mnt/project-files/bron")
