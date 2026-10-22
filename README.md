# nijmegenonline.nl (testomgeving)

Startpunt voor de nieuwe versie van [nijmegenonline.nl](https://www.nijmegenonline.nl), die nu nog op
WordPress draait. Deze repo is bedoeld om te testen; de live site verandert hierdoor niet.

## Structuur

```
index.html            homepage (testversie met voorbeeldblokken: agenda, nieuws, bedrijvengids)
404.html              pagina voor onbekende URL's
assets/css/site.css   kleuren, lettertypes en opmaak
kerstmarkten-in-nijmegen/  eerste echte pagina (zelfde URL als op WordPress)
partials/zijbalk.html zijbalk voor artikelen (alleen naast de tekst op desktop)
partners/             centrale partnerlijst + roterende slider, zie partners/README.md
<artikel>/            alle 214 artikelen, op dezelfde URL als op WordPress
category/<rubriek>/   overzicht per rubriek (8 rubrieken + partnerbijdragen)
blog/                 "Inspiratie opdoen": alle rubrieken op één pagina
data/indeling-artikelen.csv   welke rubriek elk artikel heeft
_redirects            301's van oude WordPress-categoriepagina's (voor Cloudflare Pages)
partials/             gedeelde header, footer en zijbalk
tools/import_wordpress.py     zet de WordPress-export om naar pagina's
tools/build.py        zet de onderdelen uit partials/ in alle pagina's
robots.txt            blokkeert zoekmachines zolang dit een test is
.nojekyll             zorgt dat GitHub Pages de bestanden ongewijzigd serveert
```

## Bekijken

- **Online:** via GitHub Pages op `https://itandleisure.github.io/website-nijmegenonline-nl/`
  (Settings → Pages → Deploy from a branch → `main` / root).
- **Lokaal:** `python -m http.server 8080` in deze map en ga naar http://localhost:8080.

## Artikelen opnieuw importeren

```bash
python tools/import_wordpress.py /pad/naar/wp-json   # REST-export van WordPress
python tools/build.py
```

Een artikel naar een andere rubriek verplaatsen: pas `data/indeling-artikelen.csv` aan en draai beide
scripts opnieuw. Afbeeldingen komen nog van wp-content/uploads op de live site; die moeten vóór de
livegang naar deze repo of een opslagdienst.

## Zijbalk aanpassen

Pas `partials/zijbalk.html` (of header/footer) aan en draai `python tools/build.py`. Dat zet de nieuwe zijbalk in elke
pagina die `<!-- zijbalk --><!-- /zijbalk -->` bevat. Op desktop staat de zijbalk naast de tekst en
blijven de partners onderaan in beeld tijdens het scrollen; op mobiel komt hij onder het artikel,
zonder partners (die staan daar al in de tekst).

Zie [LIVEGANG.md](LIVEGANG.md) voor de stappen naar www.nijmegenonline.nl.

## Belangrijk zolang dit een test is

- Geen `CNAME`-bestand toevoegen: dat koppelt het domein en zou de echte site vervangen.
- `robots.txt` en `noindex` laten staan, zodat Google geen dubbele content ziet.
- URL's van de echte site (artikelen, `/events/…`, `/bedrijvengids/…`, `/nieuwsoverzicht/…`) houden we
  straks precies gelijk vanwege de backlinks. Zie het bouwplan in het project.

## SEO per artikel

`data/seo-artikelen.csv` bevat per artikel het zoekwoord, de SEO-titel en de meta description.
`tools/import_wordpress.py` leest dit bestand en zet ze in de `<title>`, `meta description` en Open Graph.
Aanpassen: wijzig de rij en draai `python3 tools/import_wordpress.py && python3 tools/build.py`.
De versie om na te lopen staat als spreadsheet in `advies/seo/seo-artikelen.xlsx` in de projectbestanden.

## Gidsen

`data/gidsen.json` bevat de gidsen (themapagina's op de bestaande WordPress-URL's, zoals `/thema/trouwen-in-nijmegen/`):
naam, SEO-titel, beschrijving, intro, secties met de artikelen die erbij horen, veelgestelde vragen en de link naar de bedrijvengids.
`tools/import_wordpress.py` bouwt daaruit de gidspagina's en het overzicht op `/thema/`, en zet in elk artikel een link naar zijn gids
plus "Meer uit de gids". Een artikel toevoegen aan een gids: zet de slug in de juiste sectie en draai het importscript opnieuw.

## Samengevoegde artikelen

Artikelen die over hetzelfde gingen zijn samengevoegd tot één sterker artikel. `data/samenvoegen.csv`
zegt welk oud artikel in welk nieuw artikel is opgegaan. Het oude artikel krijgt een 301 in `_redirects`
en een doorverwijspagina op de oude URL. De samengevoegde tekst staat in `data/samengevoegd/<slug>.html`
en vervangt bij het importeren de tekst uit WordPress. Partnerbijdragen worden nooit samengevoegd.

## Afbeeldingen

De foto's van de WordPress-site staan als verkleinde webp in `assets/uploads/` (zelfde pad als in `wp-content/uploads/`).
Volgorde bij opnieuw bouwen: `python3 tools/import_wordpress.py && python3 tools/afbeeldingen.py && python3 tools/build.py`.

## Agenda

De agenda staat in `data/evenementen.json` en wordt gebouwd door `tools/agenda.py` (overzicht op
`/nijmegen-evenementen-overzicht/`, een pagina per evenement op `/events/<slug>/`, plus de agenda op de
homepage en in de zijbalk). `.github/workflows/agenda.yml` draait dit elke nacht. Afspraak:

- Een evenement verdwijnt de dag na afloop uit de agenda, de homepage en de zijbalk.
- De pagina blijft nog 3 maanden staan met "Dit evenement is afgelopen" en verwijst daarna met een 301 naar de agenda.
- Terugkerende evenementen (`"terugkerend": true`) houden hun pagina; zet daar elk jaar de nieuwe datum in.

Volgorde bij een volledige herbouw:
`python tools/import_wordpress.py && python tools/agenda.py && python tools/afbeeldingen.py && python tools/build.py`.
De eenmalige import uit WordPress staat in `tools/import_evenementen.py`.
