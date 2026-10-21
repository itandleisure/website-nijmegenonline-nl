# nijmegenonline.nl (testomgeving)

Startpunt voor de nieuwe versie van [nijmegenonline.nl](https://www.nijmegenonline.nl), die nu nog op
WordPress draait. Deze repo is bedoeld om te testen; de live site verandert hierdoor niet.

## Structuur

```
index.html            homepage (testversie met voorbeeldblokken: agenda, nieuws, bedrijvengids)
404.html              pagina voor onbekende URL's
assets/css/site.css   kleuren, lettertypes en opmaak
robots.txt            blokkeert zoekmachines zolang dit een test is
.nojekyll             zorgt dat GitHub Pages de bestanden ongewijzigd serveert
```

## Bekijken

- **Online:** via GitHub Pages op `https://itandleisure.github.io/website-nijmegenonline-nl/`
  (Settings → Pages → Deploy from a branch → `main` / root).
- **Lokaal:** `python -m http.server 8080` in deze map en ga naar http://localhost:8080.

## Belangrijk zolang dit een test is

- Geen `CNAME`-bestand toevoegen: dat koppelt het domein en zou de echte site vervangen.
- `robots.txt` en `noindex` laten staan, zodat Google geen dubbele content ziet.
- URL's van de echte site (artikelen, `/events/…`, `/bedrijvengids/…`, `/nieuwsoverzicht/…`) houden we
  straks precies gelijk vanwege de backlinks. Zie het bouwplan in het project.
