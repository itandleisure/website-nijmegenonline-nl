# Datacheck lunchrooms (23 oktober 2026)

Zelfde aanpak als bij de restaurants. Van de 212 gevonden zaken staan er nu **56 lunchrooms** in de gids, met een
concepttekst op basis van hun eigen site. Daar komt De Bruijn bij als uitgelichte partner. Er zijn 21 zaken bij die bij de restaurantscan al als lunchroom
herkend waren. Van 45 zaken zegt de scan dat ze eigenlijk een café of een koffiebar zijn. Die komen terug bij die categorieën.

## Beslissingen voor Frans

Mijn voorstel staat erbij. Zeg "akkoord", of noem wat je anders wilt.

**A. Verwijderen**

1. Golestan: op die website en dat adres zit nu Café De Plak, en die staat al bij de restaurants. Het is dus dubbel.

**B. Adres aanpassen naar hun eigen site**

| Bedrijf | Bij ons | Op hun site |
|---|---|---|
| BLUF Nijmegen | 95, Van Welderenstraat | Van Welderenstraat 95 |
| DROOM de Boekweit | Boekweitweg 4 | Boekweit 4 |
| Zeezicht | Marikenstraat 42 | Marikenstraat 46-48 |
| Museumcafé (De Bastei) | (geen adres) | Lange Baan 4, 6511 XJ |

**C. Overig**

2. Sportcafé The Yard (campus): onze link gaat naar de algemene horecapagina van de Radboud. Voorstel: de link naar hun eigen pagina zetten (ru.nl/diensten/eten-en-drinken/the-yard) en de naam aanpassen naar Sportsbar The Yard.

**D. Twijfelachtige kenmerken: weghalen**

| Bedrijf | Kenmerk | Waarom twijfel |
|---|---|---|
| Lunchbar de Viking | groepen | alleen "reserveren vanaf 6 personen" |
| Brood Op de Plank | terras, ontbijt | staan alleen in Instagram-berichten op de site |

---

## Besluit van Frans (23 oktober 2026)

Uitgevoerd: Golestan en Sportcafé The Yard zijn verwijderd, de vier adressen staan in `data/bedrijvengids-correcties.json` en de twijfelachtige kenmerken zijn weg. Resultaat: 54 lunchrooms, plus De Bruijn als partner.

## Samenvatting

|  | Aantal |
|---|---|
| Gevonden in oude gids, OpenStreetMap en Overture | 212 |
| Meteen niet meegenomen: geen website | 44 |
| Meteen niet meegenomen: onzekere bron | 8 |
| Meteen niet meegenomen: hoort bij een andere categorie | 3 |
| Meteen niet meegenomen: geen eigen website | 2 |
| Meteen niet meegenomen: permanent gesloten volgens Overture | 2 |
| Website werkt niet | 8 |
| Automatisch verwijderd na de scan | 44 |
| Hoort bij een andere categorie (komt daar later terug) | 45 |
| Fout bij het scannen | 0 |
| Nog niet gescand | 0 |
| **In de gids, met tekst als concept** | 56 |

## 1. Adres op hun eigen site wijkt af

| Bedrijf | Bij ons | Op hun site |
|---|---|---|
| BLUF Nijmegen | 95, Van Welderenstraat, 6511 ME | Van Welderenstraat 95, 6511 ME Nijmegen |
| DROOM de Boekweit | Boekweitweg 4, 6534 AC | Boekweit 4, 6534 AC Nijmegen |
| Philipse | Sint Stevenskerkhof 44, 6511 VZ | St. Stevenskerkhof 44, 6511VZ Nijmegen |
| Zeezicht | Marikenstraat 42, 6511 PX | Marikenstraat 46-48, 6511 PX Nijmegen |

## 2. Opmerkingen uit de scan (twijfel over kenmerken, openingstijden of of ze open zijn)

| Bedrijf | Opmerking |
|---|---|
| Atelier | Het gaat om Atelier Bar & Hotel: een all-day bar (brunch, barfood en borrel) met een boutiquehotel erboven. Het hotel past in geen van de categorieën. Op de homepage staat 'open everyday', maar volgens de contactpagina is de bar van dinsdag tot en met zondag open. Dat maandag gesloten is, is daarvan afgeleid. Op de homepage staat ook 'new website loading', dus de site wordt mogelijk binnenkort vernieuwd. De keuken heet op de site 'bistro-twist'. De site linkt verder naar 'Reformer Pilates & City Sauna' onder 'Explore Nijmegen'. Die pagina heb ik niet gelezen. |
| Brood Op de Plank | Er is alleen overdag een lunchroom met broodjes, soep en koffie, en geen dinerkaart. Daarom heb ik lunch als hoofdcategorie gekozen in plaats van restaurant. Het terras en het ontbijt staan alleen in de Instagram-berichten op de site. Volgens een recent bericht sluit de zaak die week tijdelijk om 14.30 uur. Catering wordt geregeld via de hele organisatie (Het Bakkerscafé) en niet specifiek via deze vestiging. |
| Golestan | De naam bij ons (Golestan) klopt niet met de website: op dit adres en deze site zit Collectief Café de Plak. Graag de naam controleren. Het is een eetcafé met lunch én een dinerkaart, daarom staat de hoofdcategorie op restaurant in plaats van lunchroom. Volgens de site is het café dicht van zondag 25 oktober tot en met maandag 2 november vanwege onderhoud aan het pand. Ze doen ook catering op festivals. |
| Lunchbar de Viking | Ik heb gekozen voor 'lunch' in plaats van 'restaurant': de zaak is alleen overdag open en heeft geen dinerkaart. Het kenmerk 'groepen' heb ik toegevoegd omdat je kunt reserveren vanaf 6 personen, maar een groepsmenu of aparte zaal wordt niet genoemd, dus dat is twijfelachtig. Op de menupagina staat geen uitgebreide kaart, alleen een paar voorbeeldgerechten. |
| Museumcafé | Het café zit in Museum De Bastei, maar het adres stond niet op de pagina die ik heb gelezen. Het adres bij ons is leeg, dus dat moet nog worden aangevuld. De menukaart (PDF) en de contactpagina kon ik niet openen, omdat de limiet voor het ophalen van pagina's bereikt was. Daardoor weet ik niet wat er precies op de kaart staat (lunch, ontbijt, vegan, enzovoort). Volgens de site is het café gesloten op donderdag 8 oktober van 12.30 tot 14.30 uur. Je kunt er alleen pinnen. De catering komt van Pura. |
| Philipse | Ik heb alleen de pagina Philipse Koffie kunnen lezen. Het menu met de high tea en de pagina's over feestjes en reserveren heb ik niet kunnen openen, omdat het maximale aantal opvragingen bereikt was. Daarom heb ik geen kenmerken als ontbijt, vegan of groepen ingevuld en ook geen keuken. De openingstijden staan op de site in losse kolommen (een dagenlijst en een tijdenlijst). Ik heb ze zo gekoppeld dat maandag gesloten is. In de footer staat ook Philipse Suite op Achter de Smidstraat 5; dat lijkt een apart onderdeel van het bedrijf. |
| Puck Specialty Coffee | Het online menu is van lente 2023 (Menu-lente-2023.pdf) en is daardoor mogelijk verouderd. Op de site staan ook wijn en bier, en in de meta-keywords wordt 'borrel' genoemd. De pagina met workshops (product_cat=workshops) heb ik niet gelezen. |
| Puux | Op de homepage staat een icoon met 'dinner', maar de openingstijden zijn tot 17:00, dus diner is niet aannemelijk. Een terras wordt alleen in Google-recensies genoemd en niet door de site zelf, daarom is het niet als kenmerk opgenomen. De menukaart was niet als aparte pagina te lezen. De soep van de week op de site (5 t/m 11 maart) is verouderd. Openingstijden: de site verwijst naar Google voor de actuele tijden. |
| Sportcafé The Yard | De link verwijst naar de algemene horecapagina van de Radboud Universiteit. De pagina van The Yard zelf staat op ru.nl/diensten/eten-en-drinken/the-yard. Op de site heet de zaak 'Sportsbar The Yard'. Overdag zijn er broodjes en koffie, maar het accent ligt op de sportbar met bier, pool en live sport. Daarom staat de hoofdcategorie op 'cafe' in plaats van lunchroom. Het terras is een dakterras. Tussen 21 december 2026 en 3 januari 2027 is de zaak gesloten. |

## 3. Automatisch verwijderd na de scan

| Bedrijf | Website | Reden |
|---|---|---|
| 't Marikenpaleis | http://www.marikenpaleis.nl/ | automatisch: te weinig informatie op de eigen website (scan 23-10-2026) |
| Anytyme Zwanenveld | http://www.anytyme.nl/Cafetarias/AnyTyme-Zwanenveld-anytime-is-snacktime.htm | automatisch: te weinig informatie op de eigen website (scan 23-10-2026) |
| Bagels & Beans | http://www.bagelsbeans.nl/winkel_nijmegen_hezelstraat.shtml | automatisch: website niet uit te lezen, liever geen halve gegevens (scan 23-10-2026) |
| Bij Bosshardt, Nijmegen | http://www.legerdesheils.nl/ | automatisch: te weinig informatie op de eigen website (scan 23-10-2026) |
| Billy's Coffee | https://billy.coffee/ | automatisch: gestopt of verhuisd volgens de eigen website (scan 23-10-2026) |
| Blommers Coffee Brewers | http://www.blommersbrewers.nl/ | automatisch: website niet uit te lezen, liever geen halve gegevens (scan 23-10-2026) |
| Blommers Coffee Brewers | https://www.blommersbrewers.nl/ | automatisch: website niet uit te lezen, liever geen halve gegevens (scan 23-10-2026) |
| Boerske | http://www.boerske.nl | automatisch: website niet uit te lezen, liever geen halve gegevens (scan 23-10-2026) |
| Bustro | https://www.bustro.nl/ | automatisch: gestopt of verhuisd volgens de eigen website (scan 23-10-2026) |
| Café De Kroon | http://www.cafe-dekroon.nl/ | automatisch: website niet uit te lezen, liever geen halve gegevens (scan 23-10-2026) |
| Café Frowijn | http://www.cafefrowijn.nl | automatisch: website niet uit te lezen, liever geen halve gegevens (scan 23-10-2026) |
| Café Hop en Heivuur | https://hopenheivuur.nl/ | automatisch: te weinig informatie op de eigen website (scan 23-10-2026) |
| Café Restaurant Merkus | http://www.cafezaalmerkus.nl/ | automatisch: website niet uit te lezen, liever geen halve gegevens (scan 23-10-2026) |
| Café Sjors en Sjimmie | http://www.cafesjorsensjimmie.nl/ | automatisch: website niet uit te lezen, liever geen halve gegevens (scan 23-10-2026) |
| CALI Nijmegen | http://www.bar-cali.nl/ | automatisch: website niet uit te lezen, liever geen halve gegevens (scan 23-10-2026) |
| Coffeelovers | http://www.coffeelovers.nl/locaties/marienburg-nijmegen | automatisch: gestopt of verhuisd volgens de eigen website (scan 23-10-2026) |
| Coffeeshop 24 7 Nijmegen | http://www.tkunsje.com/ | automatisch: te weinig informatie op de eigen website (scan 23-10-2026) |
| Coffeeshop-Buggy | http://www.buggycoffeeshop.nl/ | automatisch: te weinig informatie op de eigen website (scan 23-10-2026) |
| Dakota Nijmegen | http://www.coffeeshop.freeuk.com/dakota.html | automatisch: website niet uit te lezen, liever geen halve gegevens (scan 23-10-2026) |
| Delimore | https://bestellen2.vissersenergygroup.nl/locaties/esso-vissers-nijmegen/bezorgmethode?utm_source=google&utm_medium=zoekresultaat&utm_campaign=GoogleMBNijmegen | automatisch: website niet uit te lezen, liever geen halve gegevens (scan 23-10-2026) |
| Eetcafe poort van nijmegen | http://www.centrumnijmegen.nl/eten-en-drinken/eetcafes/eetcafe-poort-van-nijmegen | automatisch: website niet uit te lezen, liever geen halve gegevens (scan 23-10-2026) |
| Eethuis Centraal | https://eethuiscentraal.nl/ | automatisch: te weinig informatie op de eigen website (scan 23-10-2026) |
| Gesha Coffee Bar | http://Gesha.nl/ | automatisch: te weinig informatie op de eigen website (scan 23-10-2026) |
| Gladius Koffie | https://www.gladiuskoffie.nl/ | automatisch: website niet uit te lezen, liever geen halve gegevens (scan 23-10-2026) |
| Hete kip op locatie | http://www.hetekipoplocatie.nl/ | automatisch: website niet uit te lezen, liever geen halve gegevens (scan 23-10-2026) |
| Kaketoe Biljart | http://www.kaketoebiljart.nl/ | automatisch: gestopt of verhuisd volgens de eigen website (scan 23-10-2026) |
| Koffie Van Kai - Koffie, Training En Machines. Op De Zaak Én Bij Jouw Thuis. | https://www.koffievankai.nl/ | automatisch: website niet uit te lezen, liever geen halve gegevens (scan 23-10-2026) |
| Kollektief Kafee Bijstand | http://www.debijstand.nl/ | automatisch: website niet uit te lezen, liever geen halve gegevens (scan 23-10-2026) |
| Kronkel Nijmegen | http://www.kronkel.nl | automatisch: te weinig informatie op de eigen website (scan 23-10-2026) |
| Le Duc | http://www.brasserieleduc.nl/ | automatisch: website niet uit te lezen, liever geen halve gegevens (scan 23-10-2026) |
| Manetti Espresso | http://www.manetti.nl/ | automatisch: te weinig informatie op de eigen website (scan 23-10-2026) |
| Ons Thuis | https://onsthuisnijmegen.nl | automatisch: website niet uit te lezen, liever geen halve gegevens (scan 23-10-2026) |
| ROC Nijmegen Het Café | https://www.roc-nijmegen.nl/het-cafe | automatisch: website niet uit te lezen, liever geen halve gegevens (scan 23-10-2026) |
| Stadscafé Jan | http://www.stadscafejan.nl/ | automatisch: website niet uit te lezen, liever geen halve gegevens (scan 23-10-2026) |
| Subway | https://restaurants.subway.com/netherlands/nijmegen/arend-noorduijnstraat-24 | automatisch: website niet uit te lezen, liever geen halve gegevens (scan 23-10-2026) |
| Subway | https://restaurants.subway.com/netherlands/nijmegen/zwanenveld-8405?utm_source=yxt-bing&utm_medium=local&utm_term=acq&utm_content=52922&utm_campaign=evergreen-2020&y_source=1_MTQ5MjUyMTMtNDgzLWxvY2F0aW9uLndlYnNpdGU%3D | automatisch: website niet uit te lezen, liever geen halve gegevens (scan 23-10-2026) |
| Subway Oosterhout Park15 | http://Www.subway.com/ | automatisch: te weinig informatie op de eigen website (scan 23-10-2026) |
| The Tosti Club | https://thetosticlub.nl | automatisch: te weinig informatie op de eigen website (scan 23-10-2026) |
| Theehuis de Goffert | http://www.theehuisdegoffert.nl/ | automatisch: website niet uit te lezen, liever geen halve gegevens (scan 23-10-2026) |
| Theeschenkerij de Goffert | http://www.theeschenkerijdegoffert.nl/ | automatisch: gestopt of verhuisd volgens de eigen website (scan 23-10-2026) |
| ThiemeFoyer | https://thiemeloods.nl/eten-en-drinken/ | automatisch: website niet uit te lezen, liever geen halve gegevens (scan 23-10-2026) |
| Van Hilst Koffie en Thee | http://www.vanhilst.com/ | automatisch: gestopt of verhuisd volgens de eigen website (scan 23-10-2026) |
| Van Hilst Koffie en Thee | http://www.vanhilst.com/ | automatisch: gestopt of verhuisd volgens de eigen website (scan 23-10-2026) |
| Wakuli | https://wakuli.com | automatisch: te weinig informatie op de eigen website (scan 23-10-2026) |

## 4. Hoort bij een andere categorie

| Bedrijf | Website | Volgens de scan |
|---|---|---|
| Aangenaam Aleppo | https://www.aangenaamaleppo.nl/ | hoort bij Koffiebars (scan 23-10-2026) |
| Bascafe | http://www.basnijmegen.nl/ | hoort bij Cafés en kroegen (scan 23-10-2026) |
| Bloem ice coffee & more | https://www.bloem-icecoffeeandmore.nl/ | hoort bij IJssalons (scan 23-10-2026) |
| Blommers Coffee | http://www.blommers.coffee/ | hoort bij Koffiebars (scan 23-10-2026) |
| Blommers Coffee | https://www.blommers.coffee/nl/ | hoort bij Koffiebars (scan 23-10-2026) |
| Cafe Daen | http://www.cafedaen.nl/ | hoort bij Cafés en kroegen (scan 23-10-2026) |
| Cafe Pool | http://www.cafepool.nl/ | hoort bij Cafés en kroegen (scan 23-10-2026) |
| Cafe St. Anneke | http://www.stanneke.nl/ | hoort bij Cafés en kroegen (scan 23-10-2026) |
| Café de Aesculaaf | http://www.aesculaaf.nl/ | hoort bij Cafés en kroegen (scan 23-10-2026) |
| Café de Burgemeester | https://cafeburgemeester.nl | hoort bij Cafés en kroegen (scan 23-10-2026) |
| Café Faber | http://www.cafefaber.nl/ | hoort bij Cafés en kroegen (scan 23-10-2026) |
| Café Piet Huisman | http://www.piethuisman.nl/ | hoort bij Cafés en kroegen (scan 23-10-2026) |
| Café Velocitas | https://velorama.nl/cafe-velocitas | hoort bij Koffiebars (scan 23-10-2026) |
| Café Wunderkammer | http://www.cafewunderkammer.nl/ | hoort bij Cafés en kroegen (scan 23-10-2026) |
| Coffeeted | https://www.coffeeted.nl/ | hoort bij Koffiebars (scan 23-10-2026) |
| Cultuurcafé | https://www.ru.nl/services/eten-en-drinken/cultuurcafe | hoort bij Cafés en kroegen (scan 23-10-2026) |
| De Paljas | https://depaljas.nl | hoort bij Cafés en kroegen (scan 23-10-2026) |
| De Professor | http://www.cafe-deprofessor.nl/ | hoort bij Snackbars en afhaal (scan 23-10-2026) |
| De Witte Raaf - Bordspellencafé | https://dewitteraafbordspellen.nl/ | hoort bij Cafés en kroegen (scan 23-10-2026) |
| Drie Gezusters Nijmegen | http://www.driegezustersnijmegen.nl/ | hoort bij Cafés en kroegen (scan 23-10-2026) |
| Filosofisch Café Nijmegen | http://www.filosofisch-cafe.nl/ | hoort bij Theaters en poppodia (scan 23-10-2026) |
| Foodservice Royale | http://www.cateringroyale.nl | hoort bij Catering (scan 23-10-2026) |
| Glitch | https://barglitch.nl | hoort bij Cocktailbars (scan 23-10-2026) |
| Het Theezaakje | http://www.het-theezaakje.nl | hoort bij Koffiebars (scan 23-10-2026) |
| Holy Beans | http://www.holybeans.nl/ | hoort bij Koffiebars (scan 23-10-2026) |
| Karaoke Cafe van Deelen | http://cafevandeelen.nl/ | hoort bij Cafés en kroegen (scan 23-10-2026) |
| Koffiebarhuren | http://koffiebarhuren.nl/ | hoort bij Catering (scan 23-10-2026) |
| Le Café | http://www.lecafenijmegen.nl/ | hoort bij Cafés en kroegen (scan 23-10-2026) |
| Lima Nijmegen | https://lima-nijmegen.nl/ | hoort bij Cocktailbars (scan 23-10-2026) |
| Matcha Boutique | https://matchanijmegen.nl/ | hoort bij Koffiebars (scan 23-10-2026) |
| McCafé | https://mcdonaldsrestaurant.nl/nijmegen-novium | hoort bij Koffiebars (scan 23-10-2026) |
| Meneer Otis | https://meneerotis.nl/ | hoort bij Theaters en poppodia (scan 23-10-2026) |
| Mr. Sushi & Miss Wok Nijmegen | http://www.mrsushi.nl/ | hoort bij Snackbars en afhaal (scan 23-10-2026) |
| MÖGE TEE | https://www.mogetee.nl | hoort bij Koffiebars (scan 23-10-2026) |
| Old Cave Nijmegen | http://www.oldcave.nl/ | hoort bij Zalen en locaties (scan 23-10-2026) |
| Panama | https://www.ru.nl/services/eten-en-drinken/de-refter | hoort bij Koffiebars (scan 23-10-2026) |
| Roxy’s tikibar | https://roxystikibar.nl | hoort bij Cocktailbars (scan 23-10-2026) |
| Royal | http://www.royaletendrinken.nl/ | hoort bij Cafés en kroegen (scan 23-10-2026) |
| Science Café Nijmegen | https://www.sciencecafenijmegen.nl/ | hoort bij Theaters en poppodia (scan 23-10-2026) |
| Song da street food | https://online.byonesix.com/song-da-streetfood-nijmegen/ | hoort bij Snackbars en afhaal (scan 23-10-2026) |
| Starbucks | https://www.starbucks.nl | hoort bij Koffiebars (scan 23-10-2026) |
| Strik Patisserie | https://www.strik-patisserie.nl | hoort bij Bakkerijen (scan 23-10-2026) |
| Strik Patisserie | https://strik-patisserie.nl/contact/ | hoort bij Bakkerijen (scan 23-10-2026) |
| Waalzicht | http://www.cafewaalzicht.nl/ | hoort bij Cafés en kroegen (scan 23-10-2026) |
| Zorgcafé Looppunt | http://www.looppunt-nijmegen.nl/ | hoort bij Fysiotherapie (scan 23-10-2026) |

## 5. Website werkt niet

| Bedrijf | Website | Uitkomst |
|---|---|---|
| A Tazza Rima Thee, Koffie & Meer. | http://www.atazza-rima.nl/ | domein bestaat niet |
| Broodje Horeca | http://www.broodje-horeca.nl/ | pagina bestaat niet (404) |
| Broodje Maxima | http://www.broodjemaxima.nl/ | domein bestaat niet |
| Café The Templar | http://www.cafedetempelier.com | domein bestaat niet |
| Louis | http://www.louisnijmegen.nl/ | domein bestaat niet |
| Phocas Over The Top | http://www.nsrvphocas.nl/ | domein bestaat niet |
| Piccolino Patathuisje | http://www.piccolinonijmegen.nl/ | domein bestaat niet |
| Thuis bij Inge | http://www.thuisbijinge.nl/ | domein bestaat niet |

## 6. Fout bij het scannen (wordt bij de volgende scan opnieuw geprobeerd)

_Geen._

## 7. Meteen niet meegenomen bij het verzamelen

Permanent gesloten volgens Overture, of zonder eigen website. De lijst staat in `advies/osm-bedrijvengids/lunch-uitgefilterd.csv`.

| Bedrijf | Adres | Reden |
|---|---|---|
| De Broodzaak Nijmegen | Stationsplein 6A | permanent gesloten volgens Overture |
| Ketelhuis Lent | Thermionpark 30 | permanent gesloten volgens Overture |
