"""Zet de WordPress-artikelen van nijmegenonline.nl om naar statische pagina's.

Leest de REST-export (posts/*.json en categories.json) en data/indeling-artikelen.csv en maakt:
  <slug>/index.html              elk artikel op dezelfde URL als op WordPress
  category/<rubriek>/index.html  overzicht per rubriek
  blog/index.html                "Inspiratie opdoen": alle rubrieken
  _redirects                     301's van oude categoriepagina's naar de nieuwe rubrieken

Afbeeldingen verwijzen voorlopig naar wp-content/uploads op de live site.
Daarna `python tools/build.py` draaien voor header, zijbalk en footer.

Gebruik: python tools/import_wordpress.py /pad/naar/wp-json
"""
import csv
import datetime
import glob
import html
import json
import os
import pathlib
import re
import sys
from collections import Counter, defaultdict

from bs4 import BeautifulSoup, Comment

ROOT = pathlib.Path(__file__).resolve().parent.parent
SITE = "https://www.nijmegenonline.nl"
HANDGEMAAKT = {"kerstmarkten-in-nijmegen"}  # deze pagina's niet overschrijven

RUBRIEKEN = [
    ("eten-drinken-in-nijmegen", "Eten & drinken",
     "De beste restaurants, cafés, lunchplekken en high tea-adressen in Nijmegen, van een snelle hap tot een avond culinair genieten."),
    ("uitgaan-en-cultuur", "Uitgaan & cultuur",
     "Musea, bioscopen, kerken, dansscholen en het uitgaansleven: zo beleef je de cultuur van de oudste stad van Nederland."),
    ("uitjes-en-activiteiten", "Uitjes & activiteiten",
     "Op zoek naar iets leuks om te doen? Uitjes, workshops, cursussen en activiteiten in en rond Nijmegen."),
    ("evenementen-en-seizoen", "Evenementen & seizoen",
     "Kerstmarkten, de Vierdaagse en andere hoogtepunten van het Nijmeegse jaar, met data en praktische tips."),
    ("overnachten-in-nijmegen", "Overnachten",
     "Hotels, B&B's, campings, vakantieparken en camperplaatsen in en rond Nijmegen."),
    ("winkelen-in-nijmegen", "Winkelen",
     "Kringloopwinkels, bloemisten en andere bijzondere winkels in Nijmegen."),
    ("regio-en-dagtrips", "Regio & dagtrips",
     "Net buiten Nijmegen: Kleef, Groesbeek, Wijchen en andere dagtrips in de regio."),
    ("wonen-werken-en-studeren", "Wonen, werken & studeren",
     "Praktische informatie over wonen, werken, ondernemen en studeren in Nijmegen."),
    ("partnerbijdragen", "Partnerbijdragen",
     "Artikelen die tot stand kwamen in samenwerking met onze partners."),
]
RUBRIEK_SLUG = {naam: slug for slug, naam, _ in RUBRIEKEN}
RUBRIEK_NAAM = {slug: naam for slug, naam, _ in RUBRIEKEN}
IN_MENU = [r for r in RUBRIEKEN if r[0] != "partnerbijdragen"]

MAANDEN = ["januari", "februari", "maart", "april", "mei", "juni", "juli",
           "augustus", "september", "oktober", "november", "december"]


def datum_nl(iso):
    d = datetime.date.fromisoformat(iso[:10])
    return "%d %s %d" % (d.day, MAANDEN[d.month - 1], d.year)


def esc(s):
    return html.escape(s, quote=True)


def featured(post, maat="medium_large"):
    try:
        fm = post["_embedded"]["wp:featuredmedia"][0]
    except (KeyError, IndexError):
        return None
    if not fm or "source_url" not in fm:
        return None
    sizes = fm.get("media_details", {}).get("sizes", {})
    for m in (maat, "large", "medium", "full"):
        if m in sizes:
            s = sizes[m]
            return {"src": s["source_url"], "w": s.get("width"), "h": s.get("height"),
                    "alt": fm.get("alt_text") or ""}
    return {"src": fm["source_url"], "w": None, "h": None, "alt": fm.get("alt_text") or ""}


def partner_domeinen():
    data = json.loads((ROOT / "partners" / "partners.json").read_text(encoding="utf-8"))
    return {re.sub(r"^www\.", "", re.sub(r"^https?://", "", p["url"]).split("/")[0]) for p in data["partners"]}


PARTNERS = partner_domeinen()
TOEGESTAAN = {
    "a": {"href"}, "img": {"src", "alt", "width", "height"},
    "td": {"colspan", "rowspan"}, "th": {"colspan", "rowspan"},
}
BLOK = {"p", "h2", "h3", "h4", "h5", "h6", "ul", "ol", "li", "table", "thead", "tbody", "tr", "td", "th",
        "blockquote", "figure", "figcaption"}


def domein(url):
    return re.sub(r"^www\.", "", re.sub(r"^https?://", "", url).split("/")[0].lower())


def schoon(content, slugs, root, gesponsord):
    soup = BeautifulSoup(content, "html.parser")
    for c in soup.find_all(string=lambda t: isinstance(t, Comment)):
        c.extract()
    for t in soup.find_all(["script", "style", "noscript", "form", "input", "textarea", "button", "iframe", "ins", "link"]):
        t.decompose()
    # Flatsome-titel (de h1 bovenaan), gerelateerde-berichtenblokken, scheidingslijnen, Listdom-lijsten
    for t in soup.select(".section-title-container, .box, .is-divider, .gap-element"):
        t.decompose()
    for t in soup.find_all(class_=re.compile(r"^lsd-")):
        if t.parent is not None:
            t.decompose()
    # Bannerlinks van partners: die staan nu in de partnerslider
    for a in soup.find_all("a", href=True):
        if a.find("img") and domein(a["href"]) in PARTNERS:
            a.decompose()
    for h in soup.find_all("h1"):
        h.name = "h2"
    for b in soup.find_all("b"):
        b.name = "strong"
    for i in soup.find_all("i"):
        i.name = "em"
    for t in soup.find_all(["div", "section", "span", "u", "font", "center"]):
        t.unwrap()
    for t in soup.find_all(True):
        keep = TOEGESTAAN.get(t.name, set())
        t.attrs = {k: v for k, v in t.attrs.items() if k in keep}
    for img in soup.find_all("img"):
        src = img.get("src", "")
        if not src or src.startswith("data:"):
            img.decompose()
            continue
        if src.startswith("/"):
            img["src"] = SITE + src
        img["loading"] = "lazy"
    for a in soup.find_all("a"):
        href = a.get("href", "").strip()
        if not href:
            a.unwrap()
            continue
        if href.startswith("/"):
            href = SITE + href
        m = re.match(r"https?://(www\.)?nijmegenonline\.nl/([^/?#]+)/?([?#].*)?$", href)
        if m and m.group(2) in slugs:
            a["href"] = root + m.group(2) + "/"
        elif domein(href).endswith("nijmegenonline.nl"):
            a["href"] = href
        elif href.startswith(("http://", "https://")):
            a["href"] = href
            a["target"] = "_blank"
            a["rel"] = "sponsored noopener" if gesponsord else "noopener"
    # lege alinea's en losse <br>'s opruimen
    for p in soup.find_all(["p", "li", "h2", "h3", "h4", "h5", "h6", "strong", "em"]):
        if not p.get_text(strip=True) and not p.find("img"):
            p.decompose()
    # <p> rond koppen of lijsten (komt uit de Flatsome-opmaak) is ongeldige HTML
    for p in soup.find_all("p"):
        if p.find(["h2", "h3", "h4", "h5", "h6", "ul", "ol", "table", "p", "blockquote"]):
            p.unwrap()
    for a in soup.find_all("a"):
        if a.string:
            a.string = a.string.strip()
    # Koppen zonder tekst eronder (zoals "Ook leuk om te lezen" boven de verwijderde blokken)
    while True:
        laatste = [e for e in soup.contents if getattr(e, "name", None) or str(e).strip()]
        if laatste and getattr(laatste[-1], "name", None) in ("h2", "h3", "h4", "h5", "h6"):
            laatste[-1].decompose()
        else:
            break
    tekst = str(soup)
    tekst = re.sub(r"(<br/?>\s*){2,}", "<br>", tekst)
    tekst = re.sub(r"\n\s*\n+", "\n", tekst)
    for b in BLOK:
        tekst = re.sub(r"\s*(</?%s>)\s*" % b, r"\n\1\n" if b in ("ul", "ol", "table", "thead", "tbody", "tr") else r"\1", tekst)
    tekst = re.sub(r"(</(p|h[2-6]|ul|ol|table|blockquote|figure)>)", r"\1\n", tekst)
    tekst = re.sub(r"\n{2,}", "\n", tekst).strip()
    return "\n".join("        " + r for r in tekst.split("\n"))


def samenvatting(content, n=155):
    t = BeautifulSoup(content, "html.parser")
    for x in t.select(".section-title-container, .box, script, style"):
        x.decompose()
    alineas = [x.get_text(" ") for x in t.find_all("p")]
    t = re.sub(r"\s+", " ", " ".join(alineas) if alineas else t.get_text(" ")).strip()
    if len(t) <= n:
        return t
    return t[:n].rsplit(" ", 1)[0].rstrip(",.;:") + "…"


def kop(titel, beschrijving, canonical, root, afbeelding=None, extra=""):
    og_img = '\n  <meta property="og:image" content="%s">' % esc(afbeelding) if afbeelding else ""
    return """<!doctype html>
<html lang="nl">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="robots" content="noindex, nofollow">
  <title>{titel} | NijmegenOnline</title>
  <meta name="description" content="{beschrijving}">
  <link rel="canonical" href="{canonical}">
  <meta property="og:locale" content="nl_NL">
  <meta property="og:title" content="{titel}">
  <meta property="og:description" content="{beschrijving}">
  <meta property="og:url" content="{canonical}">
  <meta property="og:site_name" content="NijmegenOnline">{og_img}
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Raleway:wght@500;600;700&display=swap">
  <link rel="stylesheet" href="{root}assets/css/site.css">
  <link rel="stylesheet" href="{root}partners/slider.css?v=3">
  <script src="{root}partners/slider.js?v=3" defer></script>{extra}
</head>
<body>
  <div class="testbalk">Dit is een testomgeving. De echte pagina staat op <a href="{canonical}">www.nijmegenonline.nl</a>.</div>

  <!-- header --><!-- /header -->
""".format(titel=esc(titel), beschrijving=esc(beschrijving), canonical=esc(canonical), root=root,
           og_img=og_img, extra=extra)


VOET = """
  <!-- footer --><!-- /footer -->
</body>
</html>
"""


def kaart(a, root):
    img = ""
    if a["img"]:
        img = '<img src="%s" alt="" loading="lazy"%s>' % (
            esc(a["img"]["src"]),
            ' width="%s" height="%s"' % (a["img"]["w"], a["img"]["h"]) if a["img"]["w"] else "")
    return ('<article class="kaart"><a href="%s%s/">%s<div class="kaart__tekst"><h3>%s</h3><p>%s</p></div></a></article>'
            % (root, a["slug"], img, esc(a["titel"]), esc(a["samenvatting"])))


def artikel_pagina(a, gerelateerd):
    root = "../"
    canonical = "%s/%s/" % (SITE, a["slug"])
    rub = a["rubriek"]
    ld = {
        "@context": "https://schema.org", "@type": "Article", "headline": a["titel"],
        "datePublished": a["date"], "dateModified": a["modified"], "mainEntityOfPage": canonical,
        "publisher": {"@type": "Organization", "name": "NijmegenOnline", "url": SITE + "/"},
    }
    if a["img"]:
        ld["image"] = a["img"]["src"]
    extra = '\n  <script type="application/ld+json">%s</script>' % json.dumps(ld, ensure_ascii=False)
    out = [kop(a["titel"], a["samenvatting"], canonical, root, a["img"]["src"] if a["img"] else None, extra)]
    out.append('  <main class="artikel-wrap">\n    <div class="container">\n      <div class="artikel-layout">\n      <article class="artikel">')
    out.append('        <div class="kruimelpad"><a href="../">Home</a> › <a href="../blog/">Inspiratie opdoen</a> › <a href="../category/%s/">%s</a></div>'
               % (rub, esc(RUBRIEK_NAAM[rub])))
    if rub == "partnerbijdragen":
        out.append('        <p class="partnerlabel">Partnerbijdrage</p>')
    out.append("        <h1>%s</h1>" % esc(a["titel"]))
    bij = "Gepubliceerd op %s" % datum_nl(a["date"])
    if a["modified"][:10] != a["date"][:10]:
        bij += ", bijgewerkt op %s" % datum_nl(a["modified"])
    out.append('        <p class="bijgewerkt">%s</p>' % bij)
    if a["img"]:
        out.append('        <figure><img src="%s" alt="%s"%s></figure>' % (
            esc(a["img"]["src"]), esc(a["img"]["alt"] or a["titel"]),
            ' width="%s" height="%s"' % (a["img"]["w"], a["img"]["h"]) if a["img"]["w"] else ""))
    out.append('        <div class="partner-slider" data-plaatsing="blog"></div>')
    out.append('        <div class="inhoud-tekst">\n%s\n        </div>' % a["html"])
    out.append("      </article>\n\n      <!-- zijbalk --><!-- /zijbalk -->\n      </div>")
    if gerelateerd:
        out.append('\n      <section class="gerelateerd" aria-labelledby="meer-lezen">\n        <h2 id="meer-lezen">Meer over %s</h2>\n        <div class="raster">'
                   % esc(RUBRIEK_NAAM[rub].lower() if rub != "partnerbijdragen" else "Nijmegen"))
        for g in gerelateerd:
            out.append("          " + kaart(g, root))
        out.append("        </div>\n      </section>")
    out.append("    </div>\n  </main>")
    out.append(VOET)
    return "\n".join(out)


def rubriek_pagina(slug, naam, intro, artikelen):
    root = "../../"
    canonical = "%s/category/%s/" % (SITE, slug)
    out = [kop(naam + " in Nijmegen" if slug != "partnerbijdragen" else naam, intro, canonical, root)]
    out.append('  <main class="artikel-wrap">\n    <div class="container">')
    out.append('      <div class="kruimelpad"><a href="../../">Home</a> › <a href="../../blog/">Inspiratie opdoen</a> › %s</div>' % esc(naam))
    out.append('      <header class="rubriek-kop">\n        <h1>%s</h1>\n        <p>%s</p>\n      </header>' % (esc(naam), esc(intro)))
    out.append('      <nav class="rubriek-menu" aria-label="Rubrieken">')
    for s, n, _ in IN_MENU:
        cur = ' aria-current="page"' if s == slug else ""
        out.append('        <a href="../%s/"%s>%s</a>' % (s, cur, esc(n)))
    out.append("      </nav>")
    out.append('      <div class="partner-slider" data-plaatsing="blog"></div>')
    out.append('      <div class="raster rubriek-raster">')
    for a in artikelen:
        out.append("        " + kaart(a, root))
    out.append("      </div>\n    </div>\n  </main>")
    out.append(VOET)
    return "\n".join(out)


def blog_pagina(per_rubriek):
    root = "../"
    canonical = SITE + "/blog/"
    intro = "Tips en artikelen over eten, uitgaan, uitjes, overnachten en wonen in Nijmegen en omgeving."
    out = [kop("Inspiratie opdoen", intro, canonical, root)]
    out.append('  <main class="artikel-wrap">\n    <div class="container">')
    out.append('      <div class="kruimelpad"><a href="../">Home</a> › Inspiratie opdoen</div>')
    out.append('      <header class="rubriek-kop">\n        <h1>Inspiratie opdoen</h1>\n        <p>%s</p>\n      </header>' % esc(intro))
    out.append('      <div class="partner-slider" data-plaatsing="blog"></div>')
    for slug, naam, _ in IN_MENU:
        arts = per_rubriek.get(slug, [])
        if not arts:
            continue
        out.append('      <section class="blog-rubriek">\n        <div class="blog-rubriek__kop"><h2>%s</h2><a href="../category/%s/">Alle %d artikelen</a></div>\n        <div class="raster">'
                   % (esc(naam), slug, len(arts)))
        for a in arts[:4]:
            out.append("          " + kaart(a, "../"))
        out.append("        </div>\n      </section>")
    out.append("    </div>\n  </main>")
    out.append(VOET)
    return "\n".join(out)


def main(bron):
    bron = pathlib.Path(bron)
    posts = [p for f in sorted(glob.glob(str(bron / "posts" / "posts-*.json"))) for p in json.load(open(f, encoding="utf-8"))]
    cats = {c["id"]: c for c in json.load(open(bron / "categories.json", encoding="utf-8"))}
    indeling = {r["url"].strip("/"): r for r in csv.DictReader(open(ROOT / "data" / "indeling-artikelen.csv", encoding="utf-8"), delimiter=";")}
    slugs = {p["slug"] for p in posts}

    artikelen = []
    for p in posts:
        r = indeling.get(p["slug"])
        rub = RUBRIEK_SLUG[r["nieuwe_rubriek"]] if r else "wonen-werken-en-studeren"
        a = {
            "slug": p["slug"], "titel": html.unescape(p["title"]["rendered"]), "date": p["date"], "modified": p["modified"],
            "rubriek": rub, "img": featured(p), "samenvatting": samenvatting(p["content"]["rendered"]),
            "verkeer": int(r["verkeer"]) if r and r["verkeer"] else 0, "cats": p["categories"],
        }
        a["html"] = schoon(p["content"]["rendered"], slugs, "../", rub == "partnerbijdragen")
        artikelen.append(a)

    per_rubriek = defaultdict(list)
    for a in sorted(artikelen, key=lambda a: (-a["verkeer"], a["date"]), reverse=False):
        per_rubriek[a["rubriek"]].append(a)
    for lijst in per_rubriek.values():
        lijst.sort(key=lambda a: (-a["verkeer"], -int(a["date"][:10].replace("-", ""))))

    for a in artikelen:
        if a["slug"] in HANDGEMAAKT:
            continue
        gerel = [g for g in per_rubriek[a["rubriek"]] if g["slug"] != a["slug"]][:4]
        d = ROOT / a["slug"]
        d.mkdir(exist_ok=True)
        (d / "index.html").write_text(artikel_pagina(a, gerel), encoding="utf-8")

    for slug, naam, intro in RUBRIEKEN:
        d = ROOT / "category" / slug
        d.mkdir(parents=True, exist_ok=True)
        (d / "index.html").write_text(rubriek_pagina(slug, naam, intro, per_rubriek.get(slug, [])), encoding="utf-8")

    (ROOT / "blog").mkdir(exist_ok=True)
    (ROOT / "blog" / "index.html").write_text(blog_pagina(per_rubriek), encoding="utf-8")

    # Oude categoriepagina's: naar de rubriek waar de meeste van hun artikelen nu in staan
    stemmen = defaultdict(Counter)
    for a in artikelen:
        for c in a["cats"]:
            if a["rubriek"] != "partnerbijdragen":  # geen bezoekers naar partnerbijdragen sturen
                stemmen[c][a["rubriek"]] += 1
    regels = ["# Doorverwijzingen (Cloudflare Pages / Netlify). Gemaakt door tools/import_wordpress.py"]
    nieuw = {"/category/%s/" % s for s, _, _ in RUBRIEKEN}
    for cid, c in sorted(cats.items(), key=lambda x: x[1]["link"]):
        oud = "/" + c["link"].split("nijmegenonline.nl/", 1)[1]
        if oud in nieuw:
            continue
        doel = "/category/%s/" % stemmen[cid].most_common(1)[0][0] if stemmen[cid] else "/blog/"
        regels.append("%s %s 301" % (oud, doel))
    (ROOT / "_redirects").write_text("\n".join(regels) + "\n", encoding="utf-8")

    print("%d artikelen, %d rubrieken, %d doorverwijzingen" % (len(artikelen), len(RUBRIEKEN), len(regels) - 1))
    for slug, naam, _ in RUBRIEKEN:
        print("  %-28s %d" % (naam, len(per_rubriek.get(slug, []))))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "/mnt/project-files/bron/wp-json")
