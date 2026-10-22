"""Bouwt de agenda uit data/evenementen.json. Draait elke nacht (zie .github/workflows/agenda.yml).

- /nijmegen-evenementen-overzicht/   alle komende evenementen per maand (/agenda/ verwijst hierheen)
- /events/<slug>/                    een pagina per evenement
- /event-location/<aanbieder>/       alle evenementen van een aanbieder (EventOn-locatie, data/aanbieders.json)
- homepage en zijbalk                de eerstvolgende evenementen (tussen <!-- agenda --> en <!-- binnenkort -->)

Afgesproken met Frans (22-10-2026):
- Een evenement verdwijnt de dag na afloop uit de agenda, de homepage en de zijbalk.
- De pagina blijft nog BEWAAR_DAGEN staan met "Dit evenement is afgelopen" en daarna verwijst hij met
  een 301 naar de agenda (_redirects, blok "# agenda", plus een noindex-pagina voor GitHub Pages).
- Terugkerende evenementen ("terugkerend": true) houden altijd hun pagina; zet daar elk jaar de nieuwe
  datum in.

Een evenement toevoegen: een nieuw item in data/evenementen.json met slug, titel, start en eind
("2026-11-28T20:30" of alleen "2026-11-28" voor de hele dag), locatie, adres, afbeelding, alt, tekst (HTML)
uitgelicht (klanten: groen, bovenaan en met een link naar hun site in "link"; de rest is een gewone,
gratis vermelding). Daarna: python tools/agenda.py && python tools/build.py

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
AANBIEDERS = "event-location"
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
    if t < vandaag:
        return "%s %d" % (korte_datum(s), s.year)
    if s < vandaag:
        return "Nu, t/m %s" % korte_datum(t)
    if s == t:
        return korte_datum(s) + (", %s uur" % tijd(e["start"]) if tijd(e["start"]) else "")
    return "%s – %s" % (korte_datum(s), korte_datum(t))


def lokaal(url):
    """Afbeelding van wp-content/uploads naar de eigen webp (die maakt tools/afbeeldingen.py)."""
    m = re.match(r"https?://(?:www\.)?nijmegenonline\.nl/wp-content/uploads/(.+)\.(?:png|jpe?g|gif|webp)$", url or "", re.I)
    return "assets/uploads/%s.webp" % m.group(1) if m and (ROOT / ("assets/uploads/%s.webp" % m.group(1))).is_file() else None


def eventkaart(e, vandaag, root):
    s = max(dag(e, "start"), vandaag) if dag(e, "eind") >= vandaag else dag(e, "start")
    foto = lokaal(e["afbeelding"])
    img = '<img src="%s%s" alt="" loading="lazy">' % (root, foto) if foto else ""
    plaats = '<span class="eventkaart__plaats">%s</span>' % esc(e["locatie"]) if e["locatie"] else ""
    label = '<span class="eventkaart__label">Uitgelicht</span>' if e["uitgelicht"] else ""
    return ('<a class="eventkaart%s" href="%sevents/%s/"><span class="eventkaart__datum"><b>%d</b>%s</span>%s'
            '<span class="eventkaart__tekst">%s<strong>%s</strong><span class="eventkaart__wanneer">%s</span>%s</span></a>'
            % (" eventkaart--uitgelicht" if e["uitgelicht"] else "", root, e["slug"], s.day, MAANDEN[s.month - 1][:3], img, label,
               esc(e["titel"]), esc(kort_wanneer(e, vandaag)), plaats))


def uitgelichtkaart(e, vandaag, root):
    """Grote groene kaart voor evenementen van klanten, bovenaan de agenda en op de homepage."""
    foto = lokaal(e["afbeelding"])
    img = ('<img src="%s%s" alt="" loading="lazy">' % (root, foto) if foto
           else '<span class="uitgelicht__geenfoto">%s</span>' % esc(e["locatie"] or "NijmegenOnline"))
    plaats = '<span class="uitgelicht__plaats">%s</span>' % esc(e["locatie"]) if e["locatie"] else ""
    return ('<a class="uitgelicht" href="%sevents/%s/">%s<span class="uitgelicht__tekst"><span class="uitgelicht__wanneer">%s</span>'
            '<strong>%s</strong>%s</span></a>' % (root, e["slug"], img, esc(kort_wanneer(e, vandaag)), esc(e["titel"]), plaats))


def uitgelicht_blok(komend, vandaag, root, aantal, kop_="h2"):
    keuze = [e for e in komend if e["uitgelicht"]][:aantal]
    if not keuze:
        return []
    return (['<section class="agenda-uitgelicht">', '  <%s>Uitgelicht</%s>' % (kop_, kop_), '  <div class="uitgelicht-raster">'] +
            ["    " + uitgelichtkaart(e, vandaag, root) for e in keuze] + ["  </div>", "</section>"])


def ld_datum(waarde):
    if "T" not in waarde:
        return waarde
    d = datetime.datetime.fromisoformat(waarde).replace(tzinfo=zoneinfo.ZoneInfo("Europe/Amsterdam"))
    return d.isoformat()


def event_pagina(e, vandaag, komend, aanbieders):
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
    out.append('        <p class="gidslabel">%s</p>' % ("Uitgelicht evenement" if e["uitgelicht"] else "Evenement"))
    out.append("        <h1>%s</h1>" % esc(e["titel"]))
    regels = ['<li><span class="evenement-info__kop">Wanneer</span>%s</li>' % esc(wanneer(e))]
    if e["locatie"] or e["adres"]:
        adres = " ".join(x for x in (e["locatie"], e["adres"]) if x)
        kaart = "https://www.google.com/maps/search/?api=1&query=" + re.sub(r"\s+", "+", adres)
        plek = esc(e["locatie"])
        if e.get("aanbieder") in aanbieders and e["locatie"]:
            plek = '<a href="%s%s/%s/">%s</a>' % (root, AANBIEDERS, e["aanbieder"], plek)
        regels.append('<li><span class="evenement-info__kop">Waar</span>%s%s <a href="%s" target="_blank" rel="noopener">Route</a></li>'
                      % (plek, ("<br>" + esc(e["adres"])) if e["adres"] and e["adres"] != e["locatie"] else "", esc(kaart)))
    if e["uitgelicht"] and e.get("link"):
        # Klanten krijgen een link naar hun eigen site (betaald, dus rel="sponsored")
        naam = e["locatie"] or re.sub(r"^www\.", "", e["link"].split("/")[2])
        regels.append('<li><a class="knop" href="%s" target="_blank" rel="sponsored noopener">Bekijk op de website van %s</a></li>'
                      % (esc(e["link"]), esc(naam)))
    out.append('        <ul class="evenement-info%s">%s</ul>' % (" evenement-info--uitgelicht" if e["uitgelicht"] else "", "".join(regels)))
    if e["afbeelding"]:
        out.append('        <figure><img src="%s" alt="%s"></figure>' % (esc(e["afbeelding"]), esc(e["alt"] or e["titel"])))
    out.append('        <div class="partner-slider" data-plaatsing="blog"></div>')
    out.append('        <div class="inhoud-tekst">\n%s\n        </div>' % e["tekst"])
    van_hen = []
    if e.get("aanbieder") in aanbieders:
        naam = aanbieders[e["aanbieder"]]["naam"]
        van_hen = [x for x in komend if x is not e and x.get("aanbieder") == e["aanbieder"]][:4]
        out.append('        <section class="gids-sectie aanbieder-meer">\n          <h2>Meer evenementen bij %s</h2>' % esc(naam))
        if van_hen:
            out.append('          <div class="eventlijst">')
            out.extend("            " + eventkaart(x, vandaag, root) for x in van_hen)
            out.append('          </div>')
        else:
            out.append('          <p>Er staan nu geen andere evenementen van %s in de agenda.</p>' % esc(naam))
        out.append('          <p class="gids-verder"><a href="%s%s/%s/">Alle evenementen bij %s</a></p>\n        </section>'
                   % (root, AANBIEDERS, e["aanbieder"], esc(naam)))
    meer = [x for x in komend if x is not e and x not in van_hen and dag(x, "start") >= vandaag][:4]
    if meer:
        out.append('        <section class="gids-sectie">\n          <h2>Binnenkort in Nijmegen</h2>\n          <div class="eventlijst">')
        out.extend("            " + eventkaart(x, vandaag, root) for x in meer)
        out.append('          </div>\n          <p class="gids-verder"><a href="%s/%s/">Bekijk de hele agenda</a></p>\n        </section>' % (SITE, OVERZICHT))
    out.append("      </article>\n\n      <!-- zijbalk --><!-- /zijbalk -->\n      </div>\n    </div>\n  </main>")
    out.append(VOET)
    return "\n".join(out)


def aanbieder_pagina(slug, naam, komend, eerder, alle, vandaag):
    """Overzicht per aanbieder op het oude EventOn-adres /event-location/<slug>/."""
    root = "../../"
    canonical = "%s/%s/%s/" % (SITE, AANBIEDERS, slug)
    adres = next((x["adres"] for x in reversed(alle) if x["adres"]), "")
    beschrijving = ("Evenementen bij %s%s: concerten, exposities en activiteiten, met datum, tijd en adres."
                    % (naam, " (%s)" % adres if adres else ""))
    kruim = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "Home", "item": SITE + "/"},
        {"@type": "ListItem", "position": 2, "name": "Agenda", "item": "%s/%s/" % (SITE, OVERZICHT)},
        {"@type": "ListItem", "position": 3, "name": naam, "item": canonical}]}
    extra = '\n  <script type="application/ld+json">%s</script>' % json.dumps(kruim, ensure_ascii=False)
    if not komend:
        # Zonder komende evenementen is de pagina te dun voor zoekmachines
        extra += '\n  <meta name="robots" content="noindex">'
    foto = next((x["afbeelding"] for x in komend + eerder if x["afbeelding"]), None)
    out = [kop("Evenementen bij %s" % naam, beschrijving, canonical, root, foto, extra)]
    out.append('  <main class="artikel-wrap">\n    <div class="container">')
    out.append('      <div class="kruimelpad"><a href="%s">Home</a> › <a href="%s/%s/">Agenda</a> › %s</div>'
               % (root, SITE, OVERZICHT, esc(naam)))
    klant = next((x for x in reversed(alle) if x["uitgelicht"] and x.get("link")), None)
    out.append('      <header class="rubriek-kop%s">\n        <h1>Evenementen bij %s</h1>'
               % (" rubriek-kop--uitgelicht" if klant else "", esc(naam)))
    if adres:
        out.append('        <p>%s</p>' % esc(adres))
    if klant:
        out.append('        <p class="gids-cta"><a class="knop" href="%s" target="_blank" rel="sponsored noopener">Naar de website van %s</a></p>'
                   % (esc(klant["link"]), esc(naam)))
    out.append('      </header>')
    if komend:
        out.append('      <section class="agenda-maand">\n        <h2>Binnenkort</h2>\n        <div class="eventlijst">')
        out.extend("          " + eventkaart(x, vandaag, root) for x in komend)
        out.append("        </div>\n      </section>")
    else:
        out.append('      <p>Er staan op dit moment geen nieuwe evenementen van %s in de agenda. '
                   '<a href="%s/%s/">Bekijk wat er verder te doen is</a>.</p>' % (esc(naam), SITE, OVERZICHT))
    if eerder:
        out.append('      <section class="agenda-maand">\n        <h2>Eerder bij %s</h2>\n        <div class="eventlijst">' % esc(naam))
        out.extend("          " + eventkaart(x, vandaag, root) for x in eerder)
        out.append("        </div>\n      </section>")
    out.append('      <div class="partner-slider" data-plaatsing="blog"></div>')
    out.append("    </div>\n  </main>")
    out.append(VOET)
    return "\n".join(out)


def aanbieder_overzicht(rij, vandaag):
    """/event-location/: alle aanbieders met komende evenementen, klanten eerst."""
    root = "../"
    canonical = "%s/%s/" % (SITE, AANBIEDERS)
    out = [kop("Evenementen per locatie in Nijmegen", "Bekijk per museum, kerk, café of podium welke evenementen er "
               "binnenkort in Nijmegen en omgeving te doen zijn.", canonical, root)]
    out.append('  <main class="artikel-wrap">\n    <div class="container">')
    out.append('      <div class="kruimelpad"><a href="%s">Home</a> › <a href="%s/%s/">Agenda</a> › Per locatie</div>' % (root, SITE, OVERZICHT))
    out.append('      <header class="rubriek-kop">\n        <h1>Evenementen per locatie</h1>\n'
               '        <p>Alle podia, musea en organisatoren met evenementen in de agenda.</p>\n      </header>')
    out.append('      <ul class="aanbieders">')
    for slug, naam, aantal, klant in rij:
        out.append('        <li%s><a href="%s/">%s</a> <span>%d %s</span></li>'
                   % (' class="aanbieders__klant"' if klant else "", slug, esc(naam), aantal, "evenement" if aantal == 1 else "evenementen"))
    out.append('      </ul>')
    out.append("    </div>\n  </main>")
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
    out.extend("      " + r for r in uitgelicht_blok(komend, vandaag, root, 6))
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
    out.append('      <p class="gids-cta"><a class="knop" href="%s">Evenement aanmelden</a> <a href="%s%s/">Bekijk evenementen per locatie</a></p>'
               % (AANMELDEN, root, AANBIEDERS))
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
    aanbieders = json.load(open(ROOT / "data" / "aanbieders.json", encoding="utf-8"))
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
        (d / "index.html").write_text(event_pagina(e, vandaag, komend, aanbieders), encoding="utf-8")
    for slug in weg:
        doorverwijzing(events / slug, "../../%s/" % OVERZICHT, "Agenda Nijmegen", agenda_url)

    # Per aanbieder een overzicht; aanbieders zonder evenementpagina's meer verwijzen naar de agenda
    locaties = ROOT / AANBIEDERS
    if locaties.exists():
        shutil.rmtree(locaties)
    rij, weg_aanbieder = [], []
    for slug, info in aanbieders.items():
        alle = [e for e in evenementen if e.get("aanbieder") == slug]
        k = [e for e in komend if e.get("aanbieder") == slug]
        eerder = sorted((e for e in pagina if e.get("aanbieder") == slug and e not in komend), key=lambda e: e["start"], reverse=True)
        if not k and not eerder:
            weg_aanbieder.append(slug)
            doorverwijzing(locaties / slug, "../../%s/" % OVERZICHT, "Agenda Nijmegen", agenda_url)
            continue
        (locaties / slug).mkdir(parents=True)
        (locaties / slug / "index.html").write_text(aanbieder_pagina(slug, info["naam"], k, eerder, alle, vandaag), encoding="utf-8")
        if k:
            rij.append((slug, info["naam"], len(k), any(e["uitgelicht"] for e in alle)))
    rij.sort(key=lambda r: (not r[3], -r[2], r[1].lower()))
    (locaties / "index.html").write_text(aanbieder_overzicht(rij, vandaag), encoding="utf-8")

    (ROOT / OVERZICHT).mkdir(exist_ok=True)
    (ROOT / OVERZICHT / "index.html").write_text(overzicht(komend, vandaag), encoding="utf-8")
    doorverwijzing(ROOT / "agenda", "../%s/" % OVERZICHT, "Agenda Nijmegen", agenda_url)

    # Lopende exposities achteraan, anders staan ze elke dag bovenaan
    eerst = [e for e in komend if dag(e, "start") >= vandaag] + [e for e in komend if dag(e, "start") < vandaag]
    # Homepage: eerst drie uitgelichte evenementen van klanten, daarna de eerstvolgende andere
    boven = [e for e in eerst if e["uitgelicht"]][:3]
    home = ["        " + r for r in uitgelicht_blok(eerst, vandaag, "./", 3, "h3")]
    home += ['        <div class="eventlijst">'] + ["          " + eventkaart(e, vandaag, "./") for e in [x for x in eerst if x not in boven][:6]]
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
    regels += ["/%s/%s/ /%s/ 301" % (AANBIEDERS, slug, OVERZICHT) for slug in sorted(weg_aanbieder)]
    redirects.write_text((oud + "\n" if oud else "") + "\n".join(regels) + "\n", encoding="utf-8")

    print("Agenda %s: %d komend, %d evenementpagina's (waarvan %d afgelopen), %d aanbieders (%d met komende evenementen), %d doorverwijzingen"
          % (vandaag, len(komend), len(pagina), len(pagina) - len(komend), len(aanbieders) - len(weg_aanbieder), len(rij),
             len(weg) + len(weg_aanbieder)))


if __name__ == "__main__":
    datum = sys.argv[sys.argv.index("--datum") + 1] if "--datum" in sys.argv else None
    main(datetime.date.fromisoformat(datum) if datum else datetime.date.today())
