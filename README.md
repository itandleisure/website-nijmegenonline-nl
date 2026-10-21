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
