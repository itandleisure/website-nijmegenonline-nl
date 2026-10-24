# Datacheck afhaal (24-10-2026)

Alles wat er met de verzamelde bedrijven is gebeurd, in één lijst. Wat automatisch is uitgefilterd staat er met de reden bij; zet je iets terug, dan zet ik de status in `data/bedrijvengids-scan.json` weer op voorstel. De volledige lijst per bedrijf staat in de projectbestanden: `bedrijvengids/datacheck-afhaal-2026-10.csv`.

## Samenvatting

|  | Aantal |
|---|---|
| Gevonden in oude gids, OpenStreetMap en Overture | 189 |
| Meteen niet meegenomen: geen website | 49 |
| Meteen niet meegenomen: hoort bij een andere categorie | 11 |
| Meteen niet meegenomen: permanent gesloten volgens Overture | 8 |
| Meteen niet meegenomen: onzekere bron | 2 |
| Meteen niet meegenomen: geen eigen website | 1 |
| Website werkt niet | 5 |
| Automatisch verwijderd na de scan | 13 |
| Hoort bij een andere categorie (komt daar later terug) | 1 |
| Fout bij het scannen | 0 |
| Nog niet gescand | 0 |
| **In de gids, met tekst als concept** | 99 |

## 1. Adres op hun eigen site wijkt af

| Bedrijf | Bij ons | Op hun site |
|---|---|---|
| Adana Mix | Sint Annastraat 236, 6525 GZ | St. Annastraat 236, 6525GZ Nijmegen |
| De Wit kaashandel | Lange Hezelstraat 11, 6511 CA | Lange Hezelstraat, hoek Houtstraat en Stikke Hezelstraat, Nijmegen (geen huisnummer genoemd) |
| Eetpaleis Marhaba | St. Annastraat 58, 6524 GG | Sint Annastraat 58, 6524GG Nijmegen |
| Johnny's Burger co. | Waalkade 108-112, 6511 XR | Smetiusstraat 12, 6511 ES Nijmegen |
| Julia's | Stationsplein 6P, 6512 AB | Stationshal naast spoor 1 (Nijmegen CS) |
| Shanghai | Molenweg 145, 6543 VB | Molenweg, Nijmegen West (geen huisnummer op de site) |
| Sterre's Delicious Food | Hatertseweg 522, 6533 GX | Kerkenbos 10-117, 6546 BJ Nijmegen |
| Ugala III | Otto C. Huismanstraat 268, 6544 ZR | O.c. Huismanstraat 268, 6544ZR Nijmegen |
| Zorba Foodbar Nijmegen | Van Welderenstraat 130, 6511 MV | Tweede Walstraat 165, 6511 HC Nijmegen |

## 2. Opmerkingen uit de scan (twijfel over kenmerken, openingstijden of of ze open zijn)

| Bedrijf | Opmerking |
|---|---|
| 1-2-3 Cafetaria | Opgegeven website (cafetaria123nijmegen.nl) leidt naar cafetaria1-2-3.nl. Alleen bezorgtijden vermeld; onduidelijk of afhalen of zitplekken mogelijk zijn. Wijk Heseveld afgeleid uit het adres. |
| Adana Mix | Op de site staan alle dagen als 'Gesloten' vermeld; mogelijk een weergavefout van het bestelsysteem of tijdelijk gesloten, graag controleren. Kenmerk 'shoarma en kebab' afgeleid van categorieën Grill/Kapsalon/Lahmacun, niet letterlijk genoemd. Keuken 'Turks' afgeleid uit naam en menu (lahmacun). Site noemt een 'Restaurant'-kolom en reserveren, maar onduidelijk hoeveel zitplekken er zijn. |
| Babo | Bezorging staat op alle dagen als 'Gesloten', terwijl de bezorgregio Deventer-postcodes (7413-7429) noemt; lijkt een template-fout, daarom kenmerk bezorgen niet gekozen. Restauranttijden op homepage 12:00-23:00 wijken af van 22:30 op infopagina. Postcode op site onvolledig (6533W). Shoarma/kebab afgeleid uit durum/kapsalon/lahmacun en 'grillroom' in URL. |
| BKK Thai | Volgens de site is BKK Thai vooral een afhaal- en bezorgzaak met online bestellen. Of je er ook aan tafel kunt eten, staat er niet op. Daarom heb ik afhaal gekozen in plaats van restaurant. De openingstijden op de site spreken elkaar tegen: in de footer staat 16:00-21:00, bij de filiaalkeuze 12:00-21:00. Verder staat er een melding dat er tijdelijk alleen in Arnhem Centrum (postcode 6811) bezorgd wordt, terwijl er ook staat 'Wij bezorgen in Nijmegen'. Graag nakijken. BKK Thai is een keten met een tweede vestiging in Arnhem. |
| Cafetaria De Biezen | Site gebruikt de naam 'Eethuis Nijmegen' in plaats van 'Cafetaria De Biezen'; mogelijk naamswijziging of handelsnaam, graag controleren. Op de homepage stond een melding dat de zaak/website 'vandaag gesloten' was wegens een storing (tijdelijk). |
| Cafetaria Family | Site op standaardplatform (DISH/makro.rest) met weinig eigen tekst; menu-items alleen als categorienamen zichtbaar. Catering genoemd als dienst, maar zonder verdere uitleg, daarom niet als extra categorie. Reserveringsknop is standaard van het platform; onduidelijk of er zitplekken zijn. |
| Cafetaria Keizer Karelplein | De openingstijdentabel op de site toont alle dagen 'Gesloten'; mogelijk een fout in het bestelsysteem of tijdelijke sluiting. Graag controleren. Openingstijden daarom leeg gelaten. Bezorgen afgeleid uit 'eten thuisbezorgd' en vermelding van bezorgkosten. |
| Cafetaria Lent | Openingstijden voor za/zo alleen als 'vandaag/morgen' getoond (afhalen 12:00-00:00 en 14:00-22:30; bezorgen 16:30-22:00 en 16:30-21:30), vermoedelijk za en zo, maar niet zeker. Site vraagt 'meenemen of hier opeten?', mogelijk zitplekken, maar niet duidelijk genoemd. Telefoon: 024-3231775. |
| Cafetaria Neerbosch | Openingstijden voor zaterdag en zondag worden niet apart genoemd; alleen 'vandaag' en 'morgen', dus weekendtijden onzeker. Site noemt 'meenemen of hier opeten?', maar zitplekken niet duidelijk bevestigd. Keuken 'Turks' afgeleid uit döner en pizza Karadeniz, twijfelachtig. |
| Cafetaria Steenbok | Menu-inhoud niet in opgehaalde tekst, dus geen kenmerk 'friet en snacks' gekozen. Site noemt 'eten thuisbezorgd' alleen in de algemene omschrijving, maar openingstijden gelden alleen voor afhalen; bezorgen daarom niet opgenomen. Openingstijden voor zaterdag/zondag niet expliciet genoemd ('Vandaag/Morgen' 14:00-21:00). Tekst 'Meenemen of hier opeten?' suggereert mogelijk zitplekken, maar onduidelijk. Telefoon: 024-3500533. |
| Caglar | Tijden voor zaterdag en zondag staan alleen als 'vandaag/morgen' (vermoedelijk za 16:00-03:00/02:45, zo 16:00-02:00/01:45); niet zeker. Menu-inhoud niet opgehaald; 'friet en snacks' afgeleid uit 'Cafetaria'. Naam op site: Eethuis Caglar / Cafetaria Pizzeria Caglar. |
| Corona Tweede Walstraat | Een snackbar/afhaalzaak (dürüm, kapsalon, pizza, friet), geen restaurant, daarom afhaal als hoofdcategorie. Volgens de site is bezorging alle dagen gesloten, dus het kenmerk bezorgen is niet gekozen, ook al noemen de metatags bezorging. De site biedt wel tafelreservering aan. De keuken 'Turks' is afgeleid van de gerechten (dürüm, kapsalon) en staat niet zo op de site. Het menu zelf (order.php) is niet gelezen. |
| Curasauce | Site presenteert zich als foodtruck-catering voor evenementen, niet als snackbar met vaste openingstijden; daarom hoofdcategorie catering in plaats van afhaal. Geen adres of openingstijden op de site; onduidelijk of je aan de Roggeweg kunt afhalen. |
| De Mandarijn | De naam suggereert een restaurant, maar de site heeft het alleen over afhalen en catering. Er staat niets over aan tafel eten, dus de hoofdcategorie is afhaal geworden. Bezorging wordt alleen bij catering genoemd (vanaf 15 personen), dus het kenmerk bezorgen is weggelaten. Het kenmerk groepen is gekozen vanwege de catering vanaf 15 personen. Twijfel je daarover, dan kun je het weghalen. Online bestellen loopt via Bistroo. |
| Giros | De site noemt zichzelf een 'Grieks afhaalrestaurant'. Daarom staat de hoofdcategorie op afhaal en niet op restaurant. Bij de openingstijden staat 'Gewijzigde openingstijden', dus die kunnen tijdelijk zijn. |
| Groenen Automatiek | Openingstijden staan als 'Vandaag/Morgen' op de site; afhaaltijd 16:45-02:30 voor 'Vandaag' (vermoedelijk zaterdag) afgeleid, controleren. Site noemt zowel 'Cafetaria Groenen' als 'Automatiek Groenen'. Of je er ter plekke kunt eten is onduidelijk ('Meenemen of hier opeten?'). |
| Johnny's Burger co. | Het adres wijkt af van wat wij hebben. Volgens de site zit de enige Nijmeegse vestiging in de Smetiusstraat 12, 6511 ES, en niet op de Waalkade 108-112. Misschien is de zaak verhuisd, dat moet de redactie nog nagaan. Johnny's is een keten met meer dan 50 vestigingen. De site noemt alleen bezorgen en afhalen; nergens staat dat je ter plekke aan tafel kunt eten. Daarom heb ik 'afhaal' gekozen en niet 'restaurant'. |
| Kwalitaria | De vestigingspagina bevat een vergelijking met concurrerende snackbars en de claim 'best beoordeelde snackbar van Lent'; deze claims zijn niet overgenomen. Vermelding 'vanaf 11:00 doordeweeks' klopt niet helemaal: op maandag pas vanaf 16:00. Bezorgtijden wijken af van openingstijden (ma 17:00-19:45, di-wo 12:00-19:45, do 12:00-20:30, vr 12:30-20:30, za 12:00-20:30, zo 16:00-19:45). |
| Made by Marn | Dit is geen restaurant maar een zaak met versbereide maaltijden om af te halen en thuis op te warmen, daarom is de hoofdcategorie afhaal. De gerechten op de homepage zijn uit 2016 (herfstvakantie, 'Italiaanse week'), dus de site lijkt al lang niet bijgewerkt. Het is daarom onzeker of de zaak nog actief is. De keuken wisselt per week. Er is ook een winkel met gebak; die pagina heb ik niet gelezen. |
| Mickey's Corner | Bezorging staat op alle dagen als 'Gesloten'; de vermelde bezorgpostcodes (7413-7429) horen bij Deventer en lijken een fout van het websitesysteem. Daarom kenmerk 'bezorgen' niet gekozen. Zitplekken worden niet expliciet genoemd, al is er een reserveerfunctie en 'restaurant'-openingstijden. |
| Multi | Site noemt online bestellen en thuisbezorgen, maar bij openingstijden staat 'Bezorging Gesloten'; daarom kenmerk bezorgen weggelaten. Zaterdag heeft een asterisk zonder toelichting. Kenmerk shoarma en kebab afgeleid uit 'durum' en 'grillroom' in de URL; eventueel controleren. |
| NIJMEGEN  ST. JACOBSLAAN | Ketenpagina (Sushi Daily) op de Britse site; menu is het Britse menu, aanbod in Nijmegen kan afwijken. Kiosk vermoedelijk in een supermarkt, maar dat staat niet op de pagina. Bezorging via Deliveroo wordt genoemd voor de UK-site, onduidelijk of dit voor Nijmegen geldt, daarom niet als kenmerk opgenomen. 'Afhalen' afgeleid uit kioskformule. |
| NIJMEGEN DAALSEWEG | Gelezen pagina's zijn van de Britse (gb-en) site van Sushi Daily; het menu is het Britse assortiment (met prijzen in ponden) en kan afwijken van de Nijmeegse kiosk. Bezorging via Deliveroo wordt genoemd voor de UK-site; niet zeker of dit voor Nijmegen geldt. Waarschijnlijk een kiosk in een supermarkt op de Daalseweg, maar dat staat niet op de pagina. |
| NIJMEGEN WAALSPRONG | De pagina hoort bij de Britse versie van de Sushi Daily-site. De openingstijden staan er als niet ingevuld ('00am - 00pm'), dus zijn ze onbekend. Het menu is van de Britse site, waardoor het aanbod in Nijmegen kan afwijken. Of er in Nijmegen wordt bezorgd is onduidelijk, want de bezorglinks verwijzen naar Britse vestigingen. De kiosk zit waarschijnlijk in een supermarkt, maar dat staat niet op de site. |
| Orient Drive | Dit is een afhaal- en bezorgzaak (bestelsite van Sitedish), dus geen restaurant waar je aan tafel eet. Daarom staat de hoofdcategorie op afhaal. Toen ik de site bekeek, stond er 'Website vandaag gesloten', maar dat lijkt alleen voor die dag te gelden. Vegan staat erbij omdat de site één gerecht als veganistisch aanduidt (Pokebowl Vega). Ik heb alleen de homepage gelezen; daar staan de menukaart, de openingstijden en het adres al op. |
| Panino di Marco | Site meldt 'No delivery', dus geen bezorging. Er stond een tijdelijke melding dat de zaak vandaag gesloten was door een elektrisch probleem en dat de website gesloten is; lijkt tijdelijk. Een melding over een Grieks gerecht met korting past niet bij het menu (vermoedelijk sjabloontekst). Of er zitplekken zijn, is niet bekend. |
| Pizza Pezzo | Ik heb gekozen voor 'afhaal' in plaats van 'restaurant': de site draait vooral om online bestellen, afhalen en bezorgen, en de kaart bestaat alleen uit pizza's en drankjes. Ter plekke eten kan volgens de site wel. Op de homepage stonden alleen afhaaltijden per dag. Daarin was vrijdag ('vandaag' op het moment van lezen) gesloten. Of dat vast zo is of alleen die dag, is niet duidelijk. Kloppen de tijden nog? De sociale media heten 'deitalianpizza'. De site noemt zichzelf 'een van de beste pizzeria's van Nijmegen', maar die claim heb ik niet overgenomen. Ik heb alleen de homepage gelezen. |
| Salade2Go | Op de homepage stond een melding dat het restaurant/de website die dag gesloten was door een elektronisch probleem; lijkt tijdelijk. Onduidelijk of er zitplekken zijn. |
| Shanghai | Site meldt tijdelijke sluiting wegens vakantie t/m 27 februari. Pagina's afhaalmenu en voordeelmenu bevatten geen leesbare tekst (menukaart waarschijnlijk als afbeelding). Bestellen alleen telefonisch: 024 377 1865. De genoemde gerechten nasi en babi pangang staan niet letterlijk op de site; redactie kan deze desgewenst vervangen door algemene omschrijving. |
| Shish Kebab | Site meldt vakantiesluiting t/m 8 september (jaar onduidelijk). De site bevat spamlinks (gokwebsites, 'slot gacor'), mogelijk gehackt. Er wordt gesproken over franchise; onduidelijk of er meer vestigingen zijn. Niet duidelijk of er zitplekken zijn of bezorgd wordt (wel 'Bestel online', reviews noemen inrichting). Wijk Nijmegen-Oost afgeleid van postcode, controleren. |
| Song da street food | De website is alleen een bestelpagina via het platform onesix, met de menukaart en verder niets. Er staat niets over zitplaatsen, afhalen of bezorgen en ook geen volledige openingstijden; alleen dat de gerechten 'beschikbaar om 11:30' zijn. De categorie afhaal is daarom een inschatting en lunchroom kan ook kloppen. Het kenmerk afhalen is niet aangevinkt, omdat de site dat niet letterlijk noemt. De postcode op de site is 6511 JH, bij ons staat 6511 JD. Op het moment van lezen stond de pagina op 'Online gesloten'. Naast Vietnamese gerechten staan er ook veel Indische en Surinaamse gerechten op de kaart. |
| Sterre's Delicious Food | Het betreft een foodtruck die op markten, braderieën en evenementen staat en te huur is; geen vaste afhaalzaak. Adres op de site (Kerkenbos 10-117, 6546 BJ) wijkt af van ons adres (Hatertseweg 522). Onduidelijk of de openingstijden voor een vaste locatie gelden. Bezorgen geldt voor ontbijtjes. Leeftijd van eigenaar (17) kan verouderd zijn. |
| Zorba Foodbar Nijmegen | Het adres op de site (Tweede Walstraat 165, 6511 HC) wijkt af van ons adres (Van Welderenstraat 130). Op de site staan alleen de tijden van maandag tot en met vrijdag duidelijk vermeld. Het weekend werd alleen getoond als 'vandaag/morgen' (vr 02:30 en za 01:00 voor het restaurant), en de zondag is onduidelijk. In de tekst staat 'dinsdag tot en met zondag'; dat moet nog gecontroleerd worden. Het kenmerk 'shoarma en kebab' is gebaseerd op het menu met durum en Griekse pita's. Het gaat om de Nijmeegse vestiging; er is ook een vestiging in Arnhem. De kortingscode is bewust niet genoemd. |

## 3. Automatisch verwijderd na de scan

| Bedrijf | Website | Reden |
|---|---|---|
| AnyTyme | https://www.anytyme.nl/vestigingen/anytyme-nieuw-zwanenveld | automatisch: te weinig informatie op de eigen website (scan 24-10-2026) |
| Cafetaria Tweety | http://tweetycafetaria.nl/ | automatisch: website niet uit te lezen, liever geen halve gegevens (scan 24-10-2026) |
| Cafeteria Heyendaalseweg | https://www.cafetaria-heyendaalseweg.nl/ | automatisch: website niet uit te lezen, liever geen halve gegevens (scan 24-10-2026) |
| Corry | http://snackbarcorry.placeweb.site | automatisch: website niet uit te lezen, liever geen halve gegevens (scan 24-10-2026) |
| Martin's Place | https://martinsplace.nl | automatisch: website niet uit te lezen, liever geen halve gegevens (scan 24-10-2026) |
| New Point | https://www.new-point-nijmegen.nl/ | automatisch: website niet uit te lezen, liever geen halve gegevens (scan 24-10-2026) |
| Pronto Pizzaservice | https://www.prontonijmegen.nl/ | automatisch: website niet uit te lezen, liever geen halve gegevens (scan 24-10-2026) |
| Sam Sam | https://www.cafetaria-samsam-nijmegen.nl/ | automatisch: website niet uit te lezen, liever geen halve gegevens (scan 24-10-2026) |
| Spare Rib Express Nijmegen | https://www.spareribexpress.com/menu/nijmegen/ | automatisch: website niet uit te lezen, liever geen halve gegevens (scan 24-10-2026) |
| SushiPoint | https://www.sushipoint.nl/ | automatisch: website niet uit te lezen, liever geen halve gegevens (scan 24-10-2026) |
| Ugala | https://www.ugala.nl | automatisch: te weinig informatie op de eigen website (scan 24-10-2026) |
| Vlaams Friteshuis Loket 13 | http://www.loket13nijmegen.nl | automatisch: website niet uit te lezen, liever geen halve gegevens (scan 24-10-2026) |
| Çiçek | https://www.ciceknijmegen.nl/ | automatisch: website niet uit te lezen, liever geen halve gegevens (scan 24-10-2026) |

## 4. Hoort bij een andere categorie

| Bedrijf | Website | Volgens de scan |
|---|---|---|
| Bollyfoods | http://www.bollyfoods.nl/ | hoort bij Catering (scan 24-10-2026) |

## 5. Website werkt niet

| Bedrijf | Website | Uitkomst |
|---|---|---|
| Big Bread Kitchen | https://www.bigbreadnijmegen.nl/ | pagina bestaat niet (404) |
| Cafetaria De Fest | https://cafetaria-de-fest.business.site/ | pagina bestaat niet (404) |
| Cafetaria Waterkwartier🍟 | http://www.cafetaria-waterkwartier.nl/ | domein bestaat niet |
| Dabba Dinner | http://www.dabbadinner.nl/ | domein bestaat niet |
| Fama Costa | http://www.fama-costa-pizzeria-grillroom.nl/ | domein bestaat niet |

## 6. Fout bij het scannen (wordt bij de volgende scan opnieuw geprobeerd)

_Geen._

## 7. Meteen niet meegenomen bij het verzamelen

Permanent gesloten volgens Overture, of zonder eigen website. De lijst staat in `advies/osm-bedrijvengids/afhaal-uitgefilterd.csv`.

| Bedrijf | Adres | Reden |
|---|---|---|
| Cafetaria "van Brenk" | Van Peltlaan 197 | permanent gesloten volgens Overture |
| Cafetaria Hanek | Arend Noorduijnstraat 34 | permanent gesloten volgens Overture |
| Cafetaria/ Lunchroom Diva | Broekstraat 39 | permanent gesloten volgens Overture |
| Chicken Nijmegen | Hertogstraat 10 | permanent gesloten volgens Overture |
| Kiosk Hunnerpark | Sint Jorisstraat 35 | permanent gesloten volgens Overture |
| Pizzeria Cafetaria La Bella | Wolfskuilseweg 99 | permanent gesloten volgens Overture |
| The Green Table Store | Moeflonstraat 18 | permanent gesloten volgens Overture |
| Étumé | Daalseweg 5 | permanent gesloten volgens Overture |
