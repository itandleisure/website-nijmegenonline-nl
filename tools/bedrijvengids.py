"""Bedrijvengids: voorbeeld met één categorie (sportscholen) en één bedrijfspagina.

Bronnen:
- de oude Listdom-gids uit de WordPress-export (bedrijvengids-listdom.xml): eigen tekst, foto, openingstijden
- OpenStreetMap/Overture (advies/osm-bedrijvengids/sportscholen-aangevuld.csv): de overige sportscholen

Gebruik: python tools/bedrijvengids.py [/mnt/project-files]
Schrijft data/bedrijvengids.json en de pagina's onder bedrijvengids/ en bedrijvengids-categorie/.
"""
import csv
import html
import json
import pathlib
import re
import sys
import unicodedata
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from import_wordpress import SITE, VOET, esc, kop, samenvatting, schoon  # noqa: E402

NS = {"wp": "http://wordpress.org/export/1.2/", "content": "http://purl.org/rss/1.0/modules/content/"}
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
    # Betaalde vermeldingen: bovenaan de categorie, link naar hun site met rel="sponsored"
    "uitgelicht": [],
    "artikelen": ["bammmm-en-je-bent-fit", "afvallen-met-sport-tips-voor-een-kleinere-maat", "7x-de-beste-warming-up-oefeningen"],
}


def slug(tekst):
    tekst = unicodedata.normalize("NFKD", tekst).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", tekst).strip("-")


def sleutel(naam):
    return re.sub(r"[^a-z0-9]", "", slug(re.sub(r"\bnijmegen\b", "", naam, flags=re.I)))


def alineas(tekst):
    """WordPress-tekst zonder <p> (losse regels) omzetten naar alinea's."""
    blokken = [b.strip() for b in re.split(r"\n\s*\n", tekst.replace("\r", "")) if b.strip()]
    return "\n".join(b if re.match(r"<(h\d|ul|ol|table|blockquote|figure)", b) else "<p>%s</p>" % b.replace("\n", "<br>")
                     for b in blokken)


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
    gids.sort(key=lambda b: (not b.get("uitgelicht"), b["naam"].lower()))
    overig = sorted((b for b in overig if sleutel(b["naam"]) not in bekend), key=lambda b: (b["naam"].lower(), b["adres"]))
    # Eigen pagina's voor de aangevulde bedrijven; dezelfde naam op meer adressen (ketens) krijgt de straat erbij
    namen = [slug(b["naam"]) for b in overig]
    bezet = {b["slug"] for b in gids} | {p.name for p in (ROOT / "bedrijvengids").iterdir() if p.is_dir()} - {slug(b["naam"]) for b in overig}
    for b in overig:
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
    return ", ".join(x for x in (b["adres"], " ".join(x for x in (b["postcode"], b["plaats"]) if x)) if x)


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
        ld["image"] = b["foto"]
    if b["openingstijden"]:
        ld["openingHoursSpecification"] = [
            {"@type": "OpeningHoursSpecification", "dayOfWeek": SCHEMA_DAG[i], "opens": t.split("–")[0], "closes": t.split("–")[1]}
            for i, t in enumerate(b["openingstijden"]) if "–" in t]
    kruim = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "Home", "item": SITE + "/"},
        {"@type": "ListItem", "position": 2, "name": cat["naam"], "item": "%s/bedrijvengids-categorie/%s/" % (SITE, cat["slug"])},
        {"@type": "ListItem", "position": 3, "name": b["naam"], "item": canonical}]}
    extra = "".join('\n  <script type="application/ld+json">%s</script>' % json.dumps(x, ensure_ascii=False) for x in (ld, kruim))
    if not b["tekst"]:
        # Nog geen eigen tekst: wel een pagina (klikbaar vanuit de lijst), maar niet in Google tot de tekst er is
        extra += '\n  <meta name="robots" content="noindex">'
    out = [kop(b["naam"], beschrijving, canonical, root, b["foto"] or None, extra)]
    out.append('  <main class="artikel-wrap">\n    <div class="container">\n      <div class="artikel-layout">\n      <article class="artikel bedrijf">')
    out.append('        <div class="kruimelpad"><a href="%s">Home</a> › <a href="%sbedrijvengids-categorie/%s/">%s</a> › %s</div>'
               % (root, root, cat["slug"], esc(cat["naam"]), esc(b["naam"])))
    out.append('        <p class="gidslabel">%s</p>' % esc(cat["enkelvoud"]))
    out.append("        <h1>%s</h1>" % esc(b["naam"]))
    regels = []
    route = "https://www.openstreetmap.org/?mlat=%s&mlon=%s#map=17/%s/%s" % (b["lat"], b["lon"], b["lat"], b["lon"]) if b["lat"] else ""
    regels.append('<li><span class="evenement-info__kop">Adres</span>%s%s</li>'
                  % (esc(adresregel(b)), ' <a href="%s" target="_blank" rel="noopener">Kaart</a>' % esc(route) if route else ""))
    if b["openingstijden"]:
        rijen = "".join("<tr><th>%s</th><td>%s</td></tr>" % (DAGEN[i], esc(t or "onbekend")) for i, t in enumerate(b["openingstijden"]))
        regels.append('<li><span class="evenement-info__kop">Openingstijden</span><table class="openingstijden">%s</table></li>' % rijen)
    contact = []
    if b["website"]:
        contact.append('<a href="%s" target="_blank" rel="%s noopener">%s</a>'
                       % (esc(b["website"]), "sponsored" if b.get("uitgelicht") else "nofollow", esc(domein(b["website"]))))
    if b["telefoon"]:
        nr, tonen = telefoon(b["telefoon"])
        contact.append('<a href="tel:%s">%s</a>' % (esc(nr), esc(tonen)))
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
        out.append('        <figure><img src="%s" alt="%s"></figure>' % (esc(b["foto"]), esc(b["naam"])))
    if b["tekst"]:
        out.append('        <div class="inhoud-tekst">\n%s\n        </div>' % schoon(b["tekst"], set(), root, False, b["naam"]))
    else:
        out.append('        <div class="inhoud-tekst">%s<p class="bron">Ben jij van %s? <a href="%sbedrijf-aanmelden/">Vul je gegevens aan</a> met een '
                   'foto, openingstijden en een beschrijving.</p></div>' % (kort, esc(b["naam"]), root))
    out.append('        <section class="gids-sectie">\n          <h2>Contact en openingstijden</h2>')
    out.append('          <ul class="evenement-info%s">%s</ul>\n        </section>' % (" evenement-info--uitgelicht" if b.get("uitgelicht") else "", "".join(regels)))
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
        out.extend("            " + bedrijfkaart(x, root) for x in anderen[:4])
        out.append('          </div>\n          <p class="gids-verder"><a href="%sbedrijvengids-categorie/%s/">Bekijk alle %s</a></p>\n        </section>'
                   % (root, cat["slug"], esc(cat["naam"][0].lower() + cat["naam"][1:])))
    out.append("      </article>\n\n      <!-- zijbalk --><!-- /zijbalk -->\n      </div>\n    </div>\n  </main>")
    out.append(VOET)
    return "\n".join(out)


def bedrijfkaart(b, root):
    """Kaartje in een lijst; elk bedrijf heeft een eigen pagina, die uit de gids met foto en openingstijden."""
    label = '<span class="bedrijfkaart__label">Uitgelicht</span>' if b.get("uitgelicht") else ""
    foto = '<img src="%s" alt="" loading="lazy">' % esc(b["foto"]) if b["foto"] else ""
    open_ = '<span class="bedrijfkaart__open">Ma–vr %s</span>' % esc(b["openingstijden"][0]) if b["openingstijden"] else ""
    return ('<a class="bedrijfkaart%s" href="%sbedrijvengids/%s/">%s<span class="bedrijfkaart__tekst">%s<strong>%s</strong><span>%s</span>%s</span></a>'
            % (" bedrijfkaart--uitgelicht" if b.get("uitgelicht") else "", root, b["slug"], foto, label, esc(b["naam"]),
               esc(adresregel(b)), open_))


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
            '          <script src="%sassets/js/kaart.js?v=1" defer></script>'
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


def categorie_pagina(cat, gids, overig, artikelen, root="../../"):
    canonical = "%s/bedrijvengids-categorie/%s/" % (SITE, cat["slug"])
    alle = gids + overig
    lijst = {"@context": "https://schema.org", "@type": "ItemList", "name": cat["naam"], "itemListElement": [
        {"@type": "ListItem", "position": n + 1, "name": b["naam"],
         "url": "%s/bedrijvengids/%s/" % (SITE, b["slug"])} for n, b in enumerate(alle)]}
    faq = {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": v, "acceptedAnswer": {"@type": "Answer", "text": a}} for v, a in cat["faq"]]}
    extra = "".join('\n  <script type="application/ld+json">%s</script>' % json.dumps(x, ensure_ascii=False) for x in (lijst, faq))
    out = [kop(cat["naam"], cat["beschrijving"], canonical, root, gids[0]["foto"] if gids else None, extra + LEAFLET)]
    out.append('  <main class="artikel-wrap">\n    <div class="container">\n      <div class="artikel-layout">\n      <article class="artikel gids">')
    out.append('        <div class="kruimelpad"><a href="%s">Home</a> › Bedrijvengids › %s</div>' % (root, esc(cat["naam"])))
    out.append('        <p class="gidslabel">Bedrijvengids</p>')
    out.append("        <h1>%s</h1>" % esc(cat["naam"]))
    out.append('        <div class="inhoud-tekst">%s</div>' % cat["intro"])
    out.append('        <p class="gidsteller">%d sportscholen in Nijmegen, waarvan %d met een eigen pagina in onze gids.</p>' % (len(alle), len(gids)))
    uitgelicht = [b for b in gids if b.get("uitgelicht")]
    aangemeld = [b for b in gids if not b.get("uitgelicht")]
    if uitgelicht:
        out.append('        <section class="gids-sectie">\n          <h2>Uitgelicht</h2>\n          <div class="bedrijflijst bedrijflijst--uitgelicht">')
        out.extend("            " + bedrijfkaart(b, root) for b in uitgelicht)
        out.append("          </div>\n        </section>")
    if aangemeld:
        out.append('        <section class="gids-sectie">\n          <h2>Uit onze bedrijvengids</h2>\n          <div class="bedrijflijst bedrijflijst--groot">')
        out.extend("            " + bedrijfkaart(b, root) for b in aangemeld)
        out.append("          </div>\n        </section>")
    out.append('        <div class="partner-slider" data-plaatsing="blog"></div>')
    out.append('        <section class="gids-sectie">\n          <h2>Op de kaart</h2>')
    out.append(kaart_blok([(cat["groep"], b) for b in alle], root))
    out.append('        </section>')
    out.append('        <section class="gids-sectie">\n          <h2>Alle sportscholen in Nijmegen</h2>\n          <div class="bedrijflijst">')
    out.extend("            " + bedrijfkaart(b, root) for b in overig)
    out.append('          </div>')
    out.append('          <p class="bron">Gegevens: onze eigen gids, aangevuld met © <a href="https://www.openstreetmap.org/copyright" target="_blank" '
               'rel="noopener">OpenStreetMap-bijdragers</a> en Overture Maps. Klopt er iets niet, of staat jouw sportschool er niet bij? '
               '<a href="%sbedrijf-aanmelden/">Meld je bedrijf aan</a>.</p>\n        </section>' % root)
    if artikelen:
        out.append('        <section class="gids-sectie">\n          <h2>Lees ook</h2>\n          <ul>')
        out.extend('            <li><a href="%s%s/">%s</a></li>' % (root, s, esc(t)) for s, t in artikelen)
        out.append("          </ul>\n        </section>")
    out.append('        <section class="gids-sectie faq">\n          <h2>Veelgestelde vragen</h2>')
    out.extend("          <details><summary>%s</summary><p>%s</p></details>" % (esc(v), esc(a)) for v, a in cat["faq"])
    out.append("        </section>")
    out.append("      </article>\n\n      <!-- zijbalk --><!-- /zijbalk -->\n      </div>\n    </div>\n  </main>")
    out.append(VOET)
    return "\n".join(out)


def titel_van(slug_):
    pad = ROOT / slug_ / "index.html"
    if not pad.exists():
        return None
    m = re.search(r"<h1[^>]*>(.*?)</h1>", pad.read_text(encoding="utf-8"), re.S)
    return html.unescape(re.sub(r"<[^>]+>", "", m.group(1))).strip() if m else None


def schrijf(pad, tekst):
    map_ = ROOT / pad
    map_.mkdir(parents=True, exist_ok=True)
    (map_ / "index.html").write_text(tekst, encoding="utf-8")


def main(bron):
    bron = pathlib.Path(bron)
    cat = CATEGORIE
    gids = gids_uit_xml(bron / "bron" / "wp-xml" / "bedrijvengids-listdom.xml", cat["slug"])
    for b in gids:
        b["uitgelicht"] = b["slug"] in cat["uitgelicht"]
    gids, overig = samenvoegen(gids, osm_uit_csv(bron / "advies" / "osm-bedrijvengids" / "sportscholen-aangevuld.csv", cat["soorten"]))
    (ROOT / "data" / "bedrijvengids.json").write_text(
        json.dumps({cat["slug"]: {"gids": gids, "overig": overig}}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    artikelen = [(s, titel_van(s)) for s in cat["artikelen"] if titel_van(s)]
    schrijf("bedrijvengids-categorie/%s" % cat["slug"], categorie_pagina(cat, gids, overig, artikelen))
    for b in gids + overig:
        anderen = [x for x in gids if x is not b] + [x for x in overig if x is not b]
        schrijf("bedrijvengids/%s" % b["slug"], bedrijf_pagina(b, cat, anderen))
    schrijf("bedrijvengids", start_pagina([(cat["groep"], [(cat, gids, overig)])]))
    print("%s: %d uit de gids, %d aangevuld" % (cat["slug"], len(gids), len(overig)))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "/mnt/project-files")
