"""Bouwt gidspagina's op /thema/ zonder de WordPress-export.

tools/import_wordpress.py maakt de gidsen uit data/gidsen.json, maar kent alleen de geïmporteerde artikelen en heeft de
REST-export nodig. Dit script gebruikt dezelfde opmaak (gids_pagina en gidsen_overzicht), maar haalt titel, omschrijving
en foto van elke kaart uit de pagina zelf, zoals tools/bezoekers.py dat doet. Zo kunnen ook handgemaakte pagina's
(parkeren, wandelen, Kronenburgerpark) in een gids staan.

Gebruik: python tools/gidsen_bouwen.py [url ...]     bijv. /thema/centrum-nijmegen/
         zonder argumenten: alle gidsen met "hand": true in data/gidsen.json
Daarna tools/build.py. Het overzicht op /thema/ wordt altijd opnieuw gemaakt.
"""
import csv
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import import_wordpress as iw  # noqa: E402
from bezoekers import eigen_pagina  # noqa: E402

# Bezoekcijfers per artikel, zodat het overzicht op /thema/ dezelfde kaartfoto kiest als import_wordpress.py
VERKEER = {r["url"].strip("/"): int(r["verkeer"] or 0) for r in csv.DictReader(
    open(ROOT / "data" / "indeling-artikelen.csv", encoding="utf-8"), delimiter=";")}


def maat(pad):
    """Breedte en hoogte van een eigen foto, voor width/height op de kaart."""
    try:
        from PIL import Image
        with Image.open(ROOT / pad) as im:
            return im.size
    except Exception:
        return (0, 0)


def artikel(slug, root):
    """Artikel-achtige dict voor import_wordpress.kaart(), uit de pagina op de site."""
    info = eigen_pagina("/%s/" % slug)
    if info is None:
        print("Overgeslagen, bestaat niet of is een doorverwijzing:", slug)
        return None
    img = None
    if info["foto"]:
        if info["foto"].startswith("http"):
            img = {"src": info["foto"], "w": 0, "h": 0, "alt": ""}
        else:
            w, h = maat(info["foto"])
            img = {"src": root + info["foto"], "w": w, "h": h, "alt": ""}
    tekst = info["tekst"]
    if len(tekst) > 155:
        tekst = tekst[:152].rsplit(" ", 1)[0] + "…"
    return {"slug": slug, "titel": info["titel"], "samenvatting": tekst, "img": img, "verkeer": VERKEER.get(slug, 0)}


def per_slug_voor(root, gidsen):
    out = {}
    for g in gidsen:
        for sec in g["secties"]:
            for slug in sec["artikelen"]:
                if slug not in out:
                    a = artikel(slug, root)
                    if a:
                        out[slug] = a
    return out


def main(urls):
    gidsen = [g for g in iw.GIDSEN if (g["url"] in urls if urls else g.get("hand"))]
    for g in gidsen:
        root = "../" * (g["url"].strip("/").count("/") + 1)
        per_slug = per_slug_voor(root, [g])
        d = ROOT / g["url"].strip("/")
        d.mkdir(parents=True, exist_ok=True)
        s = iw.gids_pagina(g, per_slug)
        # De carrousel met bedrijven (tools/bedrijvengids.py, thema_blokken) blijft staan
        oud = (d / "index.html").read_text(encoding="utf-8") if (d / "index.html").is_file() else ""
        m = re.search(r"[ \t]*<!-- gidsbedrijven -->.*?<!-- /gidsbedrijven -->\n", oud, re.S)
        if m:
            anker = '        <section class="gids-sectie faq"' if '<section class="gids-sectie faq"' in s else "      </article>"
            s = s.replace(anker, m.group(0) + anker, 1)
        (d / "index.html").write_text(s, encoding="utf-8")
        print("Gemaakt:", g["url"])
    # Het overzicht op /thema/: kaartfoto's komen uit de gidsfoto of de eerste pagina met foto
    per_slug = per_slug_voor("../", iw.GIDSEN)
    s = iw.gidsen_overzicht(per_slug)
    s = s.replace('src="%s/assets/' % iw.SITE, 'src="../assets/')
    (ROOT / "thema" / "index.html").write_text(s, encoding="utf-8")
    print("Gemaakt: /thema/")


if __name__ == "__main__":
    main(sys.argv[1:])
