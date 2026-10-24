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
- [ ] Alle URL's uit de huidige sitemap en paginalijst geven 200 of een bedoelde 301 (paginalijst gecontroleerd op
      24-10-2026; oude pagina's die niet terugkomen staan in `data/oude-paginas.csv`)
- [x] Google Analytics-code (zelfde Google-tag `GT-5R43F82` als WordPress, GA4-property 337370292) in elke pagina via
      `partials/analytics.html`; laadt alleen op www.nijmegenonline.nl, dus de testsite telt niet mee
- [ ] Google Analytics privacyvriendelijk (zie /privacy-policy/), in Analytics → Beheer:
      verwerkersovereenkomst (Accountinstellingen → Wijzigingsvoorwaarden voor gegevensverwerking) geaccepteerd;
      Accountinstellingen → gegevens delen: alles uit; Gegevensverzameling → Google Signals uit;
      Gegevensbewaring op 14 maanden; geen koppeling met Google Ads. Zonder deze instellingen is een cookiemelding nodig
- [x] Search Console: de verificatie-tag (HTML-tag) staat in `partials/analytics.html`, dus de property blijft geverifieerd

## Op de dag zelf

1. `python tools/build.py --live`: haalt de testbalk en `noindex` weg en zet robots.txt open
2. In `404.html` de verwijzingen `/website-nijmegenonline-nl/` vervangen door `/`
3. Sitemap controleren: `sitemap.xml` wordt door `tools/build.py` gemaakt. Pagina's die nog op WordPress staan (bedrijvengids, agenda, nieuws) komen erin zodra ze hier gebouwd zijn
4. Hosting naar Cloudflare Pages (die leest `_redirects` voor de 301's van oude categoriepagina's;
   GitHub Pages kan dat niet)
5. DNS van nijmegenonline.nl naar de nieuwe hosting; WordPress als back-up laten staan
6. MailerLite: in de RSS-campagne de feed-adressen veranderen in
   `https://www.nijmegenonline.nl/nieuwsbrief/uitgelicht.xml`, `.../nieuwsbrief/nieuws.xml` en `.../nieuwsbrief/agenda.xml`
7. Google Analytics → Realtime: controleren of bezoekers binnenkomen
8. Search Console: nieuwe sitemap indienen, daarna een paar weken 404's in de gaten houden
