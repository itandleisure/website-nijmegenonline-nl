"""Maakt de RSS-feeds waar MailerLite elke week zelf de nieuwsbrief van vult (RSS-campagne).

In de nieuwsbrief in deze volgorde (afgesproken met Frans, 24-10-2026):
- /nieuwsbrief/uitgelicht.xml  uitgelichte evenementen (klanten) van de komende DAGEN_UITGELICHT dagen, met foto
- /nieuwsbrief/nieuws.xml      de nieuwste nieuwsberichten, met foto
- /nieuwsbrief/agenda.xml      de overige (gratis) evenementen van vandaag t/m DAGEN_VOORUIT dagen verder, met
                               foto; lang lopende alleen in de week dat ze beginnen

MailerLite neemt bij elke verzending alleen de items die nieuw zijn sinds de vorige. Bij nieuws is dat
precies goed (echte publicatiedatum). Een evenement staat vaak meerdere weken in de agenda; daarom krijgt
het per week een eigen guid en als datum de dag dat de feed is gemaakt, zodat elke week de hele komende
week in de nieuwsbrief komt.

Afbeeldingen: de site gebruikt webp, maar Outlook op Windows toont dat niet. Daarom maakt dit script een
jpg van 600 px breed in assets/nieuwsbrief/ voor elk item in de feeds (en ruimt oude op).

Zolang de site nog niet live is (robots.txt dicht, zie LIVEGANG.md) wijzen links en afbeeldingen naar de
testsite, zodat je in MailerLite al kunt proberen. Na `python tools/build.py --live` vanzelf naar
www.nijmegenonline.nl.

Draait elke nacht na tools/agenda.py en tools/nieuws.py (zie .github/workflows/).

Gebruik: python tools/nieuwsbrief.py [--datum 2026-10-22]
"""
import datetime
import email.utils
import json
import pathlib
import sys
import zoneinfo
from xml.sax.saxutils import escape

from PIL import Image

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from agenda import dag, lokaal, wanneer  # noqa: E402
from import_wordpress import ROOT, SITE, samenvatting  # noqa: E402
import nieuws  # noqa: E402

TESTSITE = "https://itandleisure.github.io/website-nijmegenonline-nl"
DAGEN_VOORUIT = 14
DAGEN_UITGELICHT = 30   # klanten mogen al eerder in de nieuwsbrief
MAX_UITGELICHT = 20   # Frans kiest er in MailerLite zelf uit
MAX_EVENEMENTEN = 40
MAX_NIEUWS = 20
MAP = ROOT / "nieuwsbrief"
FOTOS = ROOT / "assets" / "nieuwsbrief"
AMSTERDAM = zoneinfo.ZoneInfo("Europe/Amsterdam")


def basis():
    live = "Allow: /" in (ROOT / "robots.txt").read_text(encoding="utf-8")
    return SITE if live else TESTSITE


def jpg(pad, naam, url, gemaakt):
    """Zet een eigen webp om naar jpg voor e-mail; geeft de absolute URL of None."""
    if not pad or not (ROOT / pad).is_file():
        return None
    doel = FOTOS / (naam + ".jpg")
    if not doel.is_file() or doel.stat().st_mtime < (ROOT / pad).stat().st_mtime:
        img = Image.open(ROOT / pad).convert("RGB")
        if img.width > 600:
            img = img.resize((600, round(img.height * 600 / img.width)), Image.LANCZOS)
        img.save(doel, "JPEG", quality=82, optimize=True)
    gemaakt.add(doel.name)
    return "%s/assets/nieuwsbrief/%s" % (url, doel.name)


def item(titel, link, guid, datum, tekst, foto):
    regels = ["    <item>",
              "      <title>%s</title>" % escape(titel),
              "      <link>%s</link>" % escape(link),
              '      <guid isPermaLink="false">%s</guid>' % escape(guid),
              "      <pubDate>%s</pubDate>" % email.utils.format_datetime(datum),
              "      <description>%s</description>" % escape(tekst)]
    if foto:
        lengte = (FOTOS / foto.rsplit("/", 1)[-1]).stat().st_size
        regels.append('      <enclosure url="%s" length="%d" type="image/jpeg"/>' % (escape(foto), lengte))
        regels.append('      <media:content url="%s" medium="image" type="image/jpeg"/>' % escape(foto))
    regels.append("    </item>")
    return "\n".join(regels)


def feed(url, naam, titel, beschrijving, link, items, nu):
    (MAP / naam).write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0" xmlns:media="http://search.yahoo.com/mrss/" xmlns:atom="http://www.w3.org/2005/Atom">\n'
        "  <channel>\n"
        "    <title>%s</title>\n    <link>%s</link>\n    <description>%s</description>\n"
        "    <language>nl-nl</language>\n    <lastBuildDate>%s</lastBuildDate>\n"
        '    <atom:link href="%s/nieuwsbrief/%s" rel="self" type="application/rss+xml"/>\n'
        "%s\n  </channel>\n</rss>\n"
        % (escape(titel), escape(link), escape(beschrijving), email.utils.format_datetime(nu),
           url, naam, "\n".join(items)), encoding="utf-8")


def nieuw_genoeg(e, vandaag):
    """Lang lopende tentoonstellingen e.d. niet elke week opnieuw, behalve van klanten (uitgelicht)."""
    lang = (dag(e, "eind") - dag(e, "start")).days > 14
    return e["uitgelicht"] or not lang or dag(e, "start") >= vandaag


def main(vandaag):
    url = basis()
    nu = datetime.datetime.combine(vandaag, datetime.time(6), AMSTERDAM)
    week = "%d-W%02d" % vandaag.isocalendar()[:2]
    MAP.mkdir(exist_ok=True)
    FOTOS.mkdir(parents=True, exist_ok=True)
    gemaakt = set()

    evenementen = json.load(open(ROOT / "data" / "evenementen.json", encoding="utf-8"))

    def evenementen_feed(naam, titel, beschrijving, tot, selectie, maximum, met_foto):
        gekozen = sorted((e for e in evenementen if dag(e, "eind") >= vandaag and dag(e, "start") <= tot and selectie(e)),
                         key=lambda e: (max(dag(e, "start"), vandaag), e["start"], e["slug"]))[:maximum]
        items = []
        for e in gekozen:
            w = wanneer(e)
            tekst = "%s, %s. %s" % (w[0].upper() + w[1:], e["locatie"], samenvatting(e["tekst"], 200))
            foto = jpg(lokaal(e["afbeelding"]), "event-" + e["slug"], url, gemaakt) if met_foto else None
            items.append(item(e["titel"], "%s/events/%s/" % (url, e["slug"]), "%s#%s" % (e["slug"], week), nu, tekst, foto))
        feed(url, naam, titel, beschrijving, "%s/nijmegen-evenementen-overzicht/" % url, items, nu)
        return len(gekozen)

    n_uitgelicht = evenementen_feed("uitgelicht.xml", "Uitgelicht in Nijmegen", "Uitgelichte evenementen van onze partners",
                                    vandaag + datetime.timedelta(days=DAGEN_UITGELICHT), lambda e: e["uitgelicht"],
                                    MAX_UITGELICHT, True)
    n_overig = evenementen_feed("agenda.xml", "Agenda NijmegenOnline", "Wat er de komende twee weken nog meer te doen is in Nijmegen",
                                vandaag + datetime.timedelta(days=DAGEN_VOORUIT),
                                lambda e: not e["uitgelicht"] and nieuw_genoeg(e, vandaag), MAX_EVENEMENTEN, True)

    berichten = sorted(nieuws.laad(), key=lambda b: (b["datum"], b["slug"]), reverse=True)[:MAX_NIEUWS]
    items = []
    for b in berichten:
        datum = datetime.datetime.fromisoformat(b["datum"]).replace(tzinfo=AMSTERDAM)
        foto = jpg(lokaal(b["foto"]), "nieuws-" + b["slug"], url, gemaakt)
        link = "%s/nieuwsoverzicht/%s/" % (url, b["slug"])
        items.append(item(b["titel"], link, link.replace(url, SITE), datum,
                          b.get("beschrijving") or samenvatting(b["tekst"], 200), foto))
    feed(url, "nieuws.xml", "Nieuws NijmegenOnline", "Het laatste nieuws uit Nijmegen", "%s/nieuwsberichten/" % url, items, nu)

    for oud in FOTOS.glob("*.jpg"):
        if oud.name not in gemaakt:
            oud.unlink()
    print("nieuwsbrief: %d uitgelicht, %d overige evenementen, %d nieuwsberichten, %d foto's"
          % (n_uitgelicht, n_overig, len(berichten), len(gemaakt)))


if __name__ == "__main__":
    if "--datum" in sys.argv:
        datum = datetime.date.fromisoformat(sys.argv[sys.argv.index("--datum") + 1])
    else:
        datum = datetime.datetime.now(AMSTERDAM).date()
    main(datum)
