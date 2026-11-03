"""Vacaturebank (besluit Frans, 3-11-2026; voorstel "Vacaturesectie NijmegenOnline", fase 1).

Bouwt uit data/vacatures.json:
- /vacatures/                  alle open vacatures, Uitgelicht bovenaan, met filters op soort werk en plaats
- /vacatures/<slug>/           een pagina per vacature met JobPosting-gegevens voor Google for Jobs
- /vacature-plaatsen/          uitleg, prijzen en het formulier (naar tools/google-formulier/Code.gs, type "vacature")

Afspraken:
- Een vacature staat standaard 45 dagen online (sluit = geplaatst + 45 dagen). Geeft de werkgever een eerdere
  sluitdatum op, dan geldt die.
- Basis is gratis voor lokale werkgevers; Uitgelicht kost € 49 (factuur achteraf). Uitzend-, wervings- en
  selectiebureaus ("bureau": true) betalen € 19 per vacature en krijgen het label "Via een bureau".
- Na de sluitdatum gaat de vacature uit de lijst en verdwijnen de JobPosting-gegevens; de pagina blijft
  BEWAAR_DAGEN staan met "Deze vacature is gesloten" (noindex) en verwijst daarna met een 301 naar /vacatures/
  (_redirects, blok "# vacatures").
- Vacatures van NijmegenOnline zelf hebben "eigen_pagina": true: ze staan in de lijst, maar hun pagina in
  vacatures/<slug>/ wordt niet door dit script gemaakt.

Velden per vacature: slug, functie, werkgever, bedrijf (sleutel in de bedrijvengids, of ""), site, logo, bureau,
soort, dienstverband, uren_van, uren_tot, opleiding, adres, postcode, plaats, thuiswerken, salaris_van, salaris_tot,
salaris_per ("uur" of "maand"), tekst (HTML), kort, solliciteren (link of e-mailadres), geplaatst, sluit, uitgelicht,
aanmelding, eigen_pagina.

Gebruik: python tools/vacatures.py [--datum 2026-11-03]
"""
import datetime
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from import_wordpress import DOORVERWIJZING, SITE, datum_nl, esc, samenvatting  # noqa: E402
import koppeling  # noqa: E402
import paginas  # noqa: E402

DATA = ROOT / "data" / "vacatures.json"
LOOPTIJD = 45        # dagen online (besluit Frans, 3-11-2026)
BEWAAR_DAGEN = 90    # gesloten pagina blijft zo lang staan, daarna een 301
SOORTEN = ["Horeca", "Zorg en welzijn", "Winkel en verkoop", "Techniek en bouw", "Kantoor en administratie",
           "Onderwijs en kinderopvang", "ICT en marketing", "Bijbaan of stage", "Overig"]
DIENSTVERBANDEN = ["Vast", "Tijdelijk", "Bijbaan", "Stage", "Freelance"]
OPLEIDINGEN = ["Geen voorkeur", "Vmbo", "Mbo", "Hbo", "Wo"]
THUISWERKEN = ["Nee", "Deels", "Volledig"]
# Werkgebied: Nijmegen, de gemeenten eromheen en Kleve (plaatsnamen zoals in tools/koppeling.py)
WERKGEBIED = ["Nijmegen", "Wijchen", "Beuningen", "Berg en Dal", "Groesbeek", "Heumen", "Mook", "Elst", "Bemmel",
              "Kleef", "Kranenburg", "Druten", "Gennep"]


def laad():
    return json.loads(DATA.read_text(encoding="utf-8")) if DATA.exists() else []


def bewaar(vacatures):
    DATA.write_text(json.dumps(vacatures, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def sluitdatum(geplaatst, gekozen=""):
    """45 dagen na plaatsing, of eerder als de werkgever dat koos."""
    standaard = datetime.date.fromisoformat(geplaatst) + datetime.timedelta(days=LOOPTIJD)
    try:
        eigen = datetime.date.fromisoformat((gekozen or "")[:10])
    except ValueError:
        eigen = None
    return (eigen if eigen and datetime.date.fromisoformat(geplaatst) <= eigen < standaard else standaard).isoformat()


def is_open(v, vandaag):
    if v.get("ingevuld"):
        return False
    return v.get("geplaatst", "") <= vandaag.isoformat() and (not v.get("sluit") or v["sluit"] >= vandaag.isoformat())


def open_vacatures(vandaag=None, vacatures=None):
    """Open vacatures, Uitgelicht eerst en dan de nieuwste."""
    vandaag = vandaag or datetime.date.today()
    lijst = [v for v in (laad() if vacatures is None else vacatures) if is_open(v, vandaag)]
    lijst.sort(key=lambda v: v.get("geplaatst", ""), reverse=True)            # nieuwste eerst
    return sorted(lijst, key=lambda v: 0 if v.get("uitgelicht") else 1)       # stabiel: Uitgelicht bovenaan


def per_bedrijf(vandaag=None):
    uit = {}
    for v in open_vacatures(vandaag):
        if v.get("bedrijf"):
            uit.setdefault(v["bedrijf"], []).append(v)
    return uit


def plaats_van(v):
    return koppeling.plaats_naam(v.get("plaats", "")) or koppeling.plaats_van(" ".join((v.get("adres", ""), v.get("postcode", ""), v.get("plaats", "")))) \
        or (v.get("plaats") or "").strip() or "Nijmegen"


def uren(v):
    van, tot = v.get("uren_van") or "", v.get("uren_tot") or ""
    if van and tot and van != tot:
        return "%s tot %s uur per week" % (van, tot)
    return "%s uur per week" % (van or tot) if (van or tot) else ""


def bedrag(x):
    """'2.600', '2600', '14,50' of '€ 3.100,-' als getal; None als het geen bedrag is."""
    s = re.sub(r"[€\s]|,-$", "", str(x or ""))
    if re.match(r"^\d{1,3}(\.\d{3})+(,\d{1,2})?$", s):   # punt als duizendtal
        s = s.replace(".", "")
    try:
        return float(s.replace(",", "."))
    except ValueError:
        return None


def salaris(v):
    van, tot = bedrag(v.get("salaris_van") or ""), bedrag(v.get("salaris_tot") or "")
    if not van and not tot:
        return ""
    fmt = lambda f: ("€ %.2f" % f).replace(".", ",").replace(",00", "") if f < 100 else "€ {:,.0f}".format(f).replace(",", ".")
    per = "per uur" if v.get("salaris_per") == "uur" else "per maand"
    if van and tot and van != tot:
        return "%s tot %s %s" % (fmt(van), fmt(tot), per)
    return "%s %s" % (fmt(van or tot), per)


def sollicitatie_link(v):
    s = (v.get("solliciteren") or "").strip()
    if re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", s):
        return "mailto:%s?subject=%s" % (s, ("Sollicitatie " + v["functie"]).replace(" ", "%20"))
    if s and not re.match(r"https?://", s):
        s = "https://" + s
    return s


def werktype(v):
    """employmentType voor Google."""
    d = (v.get("dienstverband") or "").lower()
    uit = []
    try:
        tot = float(v.get("uren_tot") or v.get("uren_van") or 0)
    except ValueError:
        tot = 0
    if d == "stage":
        return ["INTERN"]
    if d == "freelance":
        return ["CONTRACTOR"]
    uit.append("FULL_TIME" if tot >= 32 else "PART_TIME")
    if d in ("tijdelijk", "bijbaan"):
        uit.append("TEMPORARY")
    return uit


def jobposting(v, canonical, vermeldingen):
    plaats = plaats_van(v)
    duits = re.match(r"^\d{5}$", (v.get("postcode") or "").strip()) or plaats in ("Kleef", "Kranenburg", "Goch")
    adres = {"@type": "PostalAddress", "addressLocality": "Kleve" if plaats == "Kleef" else plaats,
             "addressCountry": "DE" if duits else "NL"}
    if v.get("adres"):
        adres["streetAddress"] = v["adres"]
    if v.get("postcode"):
        adres["postalCode"] = v["postcode"]
    org = koppeling.organisatie_ld(v["bedrijf"], vermeldingen[v["bedrijf"]]) if v.get("bedrijf") in vermeldingen else \
        {"@type": "Organization", "name": v["werkgever"], **({"sameAs": v["site"]} if v.get("site") else {})}
    if v.get("logo"):
        org["logo"] = "%s/%s" % (SITE, v["logo"]) if not v["logo"].startswith("http") else v["logo"]
    ld = {"@context": "https://schema.org", "@type": "JobPosting", "title": v["functie"], "description": v["tekst"],
          "datePosted": v["geplaatst"], "employmentType": werktype(v), "hiringOrganization": org,
          "jobLocation": {"@type": "Place", "address": adres},
          "identifier": {"@type": "PropertyValue", "name": "NijmegenOnline", "value": v["slug"]}, "url": canonical}
    if v.get("sluit"):
        ld["validThrough"] = "%sT23:59:00+01:00" % v["sluit"]
    if v.get("thuiswerken") == "Volledig":
        ld["jobLocationType"] = "TELECOMMUTE"
        ld["applicantLocationRequirements"] = {"@type": "Country", "name": "Nederland"}
    van, tot = bedrag(v.get("salaris_van") or ""), bedrag(v.get("salaris_tot") or "")
    if van or tot:
        waarde = {"@type": "QuantitativeValue", "unitText": "HOUR" if v.get("salaris_per") == "uur" else "MONTH"}
        if van and tot and van != tot:
            waarde.update(minValue=van, maxValue=tot)
        else:
            waarde["value"] = van or tot
        ld["baseSalary"] = {"@type": "MonetaryAmount", "currency": "EUR", "value": waarde}
    if v.get("opleiding") and v["opleiding"] != "Geen voorkeur":
        ld["educationRequirements"] = v["opleiding"]
    return ld


def kenmerken(v):
    """Korte regel op de kaart: plaats · uren · dienstverband."""
    return " · ".join(x for x in (plaats_van(v), uren(v), v.get("dienstverband", "")) if x)


def kaart(v, root):
    href = "%svacatures/%s/" % (root, v["slug"])
    label = "Uitgelicht" if v.get("uitgelicht") else ("Via een bureau" if v.get("bureau") else v.get("soort") or "Vacature")
    kort = v.get("kort") or samenvatting(v.get("tekst", ""), 140)
    return ('<a class="vacaturekaart%s" href="%s" data-soort="%s" data-plaats="%s"><span class="vacaturekaart__status">%s</span>'
            '<strong>%s</strong><span class="vacaturekaart__werkgever">%s</span><span class="vacaturekaart__regel">%s</span><span>%s</span></a>'
            % (" vacaturekaart--uitgelicht" if v.get("uitgelicht") else "", href, esc(v.get("soort") or "Overig"), esc(plaats_van(v)),
               esc(label), esc(v["functie"]), esc(v["werkgever"]), esc(kenmerken(v)), esc(kort)))


def filterknoppen(naam, waarden, label):
    knoppen = ['<button type="button" data-%s="" aria-pressed="true">%s</button>' % (naam, "Alles")]
    knoppen += ['<button type="button" data-%s="%s" aria-pressed="false">%s <span>%d</span></button>' % (naam, esc(w), esc(w), n)
                for w, n in waarden]
    return ('        <div class="gidsen-filter vacaturefilter" role="group" aria-label="%s" hidden>\n          %s\n        </div>'
            % (esc(label), "\n          ".join(knoppen)))


def overzicht(open_, vandaag):
    root = "../"
    tel = lambda sleutel: sorted({}.fromkeys([sleutel(v) for v in open_]).keys(),
                                 key=lambda w: (-sum(1 for v in open_ if sleutel(v) == w), w))
    soorten = [(s, sum(1 for v in open_ if (v.get("soort") or "Overig") == s)) for s in tel(lambda v: v.get("soort") or "Overig")]
    plaatsen = [(p, sum(1 for v in open_ if plaats_van(v) == p)) for p in tel(plaats_van)]
    inhoud = ['        <h1>Vacatures in Nijmegen en omgeving</h1>',
              '        <p class="pagina__intro">Werk zoeken in Nijmegen, Wijchen, Beuningen of net over de grens? Hier staan de '
              'vacatures van werkgevers uit de regio, rechtstreeks van het bedrijf zelf.</p>',
              '        <p><a class="knop" href="%svacature-plaatsen/">Vacature plaatsen</a> <span class="bron">Gratis voor lokale werkgevers.</span></p>' % root]
    if open_:
        if len(soorten) > 1:
            inhoud.append(filterknoppen("soort", soorten, "Filter op soort werk"))
        if len(plaatsen) > 1:
            inhoud.append(filterknoppen("plaats", plaatsen, "Filter op plaats"))
        inhoud.append('        <p class="vacaturefilter__uitkomst" role="status" hidden></p>')
        inhoud.append('        <div class="vacaturelijst">\n%s\n        </div>' % "\n".join("          " + kaart(v, root) for v in open_))
    else:
        inhoud.append('        <p>Er staan op dit moment geen open vacatures. Kijk binnenkort nog eens.</p>')
    inhoud.append('        <h2>Zelf een vacature plaatsen?</h2>\n'
                  '        <p>Ben je een werkgever in Nijmegen of omgeving? Plaats je vacature gratis: hij staat %d dagen online, op je '
                  'bedrijfspagina in de bedrijvengids en in Google for Jobs. Wil je meer opvallen, kies dan Uitgelicht. '
                  '<a href="%svacature-plaatsen/">Zo werkt het</a>.</p>' % (LOOPTIJD, root))
    inhoud.append('        <script src="%sassets/js/vacatures.js?v=1" defer></script>' % root)
    lijst = {"@context": "https://schema.org", "@type": "ItemList", "itemListElement": [
        {"@type": "ListItem", "position": n + 1, "url": "%s/vacatures/%s/" % (SITE, v["slug"])} for n, v in enumerate(open_[:50])]}
    extra = '\n  <script type="application/ld+json">%s</script>' % json.dumps(lijst, ensure_ascii=False) if open_ else ""
    return paginas.pagina("Vacatures in Nijmegen en omgeving",
                          "Vacatures in Nijmegen en omgeving, rechtstreeks van lokale werkgevers: horeca, zorg, winkel, techniek, kantoor en bijbanen.",
                          "vacatures", "Vacatures", "\n".join(inhoud), extra)


def vacature_pagina(v, vandaag, open_, vermeldingen):
    root = "../../"
    canonical = "%s/vacatures/%s/" % (SITE, v["slug"])
    gesloten = not is_open(v, vandaag)
    bedrijf = v.get("bedrijf") if v.get("bedrijf") in vermeldingen else ""
    titel = "Vacature %s bij %s" % (v["functie"], v["werkgever"])
    beschrijving = samenvatting("<p>%s. %s</p>%s" % (titel, kenmerken(v), v["tekst"]))
    extra = ""
    if gesloten:
        extra = '\n  <meta name="robots" content="noindex">'
    else:
        extra = '\n  <script type="application/ld+json">%s</script>' % json.dumps(jobposting(v, canonical, vermeldingen), ensure_ascii=False)
    kruim = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "Home", "item": SITE + "/"},
        {"@type": "ListItem", "position": 2, "name": "Vacatures", "item": SITE + "/vacatures/"},
        {"@type": "ListItem", "position": 3, "name": v["functie"], "item": canonical}]}
    extra += '\n  <script type="application/ld+json">%s</script>' % json.dumps(kruim, ensure_ascii=False)
    out = []
    if gesloten:
        out.append('        <p class="afgelopen">Deze vacature is gesloten. <a href="../">Bekijk de open vacatures</a>.</p>')
    label = "Uitgelichte vacature" if v.get("uitgelicht") else "Vacature"
    out.append('        <p class="gidslabel">%s%s</p>' % (label, " · via een uitzend-, wervings- of selectiebureau" if v.get("bureau") else ""))
    out.append("        <h1>%s</h1>" % esc(v["functie"]))
    werkgever = ('<a href="%sbedrijvengids/%s/">%s</a>' % (root, bedrijf, esc(v["werkgever"])) if bedrijf else esc(v["werkgever"]))
    regels = ['<li><span class="evenement-info__kop">Werkgever</span>%s</li>' % werkgever]
    plek = ", ".join(x for x in (v.get("adres", ""), " ".join(x for x in (v.get("postcode", ""), v.get("plaats", "")) if x)) if x) or plaats_van(v)
    if v.get("thuiswerken") == "Volledig":
        plek = "Volledig thuiswerken (%s)" % plaats_van(v)
    elif v.get("thuiswerken") == "Deels":
        plek += "<br>Deels thuiswerken"
    regels.append('<li><span class="evenement-info__kop">Waar</span>%s</li>' % (esc(plek).replace("&lt;br&gt;", "<br>")))
    for kopje, waarde in (("Uren", uren(v)), ("Dienstverband", v.get("dienstverband", "")), ("Salaris", salaris(v)),
                          ("Opleiding", v.get("opleiding", "") if v.get("opleiding") not in ("", "Geen voorkeur") else ""),
                          ("Soort werk", v.get("soort", "")),
                          ("Geplaatst", datum_nl(v["geplaatst"])),
                          ("Reageren voor", datum_nl(v["sluit"]) if v.get("sluit") and not gesloten else "")):
        if waarde:
            regels.append('<li><span class="evenement-info__kop">%s</span>%s</li>' % (kopje, esc(waarde)))
    link = sollicitatie_link(v)
    if link and not gesloten:
        regels.append('<li><a class="knop" href="%s"%s>Solliciteer</a></li>'
                      % (esc(link), "" if link.startswith("mailto:") else ' target="_blank" rel="nofollow noopener"'))
    out.append('        <ul class="evenement-info%s">%s</ul>' % (" evenement-info--uitgelicht" if v.get("uitgelicht") else "", "".join(regels)))
    if v.get("logo"):
        out.append('        <p class="vacature__logo"><img src="%s%s" alt="Logo %s"></p>' % (root, esc(v["logo"]), esc(v["werkgever"])))
    out.append('        <div class="inhoud-tekst">\n%s\n        </div>' % v["tekst"])
    if link and not gesloten:
        out.append('        <p class="gids-cta"><a class="knop" href="%s"%s>Solliciteer op deze vacature</a></p>'
                   % (esc(link), "" if link.startswith("mailto:") else ' target="_blank" rel="nofollow noopener"'))
    if bedrijf:
        out.append(koppeling.over_bedrijf(bedrijf, vermeldingen[bedrijf], root))
    meer = [x for x in open_ if x is not v and (x.get("soort") == v.get("soort") or x.get("bedrijf") and x.get("bedrijf") == v.get("bedrijf"))][:4]
    if meer:
        out.append('        <section class="gids-sectie">\n          <h2>Meer vacatures</h2>\n          <div class="vacaturelijst">')
        out.extend("            " + kaart(x, root) for x in meer)
        out.append('          </div>\n          <p class="gids-verder"><a href="../">Alle vacatures</a></p>\n        </section>')
    out.append('        <p class="bron">Klopt deze vacature niet, of is hij al vervuld? <a href="%skom-in-contact/?onderwerp=%s">Laat het ons weten</a>.</p>'
               % (root, esc(("Vacature " + v["slug"]).replace(" ", "%20"))))
    return paginas.pagina(titel, beschrijving, "vacatures/" + v["slug"], '<a href="../">Vacatures</a> › %s' % esc(v["functie"]),
                          "\n".join(out), extra, afbeelding=("%s/%s" % (SITE, v["logo"]) if v.get("logo") else None))


def plaatsen_pagina():
    velden = [
        ("kop", "Het bedrijf", "kop", False, None),
        ("bedrijf", "Zoek je bedrijf", "bedrijf", False,
         {"werkgever": "naam", "site": "site", "adres": "adres", "postcode": "postcode", "plaats": "plaats",
          "_hint": "Staat je bedrijf in onze bedrijvengids? Kies het hier, dan komt de vacature ook op je bedrijfspagina. "
                   "Staat het er niet in, laat dit veld dan leeg en vul hieronder de gegevens in."}),
        ("werkgever", "Naam van het bedrijf", "text", True, None),
        ("site", "Website", "url", True, None),
        ("kvk", "KvK-nummer", "text", False, None),
        ("bureau", "Ben je een uitzend-, wervings- of selectiebureau?", "radio", True,
         [("nee", "Nee, we zoeken iemand voor ons eigen bedrijf"), ("ja", "Ja, we werven voor een opdrachtgever (€ 19 per vacature)")]),
        ("foto", "Logo (optioneel)", "bestand", False, "JPG, PNG of WebP."),
        ("kop", "De functie", "kop", False, None),
        ("functie", "Functietitel", "text", True, None),
        ("soort", "Soort werk", "lijst", True, SOORTEN),
        ("dienstverband", "Dienstverband", "radio", True, DIENSTVERBANDEN),
        ("uren_van", "Uren per week, vanaf", "number", False, None),
        ("uren_tot", "Uren per week, tot en met", "number", False, None),
        ("opleiding", "Opleidingsniveau", "lijst", False, OPLEIDINGEN),
        ("kop", "Werkplek", "kop", False, None),
        ("adres", "Straat en huisnummer", "text", False, None),
        ("postcode", "Postcode", "postcode", False, None),
        ("plaats", "Plaats", "text", True, None),
        ("thuiswerken", "Thuiswerken", "radio", True, THUISWERKEN),
        ("kop", "Salaris", "kop", False, "Sterk aangeraden: Google toont het salaris in de zoekresultaten."),
        ("salaris_van", "Salaris vanaf (euro)", "prijs", False, None),
        ("salaris_tot", "Salaris tot (euro)", "prijs", False, None),
        ("salaris_per", "Per", "radio", False, [("maand", "Per maand"), ("uur", "Per uur")]),
        ("kop", "De vacaturetekst", "kop", False, "Wat ga je doen, wat vragen jullie en wat bieden jullie?"),
        ("omschrijving", "Vacaturetekst", "tekst", True, None),
        ("kop", "Solliciteren", "kop", False, None),
        ("solliciteren", "Link naar de sollicitatiepagina of e-mailadres voor sollicitaties", "text", True, None),
        ("sluitdatum", "Sluitdatum (optioneel, hooguit %d dagen vooruit)" % LOOPTIJD, "date", False, None),
        ("kop", "Hoe wil je de vacature plaatsen?", "kop", False, None),
        ("pakket", "Pakket", "keuze", True, [("Basis", "Basis: gratis, %d dagen online" % LOOPTIJD),
                                             ("Uitgelicht", "Uitgelicht: € 49 excl. btw, bovenaan met label (factuur achteraf)")]),
        ("factuur", "Factuurgegevens (alleen bij Uitgelicht of als bureau)", "tekst", False, None),
        ("kop", "Jouw gegevens", "kop", False, "Deze gegevens komen niet op de website."),
        ("naam", "Je naam", "text", True, None),
        ("email", "Je e-mailadres", "email", True, None),
        ("telefoon", "Je telefoonnummer", "tel", True, None),
        ("notitie", "Opmerking voor de redactie", "tekst", False, None),
        ("voorwaarden", "Voorwaarden", "radio", True,
         [("akkoord", "Ik ga akkoord: de vacature is echt, sollicitanten hoeven nergens voor te betalen, en NijmegenOnline mag hem weigeren of offline halen.")]),
    ]
    inhoud = """        <h1>Vacature plaatsen</h1>
        <p class="pagina__intro">Zoek je personeel in Nijmegen of omgeving? Plaats je vacature op NijmegenOnline. Voor lokale werkgevers is dat gratis.</p>
        <h2>Zo werkt het</h2>
        <ul>
          <li>Vul het formulier in. Kies je bedrijf uit onze bedrijvengids, dan komt de vacature ook op je bedrijfspagina.</li>
          <li>De redactie bekijkt elke vacature voordat hij online gaat. Je krijgt een e-mail zodra hij op de site staat.</li>
          <li>Je vacature staat {dagen} dagen online, of korter als je een eerdere sluitdatum kiest. Daarna gaat hij vanzelf offline.</li>
          <li>Elke vacature komt met de juiste gegevens op de site, zodat Google hem kan tonen in Google for Jobs.</li>
        </ul>
        <h2>Prijzen</h2>
        <ul>
          <li><strong>Basis</strong>: gratis voor werkgevers uit Nijmegen en omgeving.</li>
          <li><strong>Uitgelicht</strong>: € 49 excl. btw per vacature. Bovenaan het overzicht, met een label.</li>
          <li><strong>Uitzend-, wervings- en selectiebureaus</strong>: € 19 excl. btw per vacature. We vermelden dat de vacature via een bureau gaat.</li>
          <li>Heb je een pakket in de bedrijvengids? Dan zitten er uitgelichte vacatures bij: 2 per jaar bij Uitgelicht, 6 bij Partner en onbeperkt bij Hoofdpartner.</li>
        </ul>
        <p>We plaatsen geen vacatures waarvoor sollicitanten moeten betalen, geen reclame die op een vacature lijkt en geen vacatures met discriminerende eisen. Het werk moet in Nijmegen of omgeving zijn (tot en met Kleve).</p>
        <h2>Je vacature</h2>
{formulier}""".format(dagen=LOOPTIJD, formulier=paginas.formulier("vacature", "Vacature aangemeld via NijmegenOnline", velden, "Vacature versturen",
        "Bedankt! De redactie heeft je vacature ontvangen en bekijkt hem zo snel mogelijk. Je krijgt een e-mail zodra hij online staat, "
        "of als we hem niet kunnen plaatsen."))
    return paginas.pagina("Vacature plaatsen", "Plaats je vacature gratis op NijmegenOnline: voor werkgevers in Nijmegen en omgeving, ook in Google for Jobs.",
                          "vacature-plaatsen", '<a href="../vacatures/">Vacatures</a> › Vacature plaatsen', inhoud)


def doorverwijzing(slug):
    map_ = ROOT / "vacatures" / slug
    map_.mkdir(parents=True, exist_ok=True)
    tekst = DOORVERWIJZING % {"titel": "Vacatures", "url": SITE + "/vacatures/", "pad": "../"}
    (map_ / "index.html").write_text(tekst.replace("Dit artikel is samengevoegd met", "Deze vacature is gesloten. Bekijk de"),
                                     encoding="utf-8")


def schrijf(pad, tekst):
    map_ = ROOT / pad
    map_.mkdir(parents=True, exist_ok=True)
    (map_ / "index.html").write_text(tekst, encoding="utf-8")


def main(vandaag):
    vacatures = laad()
    vermeldingen = koppeling.laad_vermeldingen()
    open_ = open_vacatures(vandaag, vacatures)
    schrijf("vacatures", overzicht(open_, vandaag))
    schrijf("vacature-plaatsen", plaatsen_pagina())
    pagina_, weg = 0, []
    for v in vacatures:
        if v.get("eigen_pagina"):
            continue
        sluit = v.get("sluit") or "9999-12-31"
        if (vandaag - datetime.date.fromisoformat(min(sluit, vandaag.isoformat()))).days > BEWAAR_DAGEN:
            doorverwijzing(v["slug"])
            weg.append(v["slug"])
            continue
        schrijf("vacatures/" + v["slug"], vacature_pagina(v, vandaag, open_, vermeldingen))
        pagina_ += 1
    # 301's voor Cloudflare; het blok "# vacatures" wordt elke keer opnieuw geschreven (net als "# agenda")
    redirects = ROOT / "_redirects"
    tekst = redirects.read_text(encoding="utf-8") if redirects.exists() else ""
    # Het blok staat vóór "# agenda": tools/agenda.py schrijft alles vanaf die regel opnieuw
    tekst = re.sub(r"# vacatures \(tools/vacatures.py\)\n(?:/vacatures/[^\n]*\n)*", "", tekst)
    blok = "# vacatures (tools/vacatures.py)\n" + "".join("/vacatures/%s/ /vacatures/ 301\n" % s for s in sorted(weg)) if weg else ""
    if blok and "# agenda" in tekst:
        tekst = tekst.replace("# agenda", blok + "# agenda", 1)
    elif blok:
        tekst = tekst.rstrip("\n") + "\n" + blok
    redirects.write_text(tekst, encoding="utf-8")
    print("Vacatures %s: %d open, %d pagina's, %d doorverwijzingen" % (vandaag, len(open_), pagina_, len(weg)))


if __name__ == "__main__":
    datum = sys.argv[sys.argv.index("--datum") + 1] if "--datum" in sys.argv else None
    main(datetime.date.fromisoformat(datum) if datum else datetime.date.today())
