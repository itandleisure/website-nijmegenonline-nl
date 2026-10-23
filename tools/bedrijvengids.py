"""Bedrijvengids: de categorieën in CATEGORIEEN, met een pagina per categorie en per bedrijf.

Bronnen per categorie:
- de oude Listdom-gids uit de WordPress-export (bedrijvengids-listdom.xml): eigen tekst, foto, openingstijden
- OpenStreetMap/Overture (advies/osm-bedrijvengids/<bron_csv>, gemaakt met tools/bronnen_verzamelen.py): de overige bedrijven

Pakketten (Uitgelicht, Partner, Hoofdpartner) staan in data/bedrijvengids-pakketten.json; een verlopen pakket
valt bij de dagelijkse herbouw (.github/workflows/agenda.yml) vanzelf terug naar gratis.

Gebruik: python tools/bedrijvengids.py [/mnt/project-files]
Schrijft data/bedrijvengids.json en de pagina's onder bedrijvengids/ en bedrijvengids-categorie/. Zonder de
bronbestanden (zoals op GitHub) bouwt het de pagina's opnieuw uit data/bedrijvengids.json.
"""
import csv
import datetime
import html
import json
import random
import pathlib
import re
import shutil
import sys
import unicodedata
import urllib.parse
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from import_wordpress import DOORVERWIJZING, SITE, VOET, esc, kop, samenvatting, schoon  # noqa: E402

NS = {"wp": "http://wordpress.org/export/1.2/", "content": "http://purl.org/rss/1.0/modules/content/"}
BETAALD = ("uitgelicht", "partner", "hoofdpartner")
MAX_UITGELICHT = 3
DAGEN = ["maandag", "dinsdag", "woensdag", "donderdag", "vrijdag", "zaterdag", "zondag"]
SCHEMA_DAG = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

CATEGORIEEN = [{
    "slug": "sportschool",
    "listdom": {"sportschool"},
    "bron_csv": "sportscholen-aangevuld.csv",
    "naam": "Sportscholen in Nijmegen",
    "enkelvoud": "Sportschool",
    "groep": "Sport en beweging",
    "soorten": {"Sportschool en fitness", "Personal training en bootcamp"},
    "schema": "ExerciseGym",
    "beschrijving": "Alle sportscholen in Nijmegen op een rij: van grote ketens tot kleine studio's voor personal "
                    "training, met adressen, openingstijden en tips om de juiste te kiezen.",
    "intro": "<p>Nijmegen is een echte sportstad. Met de Radboud Universiteit, de HAN en een flinke groep jonge "
             "inwoners is het aanbod aan sportscholen groot: van 24-uursketens aan de rand van de stad tot kleine "
             "studio's in het centrum waar je met een personal trainer werkt.</p>"
             "<p>Op deze pagina vind je alle sportscholen in Nijmegen. Bovenaan staan de sportscholen uit onze "
             "bedrijvengids, met openingstijden en een eigen pagina. Daaronder de complete lijst op alfabet.</p>",
    "faq": [
        ("Wat kost een sportschool in Nijmegen?",
         "Bij de grote ketens betaal je vanaf ongeveer 25 euro per maand. Kleinere sportscholen met begeleiding of "
         "groepslessen zitten vaak tussen de 40 en 70 euro, en personal training reken je meestal per les."),
        ("Welke sportschool in Nijmegen is 24 uur open?",
         "Een paar ketens hebben vestigingen die dag en nacht open zijn, vaak met een pas waarmee je buiten de "
         "bemande uren binnenkomt. Kijk bij de vestiging zelf welke uren gelden."),
        ("Kan ik eerst een proefles doen?",
         "Bijna alle sportscholen in Nijmegen bieden een gratis proefles of proefweek aan. Zo zie je of de sfeer, "
         "de drukte en de begeleiding bij je passen voordat je een abonnement afsluit."),
    ],
    "artikelen": ["bammmm-en-je-bent-fit", "afvallen-met-sport-tips-voor-een-kleinere-maat", "7x-de-beste-warming-up-oefeningen"],
    # Blogberichten over het onderwerp: daaronder komt het blok met de uitgelichte bedrijven (onderdeel van Uitgelicht)
    "blogs": ["bammmm-en-je-bent-fit", "afvallen-met-sport-tips-voor-een-kleinere-maat", "7x-de-beste-warming-up-oefeningen",
              "hoe-kan-een-dietist-je-helpen-gezonder-te-gaan-leven"],
    "meervoud": "sportscholen",
    "blogonderwerp": "sport en gezondheid",
    "filtervoorbeeld": "groepslessen of een proefles",
    "voorbeeld": {"naam": "Jouw sportschool", "foto": "assets/uploads/2022/11/sporten-in-nijmegen-533x400.webp",
                  "kenmerken": ["proefles", "groepslessen"], "actie": "Eerste maand gratis sporten"},
    "knop_voorbeeld": "proefles, inschrijven, bellen",
}, {
    "slug": "restaurant",
    # Oude Listdom-categorieën voor restaurants; die url's sturen door naar deze categorie (zie main)
    "listdom": {"diner", "all-you-can-eat-restaurant", "pannenkoek-restaurant", "indiaas-restaurant", "pizzeria",
                "steak-restaurant", "zuid-amerikaans-restaurant", "michelin-restaurant", "italiaans-restaurant",
                "veganistisch", "vegetarisch"},
    "bron_csv": "restaurant-aangevuld.csv",
    "plaatsen": {"Nijmegen", "Lent", "Oosterhout"},
    "naam": "Restaurants in Nijmegen",
    "enkelvoud": "Restaurant",
    "de_woord": False,
    "groep": "Eten en drinken",
    "soorten": {"Restaurant"},
    "schema": "Restaurant",
    "beschrijving": "Alle restaurants in Nijmegen op een rij: van Italiaans en Japans tot Hollandse pot en vegan, met "
                    "adressen, openingstijden, terrassen en een kaart.",
    "intro": "<p>Uit eten in Nijmegen? De oudste stad van Nederland heeft een keuken voor elk moment: een snelle hap in "
             "de Lange Hezelstraat, sushi op de Molenstraat, een terras aan de Waalkade of een avond tafelen in een "
             "van de restaurants rond de Grote Markt.</p>"
             "<p>Op deze pagina vind je alle restaurants in Nijmegen.</p>",
    "faq": [
        ("Waar kun je in Nijmegen op een terras eten?",
         "De meeste terrassen vind je in het centrum: op de Grote Markt, de Waalkade, in de Lange Hezelstraat en rond "
         "het Kelfkensbos. Filter op deze pagina op terras voor de restaurants die er zelf een noemen."),
        ("Waar kun je vegan eten in Nijmegen?",
         "Steeds meer restaurants in Nijmegen hebben vegan gerechten op de kaart, en er zijn ook volledig plantaardige "
         "zaken. Filter op vegan om ze te zien."),
        ("Moet ik reserveren?",
         "In het weekend en bij kleinere restaurants is reserveren verstandig. Bij de meeste zaken kan dat online via "
         "hun eigen website of telefonisch."),
    ],
    "artikelen": ["de-10-beste-restaurants-in-nijmegen-centrum", "betaalbaar-uit-eten-in-nijmegen-zo-doe-je-dat",
                  "waar-kun-je-het-best-vegan-uit-eten-in-nijmegen", "uit-eten-met-kinderen-in-nijmegen-deze-locaties-mag-je-niet-missen"],
    "blogs": ["de-10-beste-restaurants-in-nijmegen-centrum", "betaalbaar-uit-eten-in-nijmegen-zo-doe-je-dat",
              "waar-kun-je-het-best-vegan-uit-eten-in-nijmegen", "uit-eten-met-kinderen-in-nijmegen-deze-locaties-mag-je-niet-missen",
              "exclusief-dineren-in-nijmegen-wat-kan-je-verwachten", "culinair-genieten-in-italiaanse-sfeer-probeer-deze-restaurants-in-nijmegen",
              "geniet-van-de-hollandse-pot-in-deze-nederlandse-restaurants-in-nijmegen", "indias-culinaire-parels-toprestaurants-in-nijmegen",
              "laat-je-culinair-verrassen-in-chinese-sfeer-de-beste-restaurants-in-nijmegen", "mexicaans-genieten-in-nijmegen-dit-zijn-de-beste-adresjes",
              "op-culinaire-ontdekkingsreis-probeer-deze-griekse-restaurants-in-nijmegen",
              "op-zoek-naar-een-nieuwe-culinaire-belevenis-probeer-libanees-eten-in-nijmegen",
              "op-zoek-naar-iets-nieuws-probeer-deze-spaanse-restaurants-in-nijmegen", "pannenkoekenrestaurants-in-nijmegen-onze-top-5",
              "pizza-liefhebbers-dit-zijn-de-beste-pizzerias-in-nijmegen", "sushi-liefhebbers-dit-zijn-de-beste-japanse-restaurants-in-nijmegen",
              "tapas-eten-in-nijmegen-hier-kan-je-dat-doen", "thais-eten-in-nijmegen-onze-top-3-thaise-restaurants",
              "waarom-is-een-all-you-can-eat-restaurant-in-nijmegen-een-goede-keuze"],
    "meervoud": "restaurants",
    "blogonderwerp": "uit eten",
    "filtervoorbeeld": "een terras of vegan gerechten",
    "voorbeeld": {"naam": "Jouw restaurant", "foto": "assets/uploads/2022/11/restaurant-eten-in-nijmegen.webp",
                  "kenmerken": ["terras", "vegan"], "actie": "Gratis dessert bij een diner voor twee"},
    "knop_voorbeeld": "reserveren, menukaart, bellen",
}, {
    "slug": "lunch",
    "listdom": {"lunch", "high-tea"},
    "bron_csv": "lunch-aangevuld.csv",
    "plaatsen": {"Nijmegen", "Lent", "Oosterhout"},
    "naam": "Lunchrooms en ontbijt in Nijmegen",
    "enkelvoud": "Lunchroom",
    "groep": "Eten en drinken",
    "soorten": {"Lunchroom"},
    "schema": "CafeOrCoffeeShop",
    "beschrijving": "Lunchen of ontbijten in Nijmegen: alle lunchrooms op een rij, van een broodje op de markt tot "
                    "uitgebreid brunchen, met adressen, openingstijden, terrassen en een kaart.",
    "intro": "<p>Even pauze tijdens het shoppen, uitgebreid brunchen op zondag of een snelle lunch tussen twee colleges door? "
             "In Nijmegen zit je nooit ver van een goede lunchroom: rond de Grote Markt en de Hertogstraat, in de "
             "Benedenstad aan het water, maar ook in Oost, Lent en op de campus.</p>"
             "<p>Op deze pagina vind je alle lunchrooms in Nijmegen.</p>",
    "faq": [
        ("Waar kun je goed brunchen in Nijmegen?",
         "Veel lunchrooms in Nijmegen serveren in het weekend een uitgebreid ontbijt of brunch. Filter op ontbijt om "
         "de zaken te zien die dat zelf op hun site noemen."),
        ("Waar kun je in Nijmegen op een terras lunchen?",
         "In het centrum vind je terrassen op de Grote Markt, het Kelfkensbos en de Waalkade. Filter op terras voor de "
         "lunchrooms die er zelf een hebben."),
        ("Kan ik vegan lunchen in Nijmegen?",
         "Ja, steeds meer lunchrooms hebben vegan broodjes, bowls of taart. Filter op vegan om ze te vinden."),
    ],
    "artikelen": ["lekker-lunchen-in-nijmegen-dit-zijn-de-beste-plekjes", "hapje-eten-en-drinken-in-nijmegen",
                  "op-zoek-naar-de-beste-high-tea-locaties-in-nijmegen-5-tips-waar-je-meteen-enthousiast-van-wordt"],
    "blogs": ["lekker-lunchen-in-nijmegen-dit-zijn-de-beste-plekjes", "hapje-eten-en-drinken-in-nijmegen",
              "op-zoek-naar-de-beste-high-tea-locaties-in-nijmegen-5-tips-waar-je-meteen-enthousiast-van-wordt"],
    "meervoud": "lunchrooms",
    "blogonderwerp": "lunchen en ontbijten",
    "filtervoorbeeld": "een terras of vegan lunch",
    "voorbeeld": {"naam": "Jouw lunchroom", "foto": "assets/uploads/2023/04/de-bruijn-lunchen-op-de-markt-terras-768x384.webp",
                  "kenmerken": ["terras", "ontbijt"], "actie": "Gratis koffie bij elke lunch"},
    "knop_voorbeeld": "reserveren, menukaart, bellen",
}, {
    "slug": "cafe",
    "listdom": {"cafe", "borrelen", "cocktailbar"},
    "bron_csv": "cafe-aangevuld.csv",
    "plaatsen": {"Nijmegen", "Lent", "Oosterhout"},
    "naam": "Cafés en kroegen in Nijmegen",
    "enkelvoud": "Café",
    "de_woord": False,
    "groep": "Eten en drinken",
    "soorten": {"Café"},
    "schema": "BarOrPub",
    "beschrijving": "Alle cafés en kroegen in Nijmegen: bruine cafés, biercafés, wijnbars en cocktailbars, met adressen, "
                    "openingstijden, terrassen en een kaart.",
    "intro": "<p>Nijmegen is een echte kroegenstad. Op de Grote Markt en in de Lange Hezelstraat zitten cafés die al eeuwen "
             "meegaan, aan de Waalkade drink je een biertje met uitzicht op de brug, en in Oost en het Benedenstad vind je "
             "kleine buurtcafés met speciaalbier, live muziek of een goed glas wijn.</p>"
             "<p>Op deze pagina vind je alle cafés in Nijmegen.</p>",
    "faq": [
        ("Wat is het oudste café van Nijmegen?",
         "In de Lange Hezelstraat en rond de Grote Markt zitten cafés in panden van eeuwen oud. In ons artikel over de "
         "cafés met de meeste historie lees je welke dat zijn."),
        ("Waar drink je speciaalbier in Nijmegen?",
         "Nijmegen heeft verschillende biercafés en brouwerijen. Filter op speciaalbier voor de cafés die zelf een uitgebreide "
         "bierkaart noemen."),
        ("Waar kun je in Nijmegen op een terras zitten?",
         "Op de Grote Markt, de Waalkade en het Kelfkensbos zitten de grootste terrassen. Filter op terras voor de cafés die er een hebben."),
    ],
    "artikelen": ["de-7-cafes-met-de-meeste-historie-van-nijmegen", "de-7-gezelligste-cafes-buiten-het-centrum-van-nijmegen",
                  "de-8-beste-biercafes-van-nijmegen", "lekker-uitgaan-in-nijmegen-hier-doe-je-dat"],
    "blogs": ["de-7-cafes-met-de-meeste-historie-van-nijmegen", "de-7-gezelligste-cafes-buiten-het-centrum-van-nijmegen",
              "de-8-beste-biercafes-van-nijmegen", "de-dit-zijn-de-6-leukste-eetcafes-van-nijmegen",
              "lekker-uitgaan-in-nijmegen-hier-doe-je-dat", "happen-stappen-in-nijmegen-een-wereld-aan-mogelijkheden"],
    "meervoud": "cafés",
    "blogonderwerp": "cafés en uitgaan",
    "filtervoorbeeld": "een terras, live muziek of speciaalbier",
    "voorbeeld": {"naam": "Jouw café", "foto": "assets/uploads/2022/12/biercafe-in-nijmegen-533x400.webp",
                  "kenmerken": ["terras", "speciaalbier"], "actie": "Elke donderdag het tweede biertje gratis"},
    "knop_voorbeeld": "reserveren, agenda, bellen",
}, {
    "slug": "koffiezaak",
    "listdom": {"koffiezaak"},
    "bron_csv": "koffiezaak-aangevuld.csv",
    "plaatsen": {"Nijmegen", "Lent", "Oosterhout"},
    "naam": "Koffiebars in Nijmegen",
    "enkelvoud": "Koffiebar",
    "groep": "Eten en drinken",
    "soorten": {"Koffiebar"},
    "schema": "CafeOrCoffeeShop",
    "beschrijving": "Alle koffiebars in Nijmegen op een rij: specialty coffee, eigen branderijen en plekken om te werken, "
                    "met adressen, openingstijden en een kaart.",
    "intro": "<p>Op zoek naar een goede flat white of een rustige plek om even te werken? Nijmegen heeft een groeiend aantal "
             "koffiebars: van kleine specialty-zaken in de binnenstad tot branderijen waar je de bonen ter plekke ziet "
             "branden.</p>"
             "<p>Op deze pagina vind je alle koffiebars in Nijmegen.</p>",
    "faq": [
        ("Waar drink je de beste koffie in Nijmegen?",
         "Dat is een kwestie van smaak, maar de specialty-koffiebars in de binnenstad en in Oost hebben een goede naam. "
         "Filter op eigen branderij voor de zaken die zelf hun bonen branden."),
        ("Waar kun je in Nijmegen werken met je laptop?",
         "Verschillende koffiebars hebben wifi en plekken om te werken. Filter op werkplek om ze te vinden."),
        ("Is een coffeeshop hetzelfde als een koffiebar?",
         "Nee. In Nederland verkoopt een coffeeshop cannabis. In dit overzicht staan alleen koffiebars waar je voor koffie komt."),
    ],
    "artikelen": ["barista-training-in-nijmegen-word-koffie-expert-2", "het-belang-van-goede-koffie-op-het-werk"],
    "blogs": ["barista-training-in-nijmegen-word-koffie-expert-2", "het-belang-van-goede-koffie-op-het-werk"],
    "meervoud": "koffiebars",
    "blogonderwerp": "koffie",
    "filtervoorbeeld": "een werkplek of taart",
    "voorbeeld": {"naam": "Jouw koffiebar", "foto": "assets/uploads/2023/11/barista-training-in-nijmegen-533x400.webp",
                  "kenmerken": ["werkplek", "taart en gebak"], "actie": "Tweede cappuccino gratis"},
    "knop_voorbeeld": "menukaart, route, bellen",
}, {
    "slug": "marketingbureau",
    "listdom": {"marketingbureau", "reclamebureau"},
    "bron_csv": "marketingbureau-aangevuld.csv",
    "plaatsen": {"Nijmegen", "Lent", "Oosterhout"},
    "naam": "Marketing-, reclame- en webbureaus in Nijmegen",
    "enkelvoud": "Bureau",
    "de_woord": False,
    "groep": "Zakelijk en diensten",
    "soorten": {"Marketingbureau"},
    "schema": "ProfessionalService",
    "beschrijving": "Marketing-, reclame- en webbureaus in Nijmegen: websites, SEO, social media en branding, met adressen en specialismen.",
    "intro": "<p>Een nieuwe website, beter gevonden worden in Google of een campagne die opvalt? In Nijmegen zitten tientallen "
             "bureaus en freelancers die ondernemers daarbij helpen, van eenpitters in de Honigfabriek tot volledige "
             "reclamebureaus in het centrum.</p>"
             "<p>Op deze pagina vind je alle marketing-, reclame- en webbureaus in Nijmegen.</p>",
    "faq": [
        ("Wat kost een website laten maken in Nijmegen?",
         "Dat verschilt sterk per bureau en per wens. Vraag bij een paar bureaus een offerte op; veel bureaus bieden een gratis kennismaking."),
        ("Hoe kies ik een marketingbureau?",
         "Kijk naar het werk dat ze eerder deden en of ze ervaring hebben in jouw branche. Filter hieronder op wat je zoekt, zoals SEO of social media."),
        ("Werken Nijmeegse bureaus ook voor kleine ondernemers?",
         "Ja. Veel bureaus en freelancers richten zich juist op zzp en mkb; filter op zzp en mkb."),
    ],
    "artikelen": ["5-succesvolle-marketingstrategieen-voor-lokale-bedrijven-in-nijmegen",
                  "op-zoek-naar-originele-en-praktische-manieren-om-je-bedrijf-in-nijmegen-zichtbaar-te-maken",
                  "eindejaar-investeringen-in-seo-profiteer-als-ondernemer-in-nijmegen-van-de-kia-regeling"],
    "blogs": ["5-succesvolle-marketingstrategieen-voor-lokale-bedrijven-in-nijmegen",
              "op-zoek-naar-originele-en-praktische-manieren-om-je-bedrijf-in-nijmegen-zichtbaar-te-maken",
              "eindejaar-investeringen-in-seo-profiteer-als-ondernemer-in-nijmegen-van-de-kia-regeling"],
    "meervoud": "bureaus",
    "blogonderwerp": "marketing en ondernemen",
    "filtervoorbeeld": "websites, SEO of social media",
    "voorbeeld": {"naam": "Jouw bureau", "foto": "assets/uploads/2024/08/5-Succesvolle-Marketingstrategieen-voor-Lokale-Bedrijven-in-Nijmegen-533x400.webp",
                  "kenmerken": ["websites", "SEO"], "actie": "Gratis websitescan voor Nijmeegse ondernemers"},
    "knop_voorbeeld": "offerte aanvragen, portfolio, bellen",
}, {
    "slug": "accountant-boekhouder",
    "listdom": {"accountant-boekhouder"},
    "bron_csv": "accountant-boekhouder-aangevuld.csv",
    "plaatsen": {"Nijmegen", "Lent", "Oosterhout"},
    "naam": "Accountants en boekhouders in Nijmegen",
    "enkelvoud": "Accountant",
    "groep": "Zakelijk en diensten",
    "soorten": {"Accountant"},
    "schema": "AccountingService",
    "beschrijving": "Accountants, boekhouders en belastingadviseurs in Nijmegen, voor ondernemers en particulieren, met adressen en specialismen.",
    "intro": "<p>Je boekhouding op orde, je jaarrekening op tijd en geen zorgen over de belastingaangifte: daar helpt een "
             "accountant of boekhouder bij. In Nijmegen vind je grote kantoren én zelfstandige boekhouders die vooral zzp'ers "
             "en kleine ondernemers helpen.</p>"
             "<p>Op deze pagina vind je alle accountants en boekhouders in Nijmegen.</p>",
    "faq": [
        ("Wat is het verschil tussen een accountant en een boekhouder?",
         "Een boekhouder houdt je administratie bij en doet vaak ook je aangifte. Een accountant mag daarnaast jaarrekeningen "
         "samenstellen en controleren. Voor veel zzp'ers is een boekhouder genoeg."),
        ("Kan een boekhouder ook mijn particuliere aangifte doen?",
         "Veel kantoren doen dat. Filter op particuliere aangifte."),
        ("Ik start een bedrijf in Nijmegen, waar begin ik?",
         "Filter op startende ondernemers voor kantoren die starters begeleiden, of lees ons artikel over een bedrijf starten in Nijmegen."),
    ],
    "artikelen": ["je-boekhouding-zelf-doen-of-uitbesteden", "belastingvoordelen-en-subsidies-voor-ondernemers-in-nijmegen",
                  "stap-voor-stap-je-bedrijf-starten-in-nijmegen-alles-wat-je-moet-weten"],
    "blogs": ["je-boekhouding-zelf-doen-of-uitbesteden", "belastingvoordelen-en-subsidies-voor-ondernemers-in-nijmegen",
              "stap-voor-stap-je-bedrijf-starten-in-nijmegen-alles-wat-je-moet-weten",
              "financieringsmogelijkheden-voor-startups-en-kleine-bedrijven-in-nijmegen"],
    "meervoud": "accountants en boekhouders",
    "blogonderwerp": "boekhouding en ondernemen",
    "filtervoorbeeld": "belastingaangifte, salarisadministratie of startende ondernemers",
    "voorbeeld": {"naam": "Jouw kantoor", "foto": "assets/uploads/2022/12/boekhouding-nijmegen-533x400.webp",
                  "kenmerken": ["boekhouding", "startende ondernemers"], "actie": "Eerste gesprek gratis"},
    "knop_voorbeeld": "afspraak maken, offerte, bellen",
}, {
    "slug": "advocatenkantoor",
    "listdom": {"advocatenkantoor"},
    "bron_csv": "advocatenkantoor-aangevuld.csv",
    "plaatsen": {"Nijmegen", "Lent", "Oosterhout"},
    "naam": "Advocaten in Nijmegen",
    "enkelvoud": "Advocatenkantoor",
    "de_woord": False,
    "groep": "Zakelijk en diensten",
    "soorten": {"Advocaat"},
    "schema": "LegalService",
    "beschrijving": "Advocaten en juridisch adviseurs in Nijmegen, per rechtsgebied: arbeidsrecht, familierecht, strafrecht en meer.",
    "intro": "<p>Een conflict met je werkgever, een scheiding of een zakelijk geschil: dan wil je een advocaat die je zaak "
             "begrijpt. Nijmegen heeft een rechtbank en veel advocatenkantoren, van grote kantoren tot advocaten die zich "
             "op één rechtsgebied richten.</p>"
             "<p>Op deze pagina vind je alle advocaten in Nijmegen.</p>",
    "faq": [
        ("Hoe vind ik een advocaat voor mijn rechtsgebied?",
         "Filter hieronder op het rechtsgebied, zoals arbeidsrecht, familierecht en scheiding of strafrecht."),
        ("Heb ik recht op een advocaat via de Raad voor Rechtsbijstand?",
         "Bij een laag inkomen betaal je vaak maar een deel. Filter op gefinancierde rechtshulp voor kantoren die met een toevoeging werken."),
        ("Is een eerste gesprek gratis?",
         "Bij veel kantoren wel. Filter op gratis kennismaking."),
    ],
    "artikelen": ["advocaat-nijmegen-kies-voor-de-beste-juridische-hulp"],
    "blogs": ["advocaat-nijmegen-kies-voor-de-beste-juridische-hulp"],
    "meervoud": "advocatenkantoren",
    "blogonderwerp": "juridisch advies",
    "filtervoorbeeld": "arbeidsrecht, familierecht of strafrecht",
    "voorbeeld": {"naam": "Jouw advocatenkantoor", "foto": "assets/uploads/2023/11/advocaat-nijmegen-juridisch-advies-533x400.webp",
                  "kenmerken": ["arbeidsrecht", "gratis kennismaking"], "actie": "Gratis eerste gesprek van 30 minuten"},
    "knop_voorbeeld": "afspraak maken, bellen, route",
}, {
    "slug": "notaris",
    "listdom": set(),
    "bron_csv": "notaris-aangevuld.csv",
    "plaatsen": {"Nijmegen", "Lent", "Oosterhout"},
    "naam": "Notarissen in Nijmegen",
    "enkelvoud": "Notaris",
    "groep": "Zakelijk en diensten",
    "soorten": {"Notaris"},
    "schema": "Notary",
    "beschrijving": "Alle notariskantoren in Nijmegen: voor een huis kopen, een testament, samenwonen of een bedrijf.",
    "intro": "<p>Een huis kopen, samenwonen, een testament of een bv oprichten: voor die momenten heb je een notaris nodig. "
             "In Nijmegen zitten verschillende notariskantoren, in het centrum en in de wijken.</p>"
             "<p>Op deze pagina vind je alle notarissen in Nijmegen.</p>",
    "faq": [
        ("Wanneer heb ik een notaris nodig?",
         "Onder meer bij het kopen van een huis, een hypotheek, een testament, huwelijkse voorwaarden, een samenlevingscontract en het oprichten van een bv."),
        ("Mag ik zelf een notaris kiezen bij het kopen van een huis?",
         "Ja, als koper kies je zelf de notaris. Het loont om een paar offertes te vergelijken."),
    ],
    "artikelen": ["zoek-je-een-hypotheek-lees-deze-essentiele-info"],
    "blogs": [],
    "meervoud": "notarissen",
    "blogonderwerp": "wonen en geldzaken",
    "filtervoorbeeld": "huis kopen of testament",
    "voorbeeld": {"naam": "Jouw notariskantoor", "foto": "assets/uploads/2023/11/advocaat-nijmegen-juridisch-advies-533x400.webp",
                  "kenmerken": ["huis kopen", "testament"], "actie": "Vaste prijs voor je testament"},
    "knop_voorbeeld": "offerte, afspraak maken, bellen",
}, {
    "slug": "hypotheekadviseur",
    "listdom": set(),
    "bron_csv": "hypotheekadviseur-aangevuld.csv",
    "plaatsen": {"Nijmegen", "Lent", "Oosterhout"},
    "naam": "Hypotheek- en financieel adviseurs in Nijmegen",
    "enkelvoud": "Adviseur",
    "groep": "Zakelijk en diensten",
    "soorten": {"Hypotheekadviseur"},
    "schema": "FinancialService",
    "beschrijving": "Hypotheekadviseurs en financieel planners in Nijmegen, voor starters, oversluiten en financiële planning.",
    "intro": "<p>Je eerste huis kopen in Nijmegen, je hypotheek oversluiten of vooruitkijken naar je pensioen: een goede "
             "adviseur zet de keuzes voor je op een rij. In Nijmegen vind je onafhankelijke hypotheekadviseurs, "
             "franchisekantoren en financieel planners.</p>"
             "<p>Op deze pagina vind je alle hypotheek- en financieel adviseurs in Nijmegen.</p>",
    "faq": [
        ("Is een eerste gesprek met een hypotheekadviseur gratis?",
         "Bij de meeste kantoren wel. Filter op gratis kennismaking."),
        ("Wat is het voordeel van een onafhankelijke adviseur?",
         "Een onafhankelijke adviseur vergelijkt hypotheken van meerdere banken. Filter op onafhankelijk."),
    ],
    "artikelen": ["hypotheekwereld-laat-een-hypotheekadviseur-je-begeleiden", "zoek-je-een-hypotheek-lees-deze-essentiele-info"],
    "blogs": ["hypotheekwereld-laat-een-hypotheekadviseur-je-begeleiden", "zoek-je-een-hypotheek-lees-deze-essentiele-info"],
    "meervoud": "adviseurs",
    "blogonderwerp": "hypotheken en geldzaken",
    "filtervoorbeeld": "starters, oversluiten of onafhankelijk",
    "voorbeeld": {"naam": "Jouw adviespraktijk", "foto": "assets/uploads/2023/06/hypotheek-adviseur-nijmegen-533x400.webp",
                  "kenmerken": ["starters", "gratis kennismaking"], "actie": "Gratis oriëntatiegesprek voor starters"},
    "knop_voorbeeld": "afspraak maken, bellen, route",
}, {
    "slug": "verzekeraar",
    "listdom": set(),
    "bron_csv": "verzekeraar-aangevuld.csv",
    "plaatsen": {"Nijmegen", "Lent", "Oosterhout"},
    "naam": "Verzekeringen in Nijmegen",
    "enkelvoud": "Verzekeringskantoor",
    "de_woord": False,
    "groep": "Zakelijk en diensten",
    "soorten": {"Verzekeringen"},
    "schema": "InsuranceAgency",
    "beschrijving": "Verzekeringskantoren en -adviseurs in Nijmegen, voor particulieren en ondernemers.",
    "intro": "<p>Liever een adviseur aan tafel dan een vergelijkingssite? In Nijmegen zitten verzekeringskantoren die je "
             "persoonlijk helpen met je auto-, woon- of zakelijke verzekeringen, en die je belt als er schade is.</p>"
             "<p>Op deze pagina vind je alle verzekeringskantoren in Nijmegen.</p>",
    "faq": [
        ("Waarom een verzekeringskantoor in plaats van online afsluiten?",
         "Een adviseur kijkt naar je hele situatie en helpt je bij schade. Een onafhankelijk kantoor vergelijkt meerdere verzekeraars."),
        ("Helpen ze ook ondernemers?",
         "Veel kantoren wel. Filter op zakelijke verzekeringen."),
    ],
    "artikelen": ["vergelijk-autoverzekeringen-in-nijmegen-waar-moet-je-op-letten", "autoverzekering-vergelijken-zo-vind-je-de-beste-deal",
                  "waarom-kun-je-beter-een-huisdierenverzekering-afsluiten"],
    "blogs": ["vergelijk-autoverzekeringen-in-nijmegen-waar-moet-je-op-letten", "autoverzekering-vergelijken-zo-vind-je-de-beste-deal",
              "waarom-kun-je-beter-een-huisdierenverzekering-afsluiten"],
    "meervoud": "verzekeringskantoren",
    "blogonderwerp": "verzekeringen",
    "filtervoorbeeld": "zakelijke verzekeringen of onafhankelijk",
    "voorbeeld": {"naam": "Jouw verzekeringskantoor", "foto": "assets/uploads/2025/07/Autoverzekering-vergelijken-zo-vind-je-de-beste-deal-533x400.webp",
                  "kenmerken": ["onafhankelijk", "particulieren"], "actie": "Gratis polischeck"},
    "knop_voorbeeld": "afspraak maken, schade melden, bellen",
}, {
    "slug": "uitzendbureau",
    "listdom": {"uitzendbureau"},
    "bron_csv": "uitzendbureau-aangevuld.csv",
    "plaatsen": {"Nijmegen", "Lent", "Oosterhout"},
    "naam": "Uitzendbureaus in Nijmegen",
    "enkelvoud": "Uitzendbureau",
    "de_woord": False,
    "groep": "Zakelijk en diensten",
    "soorten": {"Uitzendbureau"},
    "schema": "EmploymentAgency",
    "beschrijving": "Uitzendbureaus, detacheerders en werving- en selectiebureaus in Nijmegen, per vakgebied.",
    "intro": "<p>Op zoek naar een bijbaan, een vaste baan of juist naar personeel? Nijmegen heeft uitzendbureaus voor "
             "studenten, techniek, zorg, logistiek en kantoorwerk, en bureaus die zich op werving en selectie of "
             "detachering richten.</p>"
             "<p>Op deze pagina vind je alle uitzendbureaus in Nijmegen.</p>",
    "faq": [
        ("Welk uitzendbureau past bij mij?",
         "Filter hieronder op je vakgebied, zoals techniek, zorg of logistiek. Studenten kunnen filteren op studenten."),
        ("Wat is het verschil tussen uitzenden en detacheren?",
         "Bij uitzendwerk werk je vaak kortere klussen; bij detachering ben je in dienst van het bureau en werk je langer bij één opdrachtgever."),
    ],
    "artikelen": ["zin-om-te-werken-ga-dan-naar-een-uitzendbureau-in-nijmegen", "vacatures"],
    "blogs": ["zin-om-te-werken-ga-dan-naar-een-uitzendbureau-in-nijmegen"],
    "meervoud": "uitzendbureaus",
    "blogonderwerp": "werken in Nijmegen",
    "filtervoorbeeld": "studenten, techniek of zorg",
    "voorbeeld": {"naam": "Jouw uitzendbureau", "foto": "assets/uploads/2023/05/uitzendbureaus-nijmegen-533x400.webp",
                  "kenmerken": ["uitzendwerk", "studenten"], "actie": "Bekijk onze vacatures in Nijmegen"},
    "knop_voorbeeld": "vacatures, inschrijven, bellen",
}, {
    "slug": "opleiding-en-training",
    "listdom": {"opleiding-en-training", "muziekschool", "onderwijs-en-educatie"},
    "bron_csv": "opleiding-en-training-aangevuld.csv",
    "plaatsen": {"Nijmegen", "Lent", "Oosterhout"},
    "naam": "Cursussen en opleidingen in Nijmegen",
    "enkelvoud": "Opleider",
    "groep": "Zakelijk en diensten",
    "soorten": {"Opleiding"},
    "schema": "EducationalOrganization",
    "beschrijving": "Cursussen, trainingen, bijles, taal- en muziekscholen in Nijmegen, voor kinderen, volwassenen en bedrijven.",
    "intro": "<p>Een nieuwe taal, eindelijk gitaar leren spelen, bijles voor je kind of een training voor je team: in "
             "Nijmegen kun je bijna alles leren. Van kleine taalscholen en muziekdocenten tot trainingsbureaus voor "
             "bedrijven.</p>"
             "<p>Op deze pagina vind je alle cursussen en opleidingen in Nijmegen.</p>",
    "faq": [
        ("Waar kan ik in Nijmegen een taalcursus volgen?",
         "Filter op taalcursus. We schreven ook over Spaans, Frans en Engels leren in Nijmegen."),
        ("Is er bijles of huiswerkbegeleiding in Nijmegen?",
         "Ja, filter op bijles en huiswerkbegeleiding."),
        ("Kan ik een proefles doen?",
         "Bij veel scholen wel. Filter op proefles."),
    ],
    "artikelen": ["ontdek-spaans-leren-in-nijmegen-de-beste-cursussen", "waarom-een-cursus-frans-in-nijmegen-kiezen",
                  "vind-uw-cursus-engels-in-nijmegen-taal-succes", "welke-nieuwe-vaardigheden-ga-jij-leren-dit-jaar"],
    "blogs": ["ontdek-spaans-leren-in-nijmegen-de-beste-cursussen", "waarom-een-cursus-frans-in-nijmegen-kiezen",
              "vind-uw-cursus-engels-in-nijmegen-taal-succes", "welke-nieuwe-vaardigheden-ga-jij-leren-dit-jaar",
              "eindeloos-betaalbaar-leren-ontdek-deze-opties", "inburgeringscursus-alles-wat-je-hierover-moet-weten",
              "houtbewerking-meesteren-cursussen-in-nijmegen", "top-5-cursussen-edelsmeden-in-nijmegen-vind-jouw-creatieve-spark",
              "fotografie-workshops-nijmegen"],
    "meervoud": "opleiders",
    "blogonderwerp": "cursussen en leren",
    "filtervoorbeeld": "taalcursus, muziekles of bijles",
    "voorbeeld": {"naam": "Jouw cursus", "foto": "assets/uploads/2022/10/nieuwe-vaardigheden-leren-in-nijmegen-533x400.webp",
                  "kenmerken": ["volwassenen", "proefles"], "actie": "Gratis proefles in september"},
    "knop_voorbeeld": "inschrijven, proefles, bellen",
}, {
    "slug": "rijschool",
    "listdom": set(),
    "bron_csv": "rijschool-aangevuld.csv",
    "plaatsen": {"Nijmegen", "Lent", "Oosterhout"},
    "naam": "Rijscholen in Nijmegen",
    "enkelvoud": "Rijschool",
    "groep": "Zakelijk en diensten",
    "soorten": {"Rijschool"},
    "schema": "EducationalOrganization",
    "beschrijving": "Alle rijscholen in Nijmegen: rijles voor auto, automaat en motor, spoedopleidingen en proeflessen.",
    "intro": "<p>Rijles in Nijmegen betekent oefenen tussen de fietsers in het centrum, op de Waalbrug en op de rondweg. "
             "Er zijn rijscholen voor auto en automaat, voor motor en aanhanger, en rijscholen met spoedopleidingen of "
             "extra aandacht voor faalangst.</p>"
             "<p>Op deze pagina vind je alle rijscholen in Nijmegen.</p>",
    "faq": [
        ("Waar haal ik in Nijmegen mijn rijbewijs?",
         "Het CBR-examencentrum voor Nijmegen zit in de regio. Je rijschool meldt je aan. Lees ook ons artikel over de soorten rijbewijzen."),
        ("Kan ik in Nijmegen les krijgen in een automaat?",
         "Ja, filter op automaat."),
        ("Is er een rijschool met een proefles?",
         "Filter op proefles voor rijscholen die een gratis of losse proefles bieden."),
    ],
    "artikelen": ["welke-soorten-rijbewijzen-kun-je-allemaal-halen-in-nijmegen"],
    "blogs": ["welke-soorten-rijbewijzen-kun-je-allemaal-halen-in-nijmegen"],
    "meervoud": "rijscholen",
    "blogonderwerp": "rijles en rijbewijs",
    "filtervoorbeeld": "automaat, motor of spoedopleiding",
    "voorbeeld": {"naam": "Jouw rijschool", "foto": "assets/uploads/2023/05/rijscholen-nijmegen-533x400.webp",
                  "kenmerken": ["automaat", "proefles"], "actie": "Gratis proefles"},
    "knop_voorbeeld": "proefles, pakketten, bellen",
}, {
    "slug": "fotograaf",
    "listdom": {"fotograaf", "videograaf"},
    "bron_csv": "fotograaf-aangevuld.csv",
    "plaatsen": {"Nijmegen", "Lent", "Oosterhout"},
    "naam": "Fotografen en videografen in Nijmegen",
    "enkelvoud": "Fotograaf",
    "groep": "Zakelijk en diensten",
    "soorten": {"Fotograaf"},
    "schema": "ProfessionalService",
    "beschrijving": "Fotografen en videografen in Nijmegen voor bruiloften, portretten, bedrijven en evenementen.",
    "intro": "<p>Een bruiloft, een nieuw portret voor LinkedIn, productfoto's voor je webshop of een film van je event: "
             "Nijmegen heeft fotografen en videografen voor elk moment. Veel van hen werken op locatie, sommigen hebben een "
             "eigen studio.</p>"
             "<p>Op deze pagina vind je alle fotografen en videografen in Nijmegen.</p>",
    "faq": [
        ("Hoe vind ik een trouwfotograaf in Nijmegen?",
         "Filter op trouwen. Bekijk het portfolio en plan een kennismaking, want goede trouwfotografen zijn vaak ruim van tevoren volgeboekt."),
        ("Is er een fotostudio in Nijmegen?",
         "Ja, filter op studio."),
    ],
    "artikelen": ["fotografen-nijmegen-emotie-vangen-momenten-vieren", "laat-je-bruiloft-op-de-gevoelige-plaat-vastleggen-door-een-fotograaf",
                  "om-deze-redenen-willen-jullie-een-videograaf-voor-de-bruiloft", "de-beste-fotospots-in-nijmegen"],
    "blogs": ["fotografen-nijmegen-emotie-vangen-momenten-vieren", "laat-je-bruiloft-op-de-gevoelige-plaat-vastleggen-door-een-fotograaf",
              "om-deze-redenen-willen-jullie-een-videograaf-voor-de-bruiloft", "de-beste-fotospots-in-nijmegen", "fotografie-workshops-nijmegen"],
    "meervoud": "fotografen",
    "blogonderwerp": "fotografie",
    "filtervoorbeeld": "trouwen, portret of bedrijfsfotografie",
    "voorbeeld": {"naam": "Jouw fotostudio", "foto": "assets/uploads/2023/05/fotografen-in-nijmegen-533x400.webp",
                  "kenmerken": ["trouwen", "portret"], "actie": "Gratis kennismaking voor bruidsparen"},
    "knop_voorbeeld": "portfolio, offerte, bellen",
}, {
    "slug": "autobedrijf",
    "listdom": {"autobedrijf", "reparatie"},
    "bron_csv": "autobedrijf-aangevuld.csv",
    "plaatsen": {"Nijmegen", "Lent", "Oosterhout"},
    "naam": "Autobedrijven en garages in Nijmegen",
    "enkelvoud": "Autobedrijf",
    "de_woord": False,
    "groep": "Zakelijk en diensten",
    "soorten": {"Autobedrijf"},
    "schema": "AutoRepair",
    "beschrijving": "Garages, autobedrijven en dealers in Nijmegen: APK, onderhoud, schadeherstel, banden en occasions.",
    "intro": "<p>APK, een grote beurt, een nieuwe set banden of een schade die hersteld moet worden: in Nijmegen zitten "
             "tientallen garages en autobedrijven, van merkdealers op de bedrijventerreinen tot de vertrouwde garage om "
             "de hoek.</p>"
             "<p>Op deze pagina vind je alle autobedrijven en garages in Nijmegen.</p>",
    "faq": [
        ("Waar kan ik in Nijmegen APK laten doen?",
         "Bij veel garages. Filter op APK; sommige bieden een leenauto of wachten met koffie."),
        ("Is er een garage voor elektrische auto's?",
         "Filter op elektrische auto's voor garages die daar onderhoud aan doen."),
        ("Waar koop ik een occasion in Nijmegen?",
         "Filter op occasions voor autobedrijven met gebruikte auto's in de verkoop."),
    ],
    "artikelen": ["private-lease-en-autofinanciering-vergeleken-op-kosten-en-vrijheid", "vergelijk-autoverzekeringen-in-nijmegen-waar-moet-je-op-letten"],
    "blogs": ["private-lease-en-autofinanciering-vergeleken-op-kosten-en-vrijheid", "met-deze-ruitenwissers-in-nijmegen-ben-je-verzekerd-van-een-helder-zicht",
              "het-effect-van-nat-weer-op-de-gezondheid-van-batterijen"],
    "meervoud": "autobedrijven",
    "blogonderwerp": "auto's",
    "filtervoorbeeld": "APK, occasions of schadeherstel",
    "voorbeeld": {"naam": "Jouw garage", "foto": "assets/uploads/2026/05/Private-lease-en-autofinanciering-vergeleken-op-kosten-en-vrijheid-533x400.webp",
                  "kenmerken": ["APK", "leenauto"], "actie": "APK met gratis wintercheck"},
    "knop_voorbeeld": "afspraak maken, occasions, bellen",
}, {
    "slug": "kinderopvang",
    "listdom": set(),
    "bron_csv": "kinderopvang-aangevuld.csv",
    "plaatsen": {"Nijmegen", "Lent", "Oosterhout"},
    "naam": "Kinderopvang in Nijmegen",
    "enkelvoud": "Kinderopvang",
    "groep": "Zakelijk en diensten",
    "soorten": {"Kinderopvang"},
    "schema": "ChildCare",
    "beschrijving": "Kinderdagverblijven, bso's, peuteropvang en gastouderbureaus in Nijmegen, per wijk op de kaart.",
    "intro": "<p>Een kinderdagverblijf dichtbij huis, een bso bij school of een gastouder die flexibel is: kinderopvang "
             "kies je met zorg. In Nijmegen zijn grote organisaties met locaties in elke wijk en kleine opvang met een "
             "eigen karakter, bijvoorbeeld tweetalig of met veel buitenspelen.</p>"
             "<p>Op deze pagina vind je alle kinderopvang in Nijmegen.</p>",
    "faq": [
        ("Hoe vind ik kinderopvang bij mij in de buurt?",
         "Bekijk de kaart onderaan deze pagina. Filter op kinderdagverblijf, bso of peuteropvang."),
        ("Krijg ik kinderopvangtoeslag?",
         "Dat hangt af van je inkomen en of de opvang geregistreerd is in het Landelijk Register Kinderopvang. Vraag het na bij de opvang."),
    ],
    "artikelen": ["uit-eten-met-kinderen-in-nijmegen-deze-locaties-mag-je-niet-missen"],
    "blogs": [],
    "meervoud": "kinderopvanglocaties",
    "blogonderwerp": "kinderen",
    "filtervoorbeeld": "kinderdagverblijf, bso of peuteropvang",
    "voorbeeld": {"naam": "Jouw kinderopvang", "foto": "assets/uploads/2023/02/uit-eten-met-kinderen-in-nijmegen-533x400.webp",
                  "kenmerken": ["kinderdagverblijf", "natuur en buiten"], "actie": "Kom vrijblijvend kijken"},
    "knop_voorbeeld": "rondleiding, inschrijven, bellen",
}, {
    "slug": "taxi",
    "listdom": {"taxi"},
    "bron_csv": "taxi-aangevuld.csv",
    "plaatsen": {"Nijmegen", "Lent", "Oosterhout"},
    "naam": "Taxi in Nijmegen",
    "enkelvoud": "Taxibedrijf",
    "de_woord": False,
    "groep": "Zakelijk en diensten",
    "soorten": {"Taxi"},
    "schema": "TaxiService",
    "beschrijving": "Taxibedrijven in Nijmegen, voor een rit in de stad, naar Schiphol of Weeze, rolstoelvervoer en groepsvervoer.",
    "intro": "<p>Na het stappen naar huis, vroeg naar Schiphol of Weeze, of vervoer met een rolstoel: in Nijmegen zijn "
             "verschillende taxibedrijven die je kunt bellen of online boeken.</p>"
             "<p>Op deze pagina vind je alle taxibedrijven in Nijmegen.</p>",
    "faq": [
        ("Waar vind ik een taxi in Nijmegen?",
         "Bij het Centraal Station staat een taxistandplaats. Je kunt ook een taxibedrijf bellen of online boeken."),
        ("Kan ik een taxi naar Schiphol of Weeze boeken?",
         "Ja, filter op luchthavenvervoer."),
    ],
    "artikelen": [],
    "blogs": [],
    "meervoud": "taxibedrijven",
    "blogonderwerp": "vervoer",
    "filtervoorbeeld": "luchthavenvervoer of rolstoelvervoer",
    "voorbeeld": {"naam": "Jouw taxibedrijf", "foto": "assets/uploads/2023/05/rijscholen-nijmegen-533x400.webp",
                  "kenmerken": ["luchthavenvervoer", "24 uur"], "actie": "Vaste prijs naar Schiphol"},
    "knop_voorbeeld": "rit boeken, bellen, whatsapp",
}, {
    "slug": "begrafenis",
    "listdom": {"begrafenis"},
    "bron_csv": "begrafenis-aangevuld.csv",
    "plaatsen": {"Nijmegen", "Lent", "Oosterhout"},
    "naam": "Uitvaart in Nijmegen",
    "enkelvoud": "Uitvaartondernemer",
    "groep": "Zakelijk en diensten",
    "soorten": {"Uitvaart"},
    "schema": "LocalBusiness",
    "beschrijving": "Uitvaartondernemers en uitvaartcentra in Nijmegen, dag en nacht bereikbaar.",
    "intro": "<p>Als iemand overlijdt, moet er in korte tijd veel geregeld worden. Een uitvaartondernemer helpt je daarbij "
             "en denkt mee over een afscheid dat past. In Nijmegen zijn grote uitvaartorganisaties en kleine, zelfstandige "
             "uitvaartbegeleiders.</p>"
             "<p>Op deze pagina vind je alle uitvaartondernemers in Nijmegen.</p>",
    "faq": [
        ("Wat moet ik doen na een overlijden?",
         "Bel eerst de huisarts voor de verklaring van overlijden en daarna een uitvaartondernemer. Die is dag en nacht bereikbaar en helpt je verder."),
        ("Mag ik zelf een uitvaartondernemer kiezen als ik verzekerd ben?",
         "Bij een kapitaalverzekering wel. Bij een naturaverzekering bepaalt de verzekeraar wie de uitvaart verzorgt; vaak kun je dat wel aanpassen."),
    ],
    "artikelen": ["wat-komt-er-allemaal-kijken-bij-een-uitvaart"],
    "blogs": ["wat-komt-er-allemaal-kijken-bij-een-uitvaart"],
    "meervoud": "uitvaartondernemers",
    "blogonderwerp": "uitvaart",
    "filtervoorbeeld": "crematie, natuurbegraven of een eigen uitvaartcentrum",
    "voorbeeld": {"naam": "Jouw uitvaartonderneming", "foto": "assets/uploads/2025/01/uitvaart-begrafenis-533x400.webp",
                  "kenmerken": ["dag en nacht bereikbaar", "persoonlijk afscheid"], "actie": "Vrijblijvend gesprek over je wensen"},
    "knop_voorbeeld": "direct bellen, wensen vastleggen, route",
}, {
    "slug": "hondentraining",
    "listdom": set(),
    "bron_csv": "hondentraining-aangevuld.csv",
    "plaatsen": {"Nijmegen", "Lent", "Oosterhout"},
    "naam": "Hondentraining en dierenverzorging in Nijmegen",
    "enkelvoud": "Dierenservice",
    "groep": "Zakelijk en diensten",
    "soorten": {"Hondentraining"},
    "schema": "LocalBusiness",
    "beschrijving": "Hondenscholen, trimsalons, dierenpensions en uitlaatservices in Nijmegen.",
    "intro": "<p>Een puppycursus, een trimbeurt of iemand die je hond uitlaat als je moet werken: in Nijmegen zijn "
             "hondenscholen, trimsalons, dierenpensions en uitlaatservices, vaak met trainingsvelden aan de rand van de "
             "stad.</p>"
             "<p>Op deze pagina vind je alle hondentraining en dierenverzorging in Nijmegen.</p>",
    "faq": [
        ("Waar kan ik in Nijmegen een puppycursus volgen?",
         "Filter op puppycursus. Lees ook ons artikel over de puppycursus in Nijmegen."),
        ("Is er een trimsalon in Nijmegen?",
         "Ja, filter op trimsalon."),
    ],
    "artikelen": ["puppy-cursus-in-nijmegen-train-je-hond", "waarom-kun-je-beter-een-huisdierenverzekering-afsluiten"],
    "blogs": ["puppy-cursus-in-nijmegen-train-je-hond", "waarom-kun-je-beter-een-huisdierenverzekering-afsluiten"],
    "meervoud": "dierenservices",
    "blogonderwerp": "honden en huisdieren",
    "filtervoorbeeld": "puppycursus, trimsalon of uitlaatservice",
    "voorbeeld": {"naam": "Jouw hondenschool", "foto": "assets/uploads/2023/12/Puppy-Cursus-in-Nijmegen-533x400.webp",
                  "kenmerken": ["puppycursus", "groepslessen"], "actie": "Eerste les gratis"},
    "knop_voorbeeld": "inschrijven, afspraak, bellen",
}]


def slug(tekst):
    tekst = unicodedata.normalize("NFKD", tekst).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", tekst).strip("-")


def sleutel(naam):
    return re.sub(r"[^a-z0-9]", "", slug(re.sub(r"\bnijmegen\b", "", naam, flags=re.I)))


def alineas(tekst):
    """WordPress-tekst zonder <p> omzetten naar HTML, zoals WordPress zelf doet (wpautop): elke regel een alinea,
    koppen en lijsten als eigen blok, en regels die met "- " beginnen samen een opsomming."""
    tekst = re.sub(r"(</h\d>|</ul>|</ol>)", r"\1\n", tekst.replace("\r", ""))
    tekst = re.sub(r"(?<!\n)(<h\d)", r"\n\1", tekst)
    tekst = re.sub(r"<(/?)h1\b", r"<\1h2", tekst)   # de h1 is de naam van het bedrijf
    uit, lijst = [], []
    for regel in (r.strip() for r in tekst.split("\n")):
        punt = re.match(r"^(<strong>)?\s*[-•]\s+(.*)$", regel)
        if punt:
            lijst.append((punt.group(1) or "") + punt.group(2))
            continue
        if lijst:
            uit.append("<ul>%s</ul>" % "".join("<li>%s</li>" % x for x in lijst))
            lijst = []
        if not regel:
            continue
        uit.append(regel if re.match(r"<(h\d|ul|ol|table|blockquote|figure|div|p)\b", regel) else "<p>%s</p>" % regel)
    if lijst:
        uit.append("<ul>%s</ul>" % "".join("<li>%s</li>" % x for x in lijst))
    return "\n".join(uit)


def openingstijden(ava):
    """Listdom bewaart openingstijden als PHP-serialisatie; dag 1 is maandag."""
    tijden = {}
    for dag, inhoud in re.findall(r'i:(\d);a:\d+:\{(.*?)\}', ava or ""):
        uren = re.search(r'"hours";s:\d+:"([^"]*)"', inhoud)
        dicht = re.search(r'"off";s:1:"1"', inhoud)
        tijden[int(dag)] = "gesloten" if dicht else (uren.group(1).replace(" - ", "–") if uren else "")
    return [tijden.get(i + 1, "") for i in range(7)] if tijden else []


def gids_uit_xml(pad, categorieen):
    r = ET.parse(pad).getroot()
    bijlagen = {i.findtext("wp:post_id", namespaces=NS): i.findtext("wp:attachment_url", namespaces=NS)
                for i in r.iter("item") if i.findtext("wp:post_type", namespaces=NS) == "attachment"}
    uit = []
    for i in r.iter("item"):
        if i.findtext("wp:post_type", namespaces=NS) != "listdom-listing" or i.findtext("wp:status", namespaces=NS) != "publish":
            continue
        if not any(c.get("domain") == "listdom-category" and c.get("nicename") in categorieen for c in i.findall("category")):
            continue
        m = {x.findtext("wp:meta_key", namespaces=NS): x.findtext("wp:meta_value", namespaces=NS) or "" for x in i.findall("wp:postmeta", NS)}
        adres = [x.strip() for x in m.get("lsd_contact_address", "").split("|")]
        foto = (bijlagen.get(m.get("_thumbnail_id")) or "").replace("http://", "https://")
        uit.append({
            "slug": i.findtext("wp:post_name", namespaces=NS),
            "naam": i.findtext("title"),
            "adres": adres[0] if adres else "",
            "postcode": adres[1] if len(adres) > 1 else "",
            "plaats": adres[2] if len(adres) > 2 else "Nijmegen",
            "telefoon": m.get("lsd_phone", ""),
            "email": m.get("lsd_email", ""),
            "website": m.get("lsd_website", ""),
            "facebook": m.get("lsd_facebook", ""),
            "instagram": m.get("lsd_instagram", ""),
            "lat": m.get("lsd_latitude", ""),
            "lon": m.get("lsd_longitude", ""),
            "openingstijden": openingstijden(m.get("lsd_ava")),
            "foto": foto,
            "beschrijving": m.get("rank_math_description", ""),
            "tekst": alineas(i.findtext("content:encoded", namespaces=NS) or ""),
            "categorieen": [c.text for c in i.findall("category") if c.get("domain") == "listdom-category"],
            "in_gids": True,
        })
    return uit


def osm_uit_csv(pad, soorten, plaatsen=("Nijmegen",)):
    uit = []
    for x in csv.DictReader(open(pad, encoding="utf-8")):
        if x["soort"] in soorten and x["plaats"] in plaatsen:
            uit.append({"naam": x["naam"], "adres": x["adres"].rstrip(", "), "postcode": x["postcode"], "plaats": x["plaats"],
                        "telefoon": x["telefoon"], "website": x["website"], "lat": x["lat"], "lon": x["lon"],
                        "soort": x["soort"], "bron": x["bron"], "in_gids": False, "email": "", "facebook": "", "instagram": "",
                        "openingstijden": [], "foto": "", "beschrijving": "", "tekst": "",
                        **({"keuken": x["keuken"]} if x.get("keuken") else {})})
    return uit


def samenvoegen(gids, overig, bezet_elders=frozenset()):
    """Bedrijven uit de gids gaan voor; dezelfde naam uit OSM/Overture valt dan weg."""
    # Ook dezelfde website telt als hetzelfde bedrijf ("Eetbar MikMak" in de gids, "MikMak" in OpenStreetMap)
    bekend = {sleutel(b["naam"]) for b in gids}
    sites = {domein(b["website"]).lower() for b in gids if b.get("website")}
    gids.sort(key=lambda b: b["naam"].lower())
    uniek = {}
    for b in overig:
        if sleutel(b["naam"]) not in bekend and not (b.get("website") and domein(b["website"]).lower() in sites):
            uniek.setdefault((b["naam"], b["adres"]), b)
    overig = sorted(uniek.values(), key=lambda b: (b["naam"].lower(), b["adres"]))
    # Eigen pagina's voor de aangevulde bedrijven; dezelfde naam op meer adressen (ketens) krijgt de straat erbij
    # Eerder uitgedeelde slugs blijven staan (de url mag niet veranderen); alleen nieuwe bedrijven krijgen er een
    vorig = {}
    pad = ROOT / "data" / "bedrijvengids.json"
    if pad.exists():
        for cat in json.loads(pad.read_text(encoding="utf-8")).values():
            vorig.update({(x["naam"], x["adres"]): x["slug"] for x in cat["overig"]})
    namen = [slug(b["naam"]) for b in overig]
    bezet = ({b["slug"] for b in gids} | set(bezet_elders) | {p.name for p in (ROOT / "bedrijvengids").iterdir() if p.is_dir()}) - set(vorig.values())
    for b in overig:
        if (b["naam"], b["adres"]) in vorig:
            b["slug"] = vorig[(b["naam"], b["adres"])]
            bezet.add(b["slug"])
    for b in overig:
        if b.get("slug"):
            continue
        s = slug(b["naam"])
        if namen.count(s) > 1 or s in bezet:
            s = slug("%s %s" % (b["naam"], re.sub(r"\s*\d.*$", "", b["adres"])))
        while s in bezet:
            s += "-2"
        b["slug"] = s
        bezet.add(s)
    return gids, overig


def domein(url):
    return re.sub(r"^www\.", "", url.split("/")[2]) if "//" in url else url


def telefoon(nummer):
    n = re.sub(r"[^\d+]", "", nummer)
    if n.startswith("+31"):
        n = "0" + n[3:]
    if re.match(r"06\d{8}$", n):
        return n, "06-%s %s %s %s" % (n[2:4], n[4:6], n[6:8], n[8:])
    return n, n


def adresregel(b):
    pc = re.sub(r"^(\d{4})\s*([A-Za-z]{2})$", lambda m: "%s %s" % (m.group(1), m.group(2).upper()), (b["postcode"] or "").strip())
    return ", ".join(x for x in (b["adres"], " ".join(x for x in (pc, b["plaats"]) if x)) if x)


def bedrijf_pagina(b, cat, anderen, root="../../"):
    canonical = "%s/bedrijvengids/%s/" % (SITE, b["slug"])
    soort = (b.get("soort") or cat["enkelvoud"]).lower()
    kort = "<p>%s is een %s aan de %s in %s.</p>" % (esc(b["naam"]), esc(soort), esc(b["adres"]), esc(b["plaats"])) if b["adres"] else ""
    beschrijving = b["beschrijving"] or samenvatting(b["tekst"] or kort)
    ld = {"@context": "https://schema.org", "@type": cat["schema"], "name": b["naam"], "url": canonical,
          "address": {"@type": "PostalAddress", "streetAddress": b["adres"], "postalCode": b["postcode"],
                      "addressLocality": b["plaats"], "addressCountry": "NL"}}
    if b["telefoon"]:
        ld["telephone"] = b["telefoon"]
    if b["lat"]:
        ld["geo"] = {"@type": "GeoCoordinates", "latitude": float(b["lat"]), "longitude": float(b["lon"])}
    if b["foto"]:
        ld["image"] = foto_url(b["foto"], SITE + "/")
    if b["openingstijden"]:
        ld["openingHoursSpecification"] = [
            {"@type": "OpeningHoursSpecification", "dayOfWeek": SCHEMA_DAG[i], "opens": t.split("–")[0], "closes": t.split("–")[1]}
            for i, t in enumerate(b["openingstijden"]) if "–" in t]
    kruim = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "Home", "item": SITE + "/"},
        {"@type": "ListItem", "position": 2, "name": cat["naam"], "item": "%s/bedrijvengids-categorie/%s/" % (SITE, cat["slug"])},
        {"@type": "ListItem", "position": 3, "name": b["naam"], "item": canonical}]}
    extra = "".join('\n  <script type="application/ld+json">%s</script>' % json.dumps(x, ensure_ascii=False) for x in (ld, kruim))
    if not b["tekst"] or b.get("concept"):
        # Nog geen (goedgekeurde) eigen tekst: wel een pagina (klikbaar vanuit de lijst), maar niet in Google tot de tekst er is
        extra += '\n  <meta name="robots" content="noindex">'
    out = [kop(b["naam"], beschrijving, canonical, root, foto_url(b["foto"], SITE + "/") or None, extra)]
    out.append('  <main class="artikel-wrap">\n    <div class="container">\n      <div class="artikel-layout">\n      <article class="artikel bedrijf">')
    out.append('        <div class="kruimelpad"><a href="%s">Home</a> › <a href="%sbedrijvengids-categorie/%s/">%s</a> › %s</div>'
               % (root, root, cat["slug"], esc(cat["naam"]), esc(b["naam"])))
    out.append('        <p class="gidslabel">%s</p>' % esc(cat["enkelvoud"]))
    out.append("        <h1>%s</h1>" % esc(b["naam"]))
    regels = []
    route = "https://www.openstreetmap.org/?mlat=%s&mlon=%s#map=17/%s/%s" % (b["lat"], b["lon"], b["lat"], b["lon"]) if b["lat"] else ""
    regels.append('<li><span class="evenement-info__kop">Adres</span>%s%s</li>'
                  % (esc(adresregel(b)), ' <a href="%s" target="_blank" rel="noopener" data-klik="route">Kaart</a>' % esc(route) if route else ""))
    if b.get("extra_vestiging"):
        regels.append('<li><span class="evenement-info__kop">Tweede vestiging</span>%s</li>' % esc(b["extra_vestiging"]))
    if not b["openingstijden"] and b.get("tijden_site"):
        regels.append('<li><span class="evenement-info__kop">Openingstijden</span>%s<br><span class="bron">(%s)</span></li>'
                      % ("<br>".join(esc(x.strip()) for x in re.split(r",\s*(?=[a-z]{2}\b)|\n", b["tijden_site"]) if x.strip()), b.get("tijden_bron", "volgens de eigen website")))
    if b["openingstijden"]:
        rijen = "".join("<tr><th>%s</th><td>%s</td></tr>" % (DAGEN[i], esc(t or "onbekend")) for i, t in enumerate(b["openingstijden"]))
        regels.append('<li><span class="evenement-info__kop">Openingstijden</span><table class="openingstijden">%s</table></li>' % rijen)
    if b.get("keuken"):
        regels.append('<li><span class="evenement-info__kop">Keuken</span>%s</li>' % esc(b["keuken"]))
    if b.get("kenmerken"):
        regels.append('<li><span class="evenement-info__kop">Goed om te weten</span><span class="bedrijfkaart__kenmerken">%s</span></li>'
                      % "".join("<span>%s</span>" % esc(k) for k in b["kenmerken"]))
    contact = []
    if b["website"]:
        contact.append('<a href="%s" target="_blank" rel="%s noopener" data-klik="website">%s</a>'
                       % (esc(b["website"]), "sponsored" if b.get("uitgelicht") else "nofollow", esc(domein(b["website"]))))
    if b["telefoon"]:
        nr, tonen = telefoon(b["telefoon"])
        contact.append('<a href="tel:%s" data-klik="telefoon">%s</a>' % (esc(nr), esc(tonen)))
    if b.get("email"):
        contact.append('<a href="mailto:%s">%s</a>' % (esc(b["email"]), esc(b["email"])))
    social = [(n, b.get(n)) for n in ("instagram", "facebook") if b.get(n)]
    if social:
        contact.append(" · ".join('<a href="%s" target="_blank" rel="nofollow noopener">%s</a>' % (esc(u), n.capitalize()) for n, u in social))
    if contact:
        regels.append('<li><span class="evenement-info__kop">Contact</span>%s</li>' % "<br>".join(contact))
    # Gewone link naar Google Maps (geen API: die mag niet in een bedrijvengids, besluit Frans 23-10-2026)
    zoek = urllib.parse.urlencode({"api": "1", "query": "%s, %s" % (b["naam"], adresregel(b))})
    regels.append('<li><span class="evenement-info__kop">Reviews</span><a href="https://www.google.com/maps/search/?%s" target="_blank" '
                  'rel="nofollow noopener" data-klik="google">Bekijk de reviews op Google Maps</a></li>' % esc(zoek))
    if not b["in_gids"]:
        regels.append('<li class="bron">Gegevens: © <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">'
                      'OpenStreetMap-bijdragers</a> en Overture Maps. Klopt er iets niet? <a href="%skom-in-contact/">Laat het weten</a>.</li>' % root)
    if b["foto"]:
        out.append('        <figure><img src="%s" alt="%s"></figure>' % (esc(foto_url(b["foto"], root)), esc(b["naam"])))
    actie = b.get("actie") or {}
    if actie.get("tekst"):
        out.append('        <p class="gidsactie"><strong>Actie</strong> %s%s</p>'
                   % (esc(actie["tekst"]), " (tot en met %s)" % esc(datum_nl(actie["tot"])) if actie.get("tot") else ""))
    knop = b.get("knop") or {}
    if knop.get("tekst") and knop.get("link"):
        out.append('        <p><a class="knop" href="%s" target="_blank" rel="sponsored noopener" data-klik="knop">%s</a></p>'
                   % (esc(knop["link"]), esc(knop["tekst"])))
    if b.get("concept"):
        out.append('        <p class="bron">Concepttekst op basis van de eigen website, nog niet door de redactie gecontroleerd.</p>')
    if b["tekst"]:
        out.append('        <div class="inhoud-tekst">\n%s\n        </div>' % schoon(b["tekst"], set(), root, False, b["naam"]))
    else:
        out.append('        <div class="inhoud-tekst">%s</div>' % kort)
    if b.get("fotos"):
        # Carrousel (Uitgelicht en Partner, tot 10 foto's): vegen op mobiel, pijlen via assets/js/bedrijf.js
        out.append('        <div class="gidsfotos" role="region" aria-label="Foto\'s van %s"><div class="gidsfotos__rij" tabindex="0">%s</div>'
                   '<button type="button" class="gidsfotos__pijl gidsfotos__pijl--vorige" aria-label="Vorige foto" hidden>&#8249;</button>'
                   '<button type="button" class="gidsfotos__pijl gidsfotos__pijl--volgende" aria-label="Volgende foto" hidden>&#8250;</button></div>'
                   % (esc(b["naam"]), "".join('<img src="%s" alt="%s, foto %d" loading="lazy">' % (esc(foto_url(f, root)), esc(b["naam"]), n + 1)
                                                for n, f in enumerate(b["fotos"]))))
    out.append('        <section class="gids-sectie">\n          <h2>Contact en openingstijden</h2>')
    out.append('          <ul class="evenement-info%s">%s</ul>\n        </section>' % (" evenement-info--uitgelicht" if b.get("uitgelicht") else "", "".join(regels)))
    if not b.get("uitgelicht"):
        out.append(mijn_bedrijf(b, cat, root))
    out.append('        <div class="partner-slider" data-plaatsing="blog"></div>')
    if b["lat"]:
        lat, lon = float(b["lat"]), float(b["lon"])
        bbox = "%.5f,%.5f,%.5f,%.5f" % (lon - 0.006, lat - 0.003, lon + 0.006, lat + 0.003)
        out.append('        <section class="gids-sectie">\n          <h2>Hier vind je %s</h2>' % esc(b["naam"]))
        out.append('          <iframe class="kaartkader" title="Kaart van %s" loading="lazy" '
                   'src="https://www.openstreetmap.org/export/embed.html?bbox=%s&amp;layer=mapnik&amp;marker=%s,%s"></iframe>'
                   % (esc(b["naam"]), bbox, b["lat"], b["lon"]))
        out.append('          <p class="bron">Kaart: © <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap-bijdragers</a></p>\n        </section>')
    if anderen:
        out.append('        <section class="gids-sectie">\n          <h2>Meer %s in Nijmegen</h2>\n          <div class="bedrijflijst">' % esc(cat["meervoud"]))
        out.extend("            " + (uitgelicht_kaart(x, root) if x.get("uitgelicht") else gewone_kaart(x, root)) for x in anderen[:4])
        out.append('          </div>\n          <p class="gids-verder"><a href="%sbedrijvengids-categorie/%s/">Bekijk alle %s</a></p>\n        </section>'
                   % (root, cat["slug"], esc(cat["naam"][0].lower() + cat["naam"][1:])))
    out.append('        <script src="%sassets/js/bedrijf.js?v=2" defer data-bedrijf="%s"></script>' % (root, esc(b["slug"])))
    out.append("      </article>\n\n      <!-- zijbalk --><!-- /zijbalk -->\n      </div>\n    </div>\n  </main>")
    out.append(VOET)
    return "\n".join(out)


def mijn_bedrijf(b, cat, root):
    """Knop naar het aanmeldformulier met het bedrijf al ingevuld (assets/js/formulier.js vult de velden uit de url)."""
    pc = re.sub(r"^(\d{4})\s*([A-Za-z]{2})$", lambda m: "%s %s" % (m.group(1), m.group(2).upper()), (b["postcode"] or "").strip())
    velden = {"vermelding": b["slug"], "bedrijf": b["naam"], "categorie": cat["enkelvoud"], "adres": b["adres"], "postcode": pc,
              "plaats": b["plaats"], "land": "Duitsland" if re.match(r"^\d{5}$", pc) else "Nederland",
              "site": b.get("website") or "", "telefoon": b.get("telefoon") or ""}
    link = "%sbedrijf-aanmelden/?%s" % (root, urllib.parse.urlencode({k: v for k, v in velden.items() if v}))
    return ('        <aside class="mijnbedrijf">\n          <p><strong>Is %s jouw bedrijf?</strong> Vul je gegevens aan met foto\'s, openingstijden '
            'en een eigen tekst. Je vermelding is en blijft gratis; wil je meer opvallen, dan kun je hem laten uitlichten.</p>\n'
            '          <p><a class="knop" href="%s">Dit is mijn bedrijf</a></p>\n        </aside>' % (esc(b["naam"]), esc(link)))


def datum_nl(iso):
    maanden = ["januari", "februari", "maart", "april", "mei", "juni", "juli", "augustus", "september", "oktober", "november", "december"]
    try:
        d = datetime.date.fromisoformat(iso)
    except ValueError:
        return iso
    return "%d %s %d" % (d.day, maanden[d.month - 1], d.year)


def pakketten_toepassen(bedrijven, pad, vandaag):
    """Betaalde pakketten: alleen zolang betaald_tot niet verstreken is. Zonder geldig pakket is alles gratis."""
    pakketten = json.loads(pad.read_text(encoding="utf-8")) if pad.exists() else {}
    for b in bedrijven:
        p = pakketten.get(b["slug"]) or {}
        actief = p.get("pakket") in BETAALD and p.get("betaald_tot", "") >= vandaag.isoformat()
        b["uitgelicht"] = actief
        if not actief:
            continue
        b["pakket"] = p["pakket"]
        b["ook_in"] = p.get("ook_in", [])
        if p.get("logo") and not b["foto"]:
            b["foto"] = p["logo"]
        if p.get("fotos"):
            b["foto"] = b["foto"] or p["fotos"][0]
            b["fotos"] = [f for f in p["fotos"] if f != b["foto"]]
        if (p.get("knop") or {}).get("link"):
            b["knop"] = p["knop"]
        actie = p.get("actie") or {}
        if actie.get("tekst") and actie.get("tot", "9999") >= vandaag.isoformat():
            b["actie"] = actie


def bedrijfkaart(b, root):
    """Kaartje in een lijst; elk bedrijf heeft een eigen pagina, die uit de gids met foto en openingstijden."""
    label = '<span class="bedrijfkaart__label">Uitgelicht</span>' if b.get("uitgelicht") else ""
    foto = '<img src="%s" alt="" loading="lazy">' % esc(foto_url(b["foto"], root)) if b["foto"] else ""
    open_ = '<span class="bedrijfkaart__open">Ma–vr %s</span>' % esc(b["openingstijden"][0]) if b["openingstijden"] else ""
    km = b.get("kenmerken") or []
    chips = '<span class="bedrijfkaart__kenmerken">%s</span>' % "".join("<span>%s</span>" % esc(k) for k in km[:4]) if km else ""
    return ('<a class="bedrijfkaart%s" href="%sbedrijvengids/%s/" data-kenmerken="%s">%s<span class="bedrijfkaart__tekst">%s<strong>%s</strong><span>%s</span>%s%s</span></a>'
            % (" bedrijfkaart--uitgelicht" if b.get("uitgelicht") else "", root, b["slug"], esc("|".join(km)), foto, label, esc(b["naam"]),
               esc(adresregel(b)), open_, chips))


LEAFLET = ('\n  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.css">'
           '\n  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet.markercluster/1.5.3/MarkerCluster.css">'
           '\n  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet.markercluster/1.5.3/MarkerCluster.Default.css">'
           '\n  <script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.js" defer></script>'
           '\n  <script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet.markercluster/1.5.3/leaflet.markercluster.js" defer></script>')


def kaart_blok(bedrijven, root, knoppen=False):
    """Kaart met alle bedrijven; bedrijven is een lijst (groep, bedrijf). Met knoppen kun je groepen aan- en uitzetten."""
    groepen = list(dict.fromkeys(g for g, _ in bedrijven))
    punten = [[b["naam"], round(float(b["lat"]), 6), round(float(b["lon"]), 6), "%sbedrijvengids/%s/" % (root, b["slug"]), adresregel(b), g]
              for g, b in bedrijven if b["lat"]]
    data = json.dumps({"groepen": groepen, "punten": punten}, ensure_ascii=False).replace("</", "<\\/")
    return ('%s          <div id="gidskaart" class="gidskaart" role="region" aria-label="Kaart met bedrijven"></div>\n'
            '          <script type="application/json" id="kaartdata">%s</script>\n'
            '          <script src="%sassets/js/kaart.js?v=2" defer></script>'
            % ('          <div id="kaartgroepen" class="kaartgroepen"></div>\n' if knoppen else "", data, root))


def start_pagina(groepen, root="../"):
    """/bedrijvengids/: kaart met alle bedrijven en de categorieën per groep."""
    canonical = "%s/bedrijvengids/" % SITE
    alle = [(g, b) for g, cats in groepen for cat, gids, overig in cats for b in gids + overig]
    beschrijving = "De bedrijvengids van Nijmegen: zoek op de kaart of per categorie naar sportscholen, restaurants, winkels en meer."
    out = [kop("Bedrijvengids Nijmegen", beschrijving, canonical, root, None, LEAFLET)]
    out.append('  <main class="artikel-wrap">\n    <div class="container">\n      <div class="artikel-layout">\n      <article class="artikel gids">')
    out.append('        <div class="kruimelpad"><a href="%s">Home</a> › Bedrijvengids</div>' % root)
    out.append("        <h1>Bedrijvengids Nijmegen</h1>")
    out.append('        <div class="inhoud-tekst"><p>Op zoek naar een sportschool, een kapper of een plek om te lunchen? In de bedrijvengids '
               'vind je de bedrijven van Nijmegen, op de kaart en per categorie. Klik op een punt voor het adres en de pagina van het bedrijf.</p></div>')
    out.append('        <section class="gids-sectie">\n          <h2>Op de kaart</h2>')
    out.append(kaart_blok(alle, root, knoppen=True))
    out.append('          <p class="bron">Gegevens: onze eigen gids, aangevuld met © OpenStreetMap-bijdragers en Overture Maps.</p>\n        </section>')
    out.append('        <section class="gids-sectie">\n          <h2>Categorieën</h2>\n          <div class="gidsgroepen">')
    for g, cats in groepen:
        out.append('            <div><h3>%s</h3><ul>%s</ul></div>' % (esc(g), "".join(
            '<li><a href="%sbedrijvengids-categorie/%s/">%s</a> (%d)</li>' % (root, cat["slug"], esc(cat["naam"]), len(gids) + len(overig))
            for cat, gids, overig in cats)))
    out.append('          </div>\n          <p>Staat jouw bedrijf er niet bij? <a href="%sbedrijf-aanmelden/">Meld je bedrijf aan</a>.</p>\n        </section>' % root)
    out.append("      </article>\n\n      <!-- zijbalk --><!-- /zijbalk -->\n      </div>\n    </div>\n  </main>")
    out.append(VOET)
    return "\n".join(out)


def voorbeeld(cat):
    v = cat["voorbeeld"]
    return {"slug": "", "naam": v["naam"], "adres": "Uitgelicht staat bovenaan, met foto en actieknop", "postcode": "", "plaats": "",
            "foto": v["foto"], "kenmerken": v["kenmerken"], "actie": {"tekst": v["actie"]}, "openingstijden": [], "uitgelicht": True}


def uitgelicht_kaart(b, root, voorbeeld=False):
    """Grote kaart voor betalende bedrijven: foto, kenmerken, de actie en een knop."""
    km = b.get("kenmerken") or []
    chips = '<span class="bedrijfkaart__kenmerken">%s</span>' % "".join("<span>%s</span>" % esc(k) for k in km[:4]) if km else ""
    actie = (b.get("actie") or {}).get("tekst", "")
    actie = '<span class="bedrijfkaart__actie">%s</span>' % esc(actie) if actie else ""
    label = "Voorbeeld" if voorbeeld else "Uitgelicht"
    href = "%sadverteren-bij-nijmegenonline/" % root if voorbeeld else "%sbedrijvengids/%s/" % (root, b["slug"])
    foto = '<img src="%s" alt="" loading="lazy">' % esc(foto_url(b["foto"], root)) if b.get("foto") else ""
    return ('<a class="bedrijfkaart bedrijfkaart--uitgelicht" href="%s" data-kenmerken="%s">%s<span class="bedrijfkaart__tekst">'
            '<span class="bedrijfkaart__label">%s</span><strong>%s</strong><span>%s</span>%s%s<span class="bedrijfkaart__knop">Bekijk %s</span></span></a>'
            % (href, esc("|".join(km)), foto, label, esc(b["naam"]), esc(adresregel(b) if not voorbeeld else b["adres"]),
               actie, chips, "hoe het werkt" if voorbeeld else "aanbod"))


def gewone_kaart(b, root):
    """Gratis vermelding: voor iedereen gelijk, zonder foto (een foto hoort bij Uitgelicht)."""
    km = b.get("kenmerken") or []
    chips = '<span class="bedrijfkaart__kenmerken">%s</span>' % "".join("<span>%s</span>" % esc(k) for k in km[:4]) if km else ""
    return ('<a class="bedrijfkaart" href="%sbedrijvengids/%s/" data-kenmerken="%s"><span class="bedrijfkaart__tekst"><strong>%s</strong><span>%s</span>%s</span></a>'
            % (root, b["slug"], esc("|".join(km)), esc(b["naam"]), esc(adresregel(b)), chips))


def categorie_pagina(cat, gids, overig, artikelen, root="../../"):
    """Indeling oktober 2026: alle gratis vermeldingen gelijk en zonder foto; alleen Uitgelicht valt op, lege plekken
    zijn advertentie, en onderaan staat wat Uitgelicht en Partner opleveren."""
    canonical = "%s/bedrijvengids-categorie/%s/" % (SITE, cat["slug"])
    alle = sorted(gids + overig, key=lambda b: b["naam"].lower())
    lijst = {"@context": "https://schema.org", "@type": "ItemList", "name": cat["naam"], "itemListElement": [
        {"@type": "ListItem", "position": n + 1, "name": b["naam"],
         "url": "%s/bedrijvengids/%s/" % (SITE, b["slug"])} for n, b in enumerate(alle)]}
    faq = {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": v, "acceptedAnswer": {"@type": "Answer", "text": a}} for v, a in cat["faq"]]}
    extra = "".join('\n  <script type="application/ld+json">%s</script>' % json.dumps(x, ensure_ascii=False) for x in (lijst, faq))
    out = [kop(cat["naam"], cat["beschrijving"], canonical, root, None, extra + LEAFLET)]
    out.append('  <main class="artikel-wrap">\n    <div class="container">\n      <div class="artikel-layout">\n      <article class="artikel gids">')
    out.append('        <div class="kruimelpad"><a href="%s">Home</a> › Bedrijvengids › %s</div>' % (root, esc(cat["naam"])))
    out.append('        <p class="gidslabel">Bedrijvengids</p>')
    out.append("        <h1>%s</h1>" % esc(cat["naam"]))
    intro = re.sub(r"<p>Op deze pagina vind je.*?</p>", "<p>Op deze pagina vind je alle %d %s in Nijmegen, met openingstijden, "
                   "een eigen pagina en een kaart. Filter hieronder op wat jij belangrijk vindt, zoals %s.</p>"
                   % (len(alle), cat["meervoud"], cat["filtervoorbeeld"]), cat["intro"], flags=re.S)
    out.append('        <div class="inhoud-tekst">%s</div>' % intro)
    uitgelicht = [b for b in alle if b.get("uitgelicht")]
    random.Random(datetime.date.today().isoformat() + cat["slug"]).shuffle(uitgelicht)
    uitgelicht = uitgelicht[:MAX_UITGELICHT]
    # Lege plekken: één voorbeeldkaart (zolang er niemand betaalt) en een uitnodiging om die plek te nemen
    out.append('        <section class="gids-sectie" id="uitgelicht">\n          <h2>Uitgelicht</h2>\n          <div class="bedrijflijst bedrijflijst--uitgelicht">')
    out.extend("            " + uitgelicht_kaart(b, root) for b in uitgelicht)
    if not uitgelicht:
        out.append("            " + uitgelicht_kaart(voorbeeld(cat), root, voorbeeld=True))
    if len(uitgelicht) < MAX_UITGELICHT:
        out.append('            <a class="vrijeplek" href="%sbedrijf-aanmelden/?pakket=uitgelicht&amp;categorie=%s"><strong>Nog %d %s vrij</strong>'
                   '<span>Zet jouw %s hier bovenaan, boven %d andere %s. Met foto\'s, je actie, een eigen knop en je banner bij onze blogs over %s.</span>'
                   '<span class="vrijeplek__prijs">Het eerste jaar &euro; 99</span></a>'
                   % (root, esc(cat["slug"]), MAX_UITGELICHT - len(uitgelicht), "plek" if MAX_UITGELICHT - len(uitgelicht) == 1 else "plekken",
                      esc(cat["enkelvoud"].lower()), len(alle), esc(cat["meervoud"]), esc(cat["blogonderwerp"])))
    out.append("          </div>\n        </section>")
    out.append(filter_blok(alle, cat))
    out.append('        <section class="gids-sectie">\n          <h2>Alle %s in Nijmegen</h2>\n          <div class="bedrijflijst">' % esc(cat["meervoud"]))
    out.extend("            " + gewone_kaart(b, root) for b in alle if b not in uitgelicht)
    out.append('          </div>\n        </section>')
    out.append('        <div class="partner-slider" data-plaatsing="blog" data-onderwerp="%s"></div>' % cat["slug"])
    out.append('        <section class="gids-sectie">\n          <h2>Op de kaart</h2>')
    out.append(kaart_blok([(cat["groep"], b) for b in alle], root))
    out.append('        </section>')
    # Vergelijking voor ondernemers: wat levert betalen op
    rijen = [("Eigen pagina met adres, kaart en openingstijden", "ja", "ja", "ja"),
             ("Tekst door onze redactie", "kort", "uitgebreid", "uitgebreid"),
             ("Foto's op je eigen pagina", "1", "tot 10", "tot 10"),
             ("Bovenaan deze pagina, met foto en label Uitgelicht", "nee", "ja", "ja"),
             ("Actie en eigen knop (%s)" % cat["knop_voorbeeld"], "nee", "ja", "ja"),
             ("Uitgelicht onder onze blogs over %s" % cat["blogonderwerp"], "nee", "ja", "ja"),
             ("Banner in de partnerbalk", "nee", "bij blogs over %s" % cat["blogonderwerp"], "op de hele site"),
             ("Artikel over je bedrijf en een plek in de nieuwsbrief", "nee", "nee", "ja"),
             ("Overzicht van weergaven en kliks", "jaarlijks", "jaarlijks", "elk kwartaal")]
    enk = esc(cat["enkelvoud"].lower())
    out.append('        <section class="gids-sectie pakketvergelijk">\n          <h2>Heb je een %s in Nijmegen?</h2>'
               '\n          <p>Elk%s %s staat gratis in onze gids. Wil je opvallen tussen %d %s? Kies dan voor Uitgelicht of Partner.</p>'
               % (enk, "e" if cat.get("de_woord", True) else "", enk, len(alle), esc(cat["meervoud"])))
    out.append('          <div class="tabel-scroll"><table>\n            <thead><tr><th></th><th>Gratis</th><th>Uitgelicht<br><small>&euro; 149 per jaar,<br>eerste jaar &euro; 99</small></th>'
               '<th>Partner<br><small>&euro; 449 per jaar</small></th></tr></thead>\n            <tbody>')
    def cel(w):
        return {"ja": '<td class="ja">&#10003;</td>', "nee": '<td class="nee">&ndash;</td>'}.get(w, "<td>%s</td>" % w)
    out.extend("              <tr><th>%s</th>%s</tr>" % (esc(r[0]), "".join(cel(w) for w in r[1:])) for r in rijen)
    out.append('            </tbody>\n          </table></div>')
    out.append('          <p class="pakketvergelijk__knoppen"><a class="knop" href="%sbedrijf-aanmelden/?pakket=uitgelicht&amp;categorie=%s">Kies Uitgelicht</a> '
               '<a href="%sadverteren-bij-nijmegenonline/">Alle mogelijkheden</a> &middot; Staat je %s er al? Klik op je pagina op <em>Dit is mijn bedrijf</em>.</p>'
               '\n        </section>' % (root, esc(cat["slug"]), root, enk))
    if artikelen:
        out.append('        <section class="gids-sectie">\n          <h2>Lees ook</h2>\n          <ul>')
        out.extend('            <li><a href="%s%s/">%s</a></li>' % (root, s, esc(t)) for s, t in artikelen)
        out.append("          </ul>\n        </section>")
    out.append('        <section class="gids-sectie faq">\n          <h2>Veelgestelde vragen</h2>')
    out.extend("          <details><summary>%s</summary><p>%s</p></details>" % (esc(v), esc(a)) for v, a in cat["faq"])
    out.append("        </section>")
    out.append('        <p class="bron">Gegevens: onze eigen gids, aangevuld met © <a href="https://www.openstreetmap.org/copyright" target="_blank" '
               'rel="noopener">OpenStreetMap-bijdragers</a> en Overture Maps.</p>')
    out.append("      </article>\n\n      <!-- zijbalk --><!-- /zijbalk -->\n      </div>\n    </div>\n  </main>")
    out.append(VOET)
    return "\n".join(out)


def blog_blokken(cat, alle):
    """Onder de blogberichten van het onderwerp: de uitgelichte bedrijven. Zolang niemand betaalt een verwijzing
    naar de categorie, met een uitnodiging voor ondernemers. Staat tussen <!-- gidstip --> en <!-- /gidstip -->."""
    uitgelicht = [b for b in alle if b.get("uitgelicht")]
    random.Random(datetime.date.today().isoformat() + cat["slug"] + "blog").shuffle(uitgelicht)
    root = "../"
    naar = '<a href="%sbedrijvengids-categorie/%s/">Bekijk alle %d %s in Nijmegen</a>' % (root, cat["slug"], len(alle), cat["meervoud"])
    if uitgelicht:
        blok = ('<section class="gidstip"><h2>%s uitgelicht</h2><div class="bedrijflijst bedrijflijst--uitgelicht">%s</div><p>%s</p></section>'
                % (esc(cat["meervoud"][0].upper() + cat["meervoud"][1:]), "".join(uitgelicht_kaart(b, root) for b in uitgelicht[:MAX_UITGELICHT]), naar))
    else:
        blok = ('<section class="gidstip"><h2>%s</h2><p>Zin om te beginnen? In onze bedrijvengids vind je alle %d %s in Nijmegen, '
                'met openingstijden, kenmerken en een kaart.</p><p>%s</p><p class="gidstip__ondernemer">Heb je zelf een %s? '
                '<a href="%sadverteren-bij-nijmegenonline/">Laat je hier uitlichten</a>.</p></section>'
                % (esc(cat["naam"]), len(alle), cat["meervoud"], naar, esc(cat["enkelvoud"].lower()), root))
    for s_ in cat.get("blogs", []):
        pad = ROOT / s_ / "index.html"
        if not pad.exists():
            continue
        tekst = re.sub(r"\n?[ \t]*<!-- gidstip -->.*?<!-- /gidstip -->", "", pad.read_text(encoding="utf-8"), flags=re.S)
        tekst = tekst.replace("      </article>", "        <!-- gidstip -->%s<!-- /gidstip -->\n      </article>" % blok, 1)
        tekst = re.sub(r'class="partner-slider" data-plaatsing="blog"(?: data-onderwerp="[^"]*")?',
                       'class="partner-slider" data-plaatsing="blog" data-onderwerp="%s"' % cat["slug"], tekst)
        pad.write_text(tekst, encoding="utf-8")


def filter_blok(bedrijven, cat):
    """Knoppen om op kenmerk te filteren (assets/js/filter.js); alleen kenmerken die bij minstens twee bedrijven voorkomen."""
    tel = {}
    for b in bedrijven:
        for k in b.get("kenmerken") or []:
            tel[k] = tel.get(k, 0) + 1
    knoppen = sorted((k for k, n in tel.items() if n >= 2), key=lambda k: (-tel[k], k))
    if not knoppen:
        return ""
    return ('        <div class="gidsfilter" id="gidsfilter" data-enkelvoud="%s" data-meervoud="%s">\n          <p class="gidsfilter__kop">Waar zoek je naar?</p>\n          <div class="gidsfilter__knoppen">%s</div>\n'
            '          <p class="gidsfilter__uitkomst" aria-live="polite" hidden></p>\n        </div>\n'
            '        <script src="%sassets/js/filter.js?v=2" defer></script>'
            % (esc(cat["enkelvoud"].lower()), esc(cat["meervoud"]), "".join('<button type="button" data-kenmerk="%s" aria-pressed="false">%s <span>%d</span></button>' % (esc(k), esc(k[0].upper() + k[1:]), tel[k])
                       for k in knoppen), "../../"))


def titel_van(slug_):
    pad = ROOT / slug_ / "index.html"
    if not pad.exists():
        return None
    m = re.search(r"<h1[^>]*>(.*?)</h1>", pad.read_text(encoding="utf-8"), re.S)
    return html.unescape(re.sub(r"<[^>]+>", "", m.group(1))).strip() if m else None


def scan_toepassen(bedrijven, pad, eigen_tekst=False):
    """Teksten uit tools/bedrijven_scan.py: een voorstel komt als concept (noindex) op de pagina, goedgekeurd gaat Google in.
    eigen_tekst: bedrijven met een tekst uit de oude gids houden die tot de redactie het voorstel goedkeurt;
    kenmerken en openingstijden krijgen ze wel meteen."""
    scan = json.loads(pad.read_text(encoding="utf-8")) if pad.exists() else {}
    for b in bedrijven:
        s = scan.get(b["slug"], {})
        if s.get("status") not in ("voorstel", "goedgekeurd") or not s.get("tekst") or not s.get("lijkt_actief", True):
            continue
        if eigen_tekst and s["status"] != "goedgekeurd":
            b["tijden_site"] = b.get("tijden_site") or s.get("openingstijden", "")
            b["kenmerken"] = s.get("kenmerken", [])
            continue
        b["tekst"] = "\n".join("<p>%s</p>" % esc(a.strip()) for a in re.split(r"\n\s*\n", s["tekst"]) if a.strip())
        b["concept"] = s["status"] != "goedgekeurd"
        b["tijden_site"] = s.get("openingstijden", "")
        b["kenmerken"] = s.get("kenmerken", [])
        b["keuken"] = s.get("keuken") or b.get("keuken", "")


def foto_url(foto, root):
    """Foto's van aanmeldingen staan in de repo (assets/uploads/...); die krijgen het pad naar de root ervoor."""
    return foto if not foto or re.match(r"https?://", foto) else root + foto


def correcties_toepassen(bedrijven, pad):
    """Correcties van de redactie (data/bedrijvengids-correcties.json): naam, adres, postcode, ligging, extra vestiging."""
    corr = json.loads(pad.read_text(encoding="utf-8")) if pad.exists() else {}
    for b in bedrijven:
        b.update({k: v for k, v in corr.get(b["slug"], {}).items() if k in ("naam", "adres", "postcode", "plaats", "lat", "lon", "extra_vestiging")})


def websites_toepassen(bedrijven, pad):
    """Uitkomst van tools/websites_controleren.py: een dode site geen link, een doorgestuurde site het nieuwe adres."""
    controle = json.loads(pad.read_text(encoding="utf-8")) if pad.exists() else {}
    for b in bedrijven:
        c = controle.get(b["slug"])
        if not c or c.get("website") != b.get("website"):
            continue   # intussen een ander adres: eerst opnieuw controleren
        if not c["werkt"]:
            b["website"] = ""
        elif c.get("eind_url") and domein(c["eind_url"]) != domein(b["website"]) and "?" not in c["eind_url"]:
            b["website"] = c["eind_url"]


def wijzigingen_toepassen(bedrijven, pad):
    """Door de redactie goedgekeurde wijzigingen via Dit is mijn bedrijf (tools/aanmeldingen.py). Die gaan voor
    op alles wat we zelf verzamelden (oude gids, OpenStreetMap, websitescan)."""
    wijz = json.loads(pad.read_text(encoding="utf-8")) if pad.exists() else {}
    for b in bedrijven:
        w = wijz.get(b["slug"])
        if not w:
            continue
        for veld, doel in (("bedrijf", "naam"), ("adres", "adres"), ("postcode", "postcode"), ("plaats", "plaats"),
                           ("site", "website"), ("telefoon", "telefoon"), ("bedrijfsmail", "email"), ("foto", "foto")):
            if w.get(veld):
                b[doel] = w[veld]
        if w.get("omschrijving"):
            b["tekst"] = "\n".join("<p>%s</p>" % esc(a.strip()).replace("\n", "<br>") for a in re.split(r"\n\s*\n", w["omschrijving"]) if a.strip())
            b["concept"] = False
        if w.get("openingstijden"):
            b["openingstijden"] = []
            b["tijden_site"] = w["openingstijden"]
            b["tijden_bron"] = "volgens het bedrijf"
        b["geclaimd"] = True


def vermeldingen(bedrijven, cat):
    """Wat er nu op de site staat, per bedrijf; Code.gs zet dit naast een wijziging via Dit is mijn bedrijf."""
    uit = {}
    for b in bedrijven:
        tijden = b.get("tijden_site") or "\n".join("%s %s" % (DAGEN[i], t or "onbekend") for i, t in enumerate(b["openingstijden"]))
        tekst = html.unescape(re.sub(r"<[^>]+>", "", re.sub(r"</(p|h\d|li)>", "\n\n", b["tekst"] or ""))).strip()
        uit[b["slug"]] = {"bedrijf": b["naam"], "categorie": cat["enkelvoud"], "adres": b["adres"], "postcode": b["postcode"] or "",
                          "plaats": b["plaats"] or "", "site": b.get("website") or "", "telefoon": b.get("telefoon") or "",
                          "bedrijfsmail": b.get("email") or "", "openingstijden": tijden,
                          "omschrijving": re.sub(r"\n{3,}", "\n\n", tekst), "foto": foto_url(b["foto"], SITE + "/") or "",
                          "url": "%s/bedrijvengids/%s/" % (SITE, b["slug"])}
    return uit


def doorverwijzen(b, cat):
    """De pagina van een verdwenen bedrijf stuurt door naar de categorie (ook in _redirects voor de echte server)."""
    map_ = ROOT / "bedrijvengids" / b["slug"]
    map_.mkdir(parents=True, exist_ok=True)
    tekst = DOORVERWIJZING % {"titel": esc(cat["naam"]), "url": "%s/bedrijvengids-categorie/%s/" % (SITE, cat["slug"]),
                              "pad": "../../bedrijvengids-categorie/%s/" % cat["slug"]}
    (map_ / "index.html").write_text(tekst.replace("Dit artikel is samengevoegd met", "Dit bedrijf staat niet meer in onze gids. Bekijk de"),
                                     encoding="utf-8")


def schrijf_redirects(weg, oude_categorieen):
    """Blok "# bedrijvengids" in _redirects, vóór het blok van tools/agenda.py (dat alles erna opnieuw schrijft).
    weg: (bedrijf, categorie); oude_categorieen: (oude Listdom-categorie, nieuwe categorie)."""
    pad = ROOT / "_redirects"
    tekst = pad.read_text(encoding="utf-8") if pad.exists() else ""
    agenda = tekst[tekst.index("# agenda"):] if "# agenda" in tekst else ""
    kop_ = tekst.split("# bedrijvengids")[0].split("# agenda")[0].rstrip("\n")
    regels = ["# bedrijvengids (tools/bedrijvengids.py)"]
    regels += ["/bedrijvengids/%s/ /bedrijvengids-categorie/%s/ 301" % (b["slug"], cat["slug"]) for b, cat in sorted(weg, key=lambda x: x[0]["slug"])]
    regels += ["/bedrijvengids-categorie/%s/ /bedrijvengids-categorie/%s/ 301" % x for x in oude_categorieen]
    pad.write_text("\n".join(x for x in (kop_, "\n".join(regels), agenda.rstrip("\n")) if x) + "\n", encoding="utf-8")


def schrijf(pad, tekst):
    map_ = ROOT / pad
    map_.mkdir(parents=True, exist_ok=True)
    (map_ / "index.html").write_text(tekst, encoding="utf-8")


def niet_in(b, cat, scan):
    """Volgens de scan hoort het bedrijf niet in deze categorie (bijvoorbeeld een cafetaria tussen de restaurants)."""
    return cat["slug"] in (scan.get(b["slug"], {}).get("niet_in") or {})


def main(bron):
    bron = pathlib.Path(bron)
    xml_ = bron / "bron" / "wp-xml" / "bedrijvengids-listdom.xml"
    pad = ROOT / "data" / "bedrijvengids.json"
    opgeslagen = json.loads(pad.read_text(encoding="utf-8")) if pad.exists() else {}
    scan = json.loads((ROOT / "data" / "bedrijvengids-scan.json").read_text(encoding="utf-8"))
    gebruikt, groepen, alle_weg, alle_vermeldingen, gebouwd = set(), {}, [], {}, []
    for cat in CATEGORIEEN:
        csv_ = bron / "advies" / "osm-bedrijvengids" / cat["bron_csv"]
        if xml_.exists() and csv_.exists():
            gids = gids_uit_xml(xml_, cat["listdom"])
            gids, overig = samenvoegen(gids, osm_uit_csv(csv_, cat["soorten"], cat.get("plaatsen", ("Nijmegen",))), gebruikt)
            # Opslaan zoals verzameld, vóór scan, correcties en websitecontrole (die passen de gegevens aan)
            opgeslagen[cat["slug"]] = json.loads(json.dumps({"gids": gids, "overig": overig}))
        elif cat["slug"] in opgeslagen:
            gids, overig = json.loads(json.dumps((opgeslagen[cat["slug"]]["gids"], opgeslagen[cat["slug"]]["overig"])))
        else:
            continue
        # Een bedrijf uit de oude gids kan in meer categorieën staan; het krijgt één pagina (bij de eerste categorie)
        # Hoort het volgens de scan bij een andere categorie, dan valt het hier stil weg (geen doorverwijzing: het
        # komt bij die andere categorie).
        gids = [b for b in gids if b["slug"] not in gebruikt and not niet_in(b, cat, scan)]
        overig = [b for b in overig if b["slug"] not in gebruikt and not niet_in(b, cat, scan)]
        gebruikt.update(b["slug"] for b in gids + overig)
        scan_toepassen(overig, ROOT / "data" / "bedrijvengids-scan.json")
        scan_toepassen(gids, ROOT / "data" / "bedrijvengids-scan.json", eigen_tekst=True)
        correcties_toepassen(gids + overig, ROOT / "data" / "bedrijvengids-correcties.json")
        websites_toepassen(gids + overig, ROOT / "data" / "bedrijvengids-websites.json")
        wijzigingen_toepassen(gids + overig, ROOT / "data" / "bedrijvengids-wijzigingen.json")
        pakketten_toepassen(gids + overig, ROOT / "data" / "bedrijvengids-pakketten.json", datetime.date.today())
        # Zonder werkende website geen vermelding (afgesproken met Frans, 23-10-2026): het bedrijf bestaat dan
        # waarschijnlijk niet meer. Behalve als het betaalt of zelf zijn gegevens heeft aangevuld.
        # Door de redactie of automatisch verwijderd (gestopt, site niet te lezen): status "verwijderd" in de scan.
        weg = [b for b in gids + overig if scan.get(b["slug"], {}).get("status") == "verwijderd"
               or not (b.get("website") or b.get("uitgelicht") or b.get("geclaimd"))]
        gids = [b for b in gids if b not in weg]
        overig = [b for b in overig if b not in weg]
        for b in weg:
            doorverwijzen(b, cat)
        alle_weg += [(b, cat) for b in weg]
        alle_vermeldingen.update(vermeldingen(gids + overig, cat))
        gebouwd.append((cat, gids, overig))
        print("%s: %d uit de gids, %d aangevuld, %d niet (meer) in de gids" % (cat["slug"], len(gids), len(overig), len(weg)))
    # Betalende bedrijven kunnen ook bij andere categorieën staan ("ook_in" in data/bedrijvengids-pakketten.json): daar
    # alleen met hun kaart, de pagina blijft bij de eigen categorie
    for cat, gids, overig in gebouwd:
        extra = [b for c, g, o in gebouwd if c is not cat for b in g + o if cat["slug"] in b.get("ook_in", [])]
        artikelen = [(s_, titel_van(s_)) for s_ in cat["artikelen"] if titel_van(s_)]
        schrijf("bedrijvengids-categorie/%s" % cat["slug"], categorie_pagina(cat, gids, overig + extra, artikelen))
        for b in gids + overig:
            anderen = [x for x in gids if x is not b] + [x for x in overig if x is not b]
            schrijf("bedrijvengids/%s" % b["slug"], bedrijf_pagina(b, cat, anderen))
        blog_blokken(cat, gids + overig + extra)
        groepen.setdefault(cat["groep"], []).append((cat, gids, overig + extra))
    if xml_.exists():
        pad.write_text(json.dumps(opgeslagen, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    schrijf_redirects(alle_weg, [(oud, cat["slug"]) for cat in CATEGORIEEN for oud in sorted(cat["listdom"]) if oud != cat["slug"]])
    (ROOT / "data" / "bedrijvengids-vermeldingen.json").write_text(
        json.dumps(alle_vermeldingen, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    schrijf("bedrijvengids", start_pagina(list(groepen.items())))
    # Pagina's die bij geen enkele categorie meer horen en geen doorverwijzing hebben (bijvoorbeeld een dubbel, of een
    # cafetaria die volgens de scan bij afhaal hoort) haal ik weg; ze zijn nooit als echte vermelding online geweest
    bewaren = {b["slug"] for _, gids, overig in (x for cats in groepen.values() for x in cats) for b in gids + overig}
    bewaren |= {b["slug"] for b, _ in alle_weg}
    for map_ in (ROOT / "bedrijvengids").iterdir():
        if map_.is_dir() and map_.name not in bewaren:
            shutil.rmtree(map_)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "/mnt/project-files")
