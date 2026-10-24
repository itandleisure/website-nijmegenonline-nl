# Datacheck taxi (24-10-2026)

Alles wat er met de verzamelde bedrijven is gebeurd, in één lijst. Wat automatisch is uitgefilterd staat er met de reden bij; zet je iets terug, dan zet ik de status in `data/bedrijvengids-scan.json` weer op voorstel. De volledige lijst per bedrijf staat in de projectbestanden: `bedrijvengids/datacheck-taxi-2026-10.csv`.

## Samenvatting

|  | Aantal |
|---|---|
| Gevonden in oude gids, OpenStreetMap en Overture | 15 |
| Meteen niet meegenomen: onzekere bron | 3 |
| Meteen niet meegenomen: geen website | 1 |
| Website werkt niet | 2 |
| Automatisch verwijderd na de scan | 4 |
| Hoort bij een andere categorie (komt daar later terug) | 0 |
| Fout bij het scannen | 0 |
| Nog niet gescand | 0 |
| **In de gids, met tekst als concept** | 5 |

## 1. Adres op hun eigen site wijkt af

| Bedrijf | Bij ons | Op hun site |
|---|---|---|
| Taxi Nijmegen 24 | De Steekse Acker 1227, 6546 DD | De Steekste acker 1227, 6546 DD Nijmegen |

## 2. Opmerkingen uit de scan (twijfel over kenmerken, openingstijden of of ze open zijn)

_Geen._

## 3. Automatisch verwijderd na de scan

| Bedrijf | Website | Reden |
|---|---|---|
| Hk taxi nijmegen | https://www.hktaxinijmegen.nl/ | automatisch: te weinig informatie op de eigen website (scan 23-10-2026) |
| Taxi 25 Uur | https://taxi25uur.nl/ | automatisch: website niet uit te lezen, liever geen halve gegevens (scan 23-10-2026) |
| Taxi De Waalsprong | http://www.taxidewaalsprong.nl/ | automatisch: website niet uit te lezen, liever geen halve gegevens (scan 23-10-2026) |
| Taxi Weeze | https://www.taxiweeze.nl/contact/ | automatisch: website niet uit te lezen, liever geen halve gegevens (scan 23-10-2026) |

## 4. Hoort bij een andere categorie

_Geen._

## 5. Website werkt niet

| Bedrijf | Website | Uitkomst |
|---|---|---|
| Hkn Taxi Nijmegen | http://www.hkntaxi.nl/ | domein bestaat niet |
| Taxi Numaga Nijmegen | http://www.taxiservicenumaga.nl | domein bestaat niet |

## 6. Fout bij het scannen (wordt bij de volgende scan opnieuw geprobeerd)

_Geen._

## 7. Meteen niet meegenomen bij het verzamelen

Permanent gesloten volgens Overture, of zonder eigen website. De lijst staat in `advies/osm-bedrijvengids/taxi-uitgefilterd.csv`.

_Geen._
