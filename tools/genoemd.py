"""Bedrijfspagina's linken terug naar de lijstartikelen waarin het bedrijf staat (vraag Frans, 21-11-2026).

Een lijstartikel (zoals /de-10-beste-ijssalons-in-nijmegen/) zet per bedrijf een kaartje met een link naar
/bedrijvengids/<sleutel>/ (class "over-bedrijf__kaart"). Dit script zoekt die kaartjes in alle artikelen en zet op de
bedrijfspagina een blokje "Aangeraden door NijmegenOnline" met een link naar elk artikel waarin het bedrijf staat.

- tools/bedrijvengids.py gebruikt blok() bij het bouwen van elke bedrijfspagina.
- Los draaien (na een nieuw lijstartikel): python tools/genoemd.py. Dat werkt het blok bij op de bestaande
  bedrijfspagina's, tussen <!-- genoemd --> en <!-- /genoemd -->, zonder de rest van de gids opnieuw te bouwen.
"""
import functools
import html
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
KAART = re.compile(r'class="over-bedrijf__kaart" href="\.\./bedrijvengids/([a-z0-9-]+)/"')
TITEL = re.compile(r"<h1>(.*?)</h1>", re.S)
# Mappen die geen artikel zijn
GEEN_ARTIKEL = {"bedrijvengids", "bedrijvengids-categorie", "assets", "partials", "tools", "data", "docs", "nieuwsberichten",
                "nieuwsoverzicht", "events", "event-location", "pagefind", "thema", "category", "partners", "vacatures"}
BEGIN, EIND = "<!-- genoemd -->", "<!-- /genoemd -->"


@functools.lru_cache(maxsize=1)
def vermeldingen():
    """{bedrijfssleutel: [(artikelslug, titel), ...]}, op titel gesorteerd."""
    uit = {}
    for pad in sorted(ROOT.glob("*/index.html")):
        slug = pad.parent.name
        if slug in GEEN_ARTIKEL or slug.startswith("."):
            continue
        tekst = pad.read_text(encoding="utf-8")
        if "over-bedrijf__kaart" not in tekst or 'http-equiv="refresh"' in tekst:
            continue
        titel = TITEL.search(tekst)
        if not titel:
            continue
        titel = html.unescape(re.sub(r"<[^>]+>", "", titel.group(1))).strip()
        for bedrijf in dict.fromkeys(KAART.findall(tekst)):
            uit.setdefault(bedrijf, []).append((slug, titel))
    for lijst in uit.values():
        lijst.sort(key=lambda x: x[1])
    return uit


def blok(slug, naam, root="../../"):
    """Het blokje voor de bedrijfspagina, met markeringen; leeg als het bedrijf in geen enkel lijstartikel staat."""
    artikelen = vermeldingen().get(slug)
    if not artikelen:
        return ""
    regels = "".join('\n            <li><a href="%s%s/">%s</a></li>' % (root, a, html.escape(t, quote=False)) for a, t in artikelen)
    return ('        %s<section class="gids-sectie" id="aangeraden">\n          <h2>Aangeraden door NijmegenOnline</h2>\n'
            '          <p>%s staat in %s:</p>\n          <ul>%s\n          </ul>\n        </section>%s'
            % (BEGIN, html.escape(naam, quote=False), "onze gids" if len(artikelen) == 1 else "deze gidsen van NijmegenOnline",
               regels, EIND))


def main():
    gewijzigd = 0
    ankers = '        <section class="gids-sectie">\n          <h2>Contact en openingstijden</h2>'
    for pad in sorted((ROOT / "bedrijvengids").glob("*/index.html")):
        tekst = pad.read_text(encoding="utf-8")
        m = re.search(r"<h1>(.*?)</h1>", tekst)
        if not m:
            continue
        nieuw_blok = blok(pad.parent.name, html.unescape(m.group(1)))
        if BEGIN in tekst:
            nieuw = re.sub(r"[ ]*%s.*?%s\n?" % (re.escape(BEGIN), re.escape(EIND)), lambda _: nieuw_blok + "\n" if nieuw_blok else "",
                           tekst, count=1, flags=re.S)
        elif nieuw_blok and ankers in tekst:
            nieuw = tekst.replace(ankers, nieuw_blok + "\n" + ankers, 1)
        else:
            continue
        if nieuw != tekst:
            pad.write_text(nieuw, encoding="utf-8")
            gewijzigd += 1
    print("genoemd: %d bedrijven in lijstartikelen, %d bedrijfspagina's bijgewerkt" % (len(vermeldingen()), gewijzigd))


if __name__ == "__main__":
    main()
