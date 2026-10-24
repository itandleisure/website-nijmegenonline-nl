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

## Nieuwsbrief (MailerLite)

`python tools/nieuwsbrief.py` maakt elke nacht drie RSS-feeds waar MailerLite met een RSS-campagne zelf de
wekelijkse nieuwsbrief van vult, in deze volgorde: `/nieuwsbrief/uitgelicht.xml` (uitgelichte evenementen van de
komende 30 dagen, met foto), `/nieuwsbrief/nieuws.xml` (nieuwste berichten) en `/nieuwsbrief/agenda.xml` (overige
evenementen van de komende 2 weken, met foto). De foto's staan als jpg in `assets/nieuwsbrief/`,
omdat Outlook geen webp toont. Tot de livegang wijzen de feeds naar de testsite.

Aanmelden: een knop in de zijbalk opent het pop-upformulier `qG49m3` van MailerLite (het MailerLite-script,
account 364874, staat in `partials/footer.html`). Tekst en kleuren van het formulier pas je aan in MailerLite zelf.

## Nieuws

De nieuwsberichten staan in `data/nieuws.json`; `python tools/nieuws.py` bouwt daaruit `/nieuwsoverzicht/<slug>/`,
het overzicht `/nieuwsberichten/` en het nieuwsblok op de homepage (daarna `tools/build.py`).
`tools/import_nieuws.py` maakt die lijst opnieuw uit de WordPress-export en overschrijft dan ook nieuwere berichten.

Nieuw nieuws komt per mail binnen:

1. De redactie stuurt een ingezonden mail door naar **nieuws@nijmegenonline.nl** (Vimexx).
2. Elke 15 minuten haalt GitHub die mails op (`.github/workflows/nieuws-ophalen.yml`, `tools/nieuws_ophalen.py`):
   tekst (ook uit pdf- en Word-bijlagen) en foto's gaan naar het Google Apps Script.
3. Het script zet het bericht in het tabblad Nieuws, laat Claude het in eigen woorden schrijven (titel, intro,
   samenvatting, fotobijschrift) en mailt de redactie de knop "Bekijken en beoordelen".
4. Na "Opslaan en publiceren" zet de uurlijkse taak (`tools/aanmeldingen.py`) het op de site en krijgt de inzender
   een mail met de link.

Is het eigenlijk een evenement, zet dan bij het doorsturen **Agenda** vooraan in het onderwerp ("Agenda: Fwd: …"). Claude
haalt dan datum, tijden, locatie en adres uit de mail en schrijft de agendatekst; het komt in het tabblad Evenementen
en gaat verder als een aangemeld evenement.

Instellen (eenmalig): secrets `NIEUWS_MAIL_SERVER`, `NIEUWS_MAIL_GEBRUIKER`, `NIEUWS_MAIL_WACHTWOORD` en
`NIEUWS_SLEUTEL` in GitHub. De sleutel maakt de functie `maakNieuwsSleutel` in het Apps Script. Alleen mails van
`nijmegenonline.nl`-adressen worden verwerkt; andere gaan naar de map Genegeerd. Een extra afzender kan erbij via de
variabele `NIEUWS_AFZENDERS` (komma's ertussen). Testen of inloggen lukt: Actions → Nieuwsmails ophalen → Run
workflow met test = ja.

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
eigen beschrijving is. Teksten, openingstijden en kenmerken komen uit de websitescan (`tools/bedrijven_scan.py`, workflow *Bedrijven scannen*) in `data/bedrijvengids-scan.json`: status `voorstel` staat als concept online (noindex), `goedgekeurd` gaat Google in, `verwijderd` haalt het bedrijf uit de gids.

Betaalde pakketten staan in `data/bedrijvengids-pakketten.json` (pakket, betaald_tot, logo, fotos, knop, actie). Foto's van Uitgelicht en Partner (tot 10) komen per mail binnen (afspraak met Frans, okt 2026): zet ze in `assets/uploads/bedrijvengids/<slug>/` en de paden in `fotos`; de eerste wordt de hoofdfoto, de rest staat in een carrousel op de bedrijfspagina. Uitgelicht = bovenaan de categorie, maximaal 3, volgorde wisselt per dag; na `betaald_tot` valt het bedrijf bij de nachtelijke herbouw (workflow *Agenda*) terug naar gratis. Elke gratis pagina heeft een knop *Dit is mijn bedrijf* naar het aanmeldformulier met de gegevens al ingevuld. Zo'n aanmelding is een wijziging van een bestaande vermelding: de mail aan de redactie zet de huidige gegevens (`data/bedrijvengids-vermeldingen.json`) naast de ingestuurde en zegt of het e-mailadres bij de website hoort. Na akkoord zet `tools/aanmeldingen.py` de wijziging in `data/bedrijvengids-wijzigingen.json`; die gaat voor op scan en oude gids. Voorstel voor de categorieën:
`/mnt/project-files/advies/bedrijvengids-categorieen.md`.

### Bedrijvengids: beslissingen en de jaarlijkse herscan

Alle beslissingen van de redactie staan in bestanden, zodat een nieuwe scan ze niet ongedaan maakt:

- `data/bedrijvengids-scan.json`: per bedrijf de status. `goedgekeurd` = tekst en kenmerken akkoord, `verwijderd` = uit de gids, met `reden` (wie en wanneer). Een verwijderd bedrijf komt nooit vanzelf terug, ook niet via een nieuwe scan of een claim; alleen door de status met de hand te veranderen.
- `data/bedrijvengids-correcties.json`: adressen en ligging die de redactie heeft verbeterd (gaan voor op oude gids en OpenStreetMap).
- `data/bedrijvengids-websites.json`: uitkomst van de wekelijkse websitecontrole; zonder werkende website valt een bedrijf vanzelf uit de gids.
- `data/bedrijvengids-wijzigingen.json`: goedgekeurde claims (*Dit is mijn bedrijf*), gaan voor op alles.

Jaarlijkse herscan (bijvoorbeeld oktober 2027): Actions > *Bedrijven scannen* met categorie `sportschool` en `opnieuw` = `ja`. Goedgekeurde bedrijven krijgen dan een nieuw voorstel (de pagina toont het als concept tot de redactie het goedkeurt), verwijderde blijven weg, nieuwe bedrijven uit OpenStreetMap worden meegenomen. Daarna een datacheck zoals in `docs/datacheck-sportscholen-2026-10.md`: adres op de eigen site, geen sportschool, twijfel of open, twijfelachtige kenmerken.

### Bedrijvengids: standaard voor elke nieuwe categorie (afgesproken met Frans, 23-10-2026)

Zo is de categorie sportscholen opgezet; elke volgende categorie gaat op dezelfde manier, zodat Frans niet meerdere rondes hoeft te doen:

1. **Verzamelen** (`tools/bronnen_verzamelen.py <categorie>`): de bedrijven uit de oude gids plus OpenStreetMap en Overture Maps voor die categorie. Dubbelen worden samengevoegd. Meteen eruit, met de reden in `advies/osm-bedrijvengids/<categorie>-uitgefilterd.csv`: permanent gesloten volgens Overture, geen (eigen) website (alleen Facebook, Thuisbezorgd e.d.), onzekere bron, of een naam die bij een andere categorie hoort (bakkerij, cafetaria). Voeg de categorie toe aan `BRONNEN` in dat script en aan `CATEGORIEEN` in `tools/bedrijvengids.py`.
2. **Websitecontrole** (`tools/websites_controleren.py`): geen website of een dode website = automatisch uit de gids.
3. **Scan** van de eigen website (`tools/bedrijven_scan.py`, workflow *Bedrijven scannen* met de categorie): tekst in de afgesproken stijl (warm, je/jij, tip van een lokale vriend, geen claims die niet te controleren zijn), kenmerken alleen als de site ze noemt (eigen lijst per categorie in `PER_CATEGORIE`), openingstijden alleen als ze leesbaar op de site staan.
4. **Automatisch uitfilteren, met reden in de scan** (gebeurt in de scan zelf): site niet uit te lezen, gestopt volgens de eigen site of te weinig informatie = status `verwijderd` met een reden die met "automatisch:" begint. Past het niet in de categorie (een cafetaria tussen de restaurants), dan komt het in `niet_in` en verschijnt het later bij de juiste categorie. Betalende bedrijven worden nooit automatisch verwijderd.
5. **Datacheck** voor Frans, één lijst (`docs/datacheck-<categorie>-<jaar-maand>.md`): adres op de eigen site wijkt af, twijfelachtige kenmerken, wat er is uitgefilterd en waarom. Frans beslist alles in één keer; de besluiten gaan in de databestanden en in `docs/`.

**Google als tweede bron (besluit Frans, 23-10-2026):** geen Google Places API. De voorwaarden van Google Maps Platform (artikel 3.2.3) verbieden gebruik "in a listings or directory service", het bewaren van gegevens, teksten maken op basis van Google-content (zoals reviews) en Places-gegevens naast een niet-Google-kaart. In plaats daarvan heeft elke bedrijfspagina een gewone link "Bekijk de reviews op Google Maps" (zonder API of sleutel), en gebruiken we voor "permanent gesloten" het veld `operating_status` van Overture Maps.

6. **Daarna** de goedgekeurde teksten live, plus de indeling van de categoriepagina (alles gelijk, alleen Uitgelicht valt op) en het blok onder de blogs over dat onderwerp.

