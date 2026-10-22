"""Losse pagina's: Kom in contact, Adverteren, Wat kost adverteren bij anderen en de vacatures.

De teksten komen uit de WordPress-export (bron/wp-xml/paginas.xml); de Flatsome-opmaak is vervangen door de
eigen huisstijl. Formulieren gaan naar het Google Apps Script in tools/google-formulier/Code.gs (Google Sheet + mail
naar de redactie, zoals bij Badass Rentals) als GOOGLE_FORM_URL is ingevuld; anders openen ze het mailprogramma
van de bezoeker met het bericht al ingevuld (assets/js/formulier.js). Instellen: zie README, "Formulieren".

Gebruik: python tools/paginas.py [map met de bron]   (daarna tools/afbeeldingen.py en tools/build.py)
"""
import html
import json
import pathlib
import re
import shutil
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from import_wordpress import SITE, VOET, esc, kop, schoon  # noqa: E402

# /exec-URL van de Google Apps Script-web-app (tools/google-formulier/Code.gs); leeg = mailknop
GOOGLE_FORM_URL = "https://script.google.com/macros/s/AKfycbyELOZGBRvXanmgy7LSaQD4G5WnAZbACtAWVvcKoslJHT0-NxunjLngM7fJJOrxQyIM/exec"
EMAIL = "redactie@nijmegenonline.nl"
TELEFOON = "085 0047 701"
MEDIAKIT = "2025/05/NijmegenOnline-Advertentiegids-2025.pdf"
UPLOADS = SITE + "/wp-content/uploads/"

# Vacatures: slug, functie, open?, korte tekst voor het overzicht (uit de oude vacaturepagina)
VACATURES = [
    ("vacature-redacteur", "Redacteur (stage)", True,
     "Voor NijmegenOnline zoeken we toppers die hun schrijfervaring willen uitbreiden. Als redacteur ga je veel op pad in "
     "Nijmegen en ben je het visitekaartje van onze organisatie."),
    ("vacature-sales-tijger", "Account manager", True,
     "We zoeken iemand die niet bang is om de telefoon te pakken en bij klanten langs te gaan, en die samen met de "
     "collega's het aantal klanten laat groeien."),
    ("vacature-fotograaf", "Fotograaf", False,
     "Ben jij dag en nacht op pad met je camera en vind je het leuk om Nijmegen en omgeving vast te leggen?"),
    ("vacature-social-media-strateeg", "Social media strateeg", False,
     "We zochten iemand die alle ins en outs van social media kent en onze kanalen laat groeien."),
]

# Pakketten uit het advies Verdienmodel NijmegenOnline (okt 2026): naam, prijs per jaar excl. btw, toelichting
PAKKETTEN = [("Gratis", "0", "voor elk bedrijf"), ("Uitgelicht", "149", "eerste jaar &euro; 99*"),
             ("Partner", "449", ""), ("Hoofdpartner", "1.200", "maximaal 10")]
KENMERKEN = [
    ("Eigen pagina in de bedrijvengids met adres, kaart en openingstijden", ["ja", "ja", "ja", "ja"]),
    ("Tekst door onze redactie geschreven", ["kort", "uitgebreid, jaarlijks bijgewerkt", "uitgebreid", "uitgebreid"]),
    ("Logo en foto's", ["nee", "tot 10 foto's", "tot 10 foto's", "tot 10 foto's"]),
    ("Bovenaan je categorie met het label Uitgelicht (maximaal 3 per categorie)", ["nee", "ja", "ja", "ja"]),
    ("Actieknop (reserveren, offerte, bellen) en een aanbieding", ["nee", "ja", "ja", "ja"]),
    ("Je evenementen uitgelicht in de agenda", ["nee", "ja", "ja", "ja"]),
    ("Nieuwsbrief", ["nee", "1&times; per jaar in Nieuw in de gids", "2&times; een eigen tegel", "logo in elke editie"]),
    ("Banner", ["nee", "nee", "in je eigen branche", "op de hele site"]),
    ("Artikel over je bedrijf (gemarkeerd als partnerbijdrage)", ["nee", "nee", "1 per jaar", "3 per jaar"]),
    ("Sponsor van een categorie- of themapagina", ["nee", "nee", "nee", "ja"]),
    ("Overzicht van weergaven en kliks", ["jaarlijks", "jaarlijks", "elk kwartaal", "elk kwartaal"]),
]
# Losse mogelijkheden: wat, prijs excl. btw
LOSSE = [
    ("Evenement uitgelicht in de agenda en op de homepage, 2 weken voor de datum", "&euro; 39"),
    ("Artikel over je bedrijf of evenement, door ons geschreven", "&euro; 249"),
    ("Tegel in de nieuwsbrief, per editie", "&euro; 49"),
    ("Vacature uitgelicht, 30 dagen", "&euro; 49"),
    ("Sponsor van een seizoenspagina (Kerstmarkten, Vierdaagse, Koningsdag), per seizoen", "vanaf &euro; 250"),
    ("Fotoreportage", "op aanvraag"),
]


def paginas_xml(bron):
    """slug -> (titel, inhoud, meta) uit de WordPress-export."""
    uit = {}
    t = (bron / "wp-xml" / "paginas.xml").read_text(encoding="utf-8")
    for item in t.split("<item>")[1:]:
        if "<wp:status><![CDATA[publish]]>" not in item:
            continue
        slug = re.search(r"<wp:post_name><!\[CDATA\[([^\]]*)", item).group(1)
        titel = re.search(r"<title><!\[CDATA\[(.*?)\]\]></title>", item, re.S)
        inhoud = re.search(r"<content:encoded><!\[CDATA\[(.*?)\]\]></content:encoded>", item, re.S)
        meta = dict(re.findall(r"<wp:meta_key><!\[CDATA\[(rank_math_\w+)\]\]></wp:meta_key>\s*<wp:meta_value><!\[CDATA\[(.*?)\]\]>", item, re.S))
        uit[slug] = (html.unescape(titel.group(1)) if titel else slug, inhoud.group(1) if inhoud else "", meta)
    return uit


def bijlagen(bron):
    """Bijlage-id -> URL, voor [ux_image id=...]."""
    t = (bron / "wp-xml" / "paginas.xml").read_text(encoding="utf-8")
    uit = {}
    for item in t.split("<item>")[1:]:
        m = re.search(r"<wp:post_id>(\d+)</wp:post_id>", item)
        u = re.search(r"<wp:attachment_url><!\[CDATA\[([^\]]*)", item)
        if m and u:
            uit[m.group(1)] = u.group(1)
    return uit


def flatsome(tekst, fotos):
    """Flatsome-shortcodes naar gewone HTML: afbeeldingen en knoppen blijven, de rest (rijen, kolommen) gaat weg."""
    tekst = re.sub(r'\[ux_image id="(\d+)"[^\]]*\]',
                   lambda m: '<p><img src="%s" alt=""></p>' % fotos[m.group(1)].replace("http://", "https://") if m.group(1) in fotos else "", tekst)
    tekst = re.sub(r'\[button text="([^"]*)"[^\]]*?link="([^"]*)"[^\]]*\]',
                   lambda m: '<p><a href="%s">%s</a></p>' % (m.group(2), m.group(1)), tekst)
    return re.sub(r"\[/?[a-z_0-9]+[^\]]*\]", "", tekst)


def opgemaakt(tekst, fotos, root):
    return schoon(flatsome(tekst, fotos), set(), root, False)


def pagina(titel, beschrijving, pad, kruimel, inhoud, extra="", zijbalk=True, afbeelding=None):
    """Standaardpagina in de huisstijl. pad is bijvoorbeeld 'vacatures/vacature-redacteur'."""
    root = "../" * (pad.count("/") + 1)
    canonical = "%s/%s/" % (SITE, pad)
    out = [kop(titel, beschrijving, canonical, root, afbeelding, extra)]
    out.append('  <main class="artikel-wrap">\n    <div class="container">\n      <div class="artikel-layout%s">\n      <article class="artikel pagina">'
               % ("" if zijbalk else " artikel-layout--breed"))
    out.append('        <div class="kruimelpad"><a href="%s">Home</a> › %s</div>' % (root, kruimel))
    out.append(inhoud)
    out.append("      </article>")
    if zijbalk:
        out.append("\n      <!-- zijbalk --><!-- /zijbalk -->")
    out.append("      </div>\n    </div>\n  </main>")
    out.append('  <script src="%sassets/js/formulier.js?v=7" defer></script>' % root if "<form" in inhoud else "")
    out.append(VOET)
    return "\n".join(r for r in out if r)


KWARTIEREN = ["%02d:%02d" % (u, m) for u in range(24) for m in (0, 15, 30, 45)]


def formulier(naam, onderwerp, velden, knop="Verstuur", bedankt=""):
    """velden: (naam, label, type, verplicht, opties). naam is het formuliertype in Code.gs (contact, partner).
    Bijzondere types: "kop" (tussenkop, opties = toelichting) en "datumtijd" (datum en tijd per kwartier naast
    elkaar; naam = (datumveld, tijdveld), label = (datumlabel, tijdlabel)). bedankt: melding na het versturen."""
    regels = ['        <form class="formulier" id="formulier" data-email="%s" data-url="%s" data-onderwerp="%s"%s novalidate>'
              % (EMAIL, GOOGLE_FORM_URL, esc(onderwerp), ' data-bedankt="%s"' % esc(bedankt) if bedankt else ""),
              '          <input type="hidden" name="form" value="%s">' % esc(naam),
              '          <input type="hidden" name="pagina" value="">',
              '          <input type="hidden" name="duur" value="">',
              '          <div class="formulier__val" aria-hidden="true"><label>Laat dit veld leeg <input type="text" name="website" tabindex="-1" autocomplete="off"></label></div>']
    for veld, label, soort, verplicht, opties in velden:
        id_ = "%s-%s" % (naam, veld)
        ster = ' <span aria-hidden="true">*</span>' if verplicht else ""
        req = " required" if verplicht else ""
        if soort == "kop":
            regels.append('          <h3 class="formulier__kop">%s</h3>' % esc(label))
            if opties:
                regels.append('          <p class="formulier__hint">%s</p>' % esc(opties))
        elif soort == "datumtijd":
            (dveld, tveld), (dlabel, tlabel) = veld, label
            regels.append('          <div class="formulier__rij">'
                          '<div><label for="%s-%s">%s%s</label><input id="%s-%s" name="%s" type="date"%s></div>'
                          '<div><label for="%s-%s">%s%s</label><select id="%s-%s" name="%s"%s><option value="">Kies</option>%s</select></div></div>'
                          % (naam, dveld, esc(dlabel), ster, naam, dveld, dveld, req,
                             naam, tveld, esc(tlabel), ster, naam, tveld, tveld, req,
                             "".join('<option>%s</option>' % k for k in KWARTIEREN)))
        elif soort == "postcode":
            regels.append('          <label for="%s">%s%s</label>\n          <input id="%s" name="%s" type="text" autocomplete="postal-code" maxlength="8" data-postcode%s>'
                          % (id_, esc(label), ster, id_, veld, req))
            regels.append('          <p class="formulier__hint">Bijvoorbeeld 6511 AB. In Duitsland 5 cijfers, bijvoorbeeld 47533.</p>')
        elif soort == "keuzes":
            regels.append('          <fieldset class="formulier__keuzes"><legend>%s%s</legend>' % (esc(label), ster))
            regels += ['            <label><input type="checkbox" name="%s" value="%s"> %s</label>' % (veld, esc(o), esc(o)) for o in opties]
            regels.append("          </fieldset>")
        elif soort == "bestand":
            regels.append('          <label for="%s">%s%s</label>\n          <input id="%s" name="%s" type="file" accept="image/jpeg,image/png,image/webp"%s>'
                          % (id_, esc(label), ster, id_, veld, req))
            if opties:
                regels.append('          <p class="formulier__hint">%s</p>' % esc(opties))
        elif soort == "tekst":
            regels.append('          <label for="%s">%s%s</label>\n          <textarea id="%s" name="%s" rows="6"%s></textarea>'
                          % (id_, esc(label), ster, id_, veld, req))
        else:
            auto = {"email": "email", "tel": "tel", "url": "url"}.get(soort, "off" if opties else "on")
            lijst = ' list="%s-lijst"' % id_ if opties else ""
            regels.append('          <label for="%s">%s%s</label>\n          <input id="%s" name="%s" type="%s" autocomplete="%s"%s%s>'
                          % (id_, esc(label), ster, id_, veld, soort, auto, lijst, req))
            if opties:
                regels.append('          <datalist id="%s-lijst">%s</datalist>' % (id_, "".join('<option value="%s">' % esc(o) for o in opties)))
    regels.append('          <p class="formulier__melding" role="status" hidden></p>')
    regels.append('          <button class="knop" type="submit">%s</button>' % esc(knop))
    regels.append("        </form>")
    return "\n".join(regels)


# Toegevoegd aan artikel 11 (Privacy): wat er met formuliergegevens gebeurt (zie tools/google-formulier/Code.gs)
PRIVACY_FORMULIEREN = [
    "11.4 Gegevens die je via een formulier op deze website instuurt, zoals een contactbericht of de aanmelding van een "
    "evenement, bedrijf of partnerschap, bewaren we in een beveiligde omgeving bij Google. We gebruiken ze alleen om je "
    "bericht of aanmelding te behandelen en om contact met je op te nemen. Na drie maanden verwijderen we deze gegevens, "
    "inclusief meegestuurde foto's.",
    "11.5 Gegevens die je instuurt om te publiceren, zoals de naam, omschrijving, datum, locatie en foto van een evenement "
    "en het adres, de website, het e-mailadres en het telefoonnummer voor bezoekers, staan op de website zolang de "
    "vermelding online staat. Je eigen naam, e-mailadres en telefoonnummer als contactpersoon publiceren we niet. Bij het "
    "redigeren van teksten kan de redactie gebruikmaken van een AI-dienst; daarbij delen we alleen de gegevens die voor "
    "publicatie bedoeld zijn.",
    "11.6 Wil je dat we je gegevens eerder verwijderen, of dat we een vermelding offline halen? Mail dan naar %s." % EMAIL,
]


# Toegevoegd bij de nieuwe pakketten (okt 2026); de rest van de voorwaarden komt letterlijk uit WordPress
AV_PAKKETTEN = [
    "13.1 Dit artikel geldt voor vermeldingen, advertenties, artikelen en pakketten die bedrijven en organisaties "
    "bij Nijmegenonline.nl afnemen, zoals Uitgelicht, Partner en Hoofdpartner. Waar dit artikel afwijkt van de "
    "artikelen hiervoor, geldt dit artikel.",
    "13.2 Prijzen voor zakelijke klanten zijn exclusief btw. Een pakket wordt per jaar vooraf gefactureerd.",
    "13.3 Een pakket loopt twaalf maanden vanaf de dag waarop de vermelding online staat. Daarna wordt het "
    "steeds met twaalf maanden verlengd, tenzij de klant uiterlijk een maand voor de einddatum per e-mail "
    "opzegt. Nijmegenonline.nl stuurt uiterlijk dertig dagen voor de verlenging een herinnering.",
    "13.4 Een prijswijziging voor de volgende periode maakt Nijmegenonline.nl minstens twee maanden voor de "
    "einddatum bekend. Een introductieprijs geldt alleen zolang dat bij het aanbod is vermeld.",
    "13.5 Nijmegenonline.nl publiceert de vermelding binnen tien werkdagen nadat de gegevens en de betaling "
    "binnen zijn. Teksten worden door de redactie geschreven of geredigeerd; de klant ziet ze voor publicatie "
    "en kan correcties doorgeven.",
    "13.6 Betaalde artikelen, vermeldingen en banners krijgen een label waaraan lezers zien dat het om betaalde "
    "inhoud gaat. Links daarin zijn gemarkeerd als gesponsord (rel=\"sponsored\"). Nijmegenonline.nl verkoopt "
    "geen links voor zoekmachines.",
    "13.7 Per categorie in de bedrijvengids zijn er maximaal drie uitgelichte plekken, tenzij op de site anders is "
    "vermeld. De volgorde van uitgelichte bedrijven wisselt.",
    "13.8 Nijmegenonline.nl belooft geen aantal bezoekers, kliks, klanten of posities in zoekmachines. Overzichten "
    "van weergaven en kliks komen uit Google Analytics en zijn een indicatie.",
    "13.9 Nijmegenonline.nl mag inhoud weigeren of verwijderen die misleidend, onrechtmatig of in strijd met de "
    "goede smaak is, of die niet past bij een site over Nijmegen en omgeving.",
    "13.10 Na afloop of opzegging van een pakket blijft het bedrijf gratis in de bedrijvengids staan, zonder de "
    "extra's van het pakket. Wil de klant helemaal uit de gids, dan kan dat met een mail.",
    "13.11 Afspraken die voor de invoering van deze pakketten zijn gemaakt, blijven gelden tot hun einddatum.",
]


def algemene_voorwaarden(tekst, meta):
    """De voorwaarden letterlijk overgenomen; alleen de opmaak is anders (artikel = kop, lid = alinea)."""
    tekst = re.sub(r"\[/?[a-z_]+[^\]]*\]|<!--.*?-->", "", tekst, flags=re.S)
    voor, _, adres = tekst.partition("Adresgegevens")
    delen = []
    for blok in re.findall(r"<p>(.*?)</p>", voor, re.S):
        regels = [html.unescape(x).strip() for x in re.split(r"<br\s*/?>", blok) if x.strip()]
        for regel in regels:
            if re.match(r"Artikel \d+\.", regel):
                delen.append("        <h2>%s</h2>" % esc(regel))
            else:
                regel = re.sub(r"^(\d+\.\d+)(?=\S)", r"\1 ", regel)
                delen.append("        <p>%s</p>" % esc(regel))
                if regel.startswith("11.3 "):
                    delen += ["        <p>%s</p>" % esc(x) for x in PRIVACY_FORMULIEREN]
    delen.append("        <h2>Artikel 13. Vermeldingen en advertentiepakketten</h2>")
    delen += ["        <p>%s</p>" % esc(x) for x in AV_PAKKETTEN]
    adres = [html.unescape(x).strip() for x in re.split(r"<br\s*/?>|</?p>", adres) if x.strip()]
    delen.append("        <h2>Adresgegevens</h2>\n        <p>%s</p>" % "<br>".join(esc(x) for x in adres))
    inhoud = "        <h1>Algemene voorwaarden</h1>\n" + "\n".join(delen)
    return pagina("Algemene voorwaarden", meta.get("rank_math_description", ""), "algemene-voorwaarden", "Algemene voorwaarden", inhoud)


def bedrijf_aanmelden(categorieen):
    inhoud = """        <h1>Bedrijf aanmelden</h1>
        <p class="pagina__intro">Zet je bedrijf in de bedrijvengids van NijmegenOnline. Vul het formulier in, dan maken we je vermelding aan en nemen we contact met je op.</p>
        <p>Meer opvallen, bijvoorbeeld met een banner of artikelen over je bedrijf? Bekijk de mogelijkheden bij <a href="{site}/adverteren-bij-nijmegenonline/">adverteren</a>.</p>
{formulier}""".format(site=SITE, formulier=formulier("bedrijf", "Aanmelding bedrijvengids NijmegenOnline", [
        ("bedrijf", "Naam van het bedrijf", "text", True, None),
        ("categorie", "Soort bedrijf", "text", True, categorieen),
        ("adres", "Adres (straat, huisnummer, postcode en plaats)", "text", True, None),
        ("site", "Website", "url", False, None),
        ("telefoon", "Telefoonnummer", "tel", True, None),
        ("bedrijfsmail", "E-mailadres van het bedrijf", "email", False, None),
        ("openingstijden", "Openingstijden", "tekst", False, None),
        ("omschrijving", "Korte omschrijving van het bedrijf", "tekst", True, None),
        ("foto", "Logo of foto", "bestand", False, "JPG, PNG of WebP, maximaal 20 MB."),
        ("naam", "Je naam (contactpersoon)", "text", True, None),
        ("email", "Je e-mailadres", "email", True, None)], "Aanmelden",
        "Bedankt! De redactie heeft je aanmelding ontvangen en bekijkt die zo snel mogelijk. Soms passen we de tekst wat aan, "
        "zodat die goed op de website past. Je krijgt een e-mail zodra je bedrijf in de bedrijvengids staat, of als we het niet kunnen plaatsen."))
    return pagina("Bedrijf aanmelden", "Zet je bedrijf in de bedrijvengids van NijmegenOnline: vul het formulier in en wij maken je vermelding aan.",
                  "bedrijf-aanmelden", "Bedrijf aanmelden", inhoud)


def evenement_aanmelden():
    inhoud = """        <h1>Evenement aanmelden</h1>
        <p class="pagina__intro">Organiseer je een evenement in Nijmegen of de regio? Zet het gratis in de agenda van NijmegenOnline, zodat iedereen die op zoek is naar iets leuks te doen het kan vinden.</p>
        <h2>Zo werkt het</h2>
        <ul>
          <li>Vul het formulier zo volledig mogelijk in. Hoe meer we weten, hoe beter we je evenement kunnen laten zien.</li>
          <li>Voeg een rechtenvrije foto van het evenement toe. Zonder foto kunnen we het helaas niet plaatsen.</li>
          <li>Onze redactie bekijkt elke aanmelding. Soms schaven we de tekst wat bij, zodat die goed op de website past.</li>
          <li>Je krijgt een e-mail zodra je evenement online staat, of als we het niet kunnen plaatsen.</li>
        </ul>
        <h2>Meer aandacht voor je evenement?</h2>
        <p>Een gratis aanmelding komt in de agenda, met je website, e-mailadres en telefoonnummer als je die invult. Je evenement wordt dan niet uitgelicht in onze wekelijkse nieuwsbrief, op social media en op onze websites. Wil je die extra aandacht wel? Mail naar <a href="mailto:{email}">{email}</a> en vraag naar de mogelijkheden, of bekijk de <a href="{site}/adverteren-bij-nijmegenonline/">pakketten</a>.</p>
        <h2>Je evenement</h2>
{formulier}""".format(email=EMAIL, site=SITE, formulier=formulier("evenement", "Evenement aangemeld via NijmegenOnline", [
        ("kop", "Het evenement", "kop", False, None),
        ("titel", "Naam van het evenement", "text", True, None),
        (("datum", "starttijd"), ("Begindatum", "Begintijd"), "datumtijd", True, None),
        (("einddatum", "eindtijd"), ("Einddatum", "Eindtijd"), "datumtijd", True, None),
        ("omschrijving", "Omschrijving van het evenement", "tekst", True, None),
        ("kop", "Locatie", "kop", False, None),
        ("locatie", "Naam van de locatie", "text", True, None),
        ("adres", "Straat en huisnummer", "text", True, None),
        ("postcode", "Postcode", "postcode", True, None),
        ("plaats", "Plaats", "text", True, None),
        ("kop", "Contactgegevens voor bezoekers", "kop", False, "Deze gegevens komen bij het evenement op de website."),
        ("site", "Website", "url", False, None),
        ("evenementmail", "E-mailadres", "email", False, None),
        ("evenementtelefoon", "Telefoonnummer", "tel", False, None),
        ("kop", "Foto", "kop", False, None),
        ("foto", "Foto van het evenement", "bestand", True, "Een rechtenvrije foto, liefst liggend. JPG, PNG of WebP, maximaal 10 MB."),
        ("kop", "Jouw gegevens", "kop", False, "Deze gegevens komen niet op de website. We gebruiken ze alleen als we nog vragen hebben over je aanmelding."),
        ("naam", "Je naam", "text", True, None),
        ("email", "Je e-mailadres", "email", True, None),
        ("telefoon", "Je telefoonnummer", "tel", True, None),
        ("notitie", "Opmerking voor de redactie", "tekst", False, None)], "Evenement aanmelden",
        "Bedankt! De redactie heeft je evenement ontvangen en bekijkt het zo snel mogelijk. Soms passen we de tekst wat aan, "
        "zodat die goed op de website past. Je krijgt een e-mail zodra je evenement online staat, of als we het niet kunnen plaatsen."))
    return pagina("Evenement aanmelden", "Organiseer je een evenement in Nijmegen of omgeving? Meld het gratis aan voor de agenda van NijmegenOnline.",
                  "evenement-aanmelden", '<a href="../nijmegen-evenementen-overzicht/">Agenda</a> › Evenement aanmelden', inhoud)


def kom_in_contact(meta):
    inhoud = """        <h1>Kom in contact</h1>
        <p class="pagina__intro">Wil je adverteren, een persbericht sturen of je evenement aanmelden? Of heb je een vraag of tip voor de redactie? We horen graag van je.</p>
        <ul class="contactgegevens">
          <li><span>Telefoon</span><a href="tel:+31850047701">{tel}</a></li>
          <li><span>E-mail</span><a href="mailto:{email}">{email}</a></li>
          <li><span>KvK</span>82473897</li>
        </ul>
        <p class="pagina__let-op"><strong>Let op:</strong> wij zijn niet de <a href="https://www.nijmegen.nl/" target="_blank" rel="noopener">Gemeente Nijmegen</a> of de <a href="https://www.politie.nl/" target="_blank" rel="noopener">politie</a>.</p>
        <h2>Laat een bericht achter</h2>
{formulier}
        <h2>Agenda- en nieuwsberichten</h2>
        <ul>
          <li>Een evenement in de regio aankondigen? <a href="{site}/evenement-aanmelden/">Meld je evenement aan</a>.</li>
          <li>Cursussen, workshops en opleidingen kondig je gratis aan als je <a href="{site}/adverteren-bij-nijmegenonline/">klant</a> bent.</li>
          <li>Promotionele berichten van bedrijven plaatsen we kosteloos voor klanten. Neem contact op over de <a href="{site}/adverteren-bij-nijmegenonline/">mogelijkheden</a>.</li>
          <li>Stuur je tekst in de e-mail of als Word-bijlage, liever niet als pdf.</li>
          <li>Stuur foto's en flyers mee als .jpg of .gif, niet als pdf en niet in een Word-document.</li>
        </ul>
        <h2>E-mail</h2>
        <ul>
          <li>Zet in elk geval het onderwerp, je naam en je telefoonnummer in de e-mail, zodat we je bericht kunnen controleren.</li>
          <li>Anonieme berichten, zonder contactgegevens in de e-mail, behandelen we niet.</li>
        </ul>
        <h2>Adverteren: promoot je winkel, bedrijf, praktijk of stichting</h2>
        <p>NijmegenOnline is al ruim 22 jaar een van de meest bezochte informatie- en uitgaanssites in de regio. Met onze pakketten promoten we je bedrijf, zaak, winkel, stichting of club het hele jaar door. <a href="{site}/adverteren-bij-nijmegenonline/">Bekijk de mogelijkheden</a>.</p>
        <h2>Foto laten verwijderen</h2>
        <p>Sta je ergens op onze site op een foto en wil je dat niet? Mail dan naar <a href="mailto:{email}">{email}</a>, dan halen we de foto zo snel mogelijk weg. We houden ons aan de regels van de Autoriteit Persoonsgegevens.</p>
        <div class="partner-slider" data-plaatsing="blog"></div>""".format(
        tel=TELEFOON, email=EMAIL, site=SITE, formulier=formulier("contact", "Bericht via NijmegenOnline: kom in contact", [
            ("naam", "Je naam", "text", True, None),
            ("email", "Je e-mailadres", "email", True, None),
            ("telefoon", "Je telefoonnummer", "tel", False, None),
            ("onderwerp", "Onderwerp", "text", False, None),
            ("bericht", "Je bericht", "tekst", True, None)]))
    return pagina("Kom in contact", meta.get("rank_math_description", ""), "kom-in-contact", "Kom in contact", inhoud)


def adverteren(meta, root="../"):
    # De oude mediakit (2025) noemt de oude prijzen; die linken we pas weer als er een nieuwe is
    kop_ = "".join("<th scope=\"col\">%s<span>&euro; %s per jaar%s</span></th>"
                   % (n, p, "<br>%s" % t if t else "") for n, p, t in PAKKETTEN)
    rijen = []
    for naam, waarden in KENMERKEN:
        cellen = "".join('<td>%s</td>' % ({"ja": '<span class="pakket-ja" aria-label="ja">&#10003;</span>',
                                           "nee": '<span class="pakket-nee" aria-label="nee">&ndash;</span>'}.get(w, w)) for w in waarden)
        rijen.append("            <tr><th scope=\"row\">%s</th>%s</tr>" % (esc(naam), cellen))
    losse = "\n".join("            <tr><th scope=\"row\">%s</th><td>%s</td></tr>" % (esc(w), p) for w, p in LOSSE)
    inhoud = """        <header class="adverteren-hero">
          <p class="gidslabel">Adverteren</p>
          <h1>Gevonden worden in Nijmegen</h1>
          <p>Elk bedrijf in Nijmegen en omgeving staat gratis in onze bedrijvengids. Wil je meer opvallen? Dat kan al vanaf &euro; 149 per jaar.</p>
          <p><a class="knop" href="#partner-worden">Meld je aan</a></p>
        </header>
        <h2>Zo werkt het</h2>
        <ul>
          <li><strong>Gratis</strong>: je bedrijf staat in de bedrijvengids met adres, kaart, openingstijden en een korte tekst. Klopt er iets niet? Laat het ons weten, dan passen we het aan.</li>
          <li><strong>Uitgelicht</strong>: je staat bovenaan je categorie, met foto's, je logo, een actieknop en een uitgebreide tekst die wij voor je schrijven. Per categorie zijn er maximaal drie uitgelichte plekken.</li>
          <li><strong>Partner</strong>: alles van Uitgelicht, plus een banner in je eigen branche, een artikel over je bedrijf en twee keer een plek in de nieuwsbrief.</li>
          <li><strong>Hoofdpartner</strong>: je banner op de hele site, drie artikelen, je logo in elke nieuwsbrief en je naam bij een categorie- of themapagina.</li>
        </ul>
        <h2>Onze pakketten</h2>
        <div class="pakketten">
          <table>
            <thead><tr><td></td>{kop}</tr></thead>
            <tbody>
{rijen}
            </tbody>
          </table>
        </div>
        <p>Prijzen per jaar, exclusief btw. * Introductieprijs voor de eerste 50 klanten, en de prijs staat twee jaar vast. Een pakket loopt twaalf maanden en wordt daarna steeds met een jaar verlengd. Opzeggen kan tot een maand voor de einddatum, met een mail. Zie <a href="{site}/algemene-voorwaarden/">artikel 13 van de algemene voorwaarden</a>.</p>
        <h2>Losse mogelijkheden</h2>
        <div class="pakketten">
          <table>
            <thead><tr><td></td><th scope="col">Prijs<span>excl. btw</span></th></tr></thead>
            <tbody>
{losse}
            </tbody>
          </table>
        </div>
        <h2>Wat je van ons mag verwachten</h2>
        <ul>
          <li>Je pagina staat binnen tien werkdagen online nadat we je gegevens en betaling hebben.</li>
          <li>We schrijven je tekst en houden je pagina actueel. Je ziet alles voordat het online gaat.</li>
          <li>Je krijgt een overzicht van hoe vaak je pagina is bekeken en hoe vaak er is geklikt op je website, telefoonnummer en route.</li>
          <li>Betaalde artikelen en vermeldingen herken je aan een label, en links daarin zijn gemarkeerd als gesponsord. Zo blijft NijmegenOnline betrouwbaar voor lezers en voor Google, en daar heb jij ook wat aan.</li>
          <li>Een vast aantal bezoekers of klanten beloven we niet. Wat we beloven, is wat we zelf in de hand hebben: je plek, je pagina en de aandacht in onze kanalen.</li>
        </ul>
        <h2>Met deze partners werken we al samen</h2>
        <div class="partner-slider" data-plaatsing="blog"></div>
        <h2 id="partner-worden">Meld je aan</h2>
        <p>Laat je gegevens achter, dan nemen we contact met je op. Bellen mag ook: <a href="tel:+31850047701">{tel}</a>.</p>
{formulier}""".format(kop=kop_, rijen="\n".join(rijen), losse=losse, site=SITE, tel=TELEFOON,
                      formulier=formulier("partner", "Aanmelding partner NijmegenOnline", [
                          ("naam", "Je naam", "text", True, None),
                          ("bedrijf", "Bedrijfsnaam", "text", True, None),
                          ("email", "E-mailadres", "email", True, None),
                          ("telefoon", "Telefoonnummer", "tel", True, None),
                          ("pakket", "Waar heb je interesse in? (meerdere antwoorden mogelijk)", "keuzes", False,
                           [n for n, _, _ in PAKKETTEN[1:]] + ["Een losse mogelijkheid"]),
                          ("bericht", "Toelichting of vraag", "tekst", False, None)], "Verzenden"))
    return pagina("Adverteren bij NijmegenOnline", meta.get("rank_math_description", ""), "adverteren-bij-nijmegenonline",
                  "Adverteren", inhoud, zijbalk=False, afbeelding=UPLOADS + "2024/11/nijmegen-bereik-cijfers.png")


def wat_kost(titel, tekst, meta, fotos):
    # Alles vanaf de eerste kop; de herhaalde "bekijk de prijzen"-knoppen en de vaste voettekst gaan eruit
    tekst = re.sub(r'\[button text="BEKIJK HIER de prijzen van NijmegenOnline"[^\]]*\]', "", tekst)
    inhoud = opgemaakt(tekst, fotos, "../")
    inhoud = re.sub(r"<h2>(<strong>)?Vergelijking met andere adverteerders(</strong>)?</h2>", "", inhoud, count=1)
    inhoud = inhoud.replace("<h2>ADVERTEREN BIJ DE GELDERLANDER</h2>", "<h2>Adverteren bij de Gelderlander</h2>")
    inhoud = inhoud.replace("<h2>Adverteren bij IN DE BUURT NIJMEGEN</h2>", "<h2>Adverteren bij Indebuurt Nijmegen</h2>")
    # Links naar de prijslijsten van anderen: geen reclame voor hen
    inhoud = re.sub(r'(<a href="https://(?:www\.dpgmediagroup|go\.dpgmediagroup)[^"]*" target="_blank") rel="noopener"', r'\1 rel="nofollow noopener"', inhoud)
    inhoud = ("        <h1>%s</h1>\n%s\n        <p class=\"gids-cta\"><a class=\"knop\" href=\"%s/adverteren-bij-nijmegenonline/\">Bekijk de pakketten van NijmegenOnline</a></p>"
              % ("Vergelijking met andere adverteerders", inhoud, SITE))
    return pagina(titel.rstrip("?") + "?", meta.get("rank_math_description", ""), "wat-kost-adverteren-bij-anderen",
                  '<a href="../adverteren-bij-nijmegenonline/">Adverteren</a> › Vergelijking', inhoud)


def vacature(slug, functie, open_, tekst, meta, fotos):
    # De vacaturetekst staat tussen de scheidingslijn en de knop "Terug naar vacatures"
    deel = tekst.split("[divider", 1)[-1]
    deel = deel.split('[button text="Terug naar vacatures"')[0]
    inhoud = opgemaakt("[divider" + deel, fotos, "../../")
    inhoud = re.sub(r"^\s*<h2>.*?</h2>\n", "", inhoud, count=1, flags=re.S)  # oude titel met "(reeds ingevuld)"
    kopje = ['        <p class="gidslabel">Vacature</p>', "        <h1>Vacature %s</h1>" % esc(functie[0].lower() + functie[1:])]
    if not open_:
        kopje.append('        <p class="afgelopen">Deze vacature is ingevuld. <a href="../">Bekijk de andere vacatures</a>.</p>')
    else:
        kopje.append('        <p class="gids-cta"><a class="knop" href="mailto:%s?subject=%s">Solliciteer direct</a></p>'
                     % (EMAIL, esc("Sollicitatie " + functie).replace(" ", "%20")))
    inhoud = "\n".join(kopje) + "\n" + inhoud + '\n        <p class="gids-verder"><a href="../">Terug naar de vacatures</a></p>'
    return pagina("Vacature %s" % functie, meta.get("rank_math_description", ""), "vacatures/" + slug,
                  '<a href="../">Vacatures</a> › %s' % esc(functie), inhoud)


def vacatures(meta):
    kaarten = []
    for slug, functie, open_, kort in VACATURES:
        kaarten.append('          <a class="vacaturekaart%s" href="%s/"><span class="vacaturekaart__status">%s</span><strong>%s</strong><span>%s</span></a>'
                       % ("" if open_ else " vacaturekaart--dicht", slug, "Open" if open_ else "Ingevuld", esc(functie), esc(kort)))
    inhoud = """        <h1>Vacatures</h1>
        <p class="pagina__intro">Werken bij NijmegenOnline? Reageer op een van de vacatures hieronder en wie weet ben jij binnenkort onze nieuwe collega.</p>
        <div class="vacaturelijst">
{kaarten}
        </div>
        <p>Staat je functie er niet bij, maar wil je wel graag meewerken? Stuur een open sollicitatie naar <a href="mailto:{email}">{email}</a>.</p>""".format(
        kaarten="\n".join(kaarten), email=EMAIL)
    return pagina("Vacatures", meta.get("rank_math_description", ""), "vacatures", "Vacatures", inhoud)


def schrijf(pad, tekst):
    map_ = ROOT / pad
    map_.mkdir(parents=True, exist_ok=True)
    (map_ / "index.html").write_text(tekst, encoding="utf-8")


def main(bron):
    bron = pathlib.Path(bron)
    pag = paginas_xml(bron)
    fotos = bijlagen(bron)
    # Mediakit lokaal bewaren als die is opgehaald (de adverteerpagina linkt er nu niet naar)
    pdf = bron / "assets" / "uploads" / MEDIAKIT
    if pdf.is_file():
        doel = ROOT / "assets" / "uploads" / MEDIAKIT
        doel.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(pdf, doel)
    schrijf("kom-in-contact", kom_in_contact(pag["kom-in-contact"][2]))
    schrijf("adverteren-bij-nijmegenonline", adverteren(pag["adverteren-bij-nijmegenonline"][2]))
    titel, tekst, meta = pag["wat-kost-adverteren-bij-anderen"]
    schrijf("wat-kost-adverteren-bij-anderen", wat_kost(titel, tekst, meta, fotos))
    schrijf("vacatures", vacatures(pag["vacatures"][2]))
    for slug, functie, open_, _ in VACATURES:
        _, tekst, meta = pag[slug]
        schrijf("vacatures/" + slug, vacature(slug, functie, open_, tekst, meta, fotos))
    titel, tekst, meta = pag["algemene-voorwaarden"]
    schrijf("algemene-voorwaarden", algemene_voorwaarden(tekst, meta))
    lijst = (bron / "wp-xml" / "bedrijvengids-listdom.xml").read_text(encoding="utf-8")
    schrijf("bedrijf-aanmelden", bedrijf_aanmelden(sorted({html.unescape(c) for c in re.findall(
        r'<category domain="listdom-category" nicename="[^"]*"><!\[CDATA\[([^\]]*)', lijst)})))
    schrijf("evenement-aanmelden", evenement_aanmelden())
    print("Pagina's: kom-in-contact, adverteren, vergelijking, vacatures (%d)%s"
          % (len(VACATURES), "" if pdf.is_file() else "; mediakit nog niet lokaal"))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "/mnt/project-files/bron")
