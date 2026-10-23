# Datacheck sportscholen (23 oktober 2026)

Hoe gecontroleerd: voor alle 37 sportscholen heb ik onze gegevens (oude gids en OpenStreetMap) vergeleken met wat er op hun eigen website staat. Daarnaast gaf de scan per bedrijf aantekeningen over wat niet klopte of niet te controleren was.

## Wat klopt

- **Website:** bij alle 37 werkt die (wekelijkse controle).
- **Adres:** bij 22 staat het precies zo op hun eigen site. Bij 7 staat de straat goed op de site, maar zonder postcode; dat is ook in orde.
- **Tekst en kenmerken:** alles is geschreven op basis van hun eigen site en door jou goedgekeurd.

## 1. Geen sportschool

Die horen in een andere categorie, of uit de gids:

| Bedrijf | Wat het is |
|---|---|
| Nijmegen Outdoor | groepsuitjes en E-Choppers (en een ander adres: Tweede Walstraat 17) |
| Xtreme Marine Sports | flyboarden, op Experience Island en in Appeltern |
| GroepsGeluk | trainingen en coaching voor het onderwijs; de site is verhuisd naar wereldvangeluk.nl |

## 2. Adres wijkt af van hun eigen site

| Bedrijf | Bij ons | Op hun site |
|---|---|---|
| The Kettlebell Club | Hatertseweg 23B, 6533 AB | Groenestraat 215, 6531 HH (verhuisd?) |
| Healtality | Gorterplaats 6 | Gorterplaats 6A |
| Nimma Moves | Archipelstraat 27 | Archipelstraat 27-29 |
| Sportloods Oost | Coehoornstraat 71 | Coehoornstraat 71T |
| Harbor Gym | Mariënburg 90 | ook een tweede vestiging: Dokstraat 255 (Waalhaven) |

## 3. Twijfel of ze echt open zijn

| Bedrijf | Waarom |
|---|---|
| Heavy Duty Outdoor Gym | volgens hun site "in ontwikkeling", bootcamp uitgesteld, geen rooster |
| Personal Fitness Nederland | landelijke keten; een vestiging in Nijmegen is op hun site niet te vinden |

## 4. Twijfelachtige kenmerken

| Bedrijf | Kenmerk | Waarom twijfel |
|---|---|---|
| Novio Fit, Ultrasport | bedrijfsuitje | ze bieden bedrijfsfitness, dat is geen uitje |
| Basic-Fit Kerkenbos | boksen | alleen een video-workout "Box" |
| Sanasport, MY35 | senioren | alleen genoemd als doelgroep, of "valpreventie" zonder uitleg |

## 5. Openingstijden

Bij 18 van de 37 staan geen openingstijden, omdat ze die niet (leesbaar) op hun site hebben. Dat is bewust: liever geen tijden dan verkeerde. Het bedrijf kan ze zelf toevoegen via "Dit is mijn bedrijf".

## Besluit van Frans (23 oktober 2026)

Alles is uitgevoerd: de 3 die geen sportschool zijn, Heavy Duty Outdoor Gym en Personal Fitness Nederland zijn verwijderd, de adressen zijn aangepast (`data/bedrijvengids-correcties.json`) en de twijfelachtige kenmerken zijn weg. Eerder die dag verwijderd: bedrijven zonder werkende of leesbare website (zie de redenen in `data/bedrijvengids-scan.json`). Resultaat: 32 sportscholen.
