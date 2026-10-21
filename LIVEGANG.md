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
- [ ] Afbeeldingen van `wp-content/uploads` naar deze repo of een opslagdienst, en de verwijzingen
      in de pagina's daarop aangepast (nu laden ze nog van de WordPress-site)
- [ ] Partnerslider, zijbalk en formulieren getest op desktop en mobiel
- [ ] Alle URL's uit de huidige sitemap en paginalijst geven 200 of een bedoelde 301
- [ ] Google Analytics-code (zelfde property) in de header

## Op de dag zelf

1. `python tools/build.py --live`: haalt de testbalk en `noindex` weg en zet robots.txt open
2. In `404.html` de verwijzingen `/website-nijmegenonline-nl/` vervangen door `/`
3. Sitemap maken (`sitemap.xml`)
4. Hosting naar Cloudflare Pages (die leest `_redirects` voor de 301's van oude categoriepagina's;
   GitHub Pages kan dat niet)
5. DNS van nijmegenonline.nl naar de nieuwe hosting; WordPress als back-up laten staan
6. Search Console: nieuwe sitemap indienen, daarna een paar weken 404's in de gaten houden
