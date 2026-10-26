# Livegang: van testsite naar www.nijmegenonline.nl

Zolang dit een testsite is, wijzen alle links naar pagina's die al in deze repo staan naar de testsite
zelf (relatieve links). Daardoor hoeft er bij de livegang **niets aan de links te veranderen**: dezelfde
bestanden werken straks gewoon op www.nijmegenonline.nl. Canonical-tags, Open Graph en structured data
wijzen nu al naar www.nijmegenonline.nl.

Links naar pagina's die nog niet gebouwd zijn (bedrijvengids, agenda, contact, thema-pagina's, ...)
wijzen nog naar de huidige WordPress-site. `python tools/build.py` toont welke dat zijn. Zodra zo'n
pagina in de repo staat, maakt hetzelfde script de links ernaartoe automatisch intern.

## Vóór de livegang

- [ ] Alle pagina's gebouwd: `python tools/build.py` meldt geen links meer naar de huidige site
      (behalve de testbalk, die bij `--live` verdwijnt)
- [ ] Nieuwsberichten (83 onder `/nieuwsoverzicht/`) overgezet; vraagt een WordPress-export (XML)
- [ ] Evenementen (809, EventOn) en bedrijvengids (84, Listdom) overgezet, met datums en adressen
- [x] Afbeeldingen van `wp-content/uploads` staan als webp in `assets/uploads/` (`tools/afbeeldingen.py`);
      `tools/build.py` laat de pagina's ernaar wijzen. Nieuwe pagina's: eerst afbeeldingen downloaden, dan dit script
- [ ] Partnerslider, zijbalk en formulieren getest op desktop en mobiel
- [x] `_redirects` onder de limiet van Cloudflare Pages (2.000 vaste regels en 100 met `*`): op 25-10-2026 276.
      `tools/build.py` laat de oude adressen zonder backlinks, zoekverkeer of plek in de oude sitemap weg
      (`data/doorverwijzingen-ongebruikt.txt`, analyse in `advies/doorverwijzingen/` in de projectmap); hun
      doorstuurpagina blijft bestaan. Nieuwe doorverwijzingen, zoals afgelopen evenementen, komen er gewoon bij
- [ ] Alle URL's uit de huidige sitemap en paginalijst geven 200 of een bedoelde 301 (paginalijst gecontroleerd op
      24-10-2026; oude pagina's die niet terugkomen staan in `data/oude-paginas.csv`)
- [x] Google Analytics-code (zelfde Google-tag `GT-5R43F82` als WordPress, GA4-property 337370292) in elke pagina via
      `partials/analytics.html`; laadt alleen op www.nijmegenonline.nl, dus de testsite telt niet mee
- [x] Google Analytics privacyvriendelijk (zie /privacy-policy/), ingesteld op 24-10-2026 in Analytics → Beheer:
      verwerkersovereenkomst (Accountinstellingen → Wijzigingsvoorwaarden voor gegevensverwerking) geaccepteerd;
      Accountinstellingen → gegevens delen: alles uit; Gegevensverzameling → Google Signals uit;
      Gegevensbewaring op 14 maanden; advertentiepersonalisatie uit. Zonder deze instellingen is een cookiemelding nodig
- [x] Search Console: de verificatie-tag (HTML-tag) staat in `partials/analytics.html`, dus de property blijft geverifieerd
- [ ] Statistiekpagina `/statistiek/` (intern, met wachtwoord): in GitHub → Settings → Secrets and variables → Actions de
      geheimen `STATISTIEK_WACHTWOORD`, `DATAFORSEO_LOGIN`, `DATAFORSEO_PASSWORD` en `GSC_SERVICE_ACCOUNT_JSON` zetten,
      dan meet `.github/workflows/statistiek.yml` elke maandag. De cijfers staan versleuteld in `statistiek/data.json`

## Op de dag zelf

De site blijft op GitHub Pages. Cloudflare Pages is niet nodig: `_redirects` werkt daar niet, maar elk oud adres heeft
een eigen doorstuurpagina in de repo (meta-refresh met canonical), en die volgt Google ook.

1. DNS bij Zxcs: de A- en AAAA-records van `@` (185.104.29.78 en 2a06:2ec0:1::117) weg, vier A-records
   185.199.108.153, 185.199.109.153, 185.199.110.153 en 185.199.111.153 erbij, en `www` als CNAME naar
   `itandleisure.github.io`. MX, `mail`, SPF, DKIM en DMARC blijven zoals ze zijn
2. De pull request met het bestand `CNAME` (`www.nijmegenonline.nl`) mergen. De workflow *Agenda bijwerken* start dan
   vanzelf en bouwt de live-versie: `tools/build.py` ziet `CNAME` en haalt de testbalk en `noindex` weg, zet robots.txt
   open en maakt 404.html geschikt voor de root. Zolang `CNAME` er staat, blijft dat zo, ook na de nachtelijke runs
3. GitHub → Settings → Pages: controleren dat het custom domain `www.nijmegenonline.nl` is, en *Enforce HTTPS*
   aanvinken zodra het certificaat klaar is (kan tot een uur duren nadat de DNS is doorgekomen)
4. WordPress als back-up laten staan
5. MailerLite: in de RSS-campagne de feed-adressen veranderen in
   `https://www.nijmegenonline.nl/nieuwsbrief/uitgelicht.xml`, `.../nieuwsbrief/nieuws.xml` en `.../nieuwsbrief/agenda.xml`
6. Google Analytics → Realtime: controleren of bezoekers binnenkomen
7. Search Console: nieuwe sitemap indienen, daarna een paar weken 404's in de gaten houden
