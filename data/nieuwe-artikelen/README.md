# Nieuwe artikelen

Artikelen die niet uit de WordPress-export komen. Eén JSON-bestand per artikel, in dezelfde vorm als een WordPress-bericht:

- `slug`, `title.rendered`, `date`, `modified`, `content.rendered` (de HTML van de tekst), `categories` (leeg laten)
- optioneel `uitgelicht`: `{"src", "w", "h", "alt"}`. Zonder uitgelichte foto wordt de eerste foto uit de tekst de foto op de kaartjes.

`tools/import_wordpress.py` leest ze mee met de berichten uit WordPress. Zet het artikel ook in
`data/indeling-artikelen.csv` (rubriek) en `data/seo-artikelen.csv` (zoekwoord, titel en meta description).
Foto's: zet de webp in `assets/uploads/<jaar>/<maand>/` en verwijs ernaar als
`https://www.nijmegenonline.nl/wp-content/uploads/<jaar>/<maand>/<naam>.jpg`; build.py maakt daar de lokale webp van.
Vermeld de bron van vrije foto's in een `<figcaption>` en in `data/fotoregister.json`.
