# Datacheck zaalverhuur (24-10-2026)

Alles wat er met de verzamelde bedrijven is gebeurd, in één lijst. Wat automatisch is uitgefilterd staat er met de reden bij; zet je iets terug, dan zet ik de status in `data/bedrijvengids-scan.json` weer op voorstel. De volledige lijst per bedrijf staat in de projectbestanden: `bedrijvengids/datacheck-zaalverhuur-2026-10.csv`.

## Samenvatting

|  | Aantal |
|---|---|
| Gevonden in oude gids, OpenStreetMap en Overture | 29 |
| Meteen niet meegenomen: geen website | 3 |
| Meteen niet meegenomen: permanent gesloten volgens Overture | 1 |
| Meteen niet meegenomen: hoort bij een andere categorie | 1 |
| Website werkt niet | 1 |
| Automatisch verwijderd na de scan | 5 |
| Hoort bij een andere categorie (komt daar later terug) | 1 |
| Fout bij het scannen | 0 |
| Nog niet gescand | 0 |
| **In de gids, met tekst als concept** | 17 |

## 1. Adres op hun eigen site wijkt af

| Bedrijf | Bij ons | Op hun site |
|---|---|---|
| Ampire Vastgoedgroep | Oranjesingel 62, 6511 NX | Oranjesingel 13A, 6511 NL Nijmegen |
| Old Cave Nijmegen | Sint Anthoniusplaats 13, 6511 TR | St.Anthoniusplaats 13, 6511 TR Nijmegen |
| Stichting Fabrikaat | Waalbanddijk 14H, 6541 AJ | Zaligestraat 10, 6663 KR Nijmegen (bereikbaar via de Oosterhoutse dijk) |

## 2. Opmerkingen uit de scan (twijfel over kenmerken, openingstijden of of ze open zijn)

| Bedrijf | Opmerking |
|---|---|
| Ampire Vastgoedgroep | Geen makelaar maar vastgoedontwikkelaar/belegger met eigen verhuur; daarom zakelijk-overig. Adres op de site (Oranjesingel 13A, 6511 NL) wijkt af van ons adres (Oranjesingel 62, 6511 NX). Kenmerk 'verkoop' betreft verkoop van eigen projecten, geen makelaarsdienst. |
| Building "roman Life" | Bedrijfsnaam in onze gids ('Building "roman Life"') is een vertaling; correcte naam is 'Roomsch Leven' (gebouw, geëxploiteerd door Stichting Michaël). Kenmerk 'tot 50 personen' twijfelachtig: kleine zaal is tot 70 personen. Geen openingstijden, catering of toegankelijkheid vermeld. |
| Fort Lent | Telefonisch bereikbaar ma-vr 9.00-17.00; bezoek alleen op afspraak. Site noemt feesten van 10 tot 850 personen en vergaderen voor 10 tot 300 personen. Formulier noemt 'Proeverij de Belvédère', onduidelijk wat dat is. |
| Stichting Fabrikaat | Adres op de site (Zaligestraat 10, 6663 KR) wijkt af van ons adres (Waalbanddijk 14H, 6541 AJ); mogelijk verhuisd. Vermoedelijke categorie zaalverhuur: de pagina 'Ruimte huren' is niet aangeleverd, dus details over zaalverhuur onbekend. Hoofdcategorie gekozen op basis van workshops/cursussen; ook 'galerie' of 'cafe' denkbaar. |

## 3. Automatisch verwijderd na de scan

| Bedrijf | Website | Reden |
|---|---|---|
| De Goffert Hospitality & Events | http://degoffert.nl | automatisch: website niet uit te lezen, liever geen halve gegevens (scan 24-10-2026) |
| Landelijk Notarieel Studenten Congres Nijmegen | http://www.lnsc.nl/ | automatisch: gestopt of verhuisd volgens de eigen website (scan 24-10-2026) |
| Nijmeegs Oktoberfest | https://www.nijmeegsoktoberfest.nl/ | automatisch: website niet uit te lezen, liever geen halve gegevens (scan 24-10-2026) |
| W I J N F O R T Huwelijk | http://wijnforthuwelijk.nl/ | automatisch: website niet uit te lezen, liever geen halve gegevens (scan 24-10-2026) |
| Z Chat | https://www.zchat.nl/ | automatisch: website niet uit te lezen, liever geen halve gegevens (scan 24-10-2026) |

## 4. Hoort bij een andere categorie

| Bedrijf | Website | Volgens de scan |
|---|---|---|
| De Kleine Weg | https://www.taichichuannijmegen.nl/?y_source=1_MjU0NzE0ODQtNDgzLWxvY2F0aW9uLndlYnNpdGU%3D | hoort bij Yoga (scan 24-10-2026) |

## 5. Website werkt niet

| Bedrijf | Website | Uitkomst |
|---|---|---|
| Wijkcentrum Dukenburg | http://www2.nijmegen.nl/content/1015505/wijkcentrum_dukenburg | domein bestaat niet |

## 6. Fout bij het scannen (wordt bij de volgende scan opnieuw geprobeerd)

_Geen._

## 7. Meteen niet meegenomen bij het verzamelen

Permanent gesloten volgens Overture, of zonder eigen website. De lijst staat in `advies/osm-bedrijvengids/zaalverhuur-uitgefilterd.csv`.

| Bedrijf | Adres | Reden |
|---|---|---|
| Ab Houtcreaties - Workshops Houtbewerken Met Elektrisch Gereedschap | Waalbandijk 16 | permanent gesloten volgens Overture |
