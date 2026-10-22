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
STANDAARD_AFBEELDING = SITE + "/assets/img/logo-nijmegenonline.png"
# Zoekwoord, SEO-titel en meta description per artikel (zie README)
SEO = {r["url"]: r for r in csv.DictReader(
    open(ROOT / "data" / "seo-artikelen.csv", encoding="utf-8"), delimiter=";")}
# Gidsen: themapagina's die artikelen over één onderwerp bundelen (bestaande WordPress-URL's)
GIDSEN = json.load(open(ROOT / "data" / "gidsen.json", encoding="utf-8"))
ARTIKEL_GIDS = {}   # slug -> eerste gids
ARTIKEL_GIDSEN = {}  # slug -> alle gidsen waar het artikel in staat
for _g in GIDSEN:
    for _sec in _g["secties"]:
        for _slug in _sec["artikelen"]:
            ARTIKEL_GIDS.setdefault(_slug, _g)
            if _g not in ARTIKEL_GIDSEN.setdefault(_slug, []):
                ARTIKEL_GIDSEN[_slug].append(_g)
# Samengevoegde artikelen: het oude artikel verdwijnt en krijgt een 301 naar het nieuwe.
# De samengevoegde tekst van het nieuwe artikel staat in data/samengevoegd/<slug>.html
SAMENVOEGEN = {r["oud"]: r["nieuw"] for r in csv.DictReader(
    open(ROOT / "data" / "samenvoegen.csv", encoding="utf-8"), delimiter=";")}
SAMENGEVOEGD_OP = "2026-10-21T12:00:00"
# Kleine tekstcorrecties per artikel (verouderde jaartallen, gesloten zaken)
CORRECTIES = json.load(open(ROOT / "data" / "correcties.json", encoding="utf-8"))
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
# Oud-partners: hun banners staan nog in oude artikelen, maar horen er niet meer in
# Eigen keuze voor de uitgelichte foto, waar WordPress er geen (openbare) heeft
EIGEN_FOTO = {
    "museums-in-nijmegen-wat-ga-jij-ontdekken": ("/wp-content/uploads/2023/09/zja-vrijheidsmuseum-groesbeek-8-kleiner.jpg",
                                                 "Het Vrijheidsmuseum in Groesbeek bij Nijmegen"),
}
OUD_PARTNERS = {"fotowandelingnijmegen.nl", "danscentrumvermeulen.nl", "modelspoorwebshop.nl"}
TOEGESTAAN = {
    "a": {"href"}, "img": {"src", "alt", "width", "height"},
    "td": {"colspan", "rowspan"}, "th": {"colspan", "rowspan"},
}
BLOK = {"p", "h2", "h3", "h4", "h5", "h6", "ul", "ol", "li", "table", "thead", "tbody", "tr", "td", "th",
        "blockquote", "figure", "figcaption"}


def goede_alt(alt, src, titel):
    """Lege alt-teksten en stockfoto-omschrijvingen ("Wedding,Table,Settings,...") vervangen
    door de bestandsnaam, die op deze site vrijwel altijd beschrijvend is."""
    alt = (alt or "").strip()
    if alt and alt.count(",") < 3 and not re.search(r"\b(shutterstock|stock photo|19|20)\d{2}\b", alt, re.I):
        return alt
    naam = re.sub(r"(-\d+x\d+|-scaled|-\d+)?\.\w+$", "", src.rsplit("/", 1)[-1])
    woorden = re.sub(r"[-_]+", " ", naam).strip()
    if len(woorden) < 8 or re.search(r"^(img|dsc|image|screenshot|schermafbeelding|whatsapp)|\d{4,}", woorden, re.I):
        return titel
    return woorden[0].upper() + woorden[1:]


def domein(url):
    return re.sub(r"^www\.", "", re.sub(r"^https?://", "", url).split("/")[0].lower())


def schoon(content, slugs, root, gesponsord, titel=""):
    # Kapotte AdSense-tag uit WordPress (<insclass=...>, zonder spatie)
    content = re.sub(r"<insclass[^>]*>.*?</ins>", "", content, flags=re.S)
    soup = BeautifulSoup(content, "html.parser")
    # Vaste voettekst "NijmegenOnline.nl is de plek voor ..." onder sommige artikelen
    for h in soup.find_all(["h2", "h3"]):
        if h.get_text(strip=True) == "NijmegenOnline.nl":
            nxt = h.find_next(lambda t: t.name == "p" and t.get_text(strip=True))
            if nxt is not None and nxt.get_text(strip=True).startswith("NijmegenOnline.nl is de plek"):
                nxt.decompose()
            h.decompose()
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
        if a.find("img") and domein(a["href"]) in PARTNERS | OUD_PARTNERS:
            a.decompose()
    for h in soup.find_all("h1"):
        h.name = "h2"
    for b in soup.find_all("b"):
        b.name = "strong"
    for i in soup.find_all("i"):
        i.name = "em"
    for t in soup.find_all(["div", "section", "span", "u", "font", "center"]):
        t.unwrap()
    # Koppen die WordPress in een losse lijst zette (gaf een los nummer of bolletje ervoor)
    for lijst in soup.find_all(["ul", "ol"]):
        items = lijst.find_all("li", recursive=False)
        if items and all(li.find(re.compile(r"^h[2-6]$")) and not li.get_text(strip=True).replace(
                li.find(re.compile(r"^h[2-6]$")).get_text(strip=True), "") for li in items):
            for li in items:
                li.unwrap()
            lijst.unwrap()
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
        img["alt"] = goede_alt(img.get("alt", ""), img["src"], titel)
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
    # "Ook leuk om te lezen" zonder de (verwijderde) blokken eronder
    tekst = re.sub(r"<h[2-6][^>]*>(<strong>)?\s*Ook leuk om te lezen\s*(</strong>)?</h[2-6]>(?=(\s|</?(div|section|p)[^>]*>)*$)", "", tekst)
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
    og_img = '\n  <meta property="og:image" content="%s">' % esc(afbeelding or STANDAARD_AFBEELDING)
    # Google toont ongeveer 60 tekens; de sitenaam alleen erachter als het past
    paginatitel = titel + " | NijmegenOnline" if len(titel) <= 43 else titel
    return """<!doctype html>
<html lang="nl">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="robots" content="noindex, nofollow">
  <title>{paginatitel}</title>
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
  <link rel="stylesheet" href="{root}assets/css/site.css?v=18">
  <link rel="stylesheet" href="{root}partners/slider.css?v=5">
  <script src="{root}partners/slider.js?v=5" defer></script>{extra}
</head>
<body>
  <div class="testbalk">Dit is een testomgeving. De echte pagina staat op <a href="{canonical}">www.nijmegenonline.nl</a>.</div>

  <!-- header --><!-- /header -->
""".format(titel=esc(titel), paginatitel=esc(paginatitel), beschrijving=esc(beschrijving), canonical=esc(canonical), root=root,
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


DOORVERWIJZING = """<!doctype html>
<html lang="nl">
<head>
  <meta charset="utf-8">
  <meta name="robots" content="noindex">
  <title>%(titel)s</title>
  <link rel="canonical" href="%(url)s">
  <meta http-equiv="refresh" content="0; url=%(pad)s">
</head>
<body>
  <p>Dit artikel is samengevoegd met <a href="%(pad)s">%(titel)s</a>.</p>
</body>
</html>
"""


def link_naar_gids(tekst, g, root):
    """Linkt de eerste keer dat de gidsnaam in een alinea of opsomming staat naar de gids.
    Niet in koppen of bestaande links, en niet als het artikel al naar de gids linkt."""
    doel = root + g["url"].lstrip("/")
    if 'href="%s"' % doel in tekst:
        return tekst
    zoek = re.compile(r"\b%s\b" % re.escape(g["naam"]), re.I)
    stukken = re.split(r"(<[^>]+>)", tekst)
    open_ = []
    for i, st in enumerate(stukken):
        if st.startswith("<"):
            m = re.match(r"<(/?)([a-z0-9]+)", st, re.I)
            if m:
                tag = m.group(2).lower()
                if m.group(1):
                    if tag in open_:
                        del open_[len(open_) - 1 - open_[::-1].index(tag)]
                elif not st.endswith("/>") and tag not in ("img", "br", "hr", "source", "input"):
                    open_.append(tag)
            continue
        if any(t in open_ for t in ("a", "h1", "h2", "h3", "h4", "h5", "h6", "figcaption", "button")):
            continue
        if not any(t in open_ for t in ("p", "li")):
            continue
        m = zoek.search(st)
        if m:
            stukken[i] = st[:m.start()] + '<a href="%s">%s</a>' % (doel, m.group(0)) + st[m.end():]
            return "".join(stukken)
    return tekst


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
    seo = SEO.get("/%s/" % a["slug"], {})
    out = [kop(seo.get("seo_titel") or a["titel"], seo.get("meta_description") or a["samenvatting"], canonical, root,
               a["img"]["src"] if a["img"] else a["eerste_img"], extra)]
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
    gids = ARTIKEL_GIDS.get(a["slug"])
    gidsen = ARTIKEL_GIDSEN.get(a["slug"], [])
    if gidsen:
        links = ['<a href="%s%s">%s</a>' % (root, x["url"].lstrip("/"), esc(x["naam"])) for x in gidsen]
        out.append('        <p class="gidslabel">Onderdeel van de gids %s</p>'
                   % (links[0] if len(links) == 1 else ", ".join(links[:-1]) + " en " + links[-1]))
    if a["img"] and not a["img"].get("uit_tekst"):
        out.append('        <figure><img src="%s" alt="%s"%s></figure>' % (
            esc(a["img"]["src"]), esc(goede_alt(a["img"]["alt"], a["img"]["src"], a["titel"])),
            ' width="%s" height="%s"' % (a["img"]["w"], a["img"]["h"]) if a["img"]["w"] else ""))
    out.append('        <div class="partner-slider" data-plaatsing="blog"></div>')
    tekst = a["html"]
    if a["img"] and not a["img"].get("uit_tekst"):
        # Dezelfde foto staat vaak ook bovenaan in de tekst: dan niet twee keer tonen
        def basis(src):
            return re.sub(r"-\d+x\d+$", "", src.rsplit("/", 1)[-1].rsplit(".", 1)[0])
        m = re.search(r'<img[^>]+src="([^"]+)"[^>]*>', tekst)
        if m and basis(m.group(1)) == basis(a["img"]["src"]):
            tekst = tekst[:m.start()] + tekst[m.end():]
    for x in gidsen:
        tekst = link_naar_gids(tekst, x, root)
    for x in BESTEMMINGEN:
        if a["slug"] in x["lees_ook"]:
            tekst = link_naar_gids(tekst, {"url": "/bestemmingen/%s/" % x["slug"], "naam": x.get("zoek", x["naam"])}, root)
    out.append('        <div class="inhoud-tekst">\n%s\n        </div>' % tekst)
    out.append("      </article>\n\n      <!-- zijbalk --><!-- /zijbalk -->\n      </div>")
    if gerelateerd:
        kopje = ("Meer uit de gids " + gids["naam"]) if gids else "Meer over %s" % (
            RUBRIEK_NAAM[rub].lower() if rub != "partnerbijdragen" else "Nijmegen")
        out.append('\n      <section class="gerelateerd" aria-labelledby="meer-lezen">\n        <h2 id="meer-lezen">%s</h2>\n        <div class="raster">'
                   % esc(kopje))
        for g in gerelateerd:
            out.append("          " + kaart(g, root))
        out.append("        </div>")
        if gids:
            out.append('        <p class="gids-verder"><a href="%s%s">Bekijk de hele gids %s</a></p>'
                       % (root, gids["url"].lstrip("/"), esc(gids["naam"])))
        out.append("      </section>")
    out.append("    </div>\n  </main>")
    out.append(VOET)
    return "\n".join(out)


def gids_pagina(g, per_slug):
    diepte = g["url"].strip("/").count("/") + 1
    root = "../" * diepte
    canonical = SITE + g["url"]
    kruimels = [("Home", root), ("Gidsen", root + "thema/")]
    if g.get("hoofdgids"):
        hg = next(x for x in GIDSEN if x["url"] == g["hoofdgids"])
        kruimels.append((hg["naam"], root + hg["url"].lstrip("/")))
    ld = [{"@context": "https://schema.org", "@type": "CollectionPage", "name": g["naam"], "url": canonical,
           "description": g["beschrijving"]},
          {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
              {"@type": "ListItem", "position": i + 1, "name": n, "item": SITE + "/" + u[len(root):]}
              for i, (n, u) in enumerate(kruimels)] + [
              {"@type": "ListItem", "position": len(kruimels) + 1, "name": g["naam"], "item": canonical}]}]
    if g["faq"]:
        ld.append({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": f["v"], "acceptedAnswer": {"@type": "Answer", "text": f["a"]}} for f in g["faq"]]})
    extra = "".join('\n  <script type="application/ld+json">%s</script>' % json.dumps(x, ensure_ascii=False) for x in ld)
    eerste = next((per_slug[x] for sec in g["secties"] for x in sec["artikelen"] if x in per_slug and per_slug[x]["img"]), None)
    deel = SITE + g["foto"] if g.get("foto") else (eerste["img"]["src"] if eerste else None)
    out = [kop(g["seo_titel"], g["beschrijving"], canonical, root, deel, extra)]
    out.append('  <main class="artikel-wrap">\n    <div class="container">\n      <div class="artikel-layout">\n      <article class="artikel gids">')
    out.append('        <div class="kruimelpad">%s › %s</div>' % (
        " › ".join('<a href="%s">%s</a>' % (u, esc(n)) for n, u in kruimels), esc(g["naam"])))
    out.append('        <p class="gidslabel">Gids</p>')
    out.append("        <h1>%s</h1>" % esc(g["naam"]))
    out.append('        <div class="inhoud-tekst gids-intro">\n%s\n        </div>' % g["intro"])
    ankers = [(re.sub(r"[^a-z0-9]+", "-", sec["kop"].lower()).strip("-"), sec["kop"]) for sec in g["secties"]]
    if len(ankers) > 1 or g["faq"]:
        out.append('        <nav class="gids-inhoud" aria-label="In deze gids"><strong>In deze gids</strong><ul>')
        for an, k in ankers:
            out.append('          <li><a href="#%s">%s</a></li>' % (an, esc(k)))
        if g["faq"]:
            out.append('          <li><a href="#veelgestelde-vragen">Veelgestelde vragen</a></li>')
        out.append("        </ul></nav>")
    out.append('        <div class="partner-slider" data-plaatsing="blog"></div>')
    for (an, _), sec in zip(ankers, g["secties"]):
        out.append('        <section class="gids-sectie" id="%s">\n          <h2>%s</h2>\n          <div class="inhoud-tekst">%s</div>\n          <div class="raster">'
                   % (an, esc(sec["kop"]), sec["tekst"]))
        for x in sec["artikelen"]:
            if x in per_slug:
                out.append("            " + kaart(per_slug[x], root))
        out.append("          </div>\n        </section>")
    subs = [x for x in GIDSEN if x.get("hoofdgids") == g["url"]]
    if subs:
        out.append('        <section class="gids-sectie"><h2>Meer gidsen over dit onderwerp</h2><ul class="gids-lijst">')
        for x in subs:
            out.append('          <li><a href="%s%s">%s</a></li>' % (root, x["url"].lstrip("/"), esc(x["naam"])))
        out.append("        </ul></section>")
    groep = next(((n, urls) for n, urls in GIDS_GROEPEN if g["url"] in urls), None)
    buren = [x for x in GIDSEN if groep and x["url"] in groep[1] and x["url"] != g["url"]
             and x["url"] != g.get("hoofdgids") and x not in subs]
    if buren:
        out.append('        <section class="gids-sectie"><h2>Andere gidsen: %s</h2><ul class="gids-lijst">' % esc(groep[0].lower()))
        for x in buren:
            out.append('          <li><a href="%s%s">%s</a></li>' % (root, x["url"].lstrip("/"), esc(x["naam"])))
        out.append("        </ul></section>")
    if g["faq"]:
        out.append('        <section class="gids-sectie faq" id="veelgestelde-vragen">\n          <h2>Veelgestelde vragen</h2>')
        for f in g["faq"]:
            out.append("          <details><summary>%s</summary><p>%s</p></details>" % (esc(f["v"]), esc(f["a"])))
        out.append("        </section>")
    if g["bedrijvengids"]:
        tekst = "Zet je bedrijf in de bedrijvengids" if "aanmelden" in g["bedrijvengids"] else "Bekijk de bedrijven in de bedrijvengids"
        out.append('        <p class="gids-cta"><a class="knop" href="%s%s">%s</a></p>' % (SITE, g["bedrijvengids"], tekst))
    out.append("      </article>\n\n      <!-- zijbalk --><!-- /zijbalk -->\n      </div>\n    </div>\n  </main>")
    out.append(VOET)
    return "\n".join(out)


def gidsen_overzicht(per_slug):
    root = "../"
    canonical = SITE + "/thema/"
    out = [kop("Gidsen over Nijmegen", "Alle gidsen van NijmegenOnline op een rij: trouwen, restaurants, cafés, overnachten, studeren, ondernemen, de Vierdaagse en meer in Nijmegen.", canonical, root)]
    out.append('  <main class="artikel-wrap">\n    <div class="container">')
    out.append('      <div class="kruimelpad"><a href="../">Home</a> › Gidsen</div>')
    out.append('      <header class="rubriek-kop">\n        <h1>Gidsen over Nijmegen</h1>\n        <p>Alles over één onderwerp op één plek. Elke gids bundelt onze artikelen, tips en antwoorden op veelgestelde vragen.</p>\n      </header>')
    out.append('      <div class="gidsen-filter" role="group" aria-label="Filter op onderwerp">')
    out.append('        <button type="button" data-groep="" aria-pressed="true">Alle gidsen</button>')
    for i, (groep, _) in enumerate(GIDS_GROEPEN):
        out.append('        <button type="button" data-groep="%d" aria-pressed="false">%s</button>' % (i, esc(groep)))
    out.append("      </div>")
    out.append('      <div class="gidsen-raster">')
    al = set()
    for i, (groep, urls) in enumerate(GIDS_GROEPEN):
        for u in urls:
            g = next(x for x in GIDSEN if x["url"] == u)
            arts = [per_slug[x] for sec in g["secties"] for x in sec["artikelen"] if x in per_slug]
            src = SITE + g["foto"] if g.get("foto") else next(
                (a["img"]["src"] for a in sorted(arts, key=lambda a: -a["verkeer"]) if a["img"] and a["img"]["src"] not in al), None)
            al.add(src)
            img = ('<img src="%s" alt="" loading="lazy">' % esc(src)) if src else ""
            out.append('        <a class="gidskaart" data-groep="%d" href="%s">%s<div class="gidskaart__tekst"><span class="gidskaart__groep">%s</span><h2>%s</h2><p>%s</p>'
                       '<span class="gidskaart__meer">%d artikelen <span aria-hidden="true">→</span></span></div></a>'
                       % (i, root + g["url"].lstrip("/"), img, esc(groep), esc(g["naam"]), esc(g["kort"]), len({a["slug"] for a in arts})))
    out.append("      </div>")
    out.append('      <div class="partner-slider" data-plaatsing="blog"></div>')
    out.append('''      <script>
        document.querySelectorAll('.gidsen-filter button').forEach(function (knop) {
          knop.addEventListener('click', function () {
            var groep = knop.getAttribute('data-groep');
            document.querySelectorAll('.gidsen-filter button').forEach(function (k) { k.setAttribute('aria-pressed', k === knop); });
            document.querySelectorAll('.gidskaart').forEach(function (kaart) {
              kaart.hidden = groep !== '' && kaart.getAttribute('data-groep') !== groep;
            });
          });
        });
      </script>''')
    out.append("    </div>\n  </main>")
    out.append(VOET)
    return "\n".join(out)


HOME_GIDSEN = ["/thema/restaurants-in-nijmegen-restaurant/", "/thema/trouwen-in-nijmegen/", "/thema/overnachten-in-nijmegen/",
               "/thema/bb-nijmegen/", "/jaarlijkse-evenementen/nijmeegse-vierdaagse/", "/thema/studeren-in-nijmegen/",
               "/thema/zaal-huren-in-nijmegen/", "/thema/cafes-in-nijmegen/"]
GIDS_GROEPEN = [
    ("Eten, drinken en cultuur", ["/thema/restaurants-in-nijmegen-restaurant/", "/thema/cafes-in-nijmegen/", "/thema/museums-nijmegen/"]),
    ("Bijzondere momenten", ["/thema/trouwen-in-nijmegen/", "/thema/zaal-huren-in-nijmegen/", "/jaarlijkse-evenementen/nijmeegse-vierdaagse/", "/thema/fotograaf-nijmegen-ontdek-de-mooiste-locaties-beste-fotografen/"]),
    ("Overnachten", ["/thema/overnachten-in-nijmegen/", "/thema/bb-nijmegen/", "/thema/campings-in-nijmegen/"]),
    ("Verzorging", ["/thema/kappers-in-nijmegen/", "/thema/massage-nijmegen/", "/thema/nagelsalon-in-nijmegen/", "/thema/pedicures-in-nijmegen/", "/thema/permanente-make-up-in-nijmegen/"]),
    ("Wonen, leren en werken", ["/thema/studeren-in-nijmegen/", "/thema/cursus-nijmegen/", "/ondernemen-in-nijmegen/", "/thema/winkelen-in-nijmegen/"]),
]


BESTEMMINGEN = json.load(open(ROOT / "data" / "bestemmingen.json", encoding="utf-8"))
WEG_KOPPEN = re.compile(r"bedrijven\s*overzicht|overzicht bedrijven|overige bestemmingen|nog meer leesplezier", re.I)


def pas_correcties_toe(sleutel, tekst):
    for c in (c for c in CORRECTIES if c["artikel"] == sleutel):
        if "regex" in c:
            tekst, n = re.subn(c["regex"], c["nieuw"], tekst, flags=re.S)
        else:
            n = tekst.count(c["oud"])
            tekst = tekst.replace(c["oud"], c["nieuw"])
        if not n:
            raise SystemExit("Correctie past niet meer bij %s: %s" % (sleutel, c.get("oud", c.get("regex"))[:60]))
    return tekst


def bestemming_inhoud(b, content):
    """Maakt van een Flatsome-bestemmingspagina een gewone tekst: titel, ondertitel en de vaste
    blokken eruit, dubbele foto's weg, foto's die naast elkaar stonden als fotorij."""
    html_ = pas_correcties_toe("bestemmingen/" + b["slug"], schoon(content, set(), "../../", False, b["naam"]))
    soup = BeautifulSoup(html_, "html.parser")
    for h in soup.find_all("h6"):
        h.decompose()
    namen = {b["naam"].lower(), b["slug"].replace("nijmegen-", "").replace("-", " ")}
    koppen = soup.find_all(["h2", "h3"])
    # De paginatitel (de plaatsnaam in hoofdletters) en de slogan eronder
    ondertitel = ""
    if koppen and koppen[0].get_text(" ", strip=True).lower().split(" (")[0] in namen:
        koppen[0].decompose()
        volgende = koppen[1] if len(koppen) > 1 else None
        if volgende is not None and len(volgende.get_text(strip=True)) > 25:
            ondertitel = volgende.get_text(" ", strip=True)
            ondertitel = re.sub(r"^%s:\s*" % re.escape(b["naam"]), "", ondertitel, flags=re.I)
            ondertitel = ondertitel[:1].upper() + ondertitel[1:]
            volgende.decompose()
    for h in soup.find_all(["h2", "h3", "h4"]):
        if WEG_KOPPEN.search(h.get_text()):
            h.decompose()
    for a in soup.find_all("a", href=True):
        tekst = a.get_text(" ", strip=True)
        if a["href"].rstrip("/").endswith("/bestemmingen") or not tekst and not a.find("img"):
            a.decompose()
        elif tekst.isupper() or re.search(r"[A-Z]{4,}", tekst):
            a.string = re.sub(r"\b[A-Z][A-Z ]{3,}[A-Z]\b", lambda m: b["naam"] if m.group(0).lower() in namen else m.group(0).capitalize(), tekst)
            a.string = a.string[:1].upper() + a.string[1:].lower() if a.string.isupper() else a.string
    for h in soup.find_all(["h2", "h3"]):
        t = h.get_text(" ", strip=True)
        nieuw = re.sub(r"\b[A-Z][A-Z ()]{3,}[A-Z)]\b", lambda m: b["naam"] if m.group(0).split(" (")[0].lower() in namen else m.group(0), t)
        nieuw = re.sub(r"\b[A-Z]{4,}\b", lambda m: m.group(0).capitalize(), nieuw)
        if nieuw.lower() == "overzicht restaurant":
            nieuw = "Restaurants om te proberen"
            h.name = "h3"
        if nieuw != t or h.find("strong"):
            h.clear()
            h.string = nieuw
    # Foto's: elke foto één keer; de eerste wordt de grote foto bovenaan
    gezien, eerste = set(), None
    for img in soup.find_all("img"):
        src = img.get("src", "")
        if src in gezien:
            img.decompose()
            continue
        gezien.add(src)
        if eerste is None:
            eerste = {"src": src, "alt": img.get("alt", ""), "w": img.get("width"), "h": img.get("height")}
            img.decompose()
    for br in soup.find_all("br"):
        ouder = br.parent
        if ouder is not None and ouder.name == "p" and ouder.find("img"):
            br.decompose()
    for p in soup.find_all("p"):
        # <br> aan het begin of eind van een alinea (resten van de Flatsome-opmaak)
        while p.contents and (getattr(p.contents[0], "name", None) == "br" or not str(p.contents[0]).strip()):
            p.contents[0].extract()
        while p.contents and (getattr(p.contents[-1], "name", None) == "br" or not str(p.contents[-1]).strip()):
            p.contents[-1].extract()
        if not p.get_text(strip=True) and not p.find(["img", "a"]):
            p.decompose()
        elif len(p.find_all("img")) > 1 and not p.get_text(strip=True):
            p["class"] = "fotos"
    # Alinea's die helemaal vet zijn (de introductie): gewone tekst
    for p in soup.find_all("p"):
        kinderen = [k for k in p.contents if str(k).strip()]
        if len(kinderen) == 1 and getattr(kinderen[0], "name", None) == "strong" and len(p.get_text()) > 120:
            kinderen[0].unwrap()
    tekst = re.sub(r"\n\s*\n+", "\n", str(soup)).strip()
    return ondertitel, eerste, "\n".join("        " + r.strip() for r in tekst.split("\n") if r.strip())


def bestemming_pagina(b, content, per_slug):
    root = "../../"
    canonical = "%s/bestemmingen/%s/" % (SITE, b["slug"])
    ondertitel, foto, tekst = bestemming_inhoud(b, content)
    land = "Duitsland" if b["land"] == "DE" else "Nederland"
    ld = [{"@context": "https://schema.org", "@type": "TouristDestination", "name": b["naam"], "url": canonical,
           "description": b["beschrijving"], "containedInPlace": {"@type": "Country", "name": land}},
          {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
              {"@type": "ListItem", "position": 1, "name": "Home", "item": SITE + "/"},
              {"@type": "ListItem", "position": 2, "name": "Bestemmingen", "item": SITE + "/bestemmingen/"},
              {"@type": "ListItem", "position": 3, "name": b["naam"], "item": canonical}]}]
    if foto:
        ld[0]["image"] = foto["src"]
    extra = "".join('\n  <script type="application/ld+json">%s</script>' % json.dumps(x, ensure_ascii=False) for x in ld)
    out = [kop(b["seo_titel"], b["beschrijving"], canonical, root, foto["src"] if foto else None, extra)]
    out.append('  <main class="artikel-wrap">\n    <div class="container">\n      <div class="artikel-layout">\n      <article class="artikel bestemming">')
    out.append('        <div class="kruimelpad"><a href="%s">Home</a> › <a href="%sbestemmingen/">Bestemmingen</a> › %s</div>'
               % (root, root, esc(b["naam"])))
    out.append('        <p class="gidslabel">%s</p>' % ("Wijk in Nijmegen" if b["groep"].startswith("Wijk") else "Bestemming bij Nijmegen"))
    out.append("        <h1>%s</h1>" % esc(b["naam"] + (" (Kleve)" if b["slug"] == "kleve" else "")))
    if ondertitel:
        out.append('        <p class="bestemming-slogan">%s</p>' % esc(ondertitel))
    if foto:
        out.append('        <figure><img src="%s" alt="%s"%s></figure>' % (
            esc(foto["src"]), esc(goede_alt(foto["alt"], foto["src"], b["naam"])),
            ' width="%s" height="%s"' % (foto["w"], foto["h"]) if foto["w"] else ""))
    out.append('        <div class="partner-slider" data-plaatsing="blog"></div>')
    out.append('        <div class="inhoud-tekst">\n%s\n        </div>' % tekst)
    lees = [per_slug[x] for x in b["lees_ook"] if x in per_slug]
    lees += [a for a in sorted(per_slug.values(), key=lambda a: -a["verkeer"]) if a["rubriek"] == "regio-en-dagtrips" and a not in lees]
    out.append('        <section class="gids-sectie">\n          <h2>Lees ook</h2>\n          <div class="raster">')
    for a in lees[:3]:
        out.append("            " + kaart(a, root))
    out.append("          </div>\n        </section>")
    out.append('        <section class="gids-sectie"><h2>Andere bestemmingen</h2><ul class="gids-lijst">')
    for x in BESTEMMINGEN:
        if x is not b:
            out.append('          <li><a href="%sbestemmingen/%s/">%s</a></li>' % (root, x["slug"], esc(x["naam"])))
    out.append("        </ul></section>")
    out.append('        <p class="gids-cta"><a class="knop" href="%s/bedrijvengids/">Bekijk de bedrijven in de bedrijvengids</a></p>' % SITE)
    out.append("      </article>\n\n      <!-- zijbalk --><!-- /zijbalk -->\n      </div>\n    </div>\n  </main>")
    out.append(VOET)
    return "\n".join(out)


def bestemmingen_overzicht(fotos):
    root = "../"
    canonical = SITE + "/bestemmingen/"
    out = [kop("Bestemmingen rond Nijmegen: dorpen, steden en wijken",
               "Op pad rond Nijmegen? Ontdek Groesbeek, Wijchen, Berg en Dal, Kleef, Kranenburg, Goch en meer plaatsen in de regio, plus de wijk Dukenburg.",
               canonical, root, next(iter(fotos.values()), None))]
    out.append('  <main class="artikel-wrap">\n    <div class="container">')
    out.append('      <div class="kruimelpad"><a href="../">Home</a> › Bestemmingen</div>')
    out.append('      <header class="rubriek-kop">\n        <h1>Bestemmingen rond Nijmegen</h1>\n        <p>Net buiten de stad liggen mooie dorpen en stadjes, in Nederland en net over de grens in Duitsland. Tips voor een dagje uit, plus alles over de wijken van Nijmegen.</p>\n      </header>')
    for groep in ("Plaatsen rond Nijmegen", "Wijken in Nijmegen"):
        out.append('      <section class="bestemmingen">\n        <h2>%s</h2>\n        <div class="bestemmingen-raster">' % groep)
        for b in BESTEMMINGEN:
            if b["groep"] != groep:
                continue
            img = '<img src="%s" alt="" loading="lazy">' % esc(fotos[b["slug"]]) if fotos.get(b["slug"]) else ""
            out.append('          <a class="bestemmingkaart" href="%s/">%s<span>%s</span></a>' % (b["slug"], img, esc(b["naam"])))
        out.append("        </div>\n      </section>")
    out.append('      <div class="partner-slider" data-plaatsing="blog"></div>')
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
    for s, n, _ in RUBRIEKEN:
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
    for slug, naam, _ in RUBRIEKEN:  # partnerbijdragen als laatste
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
        if p["slug"] in SAMENVOEGEN:
            continue
        r = indeling.get(p["slug"])
        rub = RUBRIEK_SLUG[r["nieuwe_rubriek"]] if r else "wonen-werken-en-studeren"
        a = {
            "slug": p["slug"], "titel": html.unescape(p["title"]["rendered"]), "date": p["date"], "modified": p["modified"],
            "rubriek": rub, "img": featured(p), "samenvatting": samenvatting(p["content"]["rendered"]),
            "verkeer": int(r["verkeer"]) if r and r["verkeer"] else 0, "cats": p["categories"],
        }
        a["html"] = schoon(p["content"]["rendered"], slugs, "../", rub == "partnerbijdragen", a["titel"])
        eigen = ROOT / "data" / "samengevoegd" / ("%s.html" % p["slug"])
        if eigen.is_file():
            a["html"] = "\n".join("        " + r.strip() for r in eigen.read_text(encoding="utf-8").strip().split("\n"))
            a["samenvatting"] = samenvatting(a["html"])
            a["modified"] = SAMENGEVOEGD_OP
        for oud, nieuw in SAMENVOEGEN.items():
            a["html"] = a["html"].replace('href="../%s/"' % oud, 'href="../%s/"' % nieuw)
        for c in (c for c in CORRECTIES if c["artikel"] == p["slug"]):
            if "regex" in c:
                nieuw_html, n = re.subn(c["regex"], c["nieuw"], a["html"], flags=re.S)
            else:
                n = a["html"].count(c["oud"])
                nieuw_html = a["html"].replace(c["oud"], c["nieuw"])
            if not n:
                raise SystemExit("Correctie past niet meer bij %s: %s" % (p["slug"], c.get("oud", c.get("regex"))[:60]))
            a["html"] = re.sub(r"\n\s*\n", "\n", nieuw_html)
            a["samenvatting"] = samenvatting(a["html"])
            a["modified"] = SAMENGEVOEGD_OP
        m = re.search(r'<img[^>]+src="([^"]+)"', a["html"])
        a["eerste_img"] = m.group(1) if m else None
        artikelen.append(a)

    # Uitgelichte foto: ontbreekt (media niet openbaar) of is dezelfde als bij een ander artikel?
    # Dan de eerste andere foto uit de tekst. Het artikel met het meeste verkeer houdt de foto.
    for a in artikelen:
        if a["slug"] in EIGEN_FOTO:
            pad, alt = EIGEN_FOTO[a["slug"]]
            a["img"] = {"src": SITE + pad, "w": 1400, "h": 350, "alt": alt}
    gebruikt = set()
    for a in sorted(artikelen, key=lambda a: -a["verkeer"]):
        if a["img"] and a["img"]["src"] not in gebruikt:
            gebruikt.add(a["img"]["src"])
            continue
        for src in re.findall(r'<img[^>]+src="([^"]+)"', a["html"]):
            if src not in gebruikt:
                a["img"] = {"src": src, "w": None, "h": None, "alt": "", "uit_tekst": True}
                gebruikt.add(src)
                break

    per_rubriek = defaultdict(list)
    for a in sorted(artikelen, key=lambda a: (-a["verkeer"], a["date"]), reverse=False):
        per_rubriek[a["rubriek"]].append(a)
    for lijst in per_rubriek.values():
        lijst.sort(key=lambda a: (-a["verkeer"], -int(a["date"][:10].replace("-", ""))))

    per_slug = {a["slug"]: a for a in artikelen}
    for a in artikelen:
        if a["slug"] in HANDGEMAAKT:
            continue
        gids = ARTIKEL_GIDS.get(a["slug"])
        uit_gids = [per_slug[x] for sec in gids["secties"] for x in sec["artikelen"] if x in per_slug] if gids else []
        uit_gids = sorted({x["slug"]: x for x in uit_gids if x["slug"] != a["slug"]}.values(), key=lambda x: -x["verkeer"])
        gerel = (uit_gids + [g for g in per_rubriek[a["rubriek"]] if g["slug"] != a["slug"] and g not in uit_gids])[:4]
        d = ROOT / a["slug"]
        d.mkdir(exist_ok=True)
        (d / "index.html").write_text(artikel_pagina(a, gerel), encoding="utf-8")

    for slug, naam, intro in RUBRIEKEN:
        d = ROOT / "category" / slug
        d.mkdir(parents=True, exist_ok=True)
        (d / "index.html").write_text(rubriek_pagina(slug, naam, intro, per_rubriek.get(slug, [])), encoding="utf-8")

    for g in GIDSEN:
        d = ROOT / g["url"].strip("/")
        d.mkdir(parents=True, exist_ok=True)
        (d / "index.html").write_text(gids_pagina(g, per_slug), encoding="utf-8")
    (ROOT / "thema" / "index.html").write_text(gidsen_overzicht(per_slug), encoding="utf-8")

    # Bestemmingen: plaatsen rond Nijmegen en de wijk Dukenburg (WordPress-pagina's)
    paginas = {p["link"].split("nijmegenonline.nl", 1)[1]: p for p in json.load(open(bron / "pages" / "pages-1.json", encoding="utf-8"))}
    fotos = {}
    for best in BESTEMMINGEN:
        d = ROOT / "bestemmingen" / best["slug"]
        d.mkdir(parents=True, exist_ok=True)
        pagina = bestemming_pagina(best, paginas["/bestemmingen/%s/" % best["slug"]]["content"]["rendered"], per_slug)
        (d / "index.html").write_text(pagina, encoding="utf-8")
        m = re.search(r'<figure><img src="([^"]+)"', pagina)
        fotos[best["slug"]] = m.group(1) if m else None
    # Op het overzicht dezelfde foto's als op de WordPress-overzichtspagina
    overzicht = paginas["/bestemmingen/"]["content"]["rendered"]
    for src, slug in re.findall(r'<img[^>]+src="([^"]+)".*?href="https://www\.nijmegenonline\.nl/bestemmingen/([^/"]+)/"', overzicht, re.S):
        if slug in fotos:
            fotos[slug] = src
    # De homepage van WordPress heeft voor een paar plaatsen een mooiere tegelfoto
    home_wp = next(p for u, p in paginas.items() if u == "/")["content"]["rendered"]
    blok = home_wp[home_wp.lower().find("bestemmingen net buiten"):]
    gehad = set()
    for src, slug in re.findall(r'<img[^>]+src="([^"]+)".*?href="https://www\.nijmegenonline\.nl/bestemmingen/([^/"]+)/"', blok, re.S):
        if slug in fotos and slug not in gehad and "/partners" not in src and "300-200" not in src:
            fotos[slug] = src
            gehad.add(slug)
    (ROOT / "bestemmingen" / "index.html").write_text(bestemmingen_overzicht(fotos), encoding="utf-8")

    # Homepage: bestemmingen net buiten Nijmegen, tussen <!-- bestemmingen --> en <!-- /bestemmingen -->
    blok = ['<!-- bestemmingen -->', '    <section id="bestemmingen">', '      <div class="container">',
            '        <h2>Bestemmingen net buiten Nijmegen</h2>', '        <div class="bestemmingen-raster">']
    for best in [x for x in BESTEMMINGEN if x["groep"].startswith("Plaatsen")][:6]:
        blok.append('          <a class="bestemmingkaart" href="bestemmingen/%s/"><img src="%s" alt="" loading="lazy"><span>%s</span></a>'
                    % (best["slug"], esc(fotos[best["slug"]]), esc(best["naam"])))
    blok += ['        </div>', '        <p class="gids-verder"><a href="bestemmingen/">Bekijk alle bestemmingen</a></p>', '      </div>', '    </section>', '    <!-- /bestemmingen -->']
    home = ROOT / "index.html"
    h = home.read_text(encoding="utf-8")
    h = re.sub(r"<!-- bestemmingen -->.*?<!-- /bestemmingen -->", lambda m: "\n".join(blok), h, flags=re.S)
    home.write_text(h, encoding="utf-8")

    # Homepage: de belangrijkste gidsen (veel zoekvolume) tussen <!-- gidsen --> en <!-- /gidsen -->
    top = [next(g for g in GIDSEN if g["url"] == u) for u in HOME_GIDSEN]
    blok = ['<!-- gidsen -->', '    <section id="gidsen">', '      <div class="container">', '        <h2>Populaire gidsen</h2>', '        <div class="raster">']
    for g in top:
        f = SITE + g["foto"] if g.get("foto") else next((per_slug[x]["img"]["src"] for sec in g["secties"] for x in sec["artikelen"]
                                                       if x in per_slug and per_slug[x]["img"]), None)
        blok.append('          <article class="kaart"><a href="%s">%s<div class="kaart__tekst"><h3>%s</h3><p>%s</p></div></a></article>'
                    % (g["url"].lstrip("/"), '<img src="%s" alt="" loading="lazy">' % esc(f) if f else "", esc(g["naam"]), esc(g["kort"])))
    blok += ['        </div>', '        <p class="gids-verder"><a href="thema/">Bekijk alle gidsen</a></p>', '      </div>', '    </section>', '    <!-- /gidsen -->']
    home = ROOT / "index.html"
    h = home.read_text(encoding="utf-8")
    h = re.sub(r"<!-- gidsen -->.*?<!-- /gidsen -->", lambda m: "\n".join(blok), h, flags=re.S)
    home.write_text(h, encoding="utf-8")

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
    # Dubbele kapperspagina gaat op in de gids
    regels.append("/kapper-nijmegen-top-kapsalons-voor-knippen-kleuren-en-styling/ /thema/kappers-in-nijmegen/ 301")
    for oud, nieuw in SAMENVOEGEN.items():
        regels.append("/%s/ /%s/ 301" % (oud, nieuw))
        doel = per_slug[nieuw]
        d = ROOT / oud
        d.mkdir(exist_ok=True)
        (d / "index.html").write_text(DOORVERWIJZING % {"titel": esc(doel["titel"]), "url": "%s/%s/" % (SITE, nieuw), "pad": "../%s/" % nieuw},
                                      encoding="utf-8")
    # het blok "# agenda" onderaan is van tools/agenda.py
    bestaand = (ROOT / "_redirects").read_text(encoding="utf-8") if (ROOT / "_redirects").exists() else ""
    agenda = bestaand[bestaand.index("# agenda"):] if "# agenda" in bestaand else ""
    (ROOT / "_redirects").write_text("\n".join(regels) + "\n" + agenda, encoding="utf-8")

    print("%d artikelen, %d rubrieken, %d doorverwijzingen" % (len(artikelen), len(RUBRIEKEN), len(regels) - 1))
    for slug, naam, _ in RUBRIEKEN:
        print("  %-28s %d" % (naam, len(per_rubriek.get(slug, []))))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "/mnt/project-files/bron/wp-json")
