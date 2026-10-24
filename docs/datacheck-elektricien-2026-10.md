# Datacheck elektricien (24-10-2026)

Alles wat er met de verzamelde bedrijven is gebeurd, in één lijst. Wat automatisch is uitgefilterd staat er met de reden bij; zet je iets terug, dan zet ik de status in `data/bedrijvengids-scan.json` weer op voorstel. De volledige lijst per bedrijf staat in de projectbestanden: `bedrijvengids/datacheck-elektricien-2026-10.csv`.

## Samenvatting

|  | Aantal |
|---|---|
| Gevonden in oude gids, OpenStreetMap en Overture | 21 |
| Meteen niet meegenomen: geen website | 8 |
| Meteen niet meegenomen: onzekere bron | 2 |
| Website werkt niet | 1 |
| Automatisch verwijderd na de scan | 2 |
| Hoort bij een andere categorie (komt daar later terug) | 0 |
| Fout bij het scannen | 0 |
| Nog niet gescand | 0 |
| **In de gids, met tekst als concept** | 8 |

## 1. Adres op hun eigen site wijkt af

| Bedrijf | Bij ons | Op hun site |
|---|---|---|
| R. Giesen Elektro | De Breeacker 1, 6678 DG | Breeacker 1, 6678 DG Oosterhout (Gld.) |

## 2. Opmerkingen uit de scan (twijfel over kenmerken, openingstijden of of ze open zijn)

| Bedrijf | Opmerking |
|---|---|
| Ariëns solartechniek | De opgegeven URL arienssolar.nl leidt naar ariensenergie.nl (Ariens Energie); naam wijkt af van 'Ariëns solartechniek'. De site noemt geen adres in Nijmegen; Keizer Karelplein 32Q kon niet worden bevestigd (mogelijk kantoor- of postadres). Focus ligt duidelijk op B2B; er is een menu-item 'Particulier', maar zonder inhoud in de aangeleverde tekst. Alleen de homepage bevatte bruikbare tekst, de overige pagina's waren CSS-bestanden. |

## 3. Automatisch verwijderd na de scan

| Bedrijf | Website | Reden |
|---|---|---|
| Boulka Service & Techniek | http://www.boulkaservice-techniek.nl/ | automatisch: website niet uit te lezen, liever geen halve gegevens (scan 24-10-2026) |
| Elektriciengids | https://elektriciengids.com | automatisch: website niet uit te lezen, liever geen halve gegevens (scan 24-10-2026) |

## 4. Hoort bij een andere categorie

_Geen._

## 5. Website werkt niet

| Bedrijf | Website | Uitkomst |
|---|---|---|
| Jonker Techniek | http://www.jonkertechniek.nl/ | domein bestaat niet |

## 6. Fout bij het scannen (wordt bij de volgende scan opnieuw geprobeerd)

_Geen._

## 7. Meteen niet meegenomen bij het verzamelen

Permanent gesloten volgens Overture, of zonder eigen website. De lijst staat in `advies/osm-bedrijvengids/elektricien-uitgefilterd.csv`.

_Geen._
