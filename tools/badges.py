"""Badges voor bedrijven in de bedrijvengids, en welke bedrijven in een top-lijst staan.

Maakt:
- assets/img/badge/<soort>.svg en .png (600 px breed, op de site getoond op 200 px): "Te vinden op NijmegenOnline"
  (blauw en licht) en "Aanrader van NijmegenOnline" (groen, voor bedrijven die in een top-lijst staan).
- data/badge-aanraders.json: per bedrijf (slug) de top-lijsten waarin het genoemd wordt, zoals
  "De 10 beste kappers in Nijmegen". De pagina /link-naar-ons/ biedt die bedrijven de groene badge aan.

Een top-lijst is een artikel met "beste" of "top <getal>" in de titel met een genummerde lijst (ItemList) van minstens
drie bedrijven; de bedrijven onder "Ook goed" tellen niet mee.

Gebruik: python tools/badges.py   (de PNG's alleen als Playwright voor Python er is; de SVG's en de json altijd)
"""
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
UIT = ROOT / "assets" / "img" / "badge"
SITE = "https://www.nijmegenonline.nl"

# soort: (achtergrond, rand, kleur van het label, labeltekst, logo)
SOORTEN = {
    "te-vinden-op-nijmegenonline": ("#12497c", None, "#b9e58f", "TE VINDEN OP", "logo-nijmegenonline.svg"),
    "te-vinden-op-nijmegenonline-licht": ("#ffffff", "#d5dbe2", "#6b6b70", "TE VINDEN OP", "logo-nijmegenonline-kleur.svg"),
    "aanrader-van-nijmegenonline": ("#539c20", None, "#ffffff", "AANRADER VAN", "logo-nijmegenonline.svg"),
}


def logo_binnenkant(naam):
    tekst = (ROOT / "assets" / "img" / naam).read_text(encoding="utf-8")
    tekst = re.sub(r"^.*?<svg[^>]*>", "", tekst, flags=re.S)
    tekst = re.sub(r"</svg>\s*$", "", tekst)
    return re.sub(r"<title>.*?</title>", "", tekst).strip()


def badge_svg(soort):
    bg, rand, labelkleur, label, logo = SOORTEN[soort]
    lijn = ' stroke="%s" stroke-width="2"' % rand if rand else ""
    titel = "Te vinden op NijmegenOnline" if label.startswith("TE") else "Aanrader van NijmegenOnline"
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 110" width="300" height="110" role="img" '
            'aria-label="%s">\n  <title>%s</title>\n'
            '  <rect x="1" y="1" width="298" height="108" rx="14" fill="%s"%s/>\n'
            '  <text x="22" y="27" fill="%s" font-family="Raleway, Arial, Helvetica, sans-serif" font-size="13" '
            'font-weight="700" letter-spacing="1.6">%s</text>\n'
            '  <g transform="translate(14 30) scale(0.72)">\n%s\n  </g>\n</svg>\n'
            % (titel, titel, bg, lijn, labelkleur, label, logo_binnenkant(logo)))


def pngs_maken(svgs):
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Playwright ontbreekt: PNG's niet bijgewerkt")
        return
    with sync_playwright() as p:
        browser = p.chromium.launch()
        pagina = browser.new_page(viewport={"width": 300, "height": 110}, device_scale_factor=2)
        for soort, svg in svgs.items():
            pagina.set_content('<html><body style="margin:0;background:transparent">%s</body></html>' % svg)
            pagina.locator("svg").screenshot(path=str(UIT / ("%s.png" % soort)), omit_background=True)
        browser.close()


def aanraders():
    """slug -> [{titel, url}] voor bedrijven die in een top-lijst staan."""
    uit = {}
    for index in sorted(ROOT.glob("*/index.html")):
        html = index.read_text(encoding="utf-8")
        m = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.S)
        if not m:
            continue
        titel = re.sub(r"<[^>]+>", "", m.group(1)).strip()
        if not re.search(r"\bbeste\b|\btop[ -]?\d", titel, re.I):
            continue
        # alleen de genummerde lijst (ItemList in de JSON-LD), niet "ook goed", de zijbalk of "meer lezen"
        slugs = []
        for blok in re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S):
            if '"ItemList"' in blok:
                slugs += re.findall(r'"url": "https://www\.nijmegenonline\.nl/bedrijvengids/([a-z0-9-]+)/"', blok)
        slugs = sorted(set(slugs))
        if len(slugs) < 3:
            continue
        for s in slugs:
            uit.setdefault(s, []).append({"titel": titel, "url": "%s/%s/" % (SITE, index.parent.name)})
    return uit


def main():
    UIT.mkdir(parents=True, exist_ok=True)
    svgs = {soort: badge_svg(soort) for soort in SOORTEN}
    for soort, svg in svgs.items():
        (UIT / ("%s.svg" % soort)).write_text(svg, encoding="utf-8")
    pngs_maken(svgs)
    lijst = aanraders()
    (ROOT / "data" / "badge-aanraders.json").write_text(
        json.dumps(lijst, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print("%d badges, %d bedrijven in een top-lijst" % (len(svgs), len(lijst)))


if __name__ == "__main__":
    main()
