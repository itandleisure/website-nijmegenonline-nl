"""Bedrijvengids: voorbeeld met één categorie (sportscholen) en één bedrijfspagina.

Bronnen:
- de oude Listdom-gids uit de WordPress-export (bedrijvengids-listdom.xml): eigen tekst, foto, openingstijden
- OpenStreetMap/Overture (advies/osm-bedrijvengids/sportscholen-aangevuld.csv): de overige sportscholen

Pakketten (Uitgelicht, Partner, Hoofdpartner) staan in data/bedrijvengids-pakketten.json; een verlopen pakket
valt bij de dagelijkse herbouw (.github/workflows/agenda.yml) vanzelf terug naar gratis.

Gebruik: python tools/bedrijvengids.py [/mnt/project-files]
Schrijft data/bedrijvengids.json en de pagina's onder bedrijvengids/ en bedrijvengids-categorie/. Zonder de
bronbestanden (zoals op GitHub) bouwt het de pagina's opnieuw uit data/bedrijvengids.json.
"""
import csv
import datetime
import html
import json
import random
import pathlib
import re
import sys
import unicodedata
import urllib.parse
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from import_wordpress import DOORVERWIJZING, SITE, VOET, esc, kop, samenvatting, schoon  # noqa: E402

NS = {"wp": "http://wordpress.org/export/1.2/", "content": "http://purl.org/rss/1.0/modules/content/"}
BETAALD = ("uitgelicht", "partner", "hoofdpartner")
MAX_UITGELICHT = 3
DAGEN = ["maandag", "dinsdag", "woensdag", "donderdag", "vrijdag", "zaterdag", "zondag"]
SCHEMA_DAG = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

CATEGORIE = {
    "slug": "sportschool",
    "naam": "Sportscholen in Nijmegen",
    "enkelvoud": "Sportschool",
    "groep": "Sport en beweging",
    "soorten": {"Sportschool en fitness", "Personal training en bootcamp"},
    "schema": "ExerciseGym",
    "beschrijving": "Alle sportscholen in Nijmegen op een rij: van grote ketens tot kleine studio's voor personal "
                    "training, met adressen, openingstijden en tips om de juiste te kiezen.",
    "intro": "<p>Nijmegen is een echte sportstad. Met de Radboud Universiteit, de HAN en een flinke groep jonge "
             "inwoners is het aanbod aan sportscholen groot: van 24-uursketens aan de rand van de stad tot kleine "
             "studio's in het centrum waar je met een personal trainer werkt.</p>"
             "<p>Op deze pagina vind je alle sportscholen in Nijmegen. Bovenaan staan de sportscholen uit onze "
             "bedrijvengids, met openingstijden en een eigen pagina. Daaronder de complete lijst op alfabet.</p>",
    "faq": [
        ("Wat kost een sportschool in Nijmegen?",
         "Bij de grote ketens betaal je vanaf ongeveer 25 euro per maand. Kleinere sportscholen met begeleiding of "
         "groepslessen zitten vaak tussen de 40 en 70 euro, en personal training reken je meestal per les."),
        ("Welke sportschool in Nijmegen is 24 uur open?",
         "Een paar ketens hebben vestigingen die dag en nacht open zijn, vaak met een pas waarmee je buiten de "
         "bemande uren binnenkomt. Kijk bij de vestiging zelf welke uren gelden."),
        ("Kan ik eerst een proefles doen?",
         "Bijna alle sportscholen in Nijmegen bieden een gratis proefles of proefweek aan. Zo zie je of de sfeer, "
         "de drukte en de begeleiding bij je passen voordat je een abonnement afsluit."),
    ],
    "artikelen": ["bammmm-en-je-bent-fit", "afvallen-met-sport-tips-voor-een-kleinere-maat", "7x-de-beste-warming-up-oefeningen"],
    # Blogberichten over het onderwerp: daaronder komt het blok met de uitgelichte bedrijven (onderdeel van Uitgelicht)
    "blogs": ["bammmm-en-je-bent-fit", "afvallen-met-sport-tips-voor-een-kleinere-maat", "7x-de-beste-warming-up-oefeningen",
              "hoe-kan-een-dietist-je-helpen-gezonder-te-gaan-leven"],
    "meervoud": "sportscholen",
}


def slug(tekst):
    tekst = unicodedata.normalize("NFKD", tekst).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", tekst).strip("-")


def sleutel(naam):
    return re.sub(r"[^a-z0-9]", "", slug(re.sub(r"\bnijmegen\b", "", naam, flags=re.I)))


def alineas(tekst):
    """WordPress-tekst zonder <p> omzetten naar HTML, zoals WordPress zelf doet (wpautop): elke regel een alinea,
    koppen en lijsten als eigen blok, en regels die met "- " beginnen samen een opsomming."""
    tekst = re.sub(r"(</h\d>|</ul>|</ol>)", r"\1\n", tekst.replace("\r", ""))
    tekst = re.sub(r"(?<!\n)(<h\d)", r"\n\1", tekst)
    tekst = re.sub(r"<(/?)h1\b", r"<\1h2", tekst)   # de h1 is de naam van het bedrijf
    uit, lijst = [], []
    for regel in (r.strip() for r in tekst.split("\n")):
        punt = re.match(r"^(<strong>)?\s*[-•]\s+(.*)$", regel)
        if punt:
            lijst.append((punt.group(1) or "") + punt.group(2))
            continue
        if lijst:
            uit.append("<ul>%s</ul>" % "".join("<li>%s</li>" % x for x in lijst))
            lijst = []
        if not regel:
            continue
        uit.append(regel if re.match(r"<(h\d|ul|ol|table|blockquote|figure|div|p)\b", regel) else "<p>%s</p>" % regel)
    if lijst:
        uit.append("<ul>%s</ul>" % "".join("<li>%s</li>" % x for x in lijst))
    return "\n".join(uit)


def openingstijden(ava):
    """Listdom bewaart openingstijden als PHP-serialisatie; dag 1 is maandag."""
    tijden = {}
    for dag, inhoud in re.findall(r'i:(\d);a:\d+:\{(.*?)\}', ava or ""):
        uren = re.search(r'"hours";s:\d+:"([^"]*)"', inhoud)
        dicht = re.search(r'"off";s:1:"1"', inhoud)
        tijden[int(dag)] = "gesloten" if dicht else (uren.group(1).replace(" - ", "–") if uren else "")
    return [tijden.get(i + 1, "") for i in range(7)] if tijden else []


def gids_uit_xml(pad, categorie):
    r = ET.parse(pad).getroot()
    bijlagen = {i.findtext("wp:post_id", namespaces=NS): i.findtext("wp:attachment_url", namespaces=NS)
                for i in r.iter("item") if i.findtext("wp:post_type", namespaces=NS) == "attachment"}
    uit = []
    for i in r.iter("item"):
        if i.findtext("wp:post_type", namespaces=NS) != "listdom-listing" or i.findtext("wp:status", namespaces=NS) != "publish":
            continue
        if not any(c.get("domain") == "listdom-category" and c.get("nicename") == categorie for c in i.findall("category")):
            continue
        m = {x.findtext("wp:meta_key", namespaces=NS): x.findtext("wp:meta_value", namespaces=NS) or "" for x in i.findall("wp:postmeta", NS)}
        adres = [x.strip() for x in m.get("lsd_contact_address", "").split("|")]
        foto = (bijlagen.get(m.get("_thumbnail_id")) or "").replace("http://", "https://")
        uit.append({
            "slug": i.findtext("wp:post_name", namespaces=NS),
            "naam": i.findtext("title"),
            "adres": adres[0] if adres else "",
            "postcode": adres[1] if len(adres) > 1 else "",
            "plaats": adres[2] if len(adres) > 2 else "Nijmegen",
            "telefoon": m.get("lsd_phone", ""),
            "email": m.get("lsd_email", ""),
            "website": m.get("lsd_website", ""),
            "facebook": m.get("lsd_facebook", ""),
            "instagram": m.get("lsd_instagram", ""),
            "lat": m.get("lsd_latitude", ""),
            "lon": m.get("lsd_longitude", ""),
            "openingstijden": openingstijden(m.get("lsd_ava")),
            "foto": foto,
            "beschrijving": m.get("rank_math_description", ""),
            "tekst": alineas(i.findtext("content:encoded", namespaces=NS) or ""),
            "categorieen": [c.text for c in i.findall("category") if c.get("domain") == "listdom-category"],
            "in_gids": True,
        })
    return uit


def osm_uit_csv(pad, soorten):
    uit = []
    for x in csv.DictReader(open(pad, encoding="utf-8")):
        if x["soort"] in soorten and x["plaats"] == "Nijmegen":
            uit.append({"naam": x["naam"], "adres": x["adres"].rstrip(", "), "postcode": x["postcode"], "plaats": x["plaats"],
                        "telefoon": x["telefoon"], "website": x["website"], "lat": x["lat"], "lon": x["lon"],
                        "soort": x["soort"], "bron": x["bron"], "in_gids": False, "email": "", "facebook": "", "instagram": "",
                        "openingstijden": [], "foto": "", "beschrijving": "", "tekst": ""})
    return uit


def samenvoegen(gids, overig):
    """Bedrijven uit de gids gaan voor; dezelfde naam uit OSM/Overture valt dan weg."""
    bekend = {sleutel(b["naam"]) for b in gids}
    gids.sort(key=lambda b: b["naam"].lower())
    overig = sorted((b for b in overig if sleutel(b["naam"]) not in bekend), key=lambda b: (b["naam"].lower(), b["adres"]))
    # Eigen pagina's voor de aangevulde bedrijven; dezelfde naam op meer adressen (ketens) krijgt de straat erbij
    # Eerder uitgedeelde slugs blijven staan (de url mag niet veranderen); alleen nieuwe bedrijven krijgen er een
    vorig = {}
    pad = ROOT / "data" / "bedrijvengids.json"
    if pad.exists():
        for cat in json.loads(pad.read_text(encoding="utf-8")).values():
            vorig.update({(x["naam"], x["adres"]): x["slug"] for x in cat["overig"]})
    namen = [slug(b["naam"]) for b in overig]
    bezet = ({b["slug"] for b in gids} | {p.name for p in (ROOT / "bedrijvengids").iterdir() if p.is_dir()}) - set(vorig.values())
    for b in overig:
        if (b["naam"], b["adres"]) in vorig:
            b["slug"] = vorig[(b["naam"], b["adres"])]
            bezet.add(b["slug"])
    for b in overig:
        if b.get("slug"):
            continue
        s = slug(b["naam"])
        if namen.count(s) > 1 or s in bezet:
            s = slug("%s %s" % (b["naam"], re.sub(r"\s*\d.*$", "", b["adres"])))
        while s in bezet:
            s += "-2"
        b["slug"] = s
        bezet.add(s)
    return gids, overig


def domein(url):
    return re.sub(r"^www\.", "", url.split("/")[2]) if "//" in url else url


def telefoon(nummer):
    n = re.sub(r"[^\d+]", "", nummer)
    if n.startswith("+31"):
        n = "0" + n[3:]
    if re.match(r"06\d{8}$", n):
        return n, "06-%s %s %s %s" % (n[2:4], n[4:6], n[6:8], n[8:])
    return n, n


def adresregel(b):
    pc = re.sub(r"^(\d{4})\s*([A-Za-z]{2})$", lambda m: "%s %s" % (m.group(1), m.group(2).upper()), (b["postcode"] or "").strip())
    return ", ".join(x for x in (b["adres"], " ".join(x for x in (pc, b["plaats"]) if x)) if x)


def bedrijf_pagina(b, cat, anderen, root="../../"):
    canonical = "%s/bedrijvengids/%s/" % (SITE, b["slug"])
    soort = (b.get("soort") or cat["enkelvoud"]).lower()
    kort = "<p>%s is een %s aan de %s in %s.</p>" % (esc(b["naam"]), esc(soort), esc(b["adres"]), esc(b["plaats"])) if b["adres"] else ""
    beschrijving = b["beschrijving"] or samenvatting(b["tekst"] or kort)
    ld = {"@context": "https://schema.org", "@type": cat["schema"], "name": b["naam"], "url": canonical,
          "address": {"@type": "PostalAddress", "streetAddress": b["adres"], "postalCode": b["postcode"],
                      "addressLocality": b["plaats"], "addressCountry": "NL"}}
    if b["telefoon"]:
        ld["telephone"] = b["telefoon"]
    if b["lat"]:
        ld["geo"] = {"@type": "GeoCoordinates", "latitude": float(b["lat"]), "longitude": float(b["lon"])}
    if b["foto"]:
        ld["image"] = foto_url(b["foto"], SITE + "/")
    if b["openingstijden"]:
        ld["openingHoursSpecification"] = [
            {"@type": "OpeningHoursSpecification", "dayOfWeek": SCHEMA_DAG[i], "opens": t.split("–")[0], "closes": t.split("–")[1]}
            for i, t in enumerate(b["openingstijden"]) if "–" in t]
    kruim = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "Home", "item": SITE + "/"},
        {"@type": "ListItem", "position": 2, "name": cat["naam"], "item": "%s/bedrijvengids-categorie/%s/" % (SITE, cat["slug"])},
        {"@type": "ListItem", "position": 3, "name": b["naam"], "item": canonical}]}
    extra = "".join('\n  <script type="application/ld+json">%s</script>' % json.dumps(x, ensure_ascii=False) for x in (ld, kruim))
    if not b["tekst"] or b.get("concept"):
        # Nog geen (goedgekeurde) eigen tekst: wel een pagina (klikbaar vanuit de lijst), maar niet in Google tot de tekst er is
        extra += '\n  <meta name="robots" content="noindex">'
    out = [kop(b["naam"], beschrijving, canonical, root, foto_url(b["foto"], SITE + "/") or None, extra)]
    out.append('  <main class="artikel-wrap">\n    <div class="container">\n      <div class="artikel-layout">\n      <article class="artikel bedrijf">')
    out.append('        <div class="kruimelpad"><a href="%s">Home</a> › <a href="%sbedrijvengids-categorie/%s/">%s</a> › %s</div>'
               % (root, root, cat["slug"], esc(cat["naam"]), esc(b["naam"])))
    out.append('        <p class="gidslabel">%s</p>' % esc(cat["enkelvoud"]))
    out.append("        <h1>%s</h1>" % esc(b["naam"]))
    regels = []
    route = "https://www.openstreetmap.org/?mlat=%s&mlon=%s#map=17/%s/%s" % (b["lat"], b["lon"], b["lat"], b["lon"]) if b["lat"] else ""
    regels.append('<li><span class="evenement-info__kop">Adres</span>%s%s</li>'
                  % (esc(adresregel(b)), ' <a href="%s" target="_blank" rel="noopener" data-klik="route">Kaart</a>' % esc(route) if route else ""))
    if b.get("extra_vestiging"):
        regels.append('<li><span class="evenement-info__kop">Tweede vestiging</span>%s</li>' % esc(b["extra_vestiging"]))
    if not b["openingstijden"] and b.get("tijden_site"):
        regels.append('<li><span class="evenement-info__kop">Openingstijden</span>%s<br><span class="bron">(%s)</span></li>'
                      % ("<br>".join(esc(x.strip()) for x in re.split(r",\s*(?=[a-z]{2}\b)|\n", b["tijden_site"]) if x.strip()), b.get("tijden_bron", "volgens de eigen website")))
    if b["openingstijden"]:
        rijen = "".join("<tr><th>%s</th><td>%s</td></tr>" % (DAGEN[i], esc(t or "onbekend")) for i, t in enumerate(b["openingstijden"]))
        regels.append('<li><span class="evenement-info__kop">Openingstijden</span><table class="openingstijden">%s</table></li>' % rijen)
    if b.get("kenmerken"):
        regels.append('<li><span class="evenement-info__kop">Goed om te weten</span><span class="bedrijfkaart__kenmerken">%s</span></li>'
                      % "".join("<span>%s</span>" % esc(k) for k in b["kenmerken"]))
    contact = []
    if b["website"]:
        contact.append('<a href="%s" target="_blank" rel="%s noopener" data-klik="website">%s</a>'
                       % (esc(b["website"]), "sponsored" if b.get("uitgelicht") else "nofollow", esc(domein(b["website"]))))
    if b["telefoon"]:
        nr, tonen = telefoon(b["telefoon"])
        contact.append('<a href="tel:%s" data-klik="telefoon">%s</a>' % (esc(nr), esc(tonen)))
    if b.get("email"):
        contact.append('<a href="mailto:%s">%s</a>' % (esc(b["email"]), esc(b["email"])))
    social = [(n, b.get(n)) for n in ("instagram", "facebook") if b.get(n)]
    if social:
        contact.append(" · ".join('<a href="%s" target="_blank" rel="nofollow noopener">%s</a>' % (esc(u), n.capitalize()) for n, u in social))
    if contact:
        regels.append('<li><span class="evenement-info__kop">Contact</span>%s</li>' % "<br>".join(contact))
    if not b["in_gids"]:
        regels.append('<li class="bron">Gegevens: © <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">'
                      'OpenStreetMap-bijdragers</a> en Overture Maps. Klopt er iets niet? <a href="%skom-in-contact/">Laat het weten</a>.</li>' % root)
    if b["foto"]:
        out.append('        <figure><img src="%s" alt="%s"></figure>' % (esc(foto_url(b["foto"], root)), esc(b["naam"])))
    actie = b.get("actie") or {}
    if actie.get("tekst"):
        out.append('        <p class="gidsactie"><strong>Actie</strong> %s%s</p>'
                   % (esc(actie["tekst"]), " (tot en met %s)" % esc(datum_nl(actie["tot"])) if actie.get("tot") else ""))
    knop = b.get("knop") or {}
    if knop.get("tekst") and knop.get("link"):
        out.append('        <p><a class="knop" href="%s" target="_blank" rel="sponsored noopener" data-klik="knop">%s</a></p>'
                   % (esc(knop["link"]), esc(knop["tekst"])))
    if b.get("concept"):
        out.append('        <p class="bron">Concepttekst op basis van de eigen website, nog niet door de redactie gecontroleerd.</p>')
    if b["tekst"]:
        out.append('        <div class="inhoud-tekst">\n%s\n        </div>' % schoon(b["tekst"], set(), root, False, b["naam"]))
    else:
        out.append('        <div class="inhoud-tekst">%s</div>' % kort)
    if b.get("fotos"):
        out.append('        <div class="gidsfotos">%s</div>' % "".join('<img src="%s" alt="%s" loading="lazy">' % (esc(f), esc(b["naam"])) for f in b["fotos"]))
    out.append('        <section class="gids-sectie">\n          <h2>Contact en openingstijden</h2>')
    out.append('          <ul class="evenement-info%s">%s</ul>\n        </section>' % (" evenement-info--uitgelicht" if b.get("uitgelicht") else "", "".join(regels)))
    if not b.get("uitgelicht"):
        out.append(mijn_bedrijf(b, cat, root))
    out.append('        <div class="partner-slider" data-plaatsing="blog"></div>')
    if b["lat"]:
        lat, lon = float(b["lat"]), float(b["lon"])
        bbox = "%.5f,%.5f,%.5f,%.5f" % (lon - 0.006, lat - 0.003, lon + 0.006, lat + 0.003)
        out.append('        <section class="gids-sectie">\n          <h2>Hier vind je %s</h2>' % esc(b["naam"]))
        out.append('          <iframe class="kaartkader" title="Kaart van %s" loading="lazy" '
                   'src="https://www.openstreetmap.org/export/embed.html?bbox=%s&amp;layer=mapnik&amp;marker=%s,%s"></iframe>'
                   % (esc(b["naam"]), bbox, b["lat"], b["lon"]))
        out.append('          <p class="bron">Kaart: © <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap-bijdragers</a></p>\n        </section>')
    if anderen:
        out.append('        <section class="gids-sectie">\n          <h2>Meer sportscholen in Nijmegen</h2>\n          <div class="bedrijflijst">')
        out.extend("            " + (uitgelicht_kaart(x, root) if x.get("uitgelicht") else gewone_kaart(x, root)) for x in anderen[:4])
        out.append('          </div>\n          <p class="gids-verder"><a href="%sbedrijvengids-categorie/%s/">Bekijk alle %s</a></p>\n        </section>'
                   % (root, cat["slug"], esc(cat["naam"][0].lower() + cat["naam"][1:])))
    out.append('        <script src="%sassets/js/bedrijf.js?v=1" defer data-bedrijf="%s"></script>' % (root, esc(b["slug"])))
    out.append("      </article>\n\n      <!-- zijbalk --><!-- /zijbalk -->\n      </div>\n    </div>\n  </main>")
    out.append(VOET)
    return "\n".join(out)


def mijn_bedrijf(b, cat, root):
    """Knop naar het aanmeldformulier met het bedrijf al ingevuld (assets/js/formulier.js vult de velden uit de url)."""
    pc = re.sub(r"^(\d{4})\s*([A-Za-z]{2})$", lambda m: "%s %s" % (m.group(1), m.group(2).upper()), (b["postcode"] or "").strip())
    velden = {"vermelding": b["slug"], "bedrijf": b["naam"], "categorie": cat["enkelvoud"], "adres": b["adres"], "postcode": pc,
              "plaats": b["plaats"], "land": "Duitsland" if re.match(r"^\d{5}$", pc) else "Nederland",
              "site": b.get("website") or "", "telefoon": b.get("telefoon") or ""}
    link = "%sbedrijf-aanmelden/?%s" % (root, urllib.parse.urlencode({k: v for k, v in velden.items() if v}))
    return ('        <aside class="mijnbedrijf">\n          <p><strong>Is %s jouw bedrijf?</strong> Vul je gegevens aan met foto\'s, openingstijden '
            'en een eigen tekst. Je vermelding is en blijft gratis; wil je meer opvallen, dan kun je hem laten uitlichten.</p>\n'
            '          <p><a class="knop" href="%s">Dit is mijn bedrijf</a></p>\n        </aside>' % (esc(b["naam"]), esc(link)))


def datum_nl(iso):
    maanden = ["januari", "februari", "maart", "april", "mei", "juni", "juli", "augustus", "september", "oktober", "november", "december"]
    try:
        d = datetime.date.fromisoformat(iso)
    except ValueError:
        return iso
    return "%d %s %d" % (d.day, maanden[d.month - 1], d.year)


def pakketten_toepassen(bedrijven, pad, vandaag):
    """Betaalde pakketten: alleen zolang betaald_tot niet verstreken is. Zonder geldig pakket is alles gratis."""
    pakketten = json.loads(pad.read_text(encoding="utf-8")) if pad.exists() else {}
    for b in bedrijven:
        p = pakketten.get(b["slug"]) or {}
        actief = p.get("pakket") in BETAALD and p.get("betaald_tot", "") >= vandaag.isoformat()
        b["uitgelicht"] = actief
        if not actief:
            continue
        b["pakket"] = p["pakket"]
        if p.get("logo") and not b["foto"]:
            b["foto"] = p["logo"]
        if p.get("fotos"):
            b["foto"] = b["foto"] or p["fotos"][0]
            b["fotos"] = [f for f in p["fotos"] if f != b["foto"]]
        if (p.get("knop") or {}).get("link"):
            b["knop"] = p["knop"]
        actie = p.get("actie") or {}
        if actie.get("tekst") and actie.get("tot", "9999") >= vandaag.isoformat():
            b["actie"] = actie


def bedrijfkaart(b, root):
    """Kaartje in een lijst; elk bedrijf heeft een eigen pagina, die uit de gids met foto en openingstijden."""
    label = '<span class="bedrijfkaart__label">Uitgelicht</span>' if b.get("uitgelicht") else ""
    foto = '<img src="%s" alt="" loading="lazy">' % esc(foto_url(b["foto"], root)) if b["foto"] else ""
    open_ = '<span class="bedrijfkaart__open">Ma–vr %s</span>' % esc(b["openingstijden"][0]) if b["openingstijden"] else ""
    km = b.get("kenmerken") or []
    chips = '<span class="bedrijfkaart__kenmerken">%s</span>' % "".join("<span>%s</span>" % esc(k) for k in km[:4]) if km else ""
    return ('<a class="bedrijfkaart%s" href="%sbedrijvengids/%s/" data-kenmerken="%s">%s<span class="bedrijfkaart__tekst">%s<strong>%s</strong><span>%s</span>%s%s</span></a>'
            % (" bedrijfkaart--uitgelicht" if b.get("uitgelicht") else "", root, b["slug"], esc("|".join(km)), foto, label, esc(b["naam"]),
               esc(adresregel(b)), open_, chips))


LEAFLET = ('\n  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.css">'
           '\n  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet.markercluster/1.5.3/MarkerCluster.css">'
           '\n  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet.markercluster/1.5.3/MarkerCluster.Default.css">'
           '\n  <script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.js" defer></script>'
           '\n  <script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet.markercluster/1.5.3/leaflet.markercluster.js" defer></script>')


def kaart_blok(bedrijven, root, knoppen=False):
    """Kaart met alle bedrijven; bedrijven is een lijst (groep, bedrijf). Met knoppen kun je groepen aan- en uitzetten."""
    groepen = list(dict.fromkeys(g for g, _ in bedrijven))
    punten = [[b["naam"], round(float(b["lat"]), 6), round(float(b["lon"]), 6), "%sbedrijvengids/%s/" % (root, b["slug"]), adresregel(b), g]
              for g, b in bedrijven if b["lat"]]
    data = json.dumps({"groepen": groepen, "punten": punten}, ensure_ascii=False).replace("</", "<\\/")
    return ('%s          <div id="gidskaart" class="gidskaart" role="region" aria-label="Kaart met bedrijven"></div>\n'
            '          <script type="application/json" id="kaartdata">%s</script>\n'
            '          <script src="%sassets/js/kaart.js?v=2" defer></script>'
            % ('          <div id="kaartgroepen" class="kaartgroepen"></div>\n' if knoppen else "", data, root))


def start_pagina(groepen, root="../"):
    """/bedrijvengids/: kaart met alle bedrijven en de categorieën per groep."""
    canonical = "%s/bedrijvengids/" % SITE
    alle = [(g, b) for g, cats in groepen for cat, gids, overig in cats for b in gids + overig]
    beschrijving = "De bedrijvengids van Nijmegen: zoek op de kaart of per categorie naar sportscholen, restaurants, winkels en meer."
    out = [kop("Bedrijvengids Nijmegen", beschrijving, canonical, root, None, LEAFLET)]
    out.append('  <main class="artikel-wrap">\n    <div class="container">\n      <div class="artikel-layout">\n      <article class="artikel gids">')
    out.append('        <div class="kruimelpad"><a href="%s">Home</a> › Bedrijvengids</div>' % root)
    out.append("        <h1>Bedrijvengids Nijmegen</h1>")
    out.append('        <div class="inhoud-tekst"><p>Op zoek naar een sportschool, een kapper of een plek om te lunchen? In de bedrijvengids '
               'vind je de bedrijven van Nijmegen, op de kaart en per categorie. Klik op een punt voor het adres en de pagina van het bedrijf.</p></div>')
    out.append('        <section class="gids-sectie">\n          <h2>Op de kaart</h2>')
    out.append(kaart_blok(alle, root, knoppen=True))
    out.append('          <p class="bron">Gegevens: onze eigen gids, aangevuld met © OpenStreetMap-bijdragers en Overture Maps.</p>\n        </section>')
    out.append('        <section class="gids-sectie">\n          <h2>Categorieën</h2>\n          <div class="gidsgroepen">')
    for g, cats in groepen:
        out.append('            <div><h3>%s</h3><ul>%s</ul></div>' % (esc(g), "".join(
            '<li><a href="%sbedrijvengids-categorie/%s/">%s</a> (%d)</li>' % (root, cat["slug"], esc(cat["naam"]), len(gids) + len(overig))
            for cat, gids, overig in cats)))
    out.append('          </div>\n          <p>Staat jouw bedrijf er niet bij? <a href="%sbedrijf-aanmelden/">Meld je bedrijf aan</a>.</p>\n        </section>' % root)
    out.append("      </article>\n\n      <!-- zijbalk --><!-- /zijbalk -->\n      </div>\n    </div>\n  </main>")
    out.append(VOET)
    return "\n".join(out)


VOORBEELD = {"slug": "", "naam": "Jouw sportschool", "adres": "Uitgelicht staat bovenaan, met foto en actieknop", "postcode": "", "plaats": "",
             "foto": "assets/uploads/2022/11/sporten-in-nijmegen-533x400.webp", "kenmerken": ["proefles", "groepslessen"],
             "actie": {"tekst": "Eerste maand gratis sporten"}, "openingstijden": [], "uitgelicht": True}


def uitgelicht_kaart(b, root, voorbeeld=False):
    """Grote kaart voor betalende bedrijven: foto, kenmerken, de actie en een knop."""
    km = b.get("kenmerken") or []
    chips = '<span class="bedrijfkaart__kenmerken">%s</span>' % "".join("<span>%s</span>" % esc(k) for k in km[:4]) if km else ""
    actie = (b.get("actie") or {}).get("tekst", "")
    actie = '<span class="bedrijfkaart__actie">%s</span>' % esc(actie) if actie else ""
    label = "Voorbeeld" if voorbeeld else "Uitgelicht"
    href = "%sadverteren-bij-nijmegenonline/" % root if voorbeeld else "%sbedrijvengids/%s/" % (root, b["slug"])
    foto = '<img src="%s" alt="" loading="lazy">' % esc(foto_url(b["foto"], root)) if b.get("foto") else ""
    return ('<a class="bedrijfkaart bedrijfkaart--uitgelicht" href="%s" data-kenmerken="%s">%s<span class="bedrijfkaart__tekst">'
            '<span class="bedrijfkaart__label">%s</span><strong>%s</strong><span>%s</span>%s%s<span class="bedrijfkaart__knop">Bekijk %s</span></span></a>'
            % (href, esc("|".join(km)), foto, label, esc(b["naam"]), esc(adresregel(b) if not voorbeeld else b["adres"]),
               actie, chips, "hoe het werkt" if voorbeeld else "aanbod"))


def gewone_kaart(b, root):
    """Gratis vermelding: voor iedereen gelijk, zonder foto (een foto hoort bij Uitgelicht)."""
    km = b.get("kenmerken") or []
    chips = '<span class="bedrijfkaart__kenmerken">%s</span>' % "".join("<span>%s</span>" % esc(k) for k in km[:4]) if km else ""
    return ('<a class="bedrijfkaart" href="%sbedrijvengids/%s/" data-kenmerken="%s"><span class="bedrijfkaart__tekst"><strong>%s</strong><span>%s</span>%s</span></a>'
            % (root, b["slug"], esc("|".join(km)), esc(b["naam"]), esc(adresregel(b)), chips))


def categorie_pagina(cat, gids, overig, artikelen, root="../../"):
    """Indeling oktober 2026: alle gratis vermeldingen gelijk en zonder foto; alleen Uitgelicht valt op, lege plekken
    zijn advertentie, en onderaan staat wat Uitgelicht en Partner opleveren."""
    canonical = "%s/bedrijvengids-categorie/%s/" % (SITE, cat["slug"])
    alle = sorted(gids + overig, key=lambda b: b["naam"].lower())
    lijst = {"@context": "https://schema.org", "@type": "ItemList", "name": cat["naam"], "itemListElement": [
        {"@type": "ListItem", "position": n + 1, "name": b["naam"],
         "url": "%s/bedrijvengids/%s/" % (SITE, b["slug"])} for n, b in enumerate(alle)]}
    faq = {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": v, "acceptedAnswer": {"@type": "Answer", "text": a}} for v, a in cat["faq"]]}
    extra = "".join('\n  <script type="application/ld+json">%s</script>' % json.dumps(x, ensure_ascii=False) for x in (lijst, faq))
    out = [kop(cat["naam"], cat["beschrijving"], canonical, root, None, extra + LEAFLET)]
    out.append('  <main class="artikel-wrap">\n    <div class="container">\n      <div class="artikel-layout">\n      <article class="artikel gids">')
    out.append('        <div class="kruimelpad"><a href="%s">Home</a> › Bedrijvengids › %s</div>' % (root, esc(cat["naam"])))
    out.append('        <p class="gidslabel">Bedrijvengids</p>')
    out.append("        <h1>%s</h1>" % esc(cat["naam"]))
    intro = re.sub(r"<p>Op deze pagina vind je.*?</p>", "<p>Op deze pagina vind je alle %d sportscholen in Nijmegen, met openingstijden, "
                   "een eigen pagina en een kaart. Filter hieronder op wat jij belangrijk vindt, zoals groepslessen of een proefles.</p>" % len(alle),
                   cat["intro"], flags=re.S)
    out.append('        <div class="inhoud-tekst">%s</div>' % intro)
    uitgelicht = [b for b in alle if b.get("uitgelicht")]
    random.Random(datetime.date.today().isoformat() + cat["slug"]).shuffle(uitgelicht)
    uitgelicht = uitgelicht[:MAX_UITGELICHT]
    # Lege plekken: één voorbeeldkaart (zolang er niemand betaalt) en een uitnodiging om die plek te nemen
    out.append('        <section class="gids-sectie" id="uitgelicht">\n          <h2>Uitgelicht</h2>\n          <div class="bedrijflijst bedrijflijst--uitgelicht">')
    out.extend("            " + uitgelicht_kaart(b, root) for b in uitgelicht)
    if not uitgelicht:
        out.append("            " + uitgelicht_kaart(VOORBEELD, root, voorbeeld=True))
    if len(uitgelicht) < MAX_UITGELICHT:
        out.append('            <a class="vrijeplek" href="%sbedrijf-aanmelden/?pakket=uitgelicht&amp;categorie=%s"><strong>Nog %d %s vrij</strong>'
                   '<span>Zet jouw sportschool hier bovenaan, boven %d andere sportscholen. Met foto\'s, je actie, een eigen knop en je banner bij onze sportblogs.</span>'
                   '<span class="vrijeplek__prijs">Het eerste jaar &euro; 99</span></a>'
                   % (root, esc(cat["slug"]), MAX_UITGELICHT - len(uitgelicht), "plek" if MAX_UITGELICHT - len(uitgelicht) == 1 else "plekken", len(alle)))
    out.append("          </div>\n        </section>")
    out.append(filter_blok(alle))
    out.append('        <section class="gids-sectie">\n          <h2>Alle sportscholen in Nijmegen</h2>\n          <div class="bedrijflijst">')
    out.extend("            " + gewone_kaart(b, root) for b in alle if b not in uitgelicht)
    out.append('          </div>\n        </section>')
    out.append('        <div class="partner-slider" data-plaatsing="blog" data-onderwerp="%s"></div>' % cat["slug"])
    out.append('        <section class="gids-sectie">\n          <h2>Op de kaart</h2>')
    out.append(kaart_blok([(cat["groep"], b) for b in alle], root))
    out.append('        </section>')
    # Vergelijking voor ondernemers: wat levert betalen op
    rijen = [("Eigen pagina met adres, kaart en openingstijden", "ja", "ja", "ja"),
             ("Tekst door onze redactie", "kort", "uitgebreid", "uitgebreid"),
             ("Foto's op je eigen pagina", "1", "tot 10", "tot 10"),
             ("Bovenaan deze pagina, met foto en label Uitgelicht", "nee", "ja", "ja"),
             ("Actie en eigen knop (proefles, inschrijven, bellen)", "nee", "ja", "ja"),
             ("Uitgelicht onder onze blogs over sport en gezondheid", "nee", "ja", "ja"),
             ("Banner in de partnerbalk", "nee", "bij blogs over sport", "op de hele site"),
             ("Artikel over je bedrijf en een plek in de nieuwsbrief", "nee", "nee", "ja"),
             ("Overzicht van weergaven en kliks", "jaarlijks", "jaarlijks", "elk kwartaal")]
    out.append('        <section class="gids-sectie pakketvergelijk">\n          <h2>Heb je een sportschool in Nijmegen?</h2>'
               '\n          <p>Elke sportschool staat gratis in onze gids. Wil je opvallen tussen %d sportscholen? Kies dan voor Uitgelicht of Partner.</p>'
               % len(alle))
    out.append('          <div class="tabel-scroll"><table>\n            <thead><tr><th></th><th>Gratis</th><th>Uitgelicht<br><small>&euro; 149 per jaar,<br>eerste jaar &euro; 99</small></th>'
               '<th>Partner<br><small>&euro; 449 per jaar</small></th></tr></thead>\n            <tbody>')
    def cel(w):
        return {"ja": '<td class="ja">&#10003;</td>', "nee": '<td class="nee">&ndash;</td>'}.get(w, "<td>%s</td>" % w)
    out.extend("              <tr><th>%s</th>%s</tr>" % (esc(r[0]), "".join(cel(w) for w in r[1:])) for r in rijen)
    out.append('            </tbody>\n          </table></div>')
    out.append('          <p class="pakketvergelijk__knoppen"><a class="knop" href="%sbedrijf-aanmelden/?pakket=uitgelicht&amp;categorie=%s">Kies Uitgelicht</a> '
               '<a href="%sadverteren-bij-nijmegenonline/">Alle mogelijkheden</a> &middot; Staat je sportschool er al? Klik op je pagina op <em>Dit is mijn bedrijf</em>.</p>'
               '\n        </section>' % (root, esc(cat["slug"]), root))
    if artikelen:
        out.append('        <section class="gids-sectie">\n          <h2>Lees ook</h2>\n          <ul>')
        out.extend('            <li><a href="%s%s/">%s</a></li>' % (root, s, esc(t)) for s, t in artikelen)
        out.append("          </ul>\n        </section>")
    out.append('        <section class="gids-sectie faq">\n          <h2>Veelgestelde vragen</h2>')
    out.extend("          <details><summary>%s</summary><p>%s</p></details>" % (esc(v), esc(a)) for v, a in cat["faq"])
    out.append("        </section>")
    out.append('        <p class="bron">Gegevens: onze eigen gids, aangevuld met © <a href="https://www.openstreetmap.org/copyright" target="_blank" '
               'rel="noopener">OpenStreetMap-bijdragers</a> en Overture Maps.</p>')
    out.append("      </article>\n\n      <!-- zijbalk --><!-- /zijbalk -->\n      </div>\n    </div>\n  </main>")
    out.append(VOET)
    return "\n".join(out)


def blog_blokken(cat, alle):
    """Onder de blogberichten van het onderwerp: de uitgelichte bedrijven. Zolang niemand betaalt een verwijzing
    naar de categorie, met een uitnodiging voor ondernemers. Staat tussen <!-- gidstip --> en <!-- /gidstip -->."""
    uitgelicht = [b for b in alle if b.get("uitgelicht")]
    random.Random(datetime.date.today().isoformat() + cat["slug"] + "blog").shuffle(uitgelicht)
    root = "../"
    naar = '<a href="%sbedrijvengids-categorie/%s/">Bekijk alle %d %s in Nijmegen</a>' % (root, cat["slug"], len(alle), cat["meervoud"])
    if uitgelicht:
        blok = ('<section class="gidstip"><h2>%s uitgelicht</h2><div class="bedrijflijst bedrijflijst--uitgelicht">%s</div><p>%s</p></section>'
                % (esc(cat["meervoud"][0].upper() + cat["meervoud"][1:]), "".join(uitgelicht_kaart(b, root) for b in uitgelicht[:MAX_UITGELICHT]), naar))
    else:
        blok = ('<section class="gidstip"><h2>%s</h2><p>Zin om te beginnen? In onze bedrijvengids vind je alle %d %s in Nijmegen, '
                'met openingstijden, kenmerken en een kaart.</p><p>%s</p><p class="gidstip__ondernemer">Heb je zelf een %s? '
                '<a href="%sadverteren-bij-nijmegenonline/">Laat je hier uitlichten</a>.</p></section>'
                % (esc(cat["naam"]), len(alle), cat["meervoud"], naar, esc(cat["enkelvoud"].lower()), root))
    for s_ in cat.get("blogs", []):
        pad = ROOT / s_ / "index.html"
        if not pad.exists():
            continue
        tekst = re.sub(r"\n?[ \t]*<!-- gidstip -->.*?<!-- /gidstip -->", "", pad.read_text(encoding="utf-8"), flags=re.S)
        tekst = tekst.replace("      </article>", "        <!-- gidstip -->%s<!-- /gidstip -->\n      </article>" % blok, 1)
        tekst = re.sub(r'class="partner-slider" data-plaatsing="blog"(?: data-onderwerp="[^"]*")?',
                       'class="partner-slider" data-plaatsing="blog" data-onderwerp="%s"' % cat["slug"], tekst)
        pad.write_text(tekst, encoding="utf-8")


def filter_blok(bedrijven):
    """Knoppen om op kenmerk te filteren (assets/js/filter.js); alleen kenmerken die bij minstens twee bedrijven voorkomen."""
    tel = {}
    for b in bedrijven:
        for k in b.get("kenmerken") or []:
            tel[k] = tel.get(k, 0) + 1
    knoppen = sorted((k for k, n in tel.items() if n >= 2), key=lambda k: (-tel[k], k))
    if not knoppen:
        return ""
    return ('        <div class="gidsfilter" id="gidsfilter">\n          <p class="gidsfilter__kop">Waar zoek je naar?</p>\n          <div class="gidsfilter__knoppen">%s</div>\n'
            '          <p class="gidsfilter__uitkomst" aria-live="polite" hidden></p>\n        </div>\n'
            '        <script src="%sassets/js/filter.js?v=1" defer></script>'
            % ("".join('<button type="button" data-kenmerk="%s" aria-pressed="false">%s <span>%d</span></button>' % (esc(k), esc(k[0].upper() + k[1:]), tel[k])
                       for k in knoppen), "../../"))


def titel_van(slug_):
    pad = ROOT / slug_ / "index.html"
    if not pad.exists():
        return None
    m = re.search(r"<h1[^>]*>(.*?)</h1>", pad.read_text(encoding="utf-8"), re.S)
    return html.unescape(re.sub(r"<[^>]+>", "", m.group(1))).strip() if m else None


def scan_toepassen(bedrijven, pad, eigen_tekst=False):
    """Teksten uit tools/bedrijven_scan.py: een voorstel komt als concept (noindex) op de pagina, goedgekeurd gaat Google in.
    eigen_tekst: bedrijven met een tekst uit de oude gids houden die tot de redactie het voorstel goedkeurt;
    kenmerken en openingstijden krijgen ze wel meteen."""
    scan = json.loads(pad.read_text(encoding="utf-8")) if pad.exists() else {}
    for b in bedrijven:
        s = scan.get(b["slug"], {})
        if s.get("status") not in ("voorstel", "goedgekeurd") or not s.get("tekst") or not s.get("lijkt_actief", True):
            continue
        if eigen_tekst and s["status"] != "goedgekeurd":
            b["tijden_site"] = b.get("tijden_site") or s.get("openingstijden", "")
            b["kenmerken"] = s.get("kenmerken", [])
            continue
        b["tekst"] = "\n".join("<p>%s</p>" % esc(a.strip()) for a in re.split(r"\n\s*\n", s["tekst"]) if a.strip())
        b["concept"] = s["status"] != "goedgekeurd"
        b["tijden_site"] = s.get("openingstijden", "")
        b["kenmerken"] = s.get("kenmerken", [])


def foto_url(foto, root):
    """Foto's van aanmeldingen staan in de repo (assets/uploads/...); die krijgen het pad naar de root ervoor."""
    return foto if not foto or re.match(r"https?://", foto) else root + foto


def correcties_toepassen(bedrijven, pad):
    """Correcties van de redactie (data/bedrijvengids-correcties.json): adres, postcode, ligging, extra vestiging."""
    corr = json.loads(pad.read_text(encoding="utf-8")) if pad.exists() else {}
    for b in bedrijven:
        b.update({k: v for k, v in corr.get(b["slug"], {}).items() if k in ("adres", "postcode", "plaats", "lat", "lon", "extra_vestiging")})


def websites_toepassen(bedrijven, pad):
    """Uitkomst van tools/websites_controleren.py: een dode site geen link, een doorgestuurde site het nieuwe adres."""
    controle = json.loads(pad.read_text(encoding="utf-8")) if pad.exists() else {}
    for b in bedrijven:
        c = controle.get(b["slug"])
        if not c or c.get("website") != b.get("website"):
            continue   # intussen een ander adres: eerst opnieuw controleren
        if not c["werkt"]:
            b["website"] = ""
        elif c.get("eind_url") and domein(c["eind_url"]) != domein(b["website"]) and "?" not in c["eind_url"]:
            b["website"] = c["eind_url"]


def wijzigingen_toepassen(bedrijven, pad):
    """Door de redactie goedgekeurde wijzigingen via Dit is mijn bedrijf (tools/aanmeldingen.py). Die gaan voor
    op alles wat we zelf verzamelden (oude gids, OpenStreetMap, websitescan)."""
    wijz = json.loads(pad.read_text(encoding="utf-8")) if pad.exists() else {}
    for b in bedrijven:
        w = wijz.get(b["slug"])
        if not w:
            continue
        for veld, doel in (("bedrijf", "naam"), ("adres", "adres"), ("postcode", "postcode"), ("plaats", "plaats"),
                           ("site", "website"), ("telefoon", "telefoon"), ("bedrijfsmail", "email"), ("foto", "foto")):
            if w.get(veld):
                b[doel] = w[veld]
        if w.get("omschrijving"):
            b["tekst"] = "\n".join("<p>%s</p>" % esc(a.strip()).replace("\n", "<br>") for a in re.split(r"\n\s*\n", w["omschrijving"]) if a.strip())
            b["concept"] = False
        if w.get("openingstijden"):
            b["openingstijden"] = []
            b["tijden_site"] = w["openingstijden"]
            b["tijden_bron"] = "volgens het bedrijf"
        b["geclaimd"] = True


def vermeldingen(bedrijven, cat):
    """Wat er nu op de site staat, per bedrijf; Code.gs zet dit naast een wijziging via Dit is mijn bedrijf."""
    uit = {}
    for b in bedrijven:
        tijden = b.get("tijden_site") or "\n".join("%s %s" % (DAGEN[i], t or "onbekend") for i, t in enumerate(b["openingstijden"]))
        tekst = html.unescape(re.sub(r"<[^>]+>", "", re.sub(r"</(p|h\d|li)>", "\n\n", b["tekst"] or ""))).strip()
        uit[b["slug"]] = {"bedrijf": b["naam"], "categorie": cat["enkelvoud"], "adres": b["adres"], "postcode": b["postcode"] or "",
                          "plaats": b["plaats"] or "", "site": b.get("website") or "", "telefoon": b.get("telefoon") or "",
                          "bedrijfsmail": b.get("email") or "", "openingstijden": tijden,
                          "omschrijving": re.sub(r"\n{3,}", "\n\n", tekst), "foto": foto_url(b["foto"], SITE + "/") or "",
                          "url": "%s/bedrijvengids/%s/" % (SITE, b["slug"])}
    return uit


def doorverwijzen(b, cat):
    """De pagina van een verdwenen bedrijf stuurt door naar de categorie (ook in _redirects voor de echte server)."""
    map_ = ROOT / "bedrijvengids" / b["slug"]
    map_.mkdir(parents=True, exist_ok=True)
    tekst = DOORVERWIJZING % {"titel": esc(cat["naam"]), "url": "%s/bedrijvengids-categorie/%s/" % (SITE, cat["slug"]),
                              "pad": "../../bedrijvengids-categorie/%s/" % cat["slug"]}
    (map_ / "index.html").write_text(tekst.replace("Dit artikel is samengevoegd met", "Dit bedrijf staat niet meer in onze gids. Bekijk de"),
                                     encoding="utf-8")


def schrijf_redirects(weg, cat):
    """Blok "# bedrijvengids" in _redirects, vóór het blok van tools/agenda.py (dat alles erna opnieuw schrijft)."""
    pad = ROOT / "_redirects"
    tekst = pad.read_text(encoding="utf-8") if pad.exists() else ""
    agenda = tekst[tekst.index("# agenda"):] if "# agenda" in tekst else ""
    kop_ = tekst.split("# bedrijvengids")[0].split("# agenda")[0].rstrip("\n")
    regels = ["# bedrijvengids (tools/bedrijvengids.py)"]
    regels += ["/bedrijvengids/%s/ /bedrijvengids-categorie/%s/ 301" % (b["slug"], cat["slug"]) for b in sorted(weg, key=lambda b: b["slug"])]
    pad.write_text("\n".join(x for x in (kop_, "\n".join(regels), agenda.rstrip("\n")) if x) + "\n", encoding="utf-8")


def schrijf(pad, tekst):
    map_ = ROOT / pad
    map_.mkdir(parents=True, exist_ok=True)
    (map_ / "index.html").write_text(tekst, encoding="utf-8")


def main(bron):
    bron = pathlib.Path(bron)
    cat = CATEGORIE
    xml_ = bron / "bron" / "wp-xml" / "bedrijvengids-listdom.xml"
    if xml_.exists():
        gids = gids_uit_xml(xml_, cat["slug"])
        gids, overig = samenvoegen(gids, osm_uit_csv(bron / "advies" / "osm-bedrijvengids" / "sportscholen-aangevuld.csv", cat["soorten"]))
        (ROOT / "data" / "bedrijvengids.json").write_text(
            json.dumps({cat["slug"]: {"gids": gids, "overig": overig}}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    else:
        opgeslagen = json.loads((ROOT / "data" / "bedrijvengids.json").read_text(encoding="utf-8"))[cat["slug"]]
        gids, overig = opgeslagen["gids"], opgeslagen["overig"]
    scan_toepassen(overig, ROOT / "data" / "bedrijvengids-scan.json")
    scan_toepassen(gids, ROOT / "data" / "bedrijvengids-scan.json", eigen_tekst=True)
    correcties_toepassen(gids + overig, ROOT / "data" / "bedrijvengids-correcties.json")
    websites_toepassen(gids + overig, ROOT / "data" / "bedrijvengids-websites.json")
    wijzigingen_toepassen(gids + overig, ROOT / "data" / "bedrijvengids-wijzigingen.json")
    pakketten_toepassen(gids + overig, ROOT / "data" / "bedrijvengids-pakketten.json", datetime.date.today())
    # Zonder werkende website geen vermelding (afgesproken met Frans, 23-10-2026): het bedrijf bestaat dan
    # waarschijnlijk niet meer. Behalve als het betaalt of zelf zijn gegevens heeft aangevuld.
    # Door de redactie verwijderd (bijvoorbeeld gestopt of opgegaan in een ander bedrijf): status "verwijderd" in de scan.
    scan = json.loads((ROOT / "data" / "bedrijvengids-scan.json").read_text(encoding="utf-8"))
    weg = [b for b in gids + overig if scan.get(b["slug"], {}).get("status") == "verwijderd"
           or not (b.get("website") or b.get("uitgelicht") or b.get("geclaimd"))]
    gids = [b for b in gids if b not in weg]
    overig = [b for b in overig if b not in weg]
    for b in weg:
        doorverwijzen(b, cat)
    schrijf_redirects(weg, cat)
    (ROOT / "data" / "bedrijvengids-vermeldingen.json").write_text(
        json.dumps(vermeldingen(gids + overig, cat), ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    artikelen = [(s, titel_van(s)) for s in cat["artikelen"] if titel_van(s)]
    schrijf("bedrijvengids-categorie/%s" % cat["slug"], categorie_pagina(cat, gids, overig, artikelen))
    for b in gids + overig:
        anderen = [x for x in gids if x is not b] + [x for x in overig if x is not b]
        schrijf("bedrijvengids/%s" % b["slug"], bedrijf_pagina(b, cat, anderen))
    blog_blokken(cat, gids + overig)
    schrijf("bedrijvengids", start_pagina([(cat["groep"], [(cat, gids, overig)])]))
    print("%s: %d uit de gids, %d aangevuld" % (cat["slug"], len(gids), len(overig)))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "/mnt/project-files")
