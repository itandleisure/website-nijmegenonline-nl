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
- Elk evenement heeft een `"aanbieder"` (sleutel uit `data/aanbieders.json`). Per aanbieder komt er een
  overzicht op `/event-location/<aanbieder>/` (het oude EventOn-adres) en onder elk evenement "Meer evenementen
  bij …". Aanbieders zonder komende evenementen krijgen noindex; zonder evenementpagina's meer een 301 naar de agenda.

Volgorde bij een volledige herbouw:
`python tools/import_wordpress.py && python tools/agenda.py && python tools/afbeeldingen.py && python tools/build.py`.
De eenmalige import uit WordPress staat in `tools/import_evenementen.py`.

## Losse pagina's en formulieren

`tools/paginas.py` maakt Kom in contact, Adverteren (met de vergelijking), de vacatures, Algemene voorwaarden,
Bedrijf aanmelden en Evenement aanmelden, met de teksten uit de
WordPress-export. Een vacature open of dicht zetten: pas `VACATURES` bovenin dat script aan en draai
`python tools/paginas.py && python tools/build.py`.

De formulieren werken zoals bij Badass Rentals: ze gaan naar het Google Apps Script `tools/google-formulier/Code.gs`.
Dat zet elke inzending in een Google Sheet (tabbladen Contact, Partners, Bedrijven en Evenementen) en mailt
redactie@nijmegenonline.nl. Meegestuurde foto's komen in de Drive-map "NijmegenOnline formulierfoto's".
Zolang `GOOGLE_FORM_URL` leeg is, opent het formulier het mailprogramma van de bezoeker.

Eenmalig instellen:
1. Maak een Google Sheet, bijv. "NijmegenOnline formulieren". Extensies > Apps Script: plak `Code.gs`.
2. Kies de functie `installeer` en klik Uitvoeren (toestemming geven).
3. Implementeren > Nieuwe implementatie > Web-app, uitvoeren als: ik, toegang: iedereen.
4. Zet de /exec-URL in `GOOGLE_FORM_URL` in `tools/paginas.py`, draai `python tools/paginas.py && python tools/build.py`, commit en push.

### Aanmeldingen goedkeuren (evenementen en bedrijven)

Een aangemeld evenement of bedrijf komt niet meteen online. De redactie krijgt een mail met de knoppen
**Bekijken en beoordelen** (of zet zelf "Akkoord" in de kolom Status van de Sheet).
Afwijzen opent een pagina waarop je de reden aanvinkt; de inzender krijgt dan een mail met die reden. Bewerken opent een pagina waarop je titel, datum, tijden, locatie, adres, de tekst en de foto aanpast, en dan
publiceert. Met een Anthropic API-sleutel in de scripteigenschap `ANTHROPIC_API_KEY` staan op de bewerkpagina
ook de knoppen "Nieuwe tekst laten schrijven" (Claude schrijft een eigen, unieke tekst in de kolom "Tekst site",
die online gaat, met opmerkingen in de kolom "Controle") en "Staat het al ergens anders?" (zoekt op internet of
andere sites het al hebben). Claude doet alleen iets als je op zo'n knop drukt. Elk uur haalt
`.github/workflows/aanmeldingen.yml` met `tools/aanmeldingen.py` de goedgekeurde aanmeldingen op: evenementen
gaan in `data/evenementen.json` (foto in `assets/uploads/aangemeld/`), bedrijven in `data/bedrijven-aangemeld.json`
(voor de bedrijvengids). Een evenement komt bij een bestaande aanbieder als de naam overeenkomt (los van café/het/'t, leestekens en accenten) of als straat en huisnummer gelijk zijn aan die van een eerder evenement; op de beoordeelpagina kies je de aanbieder ook zelf in een keuzelijst. Heeft de gekozen aanbieder een bekend adres (`adres` in `data/aanbieders.json`, bijgewerkt bij elke publicatie), dan vult de beoordeelpagina dat in; het adres van de inzender kun je terugzetten. Postcodes: 1234 AB, of 5 cijfers voor Duitsland. Daarna wordt de site gebouwd en zet het script de status in de Sheet op "Gepubliceerd".
Meteen publiceren in plaats van op het hele uur: Actions > Aanmeldingen publiceren > Run workflow.

### Bedrijvengids (in opbouw)

`python tools/bedrijvengids.py` bouwt de startpagina `/bedrijvengids/` (kaart met alle bedrijven, Leaflet + OpenStreetMap),
de categoriepagina's en een pagina per bedrijf. Bronnen: de oude Listdom-gids (WordPress-export) en OpenStreetMap/Overture
(`/mnt/project-files/advies/osm-bedrijvengids/`). Bedrijven zonder eigen tekst krijgen een pagina met `noindex`, tot er een
eigen beschrijving is. Uitgelichte (betalende) bedrijven staan in `CATEGORIE["uitgelicht"]`. Voorstel voor de categorieën:
`/mnt/project-files/advies/bedrijvengids-categorieen.md`.
