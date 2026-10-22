"""Zet de EventOn-evenementen van WordPress eenmalig om naar data/evenementen.json.

Tekst, afbeelding en "uitgelicht" (klanten; de rest had de tag "gratis") komen uit de REST-export (wp-json/ajde_events), datum, tijd en locatie uit de
schema.org-gegevens in de HTML van elke evenementpagina (bron/evenementen-html/<slug>.html), want die
staan niet in REST. De link naar de aanbieder komt uit de XML-export (bron/wp-xml/evenementen-eventon.xml)
of anders uit de locatielink op de evenementpagina. Evenementen die op de live site al een 404 gaven (bron/evenementen-mislukt.txt)
komen in data/evenementen-verwijderd.txt en krijgen alleen een doorverwijzing naar de agenda.

Daarna onderhoud je de agenda in data/evenementen.json en bouw je met tools/agenda.py.

Gebruik: python tools/import_evenementen.py [/mnt/project-files/bron]
"""
import glob
import html
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from import_wordpress import ROOT, featured, schoon  # noqa: E402

DATUM = re.compile(r"(\d{4})-(\d{1,2})-(\d{1,2})(?:T(\d{1,2}):(\d{2}))?")


def iso(waarde):
    """'2026-6-26T16:00+2:00' -> '2026-06-26T16:00' (lokale tijd), '2026-6-8' -> '2026-06-08'."""
    m = DATUM.match(waarde)
    j, mnd, d, u, mi = m.groups()
    datum = "%s-%02d-%02d" % (j, int(mnd), int(d))
    return datum + ("T%02d:%s" % (int(u), mi) if u else "")


def schema(pad):
    t = pad.read_text(encoding="utf-8")
    for blok in re.findall(r'<script type="application/ld\+json"[^>]*>(.*?)</script>', t, re.S):
        if '"@type": "Event"' not in blok:
            continue
        start = re.search(r'"startDate":\s*"([^"]*)"', blok).group(1)
        eind = re.search(r'"endDate":\s*"([^"]*)"', blok)
        plaats = re.search(r'"@type":"Place","name":"((?:[^"\\]|\\.)*)"', blok)
        adres = re.search(r'"streetAddress":"((?:[^"\\]|\\.)*)"', blok)
        link = re.search(r'class="evo_event_loc_link[^"]*"[^>]*href="(https?://[^"]+)"', t)
        return {"link": link.group(1) if link else "", "start": iso(start), "eind": iso(eind.group(1)) if eind else iso(start),
                "locatie": json.loads('"%s"' % plaats.group(1)) if plaats else "",
                "adres": json.loads('"%s"' % adres.group(1)) if adres else ""}
    return None


def meer_info_links(bron):
    """"Meer informatie"-link per evenement (EventOn-veld evcal_lmlink) uit de XML-export, voor zover die erin staat."""
    pad = bron / "wp-xml" / "evenementen-eventon.xml"
    if not pad.is_file():
        return {}
    links = {}
    for item in pad.read_text(encoding="utf-8").split("<item>")[1:]:
        slug = re.search(r"<wp:post_name><!\[CDATA\[([^\]]*)", item)
        m = re.search(r"<wp:meta_key><!\[CDATA\[evcal_lmlink\]\]></wp:meta_key>\s*<wp:meta_value><!\[CDATA\[(https?://[^\]]+)\]\]>", item)
        if slug and m:
            links[slug.group(1)] = m.group(1).strip()
    return links


def main(bron):
    bron = pathlib.Path(bron)
    meer_info = meer_info_links(bron)
    posts = [p for f in sorted(glob.glob(str(bron / "wp-json" / "ajde_events" / "*.json")))
             for p in json.load(open(f, encoding="utf-8"))]
    weg = {pathlib.PurePosixPath(r.split("\t")[0].rstrip("/")).name
           for r in (bron / "evenementen-mislukt.txt").read_text(encoding="utf-8").splitlines() if r.strip()}
    evenementen, verwijderd, zonder = [], [], []
    for p in posts:
        pagina = bron / "evenementen-html" / ("%s.html" % p["slug"])
        if p["slug"] in weg or not pagina.is_file():
            verwijderd.append(p["slug"])
            continue
        s = schema(pagina)
        if not s:
            zonder.append(p["slug"])
            continue
        titel = html.unescape(re.sub(r"<[^>]+>", "", p["title"]["rendered"])).strip()
        tekst = schoon(p["content"]["rendered"], set(), "../../", False, titel).strip()
        # EventOn zet de titel nog eens als kop bovenaan de tekst
        kop = re.match(r"<h[1-6][^>]*>(.*?)</h[1-6]>\s*", tekst, re.S)
        if kop and html.unescape(re.sub(r"<[^>]+>", "", kop.group(1))).strip().lower() == titel.lower():
            tekst = tekst[kop.end():]
        foto = featured(p, "large")
        klassen = p.get("class_list", [])
        evenementen.append({
            "slug": p["slug"],
            "titel": titel,
            "start": s["start"],
            "eind": s["eind"],
            "locatie": s["locatie"],
            "adres": s["adres"],
            "afbeelding": foto["src"] if foto else "",
            "alt": foto["alt"] if foto else "",
            "uitgelicht": "event_type-uitgelicht" in klassen,
            # Website van de aanbieder: de "meer informatie"-link, anders de link bij de locatie
            "link": meer_info.get(p["slug"]) or s["link"],
            "terugkerend": False,
            "gepubliceerd": p["date"][:10],
            "tekst": tekst,
        })
    evenementen.sort(key=lambda e: (e["start"], e["slug"]))
    (ROOT / "data" / "evenementen.json").write_text(json.dumps(evenementen, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    (ROOT / "data" / "evenementen-verwijderd.txt").write_text("\n".join(sorted(verwijderd + zonder)) + "\n", encoding="utf-8")
    print("%d evenementen, %d al weg op de live site, %d zonder datum" % (len(evenementen), len(verwijderd), len(zonder)))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "/mnt/project-files/bron")
