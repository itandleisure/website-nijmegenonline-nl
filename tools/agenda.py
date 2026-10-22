"""Bouwt de agenda uit data/evenementen.json. Draait elke nacht (zie .github/workflows/agenda.yml).

- /nijmegen-evenementen-overzicht/   alle komende evenementen per maand (/agenda/ verwijst hierheen)
- /events/<slug>/                    een pagina per evenement
- homepage en zijbalk                de eerstvolgende evenementen (tussen <!-- agenda --> en <!-- binnenkort -->)

Afgesproken met Frans (22-10-2026):
- Een evenement verdwijnt de dag na afloop uit de agenda, de homepage en de zijbalk.
- De pagina blijft nog BEWAAR_DAGEN staan met "Dit evenement is afgelopen" en daarna verwijst hij met
  een 301 naar de agenda (_redirects, blok "# agenda", plus een noindex-pagina voor GitHub Pages).
- Terugkerende evenementen ("terugkerend": true) houden altijd hun pagina; zet daar elk jaar de nieuwe
  datum in.

Een evenement toevoegen: een nieuw item in data/evenementen.json met slug, titel, start en eind
("2026-11-28T20:30" of alleen "2026-11-28" voor de hele dag), locatie, adres, afbeelding, alt, tekst (HTML)
en uitgelicht (partners en tips bovenaan). Daarna: python tools/agenda.py && python tools/build.py

Gebruik: python tools/agenda.py [--datum 2026-10-22]
"""
import datetime
import html
import json
import pathlib
import re
import shutil
import sys
import zoneinfo

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from import_wordpress import DOORVERWIJZING, SITE, VOET, esc, kop, samenvatting  # noqa: E402

BEWAAR_DAGEN = 92
OVERZICHT = "nijmegen-evenementen-overzicht"
AANMELDEN = SITE + "/evenement-aanmelden/"
MAANDEN = ["januari", "februari", "maart", "april", "mei", "juni", "juli", "augustus", "september",
           "oktober", "november", "december"]
DAGEN = ["maandag", "dinsdag", "woensdag", "donderdag", "vrijdag", "zaterdag", "zondag"]


def dag(e, veld):
    return datetime.date.fromisoformat(e[veld][:10])


def tijd(waarde):
    return waarde[11:16].replace(":", ".") if "T" in waarde else ""


def korte_datum(d):
    return "%d %s" % (d.day, MAANDEN[d.month - 1][:3])


def wanneer(e):
    """'zaterdag 28 november 2026, 20.30 uur' of 'vrijdag 30 oktober t/m maandag 2 november 2026'."""
    s, t = dag(e, "start"), dag(e, "eind")
    if s == t:
        tekst = "%s %d %s %d" % (DAGEN[s.weekday()], s.day, MAANDEN[s.month - 1], s.year)
        if tijd(e["start"]):
            tekst += ", %s" % tijd(e["start"])
            tekst += " tot %s uur" % tijd(e["eind"]) if tijd(e["eind"]) and e["eind"] != e["start"] else " uur"
        return tekst
    begin = "%s %d %s" % (DAGEN[s.weekday()], s.day, MAANDEN[s.month - 1]) + (" %d" % s.year if s.year != t.year else "")
    return "%s t/m %s %d %s %d" % (begin, DAGEN[t.weekday()], t.day, MAANDEN[t.month - 1], t.year)


def kort_wanneer(e, vandaag):
    s, t = dag(e, "start"), dag(e, "eind")
    if s < vandaag:
        return "Nu, t/m %s" % korte_datum(t)
    if s == t:
        return korte_datum(s) + (", %s uur" % tijd(e["start"]) if tijd(e["start"]) else "")
    return "%s – %s" % (korte_datum(s), korte_datum(t))


def lokaal(url):
    """Afbeelding van wp-content/uploads naar de eigen webp (die maakt tools/afbeeldingen.py)."""
    m = re.match(r"https?://www\.nijmegenonline\.nl/wp-content/uploads/(.+)\.(?:png|jpe?g|gif|webp)$", url or "", re.I)
    return "assets/uploads/%s.webp" % m.group(1) if m and (ROOT / ("assets/uploads/%s.webp" % m.group(1))).is_file() else None


def eventkaart(e, vandaag, root):
    s = max(dag(e, "start"), vandaag)
    foto = lokaal(e["afbeelding"])
    img = '<img src="%s%s" alt="" loading="lazy">' % (root, foto) if foto else ""
    plaats = '<span class="eventkaart__plaats">%s</span>' % esc(e["locatie"]) if e["locatie"] else ""
    tip = '<span class="eventkaart__tip">Tip</span>' if e["uitgelicht"] else ""
    return ('<a class="eventkaart" href="%sevents/%s/"><span class="eventkaart__datum"><b>%d</b>%s</span>%s'
            '<span class="eventkaart__tekst">%s<strong>%s</strong><span class="eventkaart__wanneer">%s</span>%s</span></a>'
            % (root, e["slug"], s.day, MAANDEN[s.month - 1][:3], img, tip, esc(e["titel"]), esc(kort_wanneer(e, vandaag)), plaats))


def ld_datum(waarde):
    if "T" not in waarde:
        return waarde
    d = datetime.datetime.fromisoformat(waarde).replace(tzinfo=zoneinfo.ZoneInfo("Europe/Amsterdam"))
    return d.isoformat()


def event_pagina(e, vandaag, komend):
    root = "../../"
    canonical = "%s/events/%s/" % (SITE, e["slug"])
    afgelopen = dag(e, "eind") < vandaag
    beschrijving = samenvatting("<p>%s, %s.</p>%s" % (wanneer(e), e["locatie"], e["tekst"]) if e["locatie"]
                                else "<p>%s.</p>%s" % (wanneer(e), e["tekst"]))
    ld = {"@context": "https://schema.org", "@type": "Event", "name": e["titel"], "url": canonical,
          "startDate": ld_datum(e["start"]), "endDate": ld_datum(e["eind"]),
          "eventStatus": "https://schema.org/EventScheduled",
          "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode",
          "description": beschrijving}
    if e["locatie"] or e["adres"]:
        ld["location"] = {"@type": "Place", "name": e["locatie"] or e["adres"],
                          "address": {"@type": "PostalAddress", "streetAddress": e["adres"] or e["locatie"]}}
    if e["afbeelding"]:
        ld["image"] = e["afbeelding"]
    kruim = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "Home", "item": SITE + "/"},
        {"@type": "ListItem", "position": 2, "name": "Agenda", "item": "%s/%s/" % (SITE, OVERZICHT)},
        {"@type": "ListItem", "position": 3, "name": e["titel"], "item": canonical}]}
    extra = "".join('\n  <script type="application/ld+json">%s</script>' % json.dumps(x, ensure_ascii=False) for x in (ld, kruim))
    out = [kop(e["titel"], beschrijving, canonical, root, e["afbeelding"] or None, extra)]
    out.append('  <main class="artikel-wrap">\n    <div class="container">\n      <div class="artikel-layout">\n      <article class="artikel evenement">')
    out.append('        <div class="kruimelpad"><a href="%s">Home</a> › <a href="%s/%s/">Agenda</a> › %s</div>'
               % (root, SITE, OVERZICHT, esc(e["titel"])))
    if afgelopen:
        out.append('        <p class="afgelopen">Dit evenement is afgelopen. <a href="%s/%s/">Bekijk wat er binnenkort te doen is</a>.</p>'
                   % (SITE, OVERZICHT))
    out.append('        <p class="gidslabel">Evenement</p>')
    out.append("        <h1>%s</h1>" % esc(e["titel"]))
    regels = ['<li><span class="evenement-info__kop">Wanneer</span>%s</li>' % esc(wanneer(e))]
    if e["locatie"] or e["adres"]:
        adres = " ".join(x for x in (e["locatie"], e["adres"]) if x)
        kaart = "https://www.google.com/maps/search/?api=1&query=" + re.sub(r"\s+", "+", adres)
        regels.append('<li><span class="evenement-info__kop">Waar</span>%s%s <a href="%s" target="_blank" rel="noopener">Route</a></li>'
                      % (esc(e["locatie"]), ("<br>" + esc(e["adres"])) if e["adres"] and e["adres"] != e["locatie"] else "", esc(kaart)))
    out.append('        <ul class="evenement-info">%s</ul>' % "".join(regels))
    if e["afbeelding"]:
        out.append('        <figure><img src="%s" alt="%s"></figure>' % (esc(e["afbeelding"]), esc(e["alt"] or e["titel"])))
    out.append('        <div class="partner-slider" data-plaatsing="blog"></div>')
    out.append('        <div class="inhoud-tekst">\n%s\n        </div>' % e["tekst"])
    meer = [x for x in komend if x is not e and dag(x, "start") >= vandaag][:4]
    if meer:
        out.append('        <section class="gids-sectie">\n          <h2>Binnenkort in Nijmegen</h2>\n          <div class="eventlijst">')
        out.extend("            " + eventkaart(x, vandaag, root) for x in meer)
        out.append('          </div>\n          <p class="gids-verder"><a href="%s/%s/">Bekijk de hele agenda</a></p>\n        </section>' % (SITE, OVERZICHT))
    out.append("      </article>\n\n      <!-- zijbalk --><!-- /zijbalk -->\n      </div>\n    </div>\n  </main>")
    out.append(VOET)
    return "\n".join(out)


def overzicht(komend, vandaag):
    root = "../"
    canonical = "%s/%s/" % (SITE, OVERZICHT)
    out = [kop("Agenda Nijmegen: evenementen in Nijmegen en omgeving",
               "Wat is er te doen in Nijmegen? De agenda met concerten, exposities, markten, rondleidingen en "
               "andere evenementen in Nijmegen en de regio, elke dag bijgewerkt.",
               canonical, root, next((e["afbeelding"] for e in komend if e["afbeelding"]), None))]
    out.append('  <main class="artikel-wrap">\n    <div class="container">')
    out.append('      <div class="kruimelpad"><a href="../">Home</a> › Agenda</div>')
    out.append('      <header class="rubriek-kop">\n        <h1>Agenda: evenementen in Nijmegen</h1>\n'
               '        <p>Concerten, exposities, rondleidingen en markten in Nijmegen en de regio, ook net over de grens. '
               'Organiseer je zelf iets? <a href="%s">Meld je evenement aan</a>.</p>\n      </header>' % AANMELDEN)
    if not komend:
        out.append("      <p>Er staan op dit moment geen evenementen in de agenda.</p>")
    # Langlopende exposities apart bovenaan, zodat ze niet elke maand opnieuw de lijst openen
    lopend = [e for e in komend if dag(e, "start") < vandaag]
    if lopend:
        out.append('      <section class="agenda-maand">\n        <h2>Nu te zien</h2>\n        <div class="eventlijst">')
        out.extend("          " + eventkaart(e, vandaag, root) for e in lopend)
        out.append("        </div>\n      </section>")
    maand = None
    for e in komend:
        if e in lopend:
            continue
        s = max(dag(e, "start"), vandaag)
        if (s.year, s.month) != maand:
            if maand:
                out.append("        </div>\n      </section>")
            maand = (s.year, s.month)
            out.append('      <section class="agenda-maand">\n        <h2>%s %d</h2>\n        <div class="eventlijst">'
                       % (MAANDEN[s.month - 1].capitalize(), s.year))
        out.append("          " + eventkaart(e, vandaag, root))
    if maand:
        out.append("        </div>\n      </section>")
    out.append('      <p class="gids-cta"><a class="knop" href="%s">Evenement aanmelden</a></p>' % AANMELDEN)
    out.append('      <div class="partner-slider" data-plaatsing="blog"></div>')
    out.append("    </div>\n  </main>")
    out.append(VOET)
    return "\n".join(out)


def doorverwijzing(map_, doel_pad, titel, url):
    map_.mkdir(parents=True, exist_ok=True)
    tekst = DOORVERWIJZING % {"titel": esc(titel), "url": url, "pad": doel_pad}
    tekst = tekst.replace("Dit artikel is samengevoegd met", "Dit evenement is afgelopen. Bekijk de")
    (map_ / "index.html").write_text(tekst, encoding="utf-8")


def vervang_blok(pad, naam, inhoud):
    tekst = pad.read_text(encoding="utf-8")
    nieuw, n = re.subn(r"([ \t]*)<!-- %s -->.*?<!-- /%s -->" % (naam, naam),
                       lambda m: "%s<!-- %s -->\n%s\n%s<!-- /%s -->" % (m.group(1), naam, inhoud, m.group(1), naam), tekst, flags=re.S)
    if not n:
        raise SystemExit("Markering <!-- %s --> ontbreekt in %s" % (naam, pad))
    pad.write_text(nieuw, encoding="utf-8")


def main(vandaag):
    evenementen = json.load(open(ROOT / "data" / "evenementen.json", encoding="utf-8"))
    verwijderd = [r for r in (ROOT / "data" / "evenementen-verwijderd.txt").read_text(encoding="utf-8").split() if r]
    grens = vandaag - datetime.timedelta(days=BEWAAR_DAGEN)
    komend = sorted((e for e in evenementen if dag(e, "eind") >= vandaag),
                    key=lambda e: (max(dag(e, "start"), vandaag), not e["uitgelicht"], e["start"], e["slug"]))
    pagina = [e for e in evenementen if dag(e, "eind") >= grens or e.get("terugkerend")]
    weg = [e["slug"] for e in evenementen if e not in pagina] + verwijderd

    events = ROOT / "events"
    if events.exists():
        shutil.rmtree(events)
    agenda_url = "%s/%s/" % (SITE, OVERZICHT)
    for e in pagina:
        d = events / e["slug"]
        d.mkdir(parents=True)
        (d / "index.html").write_text(event_pagina(e, vandaag, komend), encoding="utf-8")
    for slug in weg:
        doorverwijzing(events / slug, "../../%s/" % OVERZICHT, "Agenda Nijmegen", agenda_url)
    (ROOT / OVERZICHT).mkdir(exist_ok=True)
    (ROOT / OVERZICHT / "index.html").write_text(overzicht(komend, vandaag), encoding="utf-8")
    doorverwijzing(ROOT / "agenda", "../%s/" % OVERZICHT, "Agenda Nijmegen", agenda_url)

    # Homepage: de eerstvolgende zes, zijbalk: de eerstvolgende drie (lopende exposities achteraan)
    eerst = [e for e in komend if dag(e, "start") >= vandaag] + [e for e in komend if dag(e, "start") < vandaag]
    home = ['        <div class="eventlijst">'] + ["          " + eventkaart(e, vandaag, "./") for e in eerst[:6]]
    home += ["        </div>", '        <p class="gids-verder"><a href="%s">Bekijk de hele agenda</a></p>' % agenda_url]
    vervang_blok(ROOT / "index.html", "agenda", "\n".join(home))
    zij = ['      <li><span class="zijbalk__datum">%s</span><a href="%s/events/%s/">%s</a></li>'
           % (esc(kort_wanneer(e, vandaag)), SITE, e["slug"], esc(e["titel"])) for e in eerst[:3]]
    vervang_blok(ROOT / "partials" / "zijbalk.html", "binnenkort", "\n".join(zij))

    # 301's voor Cloudflare; het blok "# agenda" wordt elke keer opnieuw geschreven
    redirects = ROOT / "_redirects"
    oud = redirects.read_text(encoding="utf-8").split("# agenda")[0].rstrip("\n") if redirects.exists() else ""
    regels = ["# agenda (tools/agenda.py)", "/agenda/ /%s/ 301" % OVERZICHT]
    regels += ["/events/%s/ /%s/ 301" % (slug, OVERZICHT) for slug in sorted(weg)]
    redirects.write_text((oud + "\n" if oud else "") + "\n".join(regels) + "\n", encoding="utf-8")

    print("Agenda %s: %d komend, %d evenementpagina's (waarvan %d afgelopen), %d doorverwijzingen"
          % (vandaag, len(komend), len(pagina), len(pagina) - len(komend), len(weg)))


if __name__ == "__main__":
    datum = sys.argv[sys.argv.index("--datum") + 1] if "--datum" in sys.argv else None
    main(datetime.date.fromisoformat(datum) if datum else datetime.date.today())
