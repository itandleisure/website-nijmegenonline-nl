"""Pagina /over-ons/: wie NijmegenOnline is en hoe de redactie werkt.

Belangrijk voor Google en AI-zoekmachines: die willen kunnen zien wie achter een site zit voordat ze hem als bron
gebruiken. De pagina krijgt schema.org AboutPage-gegevens die naar de organisatie op de homepage verwijzen
(tools/vindbaar.py). Het aantal bedrijven en evenementen wordt bij elke run opnieuw geteld.

Gebruik: python tools/over_ons.py && python tools/build.py
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from paginas import EMAIL, TELEFOON, pagina  # noqa: E402
from import_wordpress import SITE  # noqa: E402


def tel(map_, alleen_echt=True):
    n = 0
    for p in (ROOT / map_).glob("*/index.html"):
        if not alleen_echt or 'http-equiv="refresh"' not in p.read_text(encoding="utf-8")[:3000]:
            n += 1
    return n


def main():
    bedrijven = tel("bedrijvengids")
    categorieen = tel("bedrijvengids-categorie")
    gidsen = len([g for g in json.loads((ROOT / "data" / "gidsen.json").read_text(encoding="utf-8"))
                  if (ROOT / g["url"].strip("/") / "index.html").is_file()])
    rond = "%d.%03d" % divmod(bedrijven // 100 * 100, 1000) if bedrijven >= 1000 else str(bedrijven)
    ld = {"@context": "https://schema.org", "@type": "AboutPage", "name": "Over NijmegenOnline", "url": SITE + "/over-ons/",
          "inLanguage": "nl-NL", "about": {"@id": SITE + "/#organisatie"}, "publisher": {"@id": SITE + "/#organisatie"}}
    extra = '\n  <script type="application/ld+json">%s</script>' % json.dumps(ld, ensure_ascii=False)
    inhoud = """        <h1>Over NijmegenOnline</h1>
        <div class="inhoud-tekst">
          <p>NijmegenOnline is de stadsgids van Nijmegen en omgeving. Al ruim 22 jaar zetten we op één plek wat er in de stad te doen is: de agenda, lokaal nieuws, gidsen over uitgaan, eten, natuur en evenementen, en een bedrijvengids met de bedrijven uit de stad.</p>

          <h2>Wat je op de site vindt</h2>
          <ul>
            <li><strong><a href="../nijmegen-evenementen-overzicht/">De agenda</a></strong>: evenementen in Nijmegen en de regio, elke nacht bijgewerkt. Organisatoren melden hun evenement zelf aan via <a href="../evenement-aanmelden/">het aanmeldformulier</a>; de redactie controleert het voordat het online komt.</li>
            <li><strong><a href="../thema/">{gidsen} gidsen</a></strong> over één onderwerp, zoals het centrum, parkeren, natuur en wandelen, uitgaan, lunch en de Vierdaagse. Elke gids heeft bovenaan een korte samenvatting en de datum waarop hij voor het laatst is bijgewerkt.</li>
            <li><strong><a href="../bedrijvengids/">De bedrijvengids</a></strong>: ruim {rond} bedrijven in {categorieen} categorieën, met adres, openingstijden en kaart. Een vermelding is gratis voor elk bedrijf in Nijmegen.</li>
            <li><strong><a href="../nieuwsberichten/">Nieuws</a></strong> uit Nijmegen en omgeving.</li>
          </ul>

          <h2>Hoe we werken</h2>
          <ul>
            <li>De gidsen schrijft en onderhoudt onze redactie zelf.</li>
            <li>Betaalde inhoud is altijd herkenbaar: artikelen die een bedrijf laat plaatsen, staan als <em>Partnerbijdrage</em>, en betaalde vermeldingen in de bedrijvengids en de agenda hebben het label <em>Uitgelicht</em>. Wat de pakketten inhouden, staat op <a href="../adverteren-bij-nijmegenonline/">Adverteren</a>.</li>
            <li>Adressen, openingstijden en websites in de bedrijvengids komen van de bedrijven zelf en uit openbare bronnen. Websites controleren we automatisch; een link die niet meer werkt, halen we weg.</li>
            <li>Klopt er iets niet meer? <a href="../kom-in-contact/">Laat het ons weten</a>, dan passen we het aan.</li>
          </ul>

          <h2>Contact</h2>
          <p>E-mail: <a href="mailto:{email}">{email}</a><br>Telefoon: {telefoon}<br>KvK: 82473897</p>
          <p>Let op: wij zijn niet de Gemeente Nijmegen of de politie. Voor vragen aan de gemeente ga je naar <a href="https://www.nijmegen.nl/" rel="noopener">nijmegen.nl</a>.</p>
        </div>""".format(gidsen=gidsen, rond=rond, categorieen=categorieen, email=EMAIL, telefoon=TELEFOON)
    beschrijving = ("NijmegenOnline is al ruim 22 jaar de stadsgids van Nijmegen: agenda, nieuws, gidsen en een bedrijvengids. "
                    "Lees wie we zijn en hoe de redactie werkt.")
    html = pagina("Over NijmegenOnline", beschrijving, "over-ons", "Over ons", inhoud, extra=extra)
    d = ROOT / "over-ons"
    d.mkdir(exist_ok=True)
    (d / "index.html").write_text(html, encoding="utf-8")
    print("Over ons: %d bedrijven, %d categorieën, %d gidsen" % (bedrijven, categorieen, gidsen))


if __name__ == "__main__":
    main()
