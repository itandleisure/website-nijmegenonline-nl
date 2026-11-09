"""Vindbaarheid voor Google en AI-zoekmachines (ChatGPT, Google AI-overzichten, Perplexity). Draait als stap van tools/build.py.

1. Gidsen (data/gidsen.json): onder de <h1> een regel "Bijgewerkt op ..." en een blok "In het kort" met de samenvatting
   uit gidsen.json (veld "samenvatting"). Tussen <!-- gidskort --> en <!-- /gidskort -->, dus elke keer opnieuw te
   schrijven. De datum verandert alleen als de inhoud van de gids zelf verandert (de agenda in de zijbalk en de carrousel
   met bedrijven tellen niet mee); de vingerafdruk en datum per gids staan in data/gidsen-bijgewerkt.json. De datum gaat
   ook als dateModified in de CollectionPage-gegevens, zodat sitemap.xml hem als lastmod meeneemt.
2. Homepage: gegevens over NijmegenOnline zelf (schema.org Organization en WebSite met zoekfunctie) tussen
   <!-- organisatie --> en <!-- /organisatie --> in de <head>.
3. llms.txt in de hoofdmap: een korte beschrijving van de site met de belangrijkste pagina's en alle gidsen, voor
   AI-zoekmachines (zie llmstxt.org).

Gebruik: via tools/build.py, of los: python tools/vindbaar.py
"""
import datetime
import hashlib
import html
import json
import pathlib
import re
import subprocess

ROOT = pathlib.Path(__file__).resolve().parent.parent
SITE = "https://www.nijmegenonline.nl"
GIDSEN = ROOT / "data" / "gidsen.json"
STAAT = ROOT / "data" / "gidsen-bijgewerkt.json"
MAANDEN = ["januari", "februari", "maart", "april", "mei", "juni", "juli", "augustus", "september", "oktober",
           "november", "december"]
# Commits van de nachtelijke scripts: die veranderen de gids zelf niet (alleen zijbalk en carrousel)
AUTOMATISCH = ("Agenda bijgewerkt", "Aanmeldingen gepubliceerd", "Social media", "Clarity bijgewerkt", "Nieuws bijgewerkt",
               "Vacatures bijgewerkt", "Bedrijvengids bijgewerkt", "Merge ")

ORGANISATIE = {
    "@context": "https://schema.org",
    "@type": "Organization",
    "@id": SITE + "/#organisatie",
    "name": "NijmegenOnline",
    "url": SITE + "/",
    "logo": SITE + "/assets/img/logo-nijmegenonline.svg",
    "description": "Stadsgids en uitgaanssite van Nijmegen en omgeving: agenda, nieuws, gidsen en een bedrijvengids.",
    "email": "redactie@nijmegenonline.nl",
    "telephone": "+31850047701",
    "areaServed": {"@type": "City", "name": "Nijmegen"},
    "knowsAbout": ["Nijmegen", "uitgaan in Nijmegen", "evenementen in Nijmegen", "restaurants in Nijmegen",
                   "bedrijven in Nijmegen", "Nijmeegse Vierdaagse"],
    "sameAs": ["https://www.facebook.com/nijmegenonline.nl", "https://www.instagram.com/nijmegenonline.nl"],
    "identifier": {"@type": "PropertyValue", "propertyID": "KvK", "value": "82473897"},
}
WEBSITE = {
    "@context": "https://schema.org",
    "@type": "WebSite",
    "@id": SITE + "/#website",
    "name": "NijmegenOnline",
    "url": SITE + "/",
    "inLanguage": "nl-NL",
    "publisher": {"@id": SITE + "/#organisatie"},
    "potentialAction": {"@type": "SearchAction", "target": SITE + "/zoeken/?q={search_term_string}",
                        "query-input": "required name=search_term_string"},
}


def nl_datum(d):
    return "%d %s %d" % (d.day, MAANDEN[d.month - 1], d.year)


def pagina(url):
    return ROOT / url.strip("/") / "index.html"


def vingerafdruk(s):
    """Hash van de gids zelf: het <article class="artikel gids"> zonder ons blok en zonder de carrousel met bedrijven."""
    m = re.search(r'<article class="artikel gids">.*?\n      </article>', s, re.S)
    tekst = m.group(0) if m else s
    tekst = re.sub(r"<!-- gidskort -->.*?<!-- /gidskort -->", "", tekst, flags=re.S)
    tekst = re.sub(r"<!-- gidsbedrijven -->.*?<!-- /gidsbedrijven -->", "", tekst, flags=re.S)
    return hashlib.sha1(re.sub(r"\s+", " ", tekst).encode("utf-8")).hexdigest()[:16]


def eerste_datum(pad):
    """Startdatum voor een gids zonder vingerafdruk: de laatste commit op de pagina die niet van een nachtelijk script is."""
    try:
        uit = subprocess.run(["git", "log", "--format=%cs|%s", "--", str(pad.relative_to(ROOT))], cwd=ROOT,
                             capture_output=True, text=True, timeout=60).stdout
    except Exception:
        uit = ""
    for regel in uit.splitlines():
        datum, _, onderwerp = regel.partition("|")
        if not onderwerp.startswith(AUTOMATISCH):
            return datum
    return datetime.date.today().isoformat()


def gidsen():
    alle = json.loads(GIDSEN.read_text(encoding="utf-8"))
    staat = json.loads(STAAT.read_text(encoding="utf-8")) if STAAT.exists() else {}
    vandaag = datetime.date.today().isoformat()
    aantal = 0
    for g in alle:
        pad = pagina(g["url"])
        if not pad.is_file() or not g.get("samenvatting"):
            continue
        s = pad.read_text(encoding="utf-8")
        if 'http-equiv="refresh"' in s or "<h1>" not in s:
            continue
        vinger = vingerafdruk(s)
        oud = staat.get(g["url"])
        if not oud:
            staat[g["url"]] = {"vinger": vinger, "datum": eerste_datum(pad)}
        elif oud["vinger"] != vinger:
            staat[g["url"]] = {"vinger": vinger, "datum": vandaag}
        datum = datetime.date.fromisoformat(staat[g["url"]]["datum"])
        blok = ('        <!-- gidskort -->\n'
                '        <p class="gids-bijgewerkt">Bijgewerkt op <time datetime="%s">%s</time></p>\n'
                '        <div class="gids-kort"><p><strong>In het kort:</strong> %s</p></div>\n'
                '        <!-- /gidskort -->') % (datum.isoformat(), nl_datum(datum), html.escape(g["samenvatting"], quote=False))
        if "<!-- gidskort -->" in s:
            nieuw = re.sub(r"[ \t]*<!-- gidskort -->.*?<!-- /gidskort -->", lambda m: blok, s, count=1, flags=re.S)
        else:
            nieuw = re.sub(r"(\n[ \t]*<h1>.*?</h1>)", lambda m: m.group(1) + "\n" + blok, s, count=1)

        def ld(m):
            try:
                data = json.loads(m.group(2))
            except ValueError:
                return m.group(0)
            if data.get("@type") != "CollectionPage":
                return m.group(0)
            data["dateModified"] = datum.isoformat()
            data["abstract"] = g["samenvatting"]
            data["publisher"] = {"@id": SITE + "/#organisatie"}
            return m.group(1) + json.dumps(data, ensure_ascii=False) + m.group(3)

        nieuw = re.sub(r'(<script type="application/ld\+json">)(.*?)(</script>)', ld, nieuw)
        if nieuw != s:
            pad.write_text(nieuw, encoding="utf-8")
            aantal += 1
    STAAT.write_text(json.dumps(staat, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return alle, aantal


def organisatie():
    pad = ROOT / "index.html"
    s = pad.read_text(encoding="utf-8")
    blok = "<!-- organisatie -->\n%s\n  <!-- /organisatie -->" % "\n".join(
        '  <script type="application/ld+json">%s</script>' % json.dumps(x, ensure_ascii=False) for x in (ORGANISATIE, WEBSITE))
    if "<!-- organisatie -->" in s:
        nieuw = re.sub(r"<!-- organisatie -->.*?<!-- /organisatie -->", lambda m: blok, s, count=1, flags=re.S)
    else:
        nieuw = s.replace("\n</head>", "\n  %s\n</head>" % blok, 1)
    if nieuw != s:
        pad.write_text(nieuw, encoding="utf-8")


def llms_txt(alle):
    regels = [
        "# NijmegenOnline",
        "",
        "> Stadsgids en uitgaanssite van Nijmegen en omgeving, al ruim 22 jaar. Met een dagelijks bijgewerkte agenda, "
        "lokaal nieuws, gidsen per onderwerp en een bedrijvengids met adressen en openingstijden van duizenden bedrijven "
        "in Nijmegen.",
        "",
        "Alle teksten zijn in het Nederlands en gaan over Nijmegen en de regio (Wijchen, Groesbeek, Berg en Dal, Beuningen, "
        "Lent, Mook en net over de grens Kleef). De gidsen worden door de redactie geschreven en bijgehouden.",
        "",
        "## Belangrijkste pagina's",
        "",
        "- [Agenda Nijmegen](%s/nijmegen-evenementen-overzicht/): alle komende evenementen in Nijmegen en omgeving, elke nacht bijgewerkt" % SITE,
        "- [Bedrijvengids](%s/bedrijvengids/): bedrijven in Nijmegen per categorie, met adres, openingstijden en kaart" % SITE,
        "- [Nieuws](%s/nieuwsberichten/): lokaal nieuws uit Nijmegen" % SITE,
        "- [Alle gidsen](%s/thema/): overzicht van de gidsen per onderwerp" % SITE,
        "- [Zien en doen](%s/zien-en-doen/): bezienswaardigheden en activiteiten" % SITE,
        "- [Plan je bezoek](%s/plan-je-bezoek/): praktische info voor een bezoek aan Nijmegen" % SITE,
        "",
        "## Gidsen",
        "",
    ]
    for g in alle:
        if pagina(g["url"]).is_file():
            regels.append("- [%s](%s%s): %s" % (g["naam"], SITE, g["url"], g.get("samenvatting") or g.get("kort", "")))
    regels += [
        "",
        "## Over NijmegenOnline",
        "",
        "- [Over ons](%s/over-ons/): wie we zijn en hoe we werken" % SITE,
        "- [Kom in contact](%s/kom-in-contact/): redactie@nijmegenonline.nl, 085 0047 701" % SITE,
        "- [Adverteren](%s/adverteren-bij-nijmegenonline/): uitgelichte vermeldingen zijn als zodanig gemarkeerd" % SITE,
        "",
    ]
    (ROOT / "llms.txt").write_text("\n".join(regels), encoding="utf-8")


def main():
    alle, aantal = gidsen()
    organisatie()
    llms_txt(alle)
    print("Vindbaar: %d gidsen bijgewerkt, organisatiegegevens op de homepage, llms.txt" % aantal)


if __name__ == "__main__":
    main()
