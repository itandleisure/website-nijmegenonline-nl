"""Zet de nieuwsberichten (WP News and Widget Pro, post type "news") om naar statische pagina's.

Datum, uitgelichte afbeelding en Rank Math-titel komen uit de XML-export (bron/wp-xml/nieuws.xml), de tekst
uit de HTML van de live pagina (bron/nieuws-html/<slug>.html), want in de XML staat nog ruwe WordPress-tekst
met shortcodes. Resultaat: data/nieuws.json, waarna tools/nieuws.py de pagina's bouwt.

Let op: dit overschrijft data/nieuws.json, dus ook de berichten die later via de Google Sheet zijn geplaatst.

Gebruik: python tools/import_nieuws.py [/mnt/project-files/bron]
"""
import html
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import nieuws  # noqa: E402
from import_wordpress import schoon  # noqa: E402


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


def main(bron):
    nieuws.bewaar(lees(pathlib.Path(bron)))
    nieuws.main()


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "/mnt/project-files/bron")
