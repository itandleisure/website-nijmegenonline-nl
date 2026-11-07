"""Webshop: /webshop/ met een pagina per categorie en per product, een winkelwagen en een bedankpagina.

Producten staan in data/webshop.json. Drie soorten:
  eigen    iets dat NijmegenOnline zelf verkoopt en verstuurt (poster, ansichtkaarten); gaat in de winkelwagen
  dienst   iets voor ondernemers (vacature of evenement uitgelicht); gaat ook in de winkelwagen, niets te versturen
  partner  een product bij een partner (bol.com e.d.) met een affiliatelink; knop naar de partner, rel="sponsored"

Beheer: in de Google Sheet, tabblad "Webshop" (zie tools/google-formulier/Code.gs, webshopProducten). Met --ophalen
haalt dit script dat tabblad op via ?actie=webshop, zet de producten in data/webshop.json en de foto's als webp in
assets/uploads/webshop/. De workflow Aanmeldingen publiceren doet dat elk uur. Staat er nog niets in het tabblad,
dan blijft data/webshop.json zoals het is.

Bestellen: de winkelwagen (assets/js/webshop.js, bewaard in de browser) stuurt de bestelling naar hetzelfde Apps
Script (form=bestelling). Dat rekent de prijzen opnieuw na met data/webshop.json op GitHub, zet de bestelling in het
tabblad "Bestellingen" en maakt een betaling bij Mollie (iDEAL, Bancontact, creditcard) als MOLLIE_API_KEY is
ingesteld. Zonder sleutel krijgt de klant een betaalverzoek van de redactie.

"open": false in de instellingen = de winkel staat wel online, maar met noindex, buiten de zoekfunctie en zonder
link in het menu. Zo kun je hem testen voordat bezoekers hem zien.

Gebruik: python tools/webshop.py [--ophalen]   (daarna tools/build.py)
"""
import base64
import html
import io
import json
import pathlib
import re
import shutil
import sys
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from import_wordpress import SITE, VOET, esc, kop  # noqa: E402
from paginas import GOOGLE_FORM_URL  # noqa: E402

DATA = ROOT / "data" / "webshop.json"
MAP = "webshop"
FOTOMAP = ROOT / "assets" / "uploads" / "webshop"
SOORTEN = ("eigen", "dienst", "partner")
CSS = "assets/css/webshop.css?v=1"
JS = "assets/js/webshop.js?v=1"


def laad():
    return json.loads(DATA.read_text(encoding="utf-8"))


def euro(bedrag):
    return "&euro;&nbsp;" + ("%.2f" % bedrag).replace(".", ",")


def excl(p):
    return round(p["prijs"] / (1 + p.get("btw", 21) / 100), 2)


def prijsregel(p):
    if p.get("zakelijk"):
        return '%s <small>excl. btw (%s incl.)</small>' % (euro(excl(p)), euro(p["prijs"]))
    if p["soort"] == "partner":
        return 'ongeveer %s <small>bij %s</small>' % (euro(p["prijs"]), esc(p.get("partner", "de partner")))
    return euro(p["prijs"])


def foto(p, root):
    if p.get("fotos"):
        return '<img src="%s%s" alt="%s" loading="lazy">' % (root, esc(p["fotos"][0]), esc(p["naam"]))
    # Geen foto (diensten): een vlak met het eerste woord, in de huisstijl
    return '<div class="webshop-geenfoto" aria-hidden="true">%s</div>' % esc(p["naam"].split()[0])


def zichtbaar(producten):
    return sorted((p for p in producten if p.get("actief", True)), key=lambda p: (p.get("volgorde", 999), p["naam"]))


def uitverkocht(p):
    return p["soort"] == "eigen" and isinstance(p.get("voorraad"), int) and p["voorraad"] <= 0


def kaart(p, root):
    label = {"partner": "Tip &middot; partnerlink", "dienst": "Voor ondernemers"}.get(p["soort"], "")
    if uitverkocht(p):
        label = "Uitverkocht"
    if p.get("voorbeeld"):
        label = "Voorbeeld" + (" &middot; " + label if label else "")
    return ('<article class="kaart webshop-kaart"><a href="%swebshop/%s/">%s<div class="kaart__tekst">%s<h3>%s</h3>'
            '<p>%s</p><p class="webshop-prijs">%s</p></div></a></article>'
            % (root, p["slug"], foto(p, root), '<div class="label">%s</div>' % label if label else "", esc(p["naam"]),
               esc(p.get("kort", "")), prijsregel(p)))


def schema(p):
    """Product-gegevens voor Google (alleen eigen producten en diensten; partnerproducten verkopen we niet zelf)."""
    if p["soort"] == "partner" or p.get("voorbeeld"):
        return ""
    data = {
        "@context": "https://schema.org", "@type": "Product", "name": p["naam"], "description": p.get("kort", ""),
        "url": "%s/webshop/%s/" % (SITE, p["slug"]),
        "offers": {"@type": "Offer", "price": "%.2f" % p["prijs"], "priceCurrency": "EUR",
                   "availability": "https://schema.org/" + ("OutOfStock" if uitverkocht(p) else "InStock")},
    }
    if p.get("fotos"):
        data["image"] = ["%s/%s" % (SITE, f) for f in p["fotos"]]
    return '\n  <script type="application/ld+json">%s</script>' % json.dumps(data, ensure_ascii=False).replace("</", "<\\/")


def opties_html(p):
    uit = []
    for i, o in enumerate(p.get("opties") or []):
        veld = "optie%d" % i
        if o.get("tekst"):
            uit.append('<label>%s *<input type="text" name="%s" data-optie="%s" maxlength="200" required></label>'
                       % (esc(o["naam"]), veld, esc(o["naam"])))
        else:
            keuzes = "".join('<option>%s</option>' % esc(k) for k in o.get("keuzes", []))
            uit.append('<label>%s<select name="%s" data-optie="%s">%s</select></label>' % (esc(o["naam"]), veld, esc(o["naam"]), keuzes))
    return "\n".join(uit)


def koopblok(p, inst):
    if p["soort"] == "partner":
        return ('<p><a class="knop" href="%s" rel="sponsored nofollow noopener" target="_blank" data-partnerlink="%s">Bekijk bij %s</a></p>'
                '<p class="webshop-uitleg">Dit is een partnerlink: koop je via deze link, dan krijgt NijmegenOnline een kleine '
                'vergoeding van %s. Jij betaalt niets extra. De prijs kan bij de partner afwijken.</p>'
                % (esc(p["link"]), esc(p["slug"]), esc(p.get("partner", "de partner")), esc(p.get("partner", "de partner"))))
    if uitverkocht(p):
        return '<p class="webshop-uitverkocht">Dit product is op dit moment uitverkocht.</p>'
    levering = inst.get("levertijd", "") if p.get("verzenden") else "Niets te versturen: we gaan aan de slag zodra je betaling binnen is."
    return ('<form class="webshop-koop" data-webshop-koop data-slug="%s" data-naam="%s" data-prijs="%.2f" data-verzenden="%d">\n%s\n'
            '<label class="webshop-aantal">Aantal<input type="number" name="aantal" value="1" min="1" max="20"></label>\n'
            '<button class="knop" type="submit">In winkelwagen</button>\n'
            '<p class="webshop-melding" role="status"></p></form>\n<p class="webshop-uitleg">%s</p>'
            % (esc(p["slug"]), esc(p["naam"]), p["prijs"], 1 if p.get("verzenden") else 0, opties_html(p), esc(levering)))


def tekst_html(tekst):
    return "".join("<p>%s</p>" % esc(a.strip()).replace("\n", "<br>") for a in re.split(r"\n\s*\n", tekst or "") if a.strip())


def pagina(titel, beschrijving, pad, kruimel, inhoud, inst, indexeren=True, extra=""):
    root = "../" * (pad.count("/") + 1)
    canonical = "%s/%s/" % (SITE, pad)
    open_ = inst.get("open")
    extra = '\n  <link rel="stylesheet" href="%s%s">' % (root, CSS) + extra
    if not (open_ and indexeren):
        extra += '\n  <meta name="robots" content="noindex">'
    # Zolang de winkel dicht is ook buiten de zoekfunctie: geen <main>, dan zet tools/build.py er geen data-pagefind-body op
    tag = "main" if open_ and indexeren else 'div role="main"'
    out = [kop(titel, beschrijving, canonical, root, None, extra)]
    out.append('  <%s class="artikel-wrap webshop">\n    <div class="container">' % tag)
    if not open_:
        out.append('      <p class="webshop-dicht">De webshop is nog niet open. Je bekijkt een testversie; bestellingen worden niet verstuurd.</p>')
    out.append('      <div class="kruimelpad"><a href="%s">Home</a> › %s</div>' % (root, kruimel))
    out.append(inhoud)
    out.append("    </div>\n  </%s>" % tag.split()[0])
    out.append('  <script>window.WEBSHOP = %s;</script>' % json.dumps({
        "url": GOOGLE_FORM_URL, "root": root, "verzendkosten": inst.get("verzendkosten", 0),
        "gratisVanaf": inst.get("gratis_verzending_vanaf") or 0, "open": bool(open_)}))
    out.append('  <script src="%s%s" defer></script>' % (root, JS))
    out.append(VOET)
    return "\n".join(out)


def schrijf(pad, inhoud):
    doel = ROOT / pad / "index.html"
    doel.parent.mkdir(parents=True, exist_ok=True)
    doel.write_text(inhoud, encoding="utf-8")


def wagenknop(root):
    return '<a class="webshop-wagenknop" href="%swebshop/winkelwagen/">Winkelwagen <span data-webshop-teller>0</span></a>' % root


def bouw():
    d = laad()
    inst, cats = d["instellingen"], d["categorieen"]
    producten = zichtbaar(d["producten"])
    fouten = [p.get("slug", "?") for p in producten if p.get("soort") not in SOORTEN or not p.get("slug") or not p.get("naam")
              or not isinstance(p.get("prijs"), (int, float)) or (p["soort"] == "partner" and not p.get("link"))]
    if fouten:
        print("Webshop: producten overgeslagen (soort, naam, prijs of link ontbreekt): " + ", ".join(fouten))
        producten = [p for p in producten if p.get("slug", "?") not in fouten]
    cat_naam = {c["slug"]: c["naam"] for c in cats}

    # Oude pagina's weg (producten die niet meer actief zijn), de map zelf opnieuw opbouwen
    if (ROOT / MAP).exists():
        shutil.rmtree(ROOT / MAP)

    # Overzicht
    root = "../"
    blokken = []
    for c in cats:
        lijst = [p for p in producten if p.get("categorie") == c["slug"]]
        if not lijst:
            continue
        blokken.append('<section class="webshop-categorie" id="%s"><h2><a href="%swebshop/%s/">%s</a></h2><p>%s</p>'
                       '<div class="raster">%s</div></section>'
                       % (c["slug"], root, c["slug"], esc(c["naam"]), esc(c.get("intro", "")), "".join(kaart(p, root) for p in lijst)))
    zonder = [p for p in producten if p.get("categorie") not in cat_naam]
    if zonder:
        blokken.append('<section class="webshop-categorie"><h2>Overig</h2><div class="raster">%s</div></section>'
                       % "".join(kaart(p, root) for p in zonder))
    knoppen = "".join('<a href="#%s">%s</a>' % (c["slug"], esc(c["naam"])) for c in cats
                      if any(p.get("categorie") == c["slug"] for p in producten))
    inhoud = ('<div class="webshop-kop"><h1>Webshop NijmegenOnline</h1>%s</div>\n'
              '<p class="webshop-intro">Nijmegen in huis halen, een cadeau voor iemand die de stad mist, of meer bezoekers voor je '
              'eigen bedrijf. Betalen gaat met iDEAL.</p>\n<nav class="webshop-filter">%s</nav>\n%s'
              % (wagenknop(root), knoppen, "\n".join(blokken) or "<p>Er staan nog geen producten in de webshop.</p>"))
    schrijf(MAP, pagina("Webshop", "Posters, ansichtkaarten en cadeaus uit Nijmegen, en zichtbaarheid voor ondernemers. "
                        "Bestel bij NijmegenOnline en betaal met iDEAL.", MAP, "Webshop", inhoud, inst))

    # Per categorie
    for c in cats:
        lijst = [p for p in producten if p.get("categorie") == c["slug"]]
        if not lijst:
            continue
        pad = "%s/%s" % (MAP, c["slug"])
        root = "../../"
        inhoud = ('<div class="webshop-kop"><h1>%s</h1>%s</div><p class="webshop-intro">%s</p><div class="raster">%s</div>'
                  % (esc(c["naam"]), wagenknop(root), esc(c.get("intro", "")), "".join(kaart(p, root) for p in lijst)))
        schrijf(pad, pagina(c["naam"], c.get("intro") or c["naam"], pad,
                            '<a href="%swebshop/">Webshop</a> › %s' % (root, esc(c["naam"])), inhoud, inst))

    # Per product
    for p in producten:
        pad = "%s/%s" % (MAP, p["slug"])
        root = "../../"
        fotos = "".join('<img src="%s%s" alt="%s"%s>' % (root, esc(f), esc(p["naam"]), "" if i == 0 else ' loading="lazy"')
                        for i, f in enumerate(p.get("fotos") or []))
        kruimel = '<a href="%swebshop/">Webshop</a>' % root
        if p.get("categorie") in cat_naam:
            kruimel += ' › <a href="%swebshop/%s/">%s</a>' % (root, p["categorie"], esc(cat_naam[p["categorie"]]))
        inhoud = ('<div class="webshop-kop"><span></span>%s</div><div class="webshop-product">'
                  '<div class="webshop-fotos">%s</div><div class="webshop-info">%s<h1>%s</h1><p class="webshop-prijs">%s</p>'
                  '<div class="webshop-tekst">%s</div>%s</div></div>'
                  % (wagenknop(root), fotos or foto(p, root),
                     '<div class="label">Voorbeeldproduct</div>' if p.get("voorbeeld") else "",
                     esc(p["naam"]), prijsregel(p), tekst_html(p.get("tekst") or p.get("kort")), koopblok(p, inst)))
        afbeelding = "%s/%s" % (SITE, p["fotos"][0]) if p.get("fotos") else None
        doel = pagina(p["naam"], p.get("kort") or p["naam"], pad, kruimel + " › " + esc(p["naam"]), inhoud, inst,
                      indexeren=not p.get("voorbeeld"), extra=schema(p))
        if afbeelding:
            doel = re.sub(r'(<meta property="og:image" content=")[^"]*', r"\g<1>" + esc(afbeelding), doel, count=1)
        schrijf(pad, doel)

    # Winkelwagen en afrekenen
    root = "../../"
    voorwaarden = '<a href="%swebshop/voorwaarden/" target="_blank">voorwaarden van de webshop</a>' % root
    inhoud = """<h1>Winkelwagen</h1>
<div data-webshop-wagen><p>Je winkelwagen is leeg.</p></div>
<form class="formulier webshop-afrekenen" data-webshop-afrekenen hidden>
  <h2>Je gegevens</h2>
  <label>Naam *<input name="naam" autocomplete="name" required maxlength="100"></label>
  <label>E-mail *<input type="email" name="email" autocomplete="email" required maxlength="150"></label>
  <label>Telefoon<input type="tel" name="telefoon" autocomplete="tel" maxlength="30"></label>
  <label>Bedrijfsnaam (voor de factuur)<input name="bedrijf" autocomplete="organization" maxlength="150"></label>
  <fieldset data-webshop-adres>
    <legend>Bezorgadres</legend>
    <label>Straat en huisnummer *<input name="adres" autocomplete="street-address" maxlength="150"></label>
    <label>Postcode *<input name="postcode" autocomplete="postal-code" maxlength="10"></label>
    <label>Plaats *<input name="plaats" autocomplete="address-level2" maxlength="80"></label>
  </fieldset>
  <label>Opmerking<textarea name="opmerking" rows="3" maxlength="1000"></textarea></label>
  <label class="webshop-akkoord"><input type="checkbox" name="voorwaarden" value="akkoord" required> Ik ga akkoord met de %s. *</label>
  <div class="formulier__val" aria-hidden="true"><label>Laat dit veld leeg <input type="text" name="website" tabindex="-1" autocomplete="off"></label></div>
  <button class="knop" type="submit">Bestellen en betalen</button>
  <p class="webshop-melding" role="status"></p>
</form>""" % voorwaarden
    schrijf(MAP + "/winkelwagen", pagina("Winkelwagen", "Je winkelwagen in de webshop van NijmegenOnline.", MAP + "/winkelwagen",
                                         '<a href="%swebshop/">Webshop</a> › Winkelwagen' % root, inhoud, inst, indexeren=False))

    inhoud = """<h1>Bedankt voor je bestelling</h1>
<div data-webshop-bedankt><p>We kijken of je betaling binnen is...</p></div>
<p><a href="%swebshop/">Terug naar de webshop</a></p>""" % root
    schrijf(MAP + "/bedankt", pagina("Bedankt voor je bestelling", "Je bestelling bij NijmegenOnline.", MAP + "/bedankt",
                                     '<a href="%swebshop/">Webshop</a> › Bedankt' % root, inhoud, inst, indexeren=False))

    schrijf(MAP + "/voorwaarden", pagina("Voorwaarden webshop", "Bestellen, betalen, verzenden, retourneren en klachten in de "
                                         "webshop van NijmegenOnline.", MAP + "/voorwaarden",
                                         '<a href="%swebshop/">Webshop</a> › Voorwaarden' % root, voorwaarden_html(inst), inst))
    print("Webshop: %d producten, %d categorieën%s" % (len(producten), len({p.get("categorie") for p in producten}),
                                                       "" if inst.get("open") else " (nog dicht: noindex)"))


def voorwaarden_html(inst):
    """Concept: laten nalopen voordat de winkel open gaat (zie het voorstel). Volgt de wettelijke regels voor kopen op afstand."""
    v = {k: esc(str(inst.get(k) or "")) for k in ("bedrijfsnaam", "kvk", "btw_nummer", "adres", "email", "levertijd")}
    v["verzend"] = euro(inst.get("verzendkosten", 0))
    v["gratis"] = euro(inst.get("gratis_verzending_vanaf", 0))
    return """<h1>Voorwaarden webshop</h1>
<p>Deze voorwaarden gelden voor bestellingen in de webshop van NijmegenOnline. Voor adverteren en de bedrijvengids gelden
daarnaast de <a href="../../algemene-voorwaarden/">algemene voorwaarden</a>.</p>
<h2>Wie zijn wij</h2>
<p>{bedrijfsnaam}<br>{adres}<br>KvK {kvk}{btw}<br>E-mail: <a href="mailto:{email}">{email}</a></p>
<h2>Prijzen en betalen</h2>
<p>Alle prijzen zijn in euro en inclusief btw. Bij producten voor ondernemers staat de prijs ook exclusief btw. Je betaalt
vooraf met iDEAL of een andere betaalmethode die we aanbieden. Je bestelling is definitief zodra de betaling binnen is.
Je krijgt een bevestiging per e-mail; ondernemers krijgen een factuur.</p>
<h2>Verzenden</h2>
<p>We versturen binnen Nederland. Verzendkosten: {verzend}, gratis vanaf {gratis}. {levertijd} Lukt het niet binnen 30 dagen,
dan mag je de bestelling kosteloos annuleren en krijg je je geld binnen 14 dagen terug.</p>
<h2>Bedenktijd en retourneren</h2>
<p>Je mag een product tot 14 dagen na ontvangst zonder opgave van reden terugsturen. Meld dat eerst per e-mail; we sturen je
het retouradres. De kosten van het terugsturen zijn voor jou. We betalen het aankoopbedrag en de oorspronkelijke verzendkosten
binnen 14 dagen na je melding terug, zodra we het product terug hebben. Producten die speciaal voor jou zijn gemaakt (zoals
een print op maat) kun je niet retourneren.</p>
<p>Voor diensten voor ondernemers (zoals een uitgelichte vacature of een uitgelicht evenement) geldt geen bedenktijd: dit zijn
zakelijke afnemers en we beginnen direct na de betaling.</p>
<h2>Partnerlinks</h2>
<p>Bij producten met de knop "Bekijk bij ..." koop je niet bij ons, maar bij die partner. Daar gelden de voorwaarden van de
partner. Wij krijgen een kleine vergoeding als je via onze link koopt; jij betaalt niets extra.</p>
<h2>Klachten</h2>
<p>Is er iets niet goed, mail ons dan binnen een redelijke termijn. We reageren binnen 14 dagen. Komen we er samen niet uit,
dan kun je je klacht ook voorleggen via het Europese ODR-platform: <a href="https://ec.europa.eu/odr" rel="nofollow">ec.europa.eu/odr</a>.</p>
<h2>Privacy</h2>
<p>We gebruiken je gegevens alleen om je bestelling af te handelen en te versturen. Zie de
<a href="../../privacy-policy/">privacyverklaring</a>. Bestellingen bewaren we 7 jaar, omdat dat wettelijk verplicht is
voor de administratie.</p>""".format(btw="<br>Btw-nummer " + v["btw_nummer"] if v["btw_nummer"] else "", **v)


# ---------- Producten ophalen uit de Google Sheet ----------

def ophalen_json(url):
    with urllib.request.urlopen(url, timeout=120) as r:
        return json.loads(r.read().decode("utf-8"))


def slug(tekst):
    t = re.sub(r"[^a-z0-9]+", "-", tekst.lower().translate(str.maketrans("áàäâéèëêíìïîóòöôúùüûç", "aaaaeeeeiiiioooouuuuc")))
    return t.strip("-")[:80]


def getal(waarde, standaard=None):
    t = str(waarde if waarde is not None else "").strip().replace("€", "").replace(" ", "")
    if not t:
        return standaard
    if "," in t:
        t = t.replace(".", "").replace(",", ".")
    try:
        return float(t)
    except ValueError:
        return standaard


def ja(waarde, standaard=True):
    t = str(waarde if waarde is not None else "").strip().lower()
    return standaard if not t else t in ("ja", "j", "yes", "true", "1", "x", "waar")


def opties(tekst):
    """'Papier: Mat, Glans' (keuzelijst) of 'Naam van je bedrijf?' (tekstveld); meer opties op aparte regels."""
    uit = []
    for regel in str(tekst or "").splitlines():
        regel = regel.strip()
        if not regel:
            continue
        if ":" in regel and regel.split(":", 1)[1].strip():
            naam, keuzes = regel.split(":", 1)
            uit.append({"naam": naam.strip(), "keuzes": [k.strip() for k in keuzes.split(",") if k.strip()]})
        else:
            uit.append({"naam": regel.rstrip(":?").strip(), "tekst": True})
    return uit


def bewaar_foto(bron, naam, url):
    """bron = Drive-ID of https-URL. Wordt een webp van max. 1200 px in assets/uploads/webshop/. Al gedaan = overslaan."""
    from PIL import Image  # alleen nodig bij ophalen
    sleutel = re.sub(r"[^A-Za-z0-9_-]", "", bron if not bron.startswith("http") else base64.urlsafe_b64encode(bron.encode()).decode())[-12:]
    pad = FOTOMAP / ("%s-%s.webp" % (naam, sleutel))
    if pad.exists():
        return pad
    if bron.startswith("http"):
        req = urllib.request.Request(bron, headers={"User-Agent": "NijmegenOnline-webshop"})
        with urllib.request.urlopen(req, timeout=60) as r:
            data = r.read()
    else:
        antwoord = ophalen_json(url + "?actie=webshopfoto&id=" + urllib.parse.quote(bron))
        if not antwoord.get("ok"):
            raise ValueError("foto %s niet gevonden" % bron)
        data = base64.b64decode(antwoord["data"])
    img = Image.open(io.BytesIO(data))
    img = img.convert("RGB")
    img.thumbnail((1200, 1200))
    FOTOMAP.mkdir(parents=True, exist_ok=True)
    img.save(pad, "WEBP", quality=82)
    return pad


def drive_id(tekst):
    m = re.search(r"(?:/d/|id=)([A-Za-z0-9_-]{20,})", tekst)
    return m.group(1) if m else (tekst if re.fullmatch(r"[A-Za-z0-9_-]{20,}", tekst) else "")


def ophalen(url=GOOGLE_FORM_URL):
    """Tabblad Webshop -> data/webshop.json. Rijen zonder naam of prijs worden overgeslagen (met een melding)."""
    antwoord = ophalen_json(url + "?actie=webshop")
    rijen = antwoord.get("producten") or []
    if not rijen:
        print("Webshop: het tabblad Webshop is leeg, data/webshop.json blijft zoals het is")
        return False
    d = laad()
    oud = {p["slug"]: p for p in d["producten"]}
    nieuw, gezien = [], set()
    for r in rijen:
        naam = str(r.get("naam") or "").strip()
        prijs = getal(r.get("prijs"))
        soort = str(r.get("soort") or "eigen").strip().lower()
        if not naam or prijs is None or soort not in SOORTEN:
            print("Webshop: rij overgeslagen (naam, prijs of soort klopt niet): %s" % (naam or r))
            continue
        s = slug(str(r.get("slug") or "") or naam)
        if s in gezien:
            print("Webshop: dubbele slug %s overgeslagen" % s)
            continue
        gezien.add(s)
        p = {"slug": s, "naam": naam, "soort": soort, "categorie": slug(str(r.get("categorie") or "")), "prijs": round(prijs, 2),
             "kort": str(r.get("kort") or "").strip(), "tekst": str(r.get("tekst") or "").strip(),
             "volgorde": int(getal(r.get("volgorde"), 999)), "actief": ja(r.get("actief"))}
        if soort == "partner":
            p["partner"] = str(r.get("partner") or "").strip()
            p["link"] = str(r.get("link") or "").strip()
        else:
            p["btw"] = int(getal(r.get("btw"), 21))
            p["opties"] = opties(r.get("opties"))
            p["verzenden"] = soort == "eigen" and ja(r.get("verzenden"))
            p["zakelijk"] = soort == "dienst"
            voorraad = getal(r.get("voorraad"))
            p["voorraad"] = int(voorraad) if voorraad is not None else None
        fotos = []
        for i, bron in enumerate(re.split(r"[\s,]+", str(r.get("fotos") or "").strip())):
            if not bron:
                continue
            bron = bron if bron.startswith("http") and "drive.google" not in bron else (drive_id(bron) or bron)
            try:
                fotos.append(bewaar_foto(bron, s, url).relative_to(ROOT).as_posix())
            except Exception as fout:  # één kapotte foto mag de rest niet tegenhouden
                print("Webshop: foto %s bij %s overgeslagen: %s" % (bron, s, fout))
        # Geen (werkende) foto: de foto's van de vorige keer houden
        p["fotos"] = fotos or (oud.get(s, {}).get("fotos") or [])
        nieuw.append(p)
    d["producten"] = nieuw
    tekst = json.dumps(d, ensure_ascii=False, indent=1) + "\n"
    if tekst != DATA.read_text(encoding="utf-8"):
        DATA.write_text(tekst, encoding="utf-8")
        print("Webshop: %d producten uit de Sheet" % len(nieuw))
        return True
    return False


if __name__ == "__main__":
    if "--ophalen" in sys.argv:
        if GOOGLE_FORM_URL:
            try:
                ophalen()
            except Exception as fout:
                print("Webshop: ophalen uit de Sheet lukte niet (%s); data/webshop.json blijft zoals het is" % fout)
    bouw()
