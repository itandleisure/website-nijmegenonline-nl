# Partners

Eén centrale lijst met partners en een roterende slider die je op elke pagina kunt inpluggen.
Deze map staat op zichzelf, zodat hij later ook naar een eigen repository kan als andere sites
dezelfde partners willen tonen.

## Partner toevoegen of wijzigen

1. Zet het logo of de banner in `img/` (liefst WebP, maximaal ±800 px breed).
2. Voeg een blok toe aan `partners.json`:

```json
{
  "id": "naam-zonder-spaties",
  "naam": "Naam zoals bezoekers hem zien",
  "url": "https://www.website-van-partner.nl/",
  "afbeelding": "img/bestand.webp",
  "plaatsingen": ["alle"],
  "start": "2026-11-01",
  "eind": "2027-01-31",
  "gewicht": 1
}
```

- `plaatsingen`: waar de partner verschijnt. `alle` is overal; anders bijvoorbeeld `blog`, `home`,
  `agenda`, `bedrijvengids` of `kerst`. Een pagina kiest zijn plaatsing met `data-plaatsing`.
- `start` en `eind` (JJJJ-MM-DD): optioneel. Buiten deze periode verschijnt de partner niet.
  Leeg laten betekent altijd.
- `onderwerpen`: optioneel, voor het pakket Uitgelicht. Met bijvoorbeeld `["sportschool"]` verschijnt de banner
  alleen in sliders met `data-onderwerp="sportschool"`: op de categoriepagina en onder de blogberichten over dat
  onderwerp (tools/bedrijvengids.py zet dat attribuut). Zonder `onderwerpen` (Partner) komt de banner overal.
- `gewicht`: een partner met gewicht 2 staat vaker vooraan dan een met gewicht 1.

## Slider op een pagina zetten

```html
<link rel="stylesheet" href="../partners/slider.css">
<div class="partner-slider" data-plaatsing="blog"></div>
<script src="../partners/slider.js" defer></script>
```

Pas `../` aan aan de diepte van de pagina. Links krijgen automatisch `rel="sponsored"`.
Als Google Analytics (gtag) op de pagina staat, gaan vertoningen en kliks als events
`partner_vertoning` en `partner_klik` naar Analytics, met de partner erbij.
