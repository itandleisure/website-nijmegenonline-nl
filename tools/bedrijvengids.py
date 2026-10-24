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
import hashlib
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
from import_wordpress import DOORVERWIJZING, SITE, VOET, datum_nl as datum_tijd_nl, esc, kop, samenvatting, schoon  # noqa: E402
import nieuws  # noqa: E402

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
}, {
    "slug": "aannemersbedrijf",
    "listdom": set(),
    "bron_csv": "aannemersbedrijf-aangevuld.csv",
    "plaatsen": {"Lent", "Nijmegen", "Oosterhout"},
    "naam": "Aannemers en verbouw in Nijmegen",
    "enkelvoud": "Aannemer",
    "groep": "Wonen en klussen",
    "soorten": {"Aannemer"},
    "schema": "GeneralContractor",
    "beschrijving": "Aannemers, bouw- en klusbedrijven in Nijmegen: verbouwen, renoveren, een nieuwe badkamer of keuken en verduurzamen.",
    "intro": "<p>Een aanbouw, een nieuwe badkamer of je jarendertigwoning in Oost verduurzamen: met de juiste aannemer gaat een verbouwing een stuk soepeler. In Nijmegen zitten grote bouwbedrijven, kleine aannemers en klusbedrijven voor de kleinere klussen.</p><p>Op deze pagina vind je alle aannemers in Nijmegen.</p>",
    "faq": [
        ("Hoe vind ik een goede aannemer in Nijmegen?",
         "Vraag bij twee of drie aannemers een offerte op en vraag naar eerdere projecten in de buurt. Filter hieronder op het soort werk, zoals badkamer of verduurzamen."),
        ("Heb ik een vergunning nodig voor een verbouwing?",
         "Voor veel kleine verbouwingen niet, voor een aanbouw of dakkapel soms wel. Check het Omgevingsloket of vraag het je aannemer."),
    ],
    "artikelen": ["vind-de-juiste-aannemer-voor-het-verduurzamen-van-jouw-woning-in-nijmegen", "verbouwen-in-nijmegen-met-weinig-ruimte-voor-de-deur", "een-frisse-start-begint-in-je-eigen-badkamer"],
    "blogs": ["vind-de-juiste-aannemer-voor-het-verduurzamen-van-jouw-woning-in-nijmegen", "verbouwen-in-nijmegen-met-weinig-ruimte-voor-de-deur", "een-frisse-start-begint-in-je-eigen-badkamer", "een-keuken-waar-je-echt-wilt-koken-zo-pak-je-dat-aan", "maak-je-huis-in-nijmegen-mooier-met-een-lavasteen-gietvloer", "pvc-vloer-bestellen-met-legservice-die-je-planning-volgt", "een-woning-in-nijmegen-zorg-dat-deze-zaken-geregeld-zijn"],
    "meervoud": "aannemers",
    "blogonderwerp": "verbouwen en wonen",
    "filtervoorbeeld": "badkamer, renovatie of verduurzamen",
    "voorbeeld": {"naam": "Jouw bouwbedrijf", "foto": "assets/uploads/2023/05/nijmegen-aannemer-533x400.webp", "kenmerken": ["verbouwen", "verduurzamen"], "actie": "Gratis advies aan huis"},
    "knop_voorbeeld": "offerte aanvragen, projecten, bellen",
}, {
    "slug": "schilder",
    "listdom": {"schilder", "stukadoor"},
    "bron_csv": "schilder-aangevuld.csv",
    "plaatsen": {"Lent", "Nijmegen", "Oosterhout"},
    "naam": "Schilders en stukadoors in Nijmegen",
    "enkelvoud": "Schilder",
    "groep": "Wonen en klussen",
    "soorten": {"Schilder"},
    "schema": "HousePainter",
    "beschrijving": "Schilders, stukadoors en behangers in Nijmegen, voor binnen- en buitenwerk.",
    "intro": "<p>Je kozijnen toe aan een nieuwe laag, strak stucwerk in je woonkamer of een monumentaal pand in de binnenstad dat met zorg geschilderd moet worden: in Nijmegen zijn genoeg vakmensen die het voor je doen.</p><p>Op deze pagina vind je alle schilders en stukadoors in Nijmegen.</p>",
    "faq": [
        ("Wanneer laat ik mijn huis buiten schilderen?",
         "Het liefst tussen april en oktober, bij droog weer boven de 10 graden. Goede schilders zijn in het voorjaar snel volgeboekt."),
        ("Doet een schilder ook stucwerk?",
         "Sommige wel. Filter op stucwerk."),
    ],
    "artikelen": [],
    "blogs": [],
    "meervoud": "schilders",
    "blogonderwerp": "wonen en klussen",
    "filtervoorbeeld": "binnen, buiten of stucwerk",
    "voorbeeld": {"naam": "Jouw schildersbedrijf", "foto": "assets/uploads/2023/05/nijmegen-aannemer-533x400.webp", "kenmerken": ["buiten", "houtrot"], "actie": "Gratis kleuradvies bij je offerte"},
    "knop_voorbeeld": "offerte aanvragen, bellen, whatsapp",
}, {
    "slug": "loodgieter",
    "listdom": {"installatietechniek"},
    "bron_csv": "loodgieter-aangevuld.csv",
    "plaatsen": {"Lent", "Nijmegen", "Oosterhout"},
    "naam": "Loodgieters en installateurs in Nijmegen",
    "enkelvoud": "Loodgieter",
    "groep": "Wonen en klussen",
    "soorten": {"Loodgieter"},
    "schema": "Plumber",
    "beschrijving": "Loodgieters en installateurs in Nijmegen: lekkages, cv-ketels, warmtepompen, badkamers en riolering.",
    "intro": "<p>Een lekkende kraan, een cv-ketel die het opgeeft of plannen voor een warmtepomp: daar heb je een loodgieter of installateur voor. In Nijmegen zitten bedrijven die ook 's avonds en in het weekend komen.</p><p>Op deze pagina vind je alle loodgieters en installateurs in Nijmegen.</p>",
    "faq": [
        ("Is er een loodgieter in Nijmegen die 24 uur per dag komt?",
         "Ja, filter op 24 uur service."),
        ("Wie installeert een warmtepomp in Nijmegen?",
         "Filter op warmtepomp voor installateurs die dat doen."),
    ],
    "artikelen": ["help-mijn-douche-overstroomt-waar-vind-ik-een-loodgieter-in-nijmegen"],
    "blogs": ["help-mijn-douche-overstroomt-waar-vind-ik-een-loodgieter-in-nijmegen", "met-deze-5-tips-bespaar-je-echt-op-jouw-energierekening"],
    "meervoud": "loodgieters",
    "blogonderwerp": "wonen en klussen",
    "filtervoorbeeld": "lekkage, cv-ketel of warmtepomp",
    "voorbeeld": {"naam": "Jouw installatiebedrijf", "foto": "assets/uploads/2023/05/nijmegen-loodgieter-533x400.webp", "kenmerken": ["cv-ketel", "24 uur service"], "actie": "Gratis advies over een warmtepomp"},
    "knop_voorbeeld": "storing melden, offerte, bellen",
}, {
    "slug": "hovenier",
    "listdom": set(),
    "bron_csv": "hovenier-aangevuld.csv",
    "plaatsen": {"Lent", "Nijmegen", "Oosterhout"},
    "naam": "Hoveniers in Nijmegen",
    "enkelvoud": "Hovenier",
    "groep": "Wonen en klussen",
    "soorten": {"Hovenier"},
    "schema": "LocalBusiness",
    "beschrijving": "Hoveniers en tuinarchitecten in Nijmegen voor tuinontwerp, aanleg en onderhoud.",
    "intro": "<p>Een nieuwe tuin, minder tegels en meer groen, of iemand die het onderhoud overneemt: een hovenier helpt je verder. In Nijmegen zitten hoveniers en tuinarchitecten voor kleine stadstuinen en grote tuinen in de dorpen eromheen.</p><p>Op deze pagina vind je alle hoveniers in Nijmegen.</p>",
    "faq": [
        ("Wat kost een hovenier?",
         "Dat hangt af van de klus. Voor aanleg vraag je een offerte op; onderhoud gaat vaak per uur of met een vast contract."),
        ("Helpt een hovenier ook met een tuinontwerp?",
         "Veel hoveniers wel. Filter op tuinontwerp."),
    ],
    "artikelen": ["geen-groene-vingers-kies-dan-voor-een-hovenier"],
    "blogs": ["geen-groene-vingers-kies-dan-voor-een-hovenier"],
    "meervoud": "hoveniers",
    "blogonderwerp": "tuinen",
    "filtervoorbeeld": "tuinontwerp, aanleg of onderhoud",
    "voorbeeld": {"naam": "Jouw hoveniersbedrijf", "foto": "assets/uploads/2023/06/hovenier-in-nijmegen-533x400.webp", "kenmerken": ["tuinontwerp", "tuinaanleg"], "actie": "Gratis tuinadvies aan huis"},
    "knop_voorbeeld": "offerte aanvragen, projecten, bellen",
}, {
    "slug": "zonnepanelen",
    "listdom": set(),
    "bron_csv": "zonnepanelen-aangevuld.csv",
    "plaatsen": {"Lent", "Nijmegen", "Oosterhout"},
    "naam": "Zonnepanelen in Nijmegen",
    "enkelvoud": "Installateur",
    "groep": "Wonen en klussen",
    "soorten": {"Zonnepanelen"},
    "schema": "LocalBusiness",
    "beschrijving": "Installateurs van zonnepanelen, thuisbatterijen en laadpalen in Nijmegen.",
    "intro": "<p>Zonnepanelen op je dak, een thuisbatterij of een laadpaal voor je auto: in Nijmegen zijn installateurs die je adviseren en alles plaatsen.</p><p>Op deze pagina vind je alle installateurs van zonnepanelen in Nijmegen.</p>",
    "faq": [
        ("Lonen zonnepanelen nog in Nijmegen?",
         "Dat hangt af van je dak en je verbruik. Een installateur rekent het voor je uit; vraag naar de terugverdientijd."),
    ],
    "artikelen": ["laat-de-zon-jouw-huis-verwarmen-met-zonnepanelen-in-nijmegen"],
    "blogs": ["laat-de-zon-jouw-huis-verwarmen-met-zonnepanelen-in-nijmegen", "met-deze-5-tips-bespaar-je-echt-op-jouw-energierekening"],
    "meervoud": "installateurs",
    "blogonderwerp": "energie en verduurzamen",
    "filtervoorbeeld": "thuisbatterij of laadpaal",
    "voorbeeld": {"naam": "Jouw installatiebedrijf", "foto": "assets/uploads/2023/06/zonnepanelen-nijmegen-533x400.webp", "kenmerken": ["zonnepanelen", "thuisbatterij"], "actie": "Gratis dakscan"},
    "knop_voorbeeld": "offerte aanvragen, dakscan, bellen",
}, {
    "slug": "meubelmaker",
    "listdom": {"meubelproductie"},
    "bron_csv": "meubelmaker-aangevuld.csv",
    "plaatsen": {"Lent", "Nijmegen", "Oosterhout"},
    "naam": "Meubelmakers in Nijmegen",
    "enkelvoud": "Meubelmaker",
    "groep": "Wonen en klussen",
    "soorten": {"Meubelmaker"},
    "schema": "LocalBusiness",
    "beschrijving": "Meubelmakers, interieurbouwers en stoffeerders in Nijmegen, voor maatwerk en restauratie.",
    "intro": "<p>Een tafel die precies in je kamer past, een kast onder de trap of je oude stoel opnieuw bekleed: Nijmeegse meubelmakers en stoffeerders maken het op maat, in hun eigen werkplaats.</p><p>Op deze pagina vind je alle meubelmakers in Nijmegen.</p>",
    "faq": [
        ("Kan ik een meubel op maat laten maken in Nijmegen?",
         "Ja, filter op maatwerk. Neem afmetingen en foto's mee naar het eerste gesprek."),
    ],
    "artikelen": ["kies-voor-een-unieke-meubels-ambachtelijke-gemaakt-door-de-meubelmaker"],
    "blogs": ["kies-voor-een-unieke-meubels-ambachtelijke-gemaakt-door-de-meubelmaker", "verhuizen-en-de-woonkamer-opnieuw-inrichten"],
    "meervoud": "meubelmakers",
    "blogonderwerp": "meubels en interieur",
    "filtervoorbeeld": "maatwerk, kasten of stoffering",
    "voorbeeld": {"naam": "Jouw werkplaats", "foto": "assets/uploads/2023/06/meubelmaker-nijmegen-533x400.webp", "kenmerken": ["maatwerk", "tafels"], "actie": "Kom langs in de werkplaats"},
    "knop_voorbeeld": "offerte aanvragen, portfolio, bellen",
}, {
    "slug": "makelaar",
    "listdom": {"makelaar"},
    "bron_csv": "makelaar-aangevuld.csv",
    "plaatsen": {"Lent", "Nijmegen", "Oosterhout"},
    "naam": "Makelaars in Nijmegen",
    "enkelvoud": "Makelaar",
    "groep": "Wonen en klussen",
    "soorten": {"Makelaar"},
    "schema": "RealEstateAgent",
    "beschrijving": "Alle makelaars in Nijmegen voor de verkoop, aankoop en verhuur van woningen en bedrijfspanden, en taxaties.",
    "intro": "<p>Je huis verkopen, een aankoopmakelaar in een krappe markt of een taxatie voor je hypotheek: in Nijmegen werken veel makelaars, van grote kantoren tot zelfstandige makelaars die hun wijk goed kennen.</p><p>Op deze pagina vind je alle makelaars in Nijmegen.</p>",
    "faq": [
        ("Heb ik een aankoopmakelaar nodig in Nijmegen?",
         "In Nijmegen is de woningmarkt krap. Een aankoopmakelaar kent de buurt, de prijzen en de verkopende makelaars, en helpt je bij het bieden."),
        ("Kan ik bij een makelaar terecht voor een taxatie?",
         "Ja, filter op taxatie."),
    ],
    "artikelen": ["huis-kopen-in-nijmegen-met-een-hypotheek", "wonen-in-nijmegen-waar-moet-je-aan-denken"],
    "blogs": ["wonen-in-nijmegen-waar-moet-je-aan-denken", "wonen-in-nijmegen-waarom-een-woning-zoeken-hier-aanvoelt-als-daten-in-een-overvolle-club", "kamernets-gids-voor-het-vinden-van-huurwoningen-in-nijmegen", "een-woning-in-nijmegen-zorg-dat-deze-zaken-geregeld-zijn"],
    "meervoud": "makelaars",
    "blogonderwerp": "wonen in Nijmegen",
    "filtervoorbeeld": "verkoop, aankoop of taxatie",
    "voorbeeld": {"naam": "Jouw makelaarskantoor", "foto": "assets/uploads/2023/01/huis-kopen-in-nijmegen-533x400.webp", "kenmerken": ["verkoop", "taxatie"], "actie": "Gratis waardebepaling van je woning"},
    "knop_voorbeeld": "waardebepaling, aanbod, bellen",
}, {
    "slug": "dakdekker",
    "listdom": set(),
    "bron_csv": "dakdekker-aangevuld.csv",
    "plaatsen": {"Lent", "Nijmegen", "Oosterhout"},
    "naam": "Dakdekkers in Nijmegen",
    "enkelvoud": "Dakdekker",
    "groep": "Wonen en klussen",
    "soorten": {"Dakdekker"},
    "schema": "RoofingContractor",
    "beschrijving": "Dakdekkers in Nijmegen voor platte daken, pannendaken, lekkages, dakgoten en dakisolatie.",
    "intro": "<p>Een lekkend dak na een flinke bui, dakgoten die verstopt zitten of een plat dak dat geïsoleerd moet worden: dan bel je een dakdekker. In Nijmegen zitten dakdekkers voor zowel kleine reparaties als een heel nieuw dak.</p><p>Op deze pagina vind je alle dakdekkers in Nijmegen.</p>",
    "faq": [
        ("Komt een dakdekker ook met spoed?",
         "Bij een lekkage vaak wel. Filter op lekkage en vraag naar spoedservice."),
    ],
    "artikelen": [],
    "blogs": [],
    "meervoud": "dakdekkers",
    "blogonderwerp": "wonen en klussen",
    "filtervoorbeeld": "platte daken, lekkage of dakisolatie",
    "voorbeeld": {"naam": "Jouw dakdekkersbedrijf", "foto": "assets/uploads/2023/05/nijmegen-aannemer-533x400.webp", "kenmerken": ["platte daken", "lekkage"], "actie": "Gratis dakinspectie"},
    "knop_voorbeeld": "offerte aanvragen, spoed, bellen",
}, {
    "slug": "slotenmaker",
    "listdom": set(),
    "bron_csv": "slotenmaker-aangevuld.csv",
    "plaatsen": {"Lent", "Nijmegen", "Oosterhout"},
    "naam": "Slotenmakers in Nijmegen",
    "enkelvoud": "Slotenmaker",
    "groep": "Wonen en klussen",
    "soorten": {"Slotenmaker"},
    "schema": "Locksmith",
    "beschrijving": "Slotenmakers in Nijmegen: buitengesloten, inbraakbeveiliging, sloten met politiekeurmerk en sleutels.",
    "intro": "<p>Buitengesloten, je sleutels kwijt of je huis beter beveiligen: een slotenmaker helpt je snel verder. In Nijmegen zijn slotenmakers die dag en nacht komen.</p><p>Op deze pagina vind je alle slotenmakers in Nijmegen.</p>",
    "faq": [
        ("Ik ben buitengesloten, wat nu?",
         "Bel een slotenmaker in de buurt en vraag vooraf naar de voorrijkosten en het tarief. Let op: niet elke slotenmaker in Google zit echt in Nijmegen."),
    ],
    "artikelen": ["de-onmisbare-rol-van-slotenmakers-in-nijmegen"],
    "blogs": ["de-onmisbare-rol-van-slotenmakers-in-nijmegen"],
    "meervoud": "slotenmakers",
    "blogonderwerp": "veilig wonen",
    "filtervoorbeeld": "24 uur service of inbraakbeveiliging",
    "voorbeeld": {"naam": "Jouw slotenmakerij", "foto": "assets/uploads/2025/11/De-onmisbare-rol-van-slotenmakers-in-Nijmegen-533x400.webp", "kenmerken": ["24 uur service", "politiekeurmerk"], "actie": "Gratis veiligheidscheck van je woning"},
    "knop_voorbeeld": "direct bellen, offerte, route",
}, {
    "slug": "elektricien",
    "listdom": set(),
    "bron_csv": "elektricien-aangevuld.csv",
    "plaatsen": {"Lent", "Nijmegen", "Oosterhout"},
    "naam": "Elektriciens in Nijmegen",
    "enkelvoud": "Elektricien",
    "groep": "Wonen en klussen",
    "soorten": {"Elektricien"},
    "schema": "Electrician",
    "beschrijving": "Elektriciens in Nijmegen voor de groepenkast, een laadpaal, verlichting en storingen.",
    "intro": "<p>Een nieuwe groepenkast, een laadpaal bij je huis of een storing die je niet vertrouwt: laat het doen door een elektricien. In Nijmegen zitten elektriciens voor particulieren en bedrijven.</p><p>Op deze pagina vind je alle elektriciens in Nijmegen.</p>",
    "faq": [
        ("Moet een elektricien mijn groepenkast vervangen?",
         "Ja, werk aan de groepenkast hoort bij een erkende installateur. Filter op groepenkast."),
    ],
    "artikelen": [],
    "blogs": [],
    "meervoud": "elektriciens",
    "blogonderwerp": "wonen en klussen",
    "filtervoorbeeld": "groepenkast, laadpaal of storing",
    "voorbeeld": {"naam": "Jouw installatiebedrijf", "foto": "assets/uploads/2022/12/energiezuinige-woning-in-nijmegen-533x400.webp", "kenmerken": ["groepenkast", "laadpaal"], "actie": "Laadpaal inclusief installatie"},
    "knop_voorbeeld": "storing melden, offerte, bellen",
}, {
    "slug": "verhuisbedrijf",
    "listdom": set(),
    "bron_csv": "verhuisbedrijf-aangevuld.csv",
    "plaatsen": {"Lent", "Nijmegen", "Oosterhout"},
    "naam": "Verhuisbedrijven in Nijmegen",
    "enkelvoud": "Verhuisbedrijf",
    "de_woord": False,
    "groep": "Wonen en klussen",
    "soorten": {"Verhuisbedrijf"},
    "schema": "MovingCompany",
    "beschrijving": "Verhuisbedrijven en verhuisliften in Nijmegen, voor particulieren en bedrijven.",
    "intro": "<p>Verhuizen naar een bovenwoning in de binnenstad of een eengezinswoning in Lent: met een verhuisbedrijf of een verhuislift gaat het een stuk sneller.</p><p>Op deze pagina vind je alle verhuisbedrijven in Nijmegen.</p>",
    "faq": [
        ("Heb ik een vergunning nodig voor een verhuislift?",
         "In de binnenstad van Nijmegen vaak wel, voor het plaatsen op de openbare weg. Het verhuisbedrijf regelt dat meestal."),
    ],
    "artikelen": ["verhuizen-en-de-woonkamer-opnieuw-inrichten"],
    "blogs": ["verhuizen-en-de-woonkamer-opnieuw-inrichten"],
    "meervoud": "verhuisbedrijven",
    "blogonderwerp": "verhuizen",
    "filtervoorbeeld": "verhuislift of opslag",
    "voorbeeld": {"naam": "Jouw verhuisbedrijf", "foto": "assets/uploads/2025/01/In-deze-wijken-van-Nijmegen-vind-je-prachtige-nieuwbouw-533x400.webp", "kenmerken": ["verhuislift", "inpakservice"], "actie": "Gratis verhuisdozen bij je verhuizing"},
    "knop_voorbeeld": "offerte aanvragen, bellen, whatsapp",
}, {
    "slug": "schoonmaakbedrijf",
    "listdom": set(),
    "bron_csv": "schoonmaakbedrijf-aangevuld.csv",
    "plaatsen": {"Lent", "Nijmegen", "Oosterhout"},
    "naam": "Schoonmaak en glazenwassers in Nijmegen",
    "enkelvoud": "Schoonmaakbedrijf",
    "de_woord": False,
    "groep": "Wonen en klussen",
    "soorten": {"Schoonmaak"},
    "schema": "LocalBusiness",
    "beschrijving": "Schoonmaakbedrijven en glazenwassers in Nijmegen voor kantoren, woningen en een eindschoonmaak.",
    "intro": "<p>Een schoon kantoor, een eindschoonmaak na de verhuizing of gewoon weer heldere ramen: in Nijmegen zijn schoonmaakbedrijven en glazenwassers voor bedrijven en particulieren.</p><p>Op deze pagina vind je alle schoonmaakbedrijven en glazenwassers in Nijmegen.</p>",
    "faq": [
        ("Is er een glazenwasser in Nijmegen?",
         "Ja, filter op glazenwassen."),
        ("Doen schoonmaakbedrijven ook een eindschoonmaak?",
         "Veel wel. Filter op eindschoonmaak."),
    ],
    "artikelen": [],
    "blogs": [],
    "meervoud": "schoonmaakbedrijven",
    "blogonderwerp": "wonen en klussen",
    "filtervoorbeeld": "kantoren, glazenwassen of eindschoonmaak",
    "voorbeeld": {"naam": "Jouw schoonmaakbedrijf", "foto": "assets/uploads/2022/12/energiezuinige-woning-in-nijmegen-533x400.webp", "kenmerken": ["kantoren", "glazenwassen"], "actie": "Eerste schoonmaakbeurt met korting"},
    "knop_voorbeeld": "offerte aanvragen, bellen, whatsapp",
}, {
    "slug": "kapper",
    "listdom": {"kapper"},
    "bron_csv": "kapper-aangevuld.csv",
    "plaatsen": {"Lent", "Nijmegen", "Oosterhout"},
    "naam": "Kappers en barbers in Nijmegen",
    "enkelvoud": "Kapper",
    "groep": "Beauty en wellness",
    "soorten": {"Kapper"},
    "schema": "HairSalon",
    "beschrijving": "Alle kappers en barbershops in Nijmegen: knippen, kleuren, krullen en bruidskapsels, met adressen en online boeken.",
    "intro": "<p>Even bijknippen tussen de middag, een nieuwe kleur of een strakke fade bij de barber: Nijmegen heeft kapsalons in elke wijk, van de vertrouwde kapper om de hoek tot salons die zich toeleggen op krullen of afrohaar.</p><p>Op deze pagina vind je alle kappers en barbers in Nijmegen.</p>",
    "faq": [
        ("Kan ik bij een kapper in Nijmegen terecht zonder afspraak?",
         "Bij een aantal kappers en barbershops wel. Filter op zonder afspraak."),
        ("Is er een krullenkapper in Nijmegen?",
         "Ja, filter op krullen voor kappers die gespecialiseerd zijn in krullend haar."),
        ("Waar vind ik een bruidskapper?",
         "Filter op bruidskapsel. Plan een proefkapsel ruim voor de bruiloft."),
    ],
    "artikelen": ["kapper-nijmegen-top-kapsalons-voor-knippen-kleuren-en-styling", "de-perfecte-krul-deze-haarstylistes-maken-jouw-kapsel-tot-een-waar-plaatje"],
    "blogs": ["kapper-nijmegen-top-kapsalons-voor-knippen-kleuren-en-styling", "de-perfecte-krul-deze-haarstylistes-maken-jouw-kapsel-tot-een-waar-plaatje", "haarstyling-tips-schitter-met-een-unieke-look", "voorkom-een-bad-hair-day-met-deze-fantastische-haarverzorgingstips", "wie-verzorgt-je-haar-als-je-op-leeftijd-bent", "hoe-ga-je-om-met-veranderingen-van-je-haar-tijdens-een-zwangerschap"],
    "meervoud": "kappers",
    "blogonderwerp": "haar en kapsels",
    "filtervoorbeeld": "barber, krullen of zonder afspraak",
    "voorbeeld": {"naam": "Jouw kapsalon", "foto": "assets/uploads/2023/08/ga-voor-die-stijlvolle-look-bij-de-kapper-in-nijmegen-533x400.webp", "kenmerken": ["knippen", "online boeken"], "actie": "10% korting op je eerste knipbeurt"},
    "knop_voorbeeld": "online boeken, bellen, route",
}, {
    "slug": "massagesalon",
    "listdom": {"massagesalon", "wellness"},
    "bron_csv": "massagesalon-aangevuld.csv",
    "plaatsen": {"Lent", "Nijmegen", "Oosterhout"},
    "naam": "Massage en wellness in Nijmegen",
    "enkelvoud": "Massagesalon",
    "groep": "Beauty en wellness",
    "soorten": {"Massage"},
    "schema": "HealthAndBeautyBusiness",
    "beschrijving": "Massagesalons, masseurs, sauna's en wellness in Nijmegen: ontspanningsmassage, sportmassage, hot stone, sauna en arrangementen.",
    "intro": "<p>Na een drukke week even helemaal niets, of juist een stevige sportmassage na het hardlopen: in Nijmegen zijn massagesalons en masseurs voor elke behoefte, sommige komen ook bij je thuis. Voor een hele dag ontspannen zijn er sauna's en wellness met arrangementen.</p><p>Op deze pagina vind je alle massagesalons en wellness in Nijmegen.</p>",
    "faq": [
        ("Welke massage past bij mij?",
         "Voor ontspanning kies je een ontspanningsmassage of hot stone; bij spierpijn een sportmassage. Lees ook ons artikel over welke massage bij je past."),
        ("Kan ik een massage cadeau geven?",
         "Veel salons verkopen cadeaubonnen. Filter op cadeaubon."),
        ("Is er een sauna in Nijmegen?",
         "Ja, filter op sauna. Er zijn ook privé-sauna's die je per dagdeel huurt."),
    ],
    "artikelen": ["massagesalon-nijmegen-zelfzorg-en-pure-ontspanning", "hoe-ontdek-je-welke-massage-het-beste-werkt-voor-jou", "hot-stone-meer-top-massages-in-nijmegen"],
    "blogs": ["massagesalon-nijmegen-zelfzorg-en-pure-ontspanning", "hoe-ontdek-je-welke-massage-het-beste-werkt-voor-jou", "hot-stone-meer-top-massages-in-nijmegen", "massagetherapie-in-nijmegen-voor-gezondheid-welzijn", "ontspannen-en-herstellen-wat-je-kunt-verwachten-bij-een-massagesalon-in-nijmegen"],
    "meervoud": "massagesalons",
    "blogonderwerp": "massage en ontspanning",
    "filtervoorbeeld": "sportmassage, sauna of aan huis",
    "voorbeeld": {"naam": "Jouw massagesalon", "foto": "assets/uploads/2023/08/massagesalon-in-nijmegen-533x400.webp", "kenmerken": ["ontspanningsmassage", "online boeken"], "actie": "Kennismakingsmassage met korting"},
    "knop_voorbeeld": "online boeken, cadeaubon, bellen",
}, {
    "slug": "permanente-make-up",
    "listdom": set(),
    "bron_csv": "permanente-make-up-aangevuld.csv",
    "plaatsen": {"Lent", "Nijmegen", "Oosterhout"},
    "naam": "Permanente make-up in Nijmegen",
    "enkelvoud": "Studio",
    "groep": "Beauty en wellness",
    "soorten": {"Permanente make-up"},
    "schema": "HealthAndBeautyBusiness",
    "beschrijving": "Studio's voor permanente make-up en microblading in Nijmegen: wenkbrauwen, lippen en eyeliner.",
    "intro": "<p>Elke ochtend perfecte wenkbrauwen of een eyeliner die blijft zitten: met permanente make-up of microblading. In Nijmegen werken specialisten die je eerst uitgebreid adviseren.</p><p>Op deze pagina vind je alle studio's voor permanente make-up in Nijmegen.</p>",
    "faq": [
        ("Hoe lang blijft permanente make-up zitten?",
         "Meestal één tot drie jaar, afhankelijk van je huid en de techniek. Een nabehandeling hoort er vaak bij."),
    ],
    "artikelen": ["de-ins-en-outs-van-permanente-make-up-in-nijmegen", "permanente-make-up-de-voordelen-overwegingen"],
    "blogs": ["de-ins-en-outs-van-permanente-make-up-in-nijmegen", "permanente-make-up-de-voordelen-overwegingen", "de-techniek-achter-permanente-make-up-onthuld", "hoe-kan-permanente-make-up-ervoor-zorgen-dat-je-zelfverzekerder-wordt", "permanente-make-up-alleen-voor-vrouwen", "permanente-make-up-boost-je-zelfvertrouwen"],
    "meervoud": "studio's",
    "blogonderwerp": "permanente make-up",
    "filtervoorbeeld": "wenkbrauwen, lippen of microblading",
    "voorbeeld": {"naam": "Jouw PMU-studio", "foto": "assets/uploads/2023/09/De-ins-en-outs-van-permanente-make-up-in-Nijmegen-533x400.webp", "kenmerken": ["wenkbrauwen", "microblading"], "actie": "Gratis adviesgesprek"},
    "knop_voorbeeld": "afspraak maken, portfolio, whatsapp",
}, {
    "slug": "schoonheidssalon",
    "listdom": {"beauty-wellness", "schoonheidsspecialist"},
    "bron_csv": "schoonheidssalon-aangevuld.csv",
    "plaatsen": {"Lent", "Nijmegen", "Oosterhout"},
    "naam": "Schoonheidssalons in Nijmegen",
    "enkelvoud": "Schoonheidssalon",
    "groep": "Beauty en wellness",
    "soorten": {"Schoonheidssalon"},
    "schema": "BeautySalon",
    "beschrijving": "Schoonheidssalons in Nijmegen voor gezichtsbehandelingen, huidverbetering, wimpers en wenkbrauwen, harsen en make-up.",
    "intro": "<p>Een gezichtsbehandeling, je wimpers laten liften of je huid laten verbeteren: in Nijmegen zitten schoonheidssalons en huidspecialisten die je advies geven en je even laten ontspannen.</p><p>Op deze pagina vind je alle schoonheidssalons in Nijmegen.</p>",
    "faq": [
        ("Wat doet een schoonheidsspecialist?",
         "Gezichtsbehandelingen, huidverbetering, harsen, wimpers en wenkbrauwen en soms make-up. Filter op wat je zoekt."),
        ("Kan ik online een afspraak maken?",
         "Bij veel salons wel. Filter op online boeken."),
    ],
    "artikelen": [],
    "blogs": [],
    "meervoud": "schoonheidssalons",
    "blogonderwerp": "beauty",
    "filtervoorbeeld": "huidverbetering, wimpers of harsen",
    "voorbeeld": {"naam": "Jouw salon", "foto": "assets/uploads/2023/09/jullie-nagelsalon-in-nijmegen-533x400.webp", "kenmerken": ["gezichtsbehandeling", "online boeken"], "actie": "Proefbehandeling met korting"},
    "knop_voorbeeld": "online boeken, behandelingen, bellen",
}, {
    "slug": "nagelsalon",
    "listdom": {"nagelsalon"},
    "bron_csv": "nagelsalon-aangevuld.csv",
    "plaatsen": {"Lent", "Nijmegen", "Oosterhout"},
    "naam": "Nagelsalons in Nijmegen",
    "enkelvoud": "Nagelsalon",
    "groep": "Beauty en wellness",
    "soorten": {"Nagelsalon"},
    "schema": "NailSalon",
    "beschrijving": "Nagelsalons in Nijmegen voor gellak, acryl, nail art en manicure.",
    "intro": "<p>Gellak dat weken mooi blijft, een volledige set acryl of nail art voor een feestje: in Nijmegen vind je nagelstylisten in kleine studio's en drukke salons.</p><p>Op deze pagina vind je alle nagelsalons in Nijmegen.</p>",
    "faq": [
        ("Hoe kies ik een goede nagelsalon?",
         "Let op hygiëne en vraag naar de producten. Lees onze tips over het kiezen van een nagelsalon."),
        ("Kan ik zonder afspraak terecht?",
         "Bij sommige salons wel. Filter op zonder afspraak."),
    ],
    "artikelen": ["de-juiste-nagelsalon-in-nijmegen-kiezen-tips-hier", "nagelverlenging-in-nijmegen-wat-zijn-de-keuzes"],
    "blogs": ["de-juiste-nagelsalon-in-nijmegen-kiezen-tips-hier", "nagelverlenging-in-nijmegen-wat-zijn-de-keuzes", "perfecte-nagels-tips-van-nijmeegse-nagelpros", "waar-worden-jouw-nagels-verzorgd-in-nijmegen", "ken-je-deze-feiten-en-fabels-al-over-nagelverzorging"],
    "meervoud": "nagelsalons",
    "blogonderwerp": "nagels",
    "filtervoorbeeld": "gellak, acryl of nail art",
    "voorbeeld": {"naam": "Jouw nagelstudio", "foto": "assets/uploads/2023/09/jullie-nagelsalon-in-nijmegen-533x400.webp", "kenmerken": ["gellak", "nail art"], "actie": "Gratis nail art bij een nieuwe set"},
    "knop_voorbeeld": "online boeken, portfolio, whatsapp",
}, {
    "slug": "pedicure",
    "listdom": set(),
    "bron_csv": "pedicure-aangevuld.csv",
    "plaatsen": {"Lent", "Nijmegen", "Oosterhout"},
    "naam": "Pedicures in Nijmegen",
    "enkelvoud": "Pedicure",
    "groep": "Beauty en wellness",
    "soorten": {"Pedicure"},
    "schema": "HealthAndBeautyBusiness",
    "beschrijving": "Pedicures en podotherapeuten in Nijmegen, ook medisch pedicure, diabetische voet en aan huis.",
    "intro": "<p>Verzorgde voeten, eelt en likdoorns weg of zorg voor je voeten als je diabetes hebt: een pedicure helpt je. In Nijmegen zijn pedicures met een eigen praktijk en pedicures die bij je thuis komen.</p><p>Op deze pagina vind je alle pedicures in Nijmegen.</p>",
    "faq": [
        ("Wat is een medisch pedicure?",
         "Een pedicure met extra opleiding voor risicovoeten, bijvoorbeeld bij diabetes of reuma. Filter op medisch pedicure."),
        ("Komt een pedicure ook aan huis?",
         "Sommige wel. Filter op aan huis."),
    ],
    "artikelen": ["de-magische-krachten-van-een-pedicure-voetproblemen-opgelost-in-nijmegen", "zorg-voor-je-voeten-het-belang-van-pedicure-voor-diabetici-in-nijmegen"],
    "blogs": ["de-magische-krachten-van-een-pedicure-voetproblemen-opgelost-in-nijmegen", "zorg-voor-je-voeten-het-belang-van-pedicure-voor-diabetici-in-nijmegen", "een-verwenmoment-voor-je-voeten-luxe-pedicurebehandelingen-in-nijmegen", "lees-hier-de-ultieme-voetverzorgingsroutine-voor-je-voeten", "stap-in-de-wereld-van-voetverwennerij"],
    "meervoud": "pedicures",
    "blogonderwerp": "voetverzorging",
    "filtervoorbeeld": "medisch pedicure of aan huis",
    "voorbeeld": {"naam": "Jouw pedicurepraktijk", "foto": "assets/uploads/2023/08/luxe-pedicurebehandelingen-bij-een-pedicure-in-nijmegen-533x400.webp", "kenmerken": ["voetverzorging", "aan huis"], "actie": "Eerste behandeling met korting"},
    "knop_voorbeeld": "afspraak maken, bellen, route",
}, {
    "slug": "tattoo",
    "listdom": set(),
    "bron_csv": "tattoo-aangevuld.csv",
    "plaatsen": {"Lent", "Nijmegen", "Oosterhout"},
    "naam": "Tattoo en piercing in Nijmegen",
    "enkelvoud": "Tattooshop",
    "groep": "Beauty en wellness",
    "soorten": {"Tattoo"},
    "schema": "HealthAndBeautyBusiness",
    "beschrijving": "Tattoostudio's en piercingshops in Nijmegen: fine line, cover-ups, piercings en laserverwijdering.",
    "intro": "<p>Je eerste kleine tattoo, een grote sleeve of een nieuwe piercing: in Nijmegen werken tattoo-artiesten met elk een eigen stijl. Bekijk hun portfolio en plan een gesprek over je ontwerp.</p><p>Op deze pagina vind je alle tattoo- en piercingstudio's in Nijmegen.</p>",
    "faq": [
        ("Hoe kies ik een tattooshop?",
         "Kijk naar de stijl in het portfolio en let op een GGD-vergunning. Een goede artiest neemt de tijd voor je ontwerp."),
    ],
    "artikelen": [],
    "blogs": [],
    "meervoud": "tattooshops",
    "blogonderwerp": "tattoo en piercing",
    "filtervoorbeeld": "fine line, cover-up of piercing",
    "voorbeeld": {"naam": "Jouw tattooshop", "foto": "assets/uploads/2023/08/haarstyling-of-hairstyling-specialisten-in-nijmegen-533x400.webp", "kenmerken": ["tattoo", "fine line"], "actie": "Gratis ontwerpgesprek"},
    "knop_voorbeeld": "afspraak maken, portfolio, instagram",
}, {
    "slug": "uitjes",
    "listdom": {"bedrijfsuitje", "familieuitje", "kinderfeestje", "vriendenuitje", "vriendinnenuitje", "vrije-tijd-en-uitgaan", "vrijgezellenfeest"},
    "bron_csv": "uitjes-aangevuld.csv",
    "plaatsen": {"Lent", "Nijmegen", "Oosterhout"},
    "naam": "Uitjes en activiteiten in Nijmegen",
    "enkelvoud": "Uitje",
    "de_woord": False,
    "groep": "Uitgaan en vrije tijd",
    "soorten": {"Uitje"},
    "schema": "EntertainmentBusiness",
    "beschrijving": "Uitjes en activiteiten in Nijmegen: escape rooms, bowlen, lasergamen, rondvaarten, stadstours, clubs en workshops. Voor vrienden, familie en bedrijfsuitjes.",
    "intro": "<p>Een vrijgezellenfeest, een teamuitje of gewoon een zaterdag met vrienden: in Nijmegen kun je ontsnappen uit een escape room, een rondvaart maken over de Waal, bowlen of de stad ontdekken met een gids.</p><p>Op deze pagina vind je alle uitjes en activiteiten in Nijmegen.</p>",
    "faq": [
        ("Wat kun je doen met een groep in Nijmegen?",
         "Filter op bedrijfsuitje of vrijgezellenfeest voor uitjes die op groepen zijn ingericht."),
        ("Wat doe je in Nijmegen bij slecht weer?",
         "Filter op slecht weer voor binnenactiviteiten, zoals een escape room of bowlen."),
        ("Waar vier je een kinderfeestje in Nijmegen?",
         "Filter op kinderfeestje."),
    ],
    "artikelen": ["5x-een-bijzonder-uitje-in-nijmegen", "teamuitje-nijmegen-spanning-natuur-en-culinair-genieten", "activiteiten-in-nijmegen"],
    "blogs": ["5x-een-bijzonder-uitje-in-nijmegen", "teamuitje-nijmegen-spanning-natuur-en-culinair-genieten", "activiteiten-in-nijmegen", "lekker-uitgaan-in-nijmegen-hier-doe-je-dat"],
    "meervoud": "uitjes",
    "blogonderwerp": "uitjes en activiteiten",
    "filtervoorbeeld": "escape room, bedrijfsuitje of slecht weer",
    "voorbeeld": {"naam": "Jouw uitje", "foto": "assets/uploads/2025/09/teamuitje-nijmegen-escape-game-the-hunt-533x400.webp", "kenmerken": ["bedrijfsuitje", "escape room"], "actie": "Groepskorting vanaf 8 personen"},
    "knop_voorbeeld": "reserveren, groepen, bellen",
}, {
    "slug": "musea",
    "listdom": {"musea"},
    "bron_csv": "musea-aangevuld.csv",
    "plaatsen": {"Lent", "Nijmegen", "Oosterhout"},
    "naam": "Musea in Nijmegen",
    "enkelvoud": "Museum",
    "de_woord": False,
    "groep": "Uitgaan en vrije tijd",
    "soorten": {"Museum"},
    "schema": "Museum",
    "beschrijving": "Alle musea in Nijmegen, de oudste stad van Nederland: van Romeinse geschiedenis tot moderne kunst.",
    "intro": "<p>Nijmegen is de oudste stad van Nederland, en dat zie je terug in de musea: Romeinse vondsten, de Tweede Wereldoorlog, kunst en cultuur van over de hele wereld. Veel musea hebben ook programma's voor kinderen.</p><p>Op deze pagina vind je alle musea in Nijmegen.</p>",
    "faq": [
        ("Kan ik met de Museumkaart naar musea in Nijmegen?",
         "Bij de meeste wel. Filter op museumkaart."),
        ("Welk museum is leuk met kinderen?",
         "Filter op kinderen voor musea met speurtochten of een kinderprogramma."),
    ],
    "artikelen": ["museums-in-nijmegen-wat-ga-jij-ontdekken", "hoe-het-afrika-museum-je-elke-keer-weer-inspireert"],
    "blogs": ["museums-in-nijmegen-wat-ga-jij-ontdekken", "hoe-het-afrika-museum-je-elke-keer-weer-inspireert"],
    "meervoud": "musea",
    "blogonderwerp": "musea",
    "filtervoorbeeld": "kinderen, rondleiding of museumkaart",
    "voorbeeld": {"naam": "Jouw museum", "foto": "assets/uploads/2024/04/vrijheidsmuseum-Grootouders-vertellen-verkleind-bevrijdingsdag-533x400.webp", "kenmerken": ["kinderen", "museumkaart"], "actie": "Gratis rondleiding op zondag"},
    "knop_voorbeeld": "tickets, agenda, route",
}, {
    "slug": "podia",
    "listdom": {"concert", "poppodia", "voorstellingen"},
    "bron_csv": "podia-aangevuld.csv",
    "plaatsen": {"Lent", "Nijmegen", "Oosterhout"},
    "naam": "Theaters en poppodia in Nijmegen",
    "enkelvoud": "Podium",
    "de_woord": False,
    "groep": "Uitgaan en vrije tijd",
    "soorten": {"Podium"},
    "schema": "PerformingArtsTheater",
    "beschrijving": "Theaters, poppodia en concertzalen in Nijmegen, met hun programma voor theater, concerten, comedy en dans.",
    "intro": "<p>Een concert in een zaal waar al decennia bands spelen, cabaret in de schouwburg of een voorstelling in een klein theater: Nijmegen heeft een rijk cultureel leven, met podia voor elk publiek.</p><p>Op deze pagina vind je alle theaters en poppodia in Nijmegen.</p>",
    "faq": [
        ("Waar zie je concerten in Nijmegen?",
         "Filter op concerten voor de poppodia en concertzalen."),
        ("Zijn er voorstellingen voor kinderen?",
         "Ja, filter op jeugdvoorstellingen."),
    ],
    "artikelen": ["lekker-uitgaan-in-nijmegen-hier-doe-je-dat", "tenten-voor-cultuur-en-buurtactiviteiten-in-nijmegen"],
    "blogs": ["lekker-uitgaan-in-nijmegen-hier-doe-je-dat", "tenten-voor-cultuur-en-buurtactiviteiten-in-nijmegen"],
    "meervoud": "podia",
    "blogonderwerp": "theater en muziek",
    "filtervoorbeeld": "concerten, comedy of jeugdvoorstellingen",
    "voorbeeld": {"naam": "Jouw podium", "foto": "assets/uploads/2022/12/bioscoop-nijmegen-533x400.webp", "kenmerken": ["theater", "concerten"], "actie": "Bekijk ons programma"},
    "knop_voorbeeld": "tickets, agenda, route",
}, {
    "slug": "bioscoop",
    "listdom": set(),
    "bron_csv": "bioscoop-aangevuld.csv",
    "plaatsen": {"Lent", "Nijmegen", "Oosterhout"},
    "naam": "Bioscopen in Nijmegen",
    "enkelvoud": "Bioscoop",
    "groep": "Uitgaan en vrije tijd",
    "soorten": {"Bioscoop"},
    "schema": "MovieTheater",
    "beschrijving": "Alle bioscopen en filmhuizen in Nijmegen, van blockbusters tot arthouse.",
    "intro": "<p>De nieuwste blockbuster op een groot doek, of een kleine film in een filmhuis met een goed glas wijn erbij: in Nijmegen kies je zelf.</p><p>Op deze pagina vind je alle bioscopen in Nijmegen.</p>",
    "faq": [
        ("Is er een filmhuis in Nijmegen?",
         "Ja, filter op arthouse."),
    ],
    "artikelen": [],
    "blogs": [],
    "meervoud": "bioscopen",
    "blogonderwerp": "film",
    "filtervoorbeeld": "arthouse of kinderfilms",
    "voorbeeld": {"naam": "Jouw bioscoop", "foto": "assets/uploads/2022/12/bioscoop-nijmegen-533x400.webp", "kenmerken": ["arthouse", "café of foyer"], "actie": "Dinsdag filmdag"},
    "knop_voorbeeld": "tickets, programma, route",
}, {
    "slug": "galerie",
    "listdom": {"kunstgalerie-atelier"},
    "bron_csv": "galerie-aangevuld.csv",
    "plaatsen": {"Lent", "Nijmegen", "Oosterhout"},
    "naam": "Kunstgaleries en ateliers in Nijmegen",
    "enkelvoud": "Galerie",
    "groep": "Uitgaan en vrije tijd",
    "soorten": {"Galerie"},
    "schema": "ArtGallery",
    "beschrijving": "Kunstgaleries, ateliers en kunstenaars in Nijmegen: exposities, kunst kopen en workshops.",
    "intro": "<p>Kunst kijken, kopen of zelf maken: Nijmegen heeft galeries in de binnenstad en ateliers waar kunstenaars hun deuren openzetten voor bezoekers.</p><p>Op deze pagina vind je alle kunstgaleries en ateliers in Nijmegen.</p>",
    "faq": [
        ("Kan ik bij een kunstenaar in het atelier kijken?",
         "Bij sommige ateliers wel. Filter op open atelier."),
    ],
    "artikelen": [],
    "blogs": [],
    "meervoud": "galeries",
    "blogonderwerp": "kunst",
    "filtervoorbeeld": "exposities, kunst kopen of workshops",
    "voorbeeld": {"naam": "Jouw galerie", "foto": "assets/uploads/2024/03/Replica-van-kijkkast-Gerrit-Schouten-tentoongesteld-in-Suriname-valkhofmuseum-533x400.webp", "kenmerken": ["exposities", "kunst kopen"], "actie": "Opening nieuwe expositie"},
    "knop_voorbeeld": "agenda, collectie, route",
}, {
    "slug": "zaalverhuur",
    "listdom": {"trouwlocatie", "verhuur", "zaalverhuur"},
    "bron_csv": "zaalverhuur-aangevuld.csv",
    "plaatsen": {"Lent", "Nijmegen", "Oosterhout"},
    "naam": "Zalen en locaties in Nijmegen",
    "enkelvoud": "Locatie",
    "groep": "Uitgaan en vrije tijd",
    "soorten": {"Zaal"},
    "schema": "EventVenue",
    "beschrijving": "Zalen en locaties in Nijmegen voor feesten, bruiloften, vergaderingen en evenementen.",
    "intro": "<p>Een verjaardag met vijftig man, een bruiloft, een vergadering of een bedrijfsfeest: in Nijmegen zijn zalen en locaties in alle soorten en maten, van industriële loodsen tot zalen met uitzicht op de Waal.</p><p>Op deze pagina vind je alle zalen en locaties in Nijmegen.</p>",
    "faq": [
        ("Waar huur ik een zaal voor een feest in Nijmegen?",
         "Filter op feesten en op het aantal personen."),
        ("Zijn er trouwlocaties in Nijmegen?",
         "Ja, filter op trouwen."),
    ],
    "artikelen": ["7x-een-zaal-huren-in-nijmegen", "zaal-huren-in-nijmegen-tips-voor-de-beste-keuze", "top-tips-voor-zaalverhuur-nijmegen-vind-de-perfecte-locatie"],
    "blogs": ["7x-een-zaal-huren-in-nijmegen", "zaal-huren-in-nijmegen-tips-voor-de-beste-keuze", "top-tips-voor-zaalverhuur-nijmegen-vind-de-perfecte-locatie", "welke-trouwlocatie-kies-je-voor-jouw-droombruiloft"],
    "meervoud": "locaties",
    "blogonderwerp": "zalen en feesten",
    "filtervoorbeeld": "feesten, vergaderen of trouwen",
    "voorbeeld": {"naam": "Jouw locatie", "foto": "assets/uploads/2022/12/vergaderlocatie-huren-nijmegen-533x400.webp", "kenmerken": ["feesten", "catering"], "actie": "Gratis rondleiding door de zaal"},
    "knop_voorbeeld": "offerte aanvragen, rondleiding, bellen",
}, {
    "slug": "bakkerij",
    "listdom": {"bakkerij"},
    "bron_csv": "bakkerij-aangevuld.csv",
    "plaatsen": {"Lent", "Nijmegen", "Oosterhout"},
    "naam": "Bakkerijen en patisserie in Nijmegen",
    "enkelvoud": "Bakkerij",
    "groep": "Eten en drinken",
    "soorten": {"Bakkerij"},
    "schema": "Bakery",
    "beschrijving": "Bakkers, banketbakkers en patisserieën in Nijmegen: vers brood, taart en gebak, ook glutenvrij en op bestelling.",
    "intro": "<p>Een vers zuurdesembrood op zaterdag, een taart voor een verjaardag of een bruidstaart: Nijmegen heeft ambachtelijke bakkers en patisserieën in de binnenstad en in de wijken.</p><p>Op deze pagina vind je alle bakkerijen en patisserieën in Nijmegen.</p>",
    "faq": [
        ("Waar bestel ik een taart in Nijmegen?",
         "Filter op taart bestellen. Voor een bruidstaart lees je ook ons artikel over bruidstaarten proeven."),
        ("Is er een glutenvrije bakker in Nijmegen?",
         "Filter op glutenvrij."),
    ],
    "artikelen": ["heel-vervelend-maar-hier-kan-jij-de-lekkerste-bruidstaarten-proeven"],
    "blogs": ["heel-vervelend-maar-hier-kan-jij-de-lekkerste-bruidstaarten-proeven"],
    "meervoud": "bakkerijen",
    "blogonderwerp": "brood en gebak",
    "filtervoorbeeld": "taart bestellen, zuurdesem of glutenvrij",
    "voorbeeld": {"naam": "Jouw bakkerij", "foto": "assets/uploads/2023/03/bruidstaart-nijmegen-533x400.webp", "kenmerken": ["brood", "taart en gebak"], "actie": "Zaterdag: tweede brood halve prijs"},
    "knop_voorbeeld": "taart bestellen, assortiment, route",
}, {
    "slug": "bierbrouwerij",
    "listdom": {"bierbrouwerij", "slijterij"},
    "bron_csv": "bierbrouwerij-aangevuld.csv",
    "plaatsen": {"Lent", "Nijmegen", "Oosterhout"},
    "naam": "Brouwerijen en slijterijen in Nijmegen",
    "enkelvoud": "Brouwerij",
    "groep": "Eten en drinken",
    "soorten": {"Brouwerij"},
    "schema": "Brewery",
    "beschrijving": "Brouwerijen, proeflokalen, slijterijen en wijnwinkels in Nijmegen.",
    "intro": "<p>Een rondleiding bij een Nijmeegse brouwerij, een proeverij in het proeflokaal of een goede fles wijn voor het weekend: Nijmegen heeft kleine brouwers en vakkundige slijters en wijnhandels.</p><p>Op deze pagina vind je alle brouwerijen en slijterijen in Nijmegen.</p>",
    "faq": [
        ("Kun je in Nijmegen een brouwerij bezoeken?",
         "Ja, filter op rondleiding of proeflokaal."),
        ("Waar vind ik een wijnwinkel?",
         "Filter op wijn."),
    ],
    "artikelen": ["de-8-beste-biercafes-van-nijmegen"],
    "blogs": ["de-8-beste-biercafes-van-nijmegen"],
    "meervoud": "brouwerijen en slijterijen",
    "blogonderwerp": "bier en wijn",
    "filtervoorbeeld": "proeflokaal, rondleiding of wijn",
    "voorbeeld": {"naam": "Jouw brouwerij", "foto": "assets/uploads/2022/12/biercafe-in-nijmegen-533x400.webp", "kenmerken": ["proeflokaal", "speciaalbier"], "actie": "Proeverij elke vrijdag"},
    "knop_voorbeeld": "proeverij boeken, webshop, route",
}, {
    "slug": "afhaal",
    "listdom": set(),
    "bron_csv": "afhaal-aangevuld.csv",
    "plaatsen": {"Lent", "Nijmegen", "Oosterhout"},
    "naam": "Snackbars en afhaal in Nijmegen",
    "enkelvoud": "Snackbar",
    "groep": "Eten en drinken",
    "soorten": {"Snackbar"},
    "schema": "FastFoodRestaurant",
    "beschrijving": "Snackbars, cafetaria's en afhaal- en bezorgzaken in Nijmegen: friet, pizza, burgers, shoarma en sushi.",
    "intro": "<p>Een patatje na het stappen, pizza op de bank of shoarma tussen de middag: in Nijmegen zijn snackbars en afhaalzaken in elke wijk, vaak met bezorging.</p><p>Op deze pagina vind je alle snackbars en afhaalzaken in Nijmegen.</p>",
    "faq": [
        ("Welke snackbars in Nijmegen zijn laat open?",
         "Filter op laat open."),
        ("Waar haal je pizza in Nijmegen?",
         "Filter op pizza. We schreven ook over de beste pizzeria's."),
    ],
    "artikelen": ["zin-in-een-broodje-shoarma-bezoek-deze-tentjes-in-nijmegen", "pizza-liefhebbers-dit-zijn-de-beste-pizzerias-in-nijmegen"],
    "blogs": ["zin-in-een-broodje-shoarma-bezoek-deze-tentjes-in-nijmegen", "pizza-liefhebbers-dit-zijn-de-beste-pizzerias-in-nijmegen"],
    "meervoud": "snackbars",
    "blogonderwerp": "snacks en afhalen",
    "filtervoorbeeld": "pizza, bezorgen of laat open",
    "voorbeeld": {"naam": "Jouw snackbar", "foto": "assets/uploads/2023/02/shoarma-eten-in-nijmegen-533x400.webp", "kenmerken": ["friet en snacks", "bezorgen"], "actie": "Dinsdag: gratis frikandel bij elke friet"},
    "knop_voorbeeld": "bestellen, menukaart, bellen",
}, {
    "slug": "catering",
    "listdom": set(),
    "bron_csv": "catering-aangevuld.csv",
    "plaatsen": {"Lent", "Nijmegen", "Oosterhout"},
    "naam": "Catering in Nijmegen",
    "enkelvoud": "Cateraar",
    "de_woord": False,
    "groep": "Eten en drinken",
    "soorten": {"Catering"},
    "schema": "FoodEstablishment",
    "beschrijving": "Cateraars, foodtrucks en koks aan huis in Nijmegen voor bruiloften, feesten en bedrijven.",
    "intro": "<p>Een buffet voor je verjaardag, een foodtruck op je bruiloft of lunch voor het hele kantoor: Nijmeegse cateraars verzorgen het, van een barbecue in de tuin tot een diner met bediening.</p><p>Op deze pagina vind je alle cateraars in Nijmegen.</p>",
    "faq": [
        ("Wie verzorgt de catering op een bruiloft?",
         "Filter op bruiloften. Vraag naar een proeverij voordat je kiest."),
        ("Kan ik een foodtruck huren in Nijmegen?",
         "Ja, filter op foodtruck."),
    ],
    "artikelen": [],
    "blogs": [],
    "meervoud": "cateraars",
    "blogonderwerp": "catering en feesten",
    "filtervoorbeeld": "bruiloften, bedrijfscatering of foodtruck",
    "voorbeeld": {"naam": "Jouw cateringbedrijf", "foto": "assets/uploads/2022/11/restaurant-eten-in-nijmegen.webp", "kenmerken": ["bruiloften", "buffet"], "actie": "Gratis proeverij bij een bruiloft"},
    "knop_voorbeeld": "offerte aanvragen, menu's, bellen",
}, {
    "slug": "ijssalon",
    "listdom": set(),
    "bron_csv": "ijssalon-aangevuld.csv",
    "plaatsen": {"Lent", "Nijmegen", "Oosterhout"},
    "naam": "IJssalons in Nijmegen",
    "enkelvoud": "IJssalon",
    "groep": "Eten en drinken",
    "soorten": {"IJssalon"},
    "schema": "IceCreamShop",
    "beschrijving": "IJssalons in Nijmegen: schepijs, softijs, vegan ijs en ijstaarten.",
    "intro": "<p>Een bolletje pistache op een zomerse avond aan de Waalkade of een ijstaart voor een verjaardag: Nijmegen heeft ijssalons met zelfgemaakt ijs.</p><p>Op deze pagina vind je alle ijssalons in Nijmegen.</p>",
    "faq": [
        ("Is er vegan ijs in Nijmegen?",
         "Ja, filter op vegan ijs."),
        ("Zijn de ijssalons het hele jaar open?",
         "Niet allemaal; veel ijssalons gaan in de winter dicht. Kijk bij de openingstijden."),
    ],
    "artikelen": [],
    "blogs": [],
    "meervoud": "ijssalons",
    "blogonderwerp": "ijs",
    "filtervoorbeeld": "vegan ijs of ijstaarten",
    "voorbeeld": {"naam": "Jouw ijssalon", "foto": "assets/uploads/2023/03/bruidstaart-nijmegen-533x400.webp", "kenmerken": ["schepijs", "vegan ijs"], "actie": "Elke woensdag een extra bolletje"},
    "knop_voorbeeld": "smaken, ijstaart bestellen, route",
}, {
    "slug": "dansschool",
    "listdom": {"dansen"},
    "bron_csv": "sportscholen-aangevuld.csv",
    "plaatsen": {"Lent", "Nijmegen", "Oosterhout"},
    "naam": "Dansscholen in Nijmegen",
    "enkelvoud": "Dansschool",
    "groep": "Sport en beweging",
    "soorten": {"Dansschool"},
    "schema": "DanceSchool",
    "beschrijving": "Dansscholen in Nijmegen: salsa, stijldansen, hiphop, ballet en lessen voor kinderen, met proeflessen.",
    "intro": "<p>Salsa op vrijdagavond, je bruiloftsdans oefenen of je kind op hiphop of ballet: Nijmegen heeft dansscholen voor elk niveau en elke stijl.</p><p>Op deze pagina vind je alle dansscholen in Nijmegen.</p>",
    "faq": [
        ("Kan ik een proefles dansen doen?",
         "Bij de meeste dansscholen wel. Filter op proefles."),
        ("Waar leer ik salsa in Nijmegen?",
         "Filter op salsa."),
    ],
    "artikelen": ["de-beste-dansscholen-in-nijmegen", "dansen-is-weer-helemaal-hip-hier-kan-je-dat-doen"],
    "blogs": ["de-beste-dansscholen-in-nijmegen", "dansen-is-weer-helemaal-hip-hier-kan-je-dat-doen"],
    "meervoud": "dansscholen",
    "blogonderwerp": "dansen",
    "filtervoorbeeld": "salsa, hiphop of kinderen en jeugd",
    "voorbeeld": {"naam": "Jouw dansschool", "foto": "assets/uploads/2022/12/beste-dansschool-nijmegen-533x400.webp", "kenmerken": ["salsa", "proefles"], "actie": "Gratis proefles in september"},
    "knop_voorbeeld": "proefles, rooster, inschrijven",
}, {
    "slug": "yoga",
    "listdom": {"yoga"},
    "bron_csv": "sportscholen-aangevuld.csv",
    "plaatsen": {"Lent", "Nijmegen", "Oosterhout"},
    "naam": "Yoga en pilates in Nijmegen",
    "enkelvoud": "Studio",
    "groep": "Sport en beweging",
    "soorten": {"Pilates", "Yoga en tai chi"},
    "schema": "SportsActivityLocation",
    "beschrijving": "Yoga-, pilates- en tai-chistudio's in Nijmegen, met proeflessen en online lessen.",
    "intro": "<p>Even tot rust komen na het werk, sterker worden met pilates of yoga tijdens je zwangerschap: in Nijmegen zijn studio's en docenten voor beginners en gevorderden.</p><p>Op deze pagina vind je alle yoga- en pilatesstudio's in Nijmegen.</p>",
    "faq": [
        ("Is er yoga voor beginners in Nijmegen?",
         "Ja, veel studio's hebben beginnerslessen. Filter op proefles om eerst te proberen."),
        ("Waar doe ik pilates in Nijmegen?",
         "Filter op pilates."),
    ],
    "artikelen": [],
    "blogs": [],
    "meervoud": "studio's",
    "blogonderwerp": "yoga en ontspanning",
    "filtervoorbeeld": "pilates, meditatie of zwangerschapsyoga",
    "voorbeeld": {"naam": "Jouw yogastudio", "foto": "assets/uploads/2022/11/sporten-in-nijmegen-533x400.webp", "kenmerken": ["yoga", "proefles"], "actie": "Eerste les gratis"},
    "knop_voorbeeld": "rooster, proefles, inschrijven",
}, {
    "slug": "vechtsport",
    "listdom": {"vechtsport"},
    "bron_csv": "sportscholen-aangevuld.csv",
    "plaatsen": {"Lent", "Nijmegen", "Oosterhout"},
    "naam": "Vechtsport in Nijmegen",
    "enkelvoud": "Vechtsportschool",
    "groep": "Sport en beweging",
    "soorten": {"Vechtsport"},
    "schema": "SportsActivityLocation",
    "beschrijving": "Vechtsportscholen in Nijmegen: boksen, kickboksen, muay thai, judo, karate, jiujitsu en zelfverdediging.",
    "intro": "<p>Boksen voor je conditie, judo voor je kind of muay thai als je echt wilt leren vechten: Nijmegen heeft vechtsportscholen en verenigingen voor elke stijl en leeftijd.</p><p>Op deze pagina vind je alle vechtsportscholen in Nijmegen.</p>",
    "faq": [
        ("Welke vechtsport is geschikt voor kinderen?",
         "Judo en karate hebben vaak jeugdgroepen. Filter op kinderen en jeugd."),
        ("Kan ik een proefles boksen?",
         "Bij veel scholen wel. Filter op proefles."),
    ],
    "artikelen": [],
    "blogs": [],
    "meervoud": "vechtsportscholen",
    "blogonderwerp": "vechtsport",
    "filtervoorbeeld": "boksen, judo of kinderen en jeugd",
    "voorbeeld": {"naam": "Jouw vechtsportschool", "foto": "assets/uploads/2022/11/sporten-in-nijmegen-533x400.webp", "kenmerken": ["kickboksen", "proefles"], "actie": "Gratis proefweek"},
    "knop_voorbeeld": "rooster, proefles, inschrijven",
}, {
    "slug": "zwembad",
    "listdom": set(),
    "bron_csv": "zwembad-aangevuld.csv",
    "plaatsen": {"Lent", "Nijmegen", "Oosterhout"},
    "naam": "Zwembaden in Nijmegen",
    "enkelvoud": "Zwembad",
    "de_woord": False,
    "groep": "Sport en beweging",
    "soorten": {"Zwembad"},
    "schema": "PublicSwimmingPool",
    "beschrijving": "Zwembaden in Nijmegen: recreatief zwemmen, baantjes trekken, zwemles en buitenbaden.",
    "intro": "<p>Baantjes trekken voor je werk, met de kinderen van de glijbaan of zwemles voor je A-diploma: in Nijmegen zijn binnen- en buitenbaden en zwemscholen.</p><p>Op deze pagina vind je alle zwembaden in Nijmegen.</p>",
    "faq": [
        ("Waar kan ik zwemles volgen in Nijmegen?",
         "Filter op zwemles."),
        ("Is er een buitenbad in Nijmegen?",
         "Ja, filter op buitenbad."),
    ],
    "artikelen": [],
    "blogs": [],
    "meervoud": "zwembaden",
    "blogonderwerp": "zwemmen",
    "filtervoorbeeld": "baantjes, zwemles of buitenbad",
    "voorbeeld": {"naam": "Jouw zwembad", "foto": "assets/uploads/2022/11/sporten-in-nijmegen-533x400.webp", "kenmerken": ["recreatief zwemmen", "zwemles"], "actie": "Gratis zwemmen op je verjaardag"},
    "knop_voorbeeld": "openingstijden, tickets, route",
}, {
    "slug": "padel",
    "listdom": set(),
    "bron_csv": "padel-aangevuld.csv",
    "plaatsen": {"Lent", "Nijmegen", "Oosterhout"},
    "naam": "Padel in Nijmegen",
    "enkelvoud": "Padelclub",
    "groep": "Sport en beweging",
    "soorten": {"Padel"},
    "schema": "SportsActivityLocation",
    "beschrijving": "Padelbanen en padelclubs in Nijmegen: banen huren, lessen en toernooien.",
    "intro": "<p>Padel is in een paar jaar een van de populairste sporten van Nederland geworden. In Nijmegen huur je een baan met vrienden, neem je les of doe je mee aan een toernooi.</p><p>Op deze pagina vind je alle padelbanen in Nijmegen.</p>",
    "faq": [
        ("Kan ik in Nijmegen een padelbaan huren zonder lid te zijn?",
         "Bij de meeste locaties wel. Filter op banen huren."),
    ],
    "artikelen": [],
    "blogs": [],
    "meervoud": "padellocaties",
    "blogonderwerp": "padel",
    "filtervoorbeeld": "banen huren, padelles of binnenbanen",
    "voorbeeld": {"naam": "Jouw padelclub", "foto": "assets/uploads/2022/11/sporten-in-nijmegen-533x400.webp", "kenmerken": ["banen huren", "padelles"], "actie": "Eerste uur gratis padelles"},
    "knop_voorbeeld": "baan boeken, lessen, route",
}, {
    "slug": "sportvereniging",
    "listdom": set(),
    "bron_csv": "sportvereniging-aangevuld.csv",
    "plaatsen": {"Lent", "Nijmegen", "Oosterhout"},
    "naam": "Sportverenigingen in Nijmegen",
    "enkelvoud": "Sportvereniging",
    "groep": "Sport en beweging",
    "soorten": {"Sportvereniging"},
    "schema": "SportsClub",
    "beschrijving": "Sportverenigingen en sportaccommodaties in Nijmegen: voetbal, hockey, tennis, atletiek, klimmen, roeien en meer.",
    "intro": "<p>Elke zaterdag op het veld, een avond in de klimhal of roeien op de Waal: Nijmegen heeft sportverenigingen voor bijna elke sport, voor jeugd en volwassenen.</p><p>Op deze pagina vind je alle sportverenigingen in Nijmegen.</p>",
    "faq": [
        ("Hoe vind ik een sportclub in mijn wijk?",
         "Bekijk de kaart en filter op je sport, zoals voetbal, hockey of tennis."),
        ("Kan ik eerst meetrainen?",
         "Bij veel verenigingen kun je een paar keer gratis meedoen; vraag het na bij de club."),
    ],
    "artikelen": ["bammmm-en-je-bent-fit"],
    "blogs": ["bammmm-en-je-bent-fit"],
    "meervoud": "verenigingen",
    "blogonderwerp": "sporten in Nijmegen",
    "filtervoorbeeld": "voetbal, tennis of klimmen",
    "voorbeeld": {"naam": "Jouw vereniging", "foto": "assets/uploads/2022/11/sporten-in-nijmegen-533x400.webp", "kenmerken": ["jeugd", "recreanten"], "actie": "Word nu lid: eerste maand gratis"},
    "knop_voorbeeld": "lid worden, trainingstijden, route",
}, {
    "slug": "fysiotherapeut",
    "listdom": set(),
    "bron_csv": "fysiotherapeut-aangevuld.csv",
    "plaatsen": {"Lent", "Nijmegen", "Oosterhout"},
    "naam": "Fysiotherapie in Nijmegen",
    "enkelvoud": "Fysiotherapeut",
    "groep": "Gezondheid en welzijn",
    "soorten": {"Fysiotherapie"},
    "schema": "Physiotherapy",
    "beschrijving": "Fysiotherapeuten in Nijmegen: sportfysiotherapie, manuele therapie, bekkenfysiotherapie, kinderfysiotherapie en meer.",
    "intro": "<p>Last van je rug, herstellen na een blessure of revalideren na een operatie: een fysiotherapeut helpt je weer op weg. In Nijmegen zitten praktijken in elke wijk, vaak met een eigen specialisme.</p><p>Op deze pagina vind je alle fysiotherapeuten in Nijmegen.</p>",
    "faq": [
        ("Heb ik een verwijzing nodig voor de fysiotherapeut?",
         "Nee, je kunt direct naar een fysiotherapeut. Of het vergoed wordt hangt af van je aanvullende verzekering."),
        ("Is er een sportfysiotherapeut in Nijmegen?",
         "Ja, filter op sportfysiotherapie."),
    ],
    "artikelen": ["voordelen-fysiotherapie-snel-herstel-met-een-fysio"],
    "blogs": ["voordelen-fysiotherapie-snel-herstel-met-een-fysio"],
    "meervoud": "fysiotherapeuten",
    "blogonderwerp": "gezondheid",
    "filtervoorbeeld": "sportfysiotherapie, manuele therapie of aan huis",
    "voorbeeld": {"naam": "Jouw praktijk", "foto": "assets/uploads/2023/05/fysiotherapie-in-nijmegen-533x400.webp", "kenmerken": ["sportfysiotherapie", "zonder verwijzing"], "actie": "Binnen 48 uur een afspraak"},
    "knop_voorbeeld": "afspraak maken, bellen, route",
}, {
    "slug": "dietist",
    "listdom": {"dietist", "voedingsdeskundige"},
    "bron_csv": "dietist-aangevuld.csv",
    "plaatsen": {"Lent", "Nijmegen", "Oosterhout"},
    "naam": "Diëtisten en voedingsadvies in Nijmegen",
    "enkelvoud": "Diëtist",
    "groep": "Gezondheid en welzijn",
    "soorten": {"Diëtist"},
    "schema": "Dietitian",
    "beschrijving": "Diëtisten en voedingsdeskundigen in Nijmegen: afvallen, sportvoeding, allergieën en darmklachten.",
    "intro": "<p>Gezonder eten, afvallen zonder crashdieet of je klachten onder controle krijgen: een diëtist kijkt met je naar wat bij jou past. In Nijmegen werken diëtisten met verschillende specialismen.</p><p>Op deze pagina vind je alle diëtisten in Nijmegen.</p>",
    "faq": [
        ("Wordt een diëtist vergoed?",
         "De basisverzekering vergoedt een aantal uur per jaar, minus je eigen risico. Filter op vergoed door de zorgverzekering."),
    ],
    "artikelen": ["hoe-kan-een-dietist-je-helpen-gezonder-te-gaan-leven"],
    "blogs": ["hoe-kan-een-dietist-je-helpen-gezonder-te-gaan-leven"],
    "meervoud": "diëtisten",
    "blogonderwerp": "gezond eten",
    "filtervoorbeeld": "afvallen, sportvoeding of allergieën",
    "voorbeeld": {"naam": "Jouw praktijk", "foto": "assets/uploads/2023/06/dietist-nijmegen-533x400.webp", "kenmerken": ["afvallen", "vergoed door de zorgverzekering"], "actie": "Gratis kennismakingsgesprek"},
    "knop_voorbeeld": "afspraak maken, bellen, route",
}, {
    "slug": "psycholoog",
    "listdom": set(),
    "bron_csv": "psycholoog-aangevuld.csv",
    "plaatsen": {"Lent", "Nijmegen", "Oosterhout"},
    "naam": "Psychologen in Nijmegen",
    "enkelvoud": "Psycholoog",
    "groep": "Gezondheid en welzijn",
    "soorten": {"Psycholoog"},
    "schema": "MedicalBusiness",
    "beschrijving": "Psychologen, psychotherapeuten en ggz-praktijken in Nijmegen, voor volwassenen, kinderen en jongeren.",
    "intro": "<p>Als je vastloopt met angst, somberheid of een trauma, kan praten met een psycholoog helpen. In Nijmegen zijn veel praktijken, van basis-ggz tot specialistische zorg, voor volwassenen en voor kinderen en jongeren.</p><p>Op deze pagina vind je alle psychologen in Nijmegen.</p>",
    "faq": [
        ("Heb ik een verwijzing nodig voor een psycholoog?",
         "Voor vergoeding vanuit de basisverzekering heb je een verwijzing van de huisarts nodig."),
        ("Hoe lang zijn de wachttijden?",
         "Dat verschilt sterk per praktijk. Veel praktijken zetten hun wachttijd op de site."),
    ],
    "artikelen": [],
    "blogs": [],
    "meervoud": "psychologen",
    "blogonderwerp": "welzijn",
    "filtervoorbeeld": "angst en stress, trauma of kinderen en jeugd",
    "voorbeeld": {"naam": "Jouw praktijk", "foto": "assets/uploads/2023/05/fysiotherapie-in-nijmegen-533x400.webp", "kenmerken": ["angst en stress", "basis-ggz"], "actie": "Korte wachttijd"},
    "knop_voorbeeld": "aanmelden, bellen, route",
}, {
    "slug": "coach",
    "listdom": {"coach", "therapeut"},
    "bron_csv": "coach-aangevuld.csv",
    "plaatsen": {"Lent", "Nijmegen", "Oosterhout"},
    "naam": "Coaches en therapeuten in Nijmegen",
    "enkelvoud": "Coach",
    "groep": "Gezondheid en welzijn",
    "soorten": {"Coach"},
    "schema": "ProfessionalService",
    "beschrijving": "Coaches en therapeuten in Nijmegen: loopbaancoaching, life coaching, relatietherapie, mindfulness en meer.",
    "intro": "<p>Een volgende stap in je loopbaan, beter omgaan met stress of samen weer verder als stel: in Nijmegen werken veel coaches en therapeuten, vaak zelfstandig en met een eigen aanpak.</p><p>Op deze pagina vind je alle coaches en therapeuten in Nijmegen.</p>",
    "faq": [
        ("Wat is het verschil tussen een coach en een psycholoog?",
         "Een psycholoog heeft een BIG-registratie en behandelt psychische klachten. Een coach helpt je verder met een vraag of doel. Voor psychologen zie onze pagina Psychologen in Nijmegen."),
        ("Is een eerste gesprek gratis?",
         "Bij veel coaches wel; vraag ernaar."),
    ],
    "artikelen": [],
    "blogs": [],
    "meervoud": "coaches en therapeuten",
    "blogonderwerp": "welzijn en persoonlijke groei",
    "filtervoorbeeld": "loopbaancoaching, burn-out of mindfulness",
    "voorbeeld": {"naam": "Jouw coachpraktijk", "foto": "assets/uploads/2023/05/fysiotherapie-in-nijmegen-533x400.webp", "kenmerken": ["loopbaancoaching", "online coaching"], "actie": "Gratis kennismakingsgesprek"},
    "knop_voorbeeld": "afspraak maken, bellen, whatsapp",
}, {
    "slug": "alternatief",
    "listdom": {"acupuncturist", "alternatieve-geneeswijze"},
    "bron_csv": "alternatief-aangevuld.csv",
    "plaatsen": {"Lent", "Nijmegen", "Oosterhout"},
    "naam": "Alternatieve geneeswijzen in Nijmegen",
    "enkelvoud": "Praktijk",
    "de_woord": False,
    "groep": "Gezondheid en welzijn",
    "soorten": {"Alternatief"},
    "schema": "HealthAndBeautyBusiness",
    "beschrijving": "Praktijken voor acupunctuur, natuurgeneeskunde, homeopathie, reiki en andere complementaire geneeswijzen in Nijmegen.",
    "intro": "<p>Acupunctuur, natuurgeneeskunde of reiki: in Nijmegen werken praktijken voor complementaire en alternatieve geneeswijzen. Overleg bij klachten ook altijd met je huisarts.</p><p>Op deze pagina vind je alle praktijken voor alternatieve geneeswijzen in Nijmegen.</p>",
    "faq": [
        ("Worden alternatieve behandelingen vergoed?",
         "Soms, vanuit een aanvullende verzekering. Check je polis."),
    ],
    "artikelen": [],
    "blogs": [],
    "meervoud": "praktijken",
    "blogonderwerp": "alternatieve geneeswijzen",
    "filtervoorbeeld": "acupunctuur, natuurgeneeskunde of reiki",
    "voorbeeld": {"naam": "Jouw praktijk", "foto": "assets/uploads/2023/05/fysiotherapie-in-nijmegen-533x400.webp", "kenmerken": ["acupunctuur", "online afspraak"], "actie": "Gratis kennismakingsgesprek"},
    "knop_voorbeeld": "afspraak maken, bellen, route",
}, {
    "slug": "opticien",
    "listdom": set(),
    "bron_csv": "opticien-aangevuld.csv",
    "plaatsen": {"Lent", "Nijmegen", "Oosterhout"},
    "naam": "Opticiens in Nijmegen",
    "enkelvoud": "Opticien",
    "groep": "Gezondheid en welzijn",
    "soorten": {"Opticien"},
    "schema": "Optician",
    "beschrijving": "Opticiens in Nijmegen voor brillen, contactlenzen, oogmetingen en hoortoestellen.",
    "intro": "<p>Een nieuwe bril, contactlenzen of je ogen laten meten: in Nijmegen zitten opticiens in de binnenstad en de winkelcentra, van ketens tot zelfstandige opticiens met eigen merken.</p><p>Op deze pagina vind je alle opticiens in Nijmegen.</p>",
    "faq": [
        ("Kan ik bij een opticien mijn ogen laten meten?",
         "Ja, de meeste opticiens doen een oogmeting. Filter op oogmeting."),
    ],
    "artikelen": ["wie-de-bril-past-zet-hem-op"],
    "blogs": ["wie-de-bril-past-zet-hem-op"],
    "meervoud": "opticiens",
    "blogonderwerp": "brillen",
    "filtervoorbeeld": "oogmeting, contactlenzen of hoortoestellen",
    "voorbeeld": {"naam": "Jouw opticien", "foto": "assets/uploads/2023/05/in-nijmegen-een-mooie-bril-vinden-533x400.webp", "kenmerken": ["brillen", "oogmeting"], "actie": "Gratis oogmeting"},
    "knop_voorbeeld": "afspraak maken, collectie, route",
}, {
    "slug": "huisarts",
    "listdom": set(),
    "bron_csv": "huisarts-aangevuld.csv",
    "plaatsen": {"Lent", "Nijmegen", "Oosterhout"},
    "naam": "Huisartsen in Nijmegen",
    "enkelvoud": "Huisarts",
    "groep": "Gezondheid en welzijn",
    "soorten": {"Huisarts"},
    "schema": "Physician",
    "beschrijving": "Alle huisartsenpraktijken in Nijmegen op de kaart, met praktijken die nieuwe patiënten aannemen.",
    "intro": "<p>Net verhuisd naar Nijmegen of op zoek naar een andere huisarts? Op de kaart zie je welke praktijk bij jou in de buurt zit, en welke praktijken nieuwe patiënten aannemen.</p><p>Op deze pagina vind je alle huisartsen in Nijmegen.</p>",
    "faq": [
        ("Welke huisarts in Nijmegen neemt nieuwe patiënten aan?",
         "Filter op nieuwe patiënten welkom. Bel de praktijk om het te bevestigen, want dit verandert vaak."),
        ("Wat doe ik 's avonds of in het weekend?",
         "Bel de huisartsenpost. Bij spoed bel je 112."),
    ],
    "artikelen": [],
    "blogs": [],
    "meervoud": "huisartsenpraktijken",
    "blogonderwerp": "gezondheid",
    "filtervoorbeeld": "nieuwe patiënten welkom of e-consult",
    "voorbeeld": {"naam": "Jouw praktijk", "foto": "assets/uploads/2023/05/fysiotherapie-in-nijmegen-533x400.webp", "kenmerken": ["nieuwe patiënten welkom", "online afspraak"], "actie": "Wij nemen nieuwe patiënten aan"},
    "knop_voorbeeld": "inschrijven, afspraak, bellen",
}, {
    "slug": "dierenarts",
    "listdom": set(),
    "bron_csv": "dierenarts-aangevuld.csv",
    "plaatsen": {"Lent", "Nijmegen", "Oosterhout"},
    "naam": "Dierenartsen in Nijmegen",
    "enkelvoud": "Dierenarts",
    "groep": "Gezondheid en welzijn",
    "soorten": {"Dierenarts"},
    "schema": "VeterinaryCare",
    "beschrijving": "Dierenartsen en dierenklinieken in Nijmegen, ook voor spoed.",
    "intro": "<p>Een vaccinatie voor je kitten, een hond die niet lekker is of spoed in het weekend: in Nijmegen zitten dierenartsen en dierenklinieken voor honden, katten en kleine huisdieren.</p><p>Op deze pagina vind je alle dierenartsen in Nijmegen.</p>",
    "faq": [
        ("Wat doe ik bij spoed met mijn huisdier?",
         "Bel je eigen dierenarts; buiten de openingstijden verwijst die je door naar de spoeddienst."),
    ],
    "artikelen": ["waarom-kun-je-beter-een-huisdierenverzekering-afsluiten"],
    "blogs": ["waarom-kun-je-beter-een-huisdierenverzekering-afsluiten"],
    "meervoud": "dierenartsen",
    "blogonderwerp": "huisdieren",
    "filtervoorbeeld": "spoed of konijnen en knaagdieren",
    "voorbeeld": {"naam": "Jouw dierenkliniek", "foto": "assets/uploads/2022/12/katten-in-nijmegen-533x400.webp", "kenmerken": ["honden en katten", "spoed"], "actie": "Gratis puppy- en kittencheck"},
    "knop_voorbeeld": "afspraak maken, spoed, bellen",
}, {
    "slug": "tandarts",
    "listdom": set(),
    "bron_csv": "tandarts-aangevuld.csv",
    "plaatsen": {"Lent", "Nijmegen", "Oosterhout"},
    "naam": "Tandartsen in Nijmegen",
    "enkelvoud": "Tandarts",
    "groep": "Gezondheid en welzijn",
    "soorten": {"Tandarts"},
    "schema": "Dentist",
    "beschrijving": "Alle tandartsen in Nijmegen op de kaart, met praktijken die nieuwe patiënten aannemen.",
    "intro": "<p>Een nieuwe tandarts zoeken is lastig: veel praktijken zitten vol. Op de kaart zie je welke tandarts bij jou in de buurt zit en welke praktijken nieuwe patiënten aannemen.</p><p>Op deze pagina vind je alle tandartsen in Nijmegen.</p>",
    "faq": [
        ("Welke tandarts in Nijmegen neemt nieuwe patiënten aan?",
         "Filter op nieuwe patiënten welkom en bel de praktijk om het te bevestigen."),
        ("Is er een tandarts voor angstpatiënten?",
         "Ja, filter op angstpatiënten."),
    ],
    "artikelen": [],
    "blogs": [],
    "meervoud": "tandartsen",
    "blogonderwerp": "gezondheid",
    "filtervoorbeeld": "nieuwe patiënten welkom of angstpatiënten",
    "voorbeeld": {"naam": "Jouw tandartspraktijk", "foto": "assets/uploads/2023/05/fysiotherapie-in-nijmegen-533x400.webp", "kenmerken": ["nieuwe patiënten welkom", "mondhygiënist"], "actie": "Wij nemen nieuwe patiënten aan"},
    "knop_voorbeeld": "inschrijven, afspraak, bellen",
}, {
    "slug": "hotel",
    "listdom": set(),
    "bron_csv": "hotel-aangevuld.csv",
    "plaatsen": {"Lent", "Nijmegen", "Oosterhout"},
    "naam": "Hotels in Nijmegen",
    "enkelvoud": "Hotel",
    "de_woord": False,
    "groep": "Overnachten",
    "soorten": {"Hotel"},
    "schema": "Hotel",
    "beschrijving": "Alle hotels in Nijmegen op de kaart: in het centrum, aan de Waal en net buiten de stad.",
    "intro": "<p>Een weekendje weg, een zakenreis of de Vierdaagse lopen: in Nijmegen kun je in het centrum slapen, met uitzicht op de Waal, of net buiten de stad in het groen.</p><p>Op deze pagina vind je alle hotels in Nijmegen.</p>",
    "faq": [
        ("Waar overnacht je tijdens de Vierdaagse?",
         "Boek ruim op tijd: in de Vierdaagseweek zitten de meeste hotels maanden vooraf vol."),
        ("Is er een hotel met parkeren in het centrum?",
         "Filter op parkeren."),
    ],
    "artikelen": ["wat-zijn-de-mooiste-hotels-in-nijmegen-onze-top-5", "weekendje-nijmegen-hier-kun-je-leuk-overnachten"],
    "blogs": ["wat-zijn-de-mooiste-hotels-in-nijmegen-onze-top-5"],
    "meervoud": "hotels",
    "blogonderwerp": "overnachten",
    "filtervoorbeeld": "centrum, ontbijt of vergaderzaal",
    "voorbeeld": {"naam": "Jouw hotel", "foto": "assets/uploads/2022/12/overnachten-in-nijmegen-1-533x400.webp", "kenmerken": ["ontbijt", "centrum"], "actie": "10% korting bij direct boeken"},
    "knop_voorbeeld": "kamer boeken, route, bellen",
}, {
    "slug": "bed-and-breakfast",
    "listdom": set(),
    "bron_csv": "bed-and-breakfast-aangevuld.csv",
    "plaatsen": {"Lent", "Nijmegen", "Oosterhout"},
    "naam": "Bed and breakfasts in Nijmegen",
    "enkelvoud": "B&B",
    "groep": "Overnachten",
    "soorten": {"B&B"},
    "schema": "BedAndBreakfast",
    "beschrijving": "B&B's, gastenverblijven en vakantiewoningen in Nijmegen, Lent en Oosterhout.",
    "intro": "<p>Persoonlijker dan een hotel: in een B&B in Nijmegen slaap je bij mensen die de stad kennen en hun tips graag delen. Er zijn B&B's in de binnenstad, in de wijken en aan de rand van de stad.</p><p>Op deze pagina vind je alle B&B's in Nijmegen.</p>",
    "faq": [
        ("Wat is het verschil tussen een B&B en een hotel?",
         "Een B&B is kleiner en vaak bij de eigenaren aan huis, met ontbijt erbij."),
    ],
    "artikelen": ["weekendje-nijmegen-hier-kun-je-leuk-overnachten", "3x-een-leuke-bed-and-breakfast-in-wijchen"],
    "blogs": ["weekendje-nijmegen-hier-kun-je-leuk-overnachten"],
    "meervoud": "B&B's",
    "blogonderwerp": "overnachten",
    "filtervoorbeeld": "eigen badkamer, tuin of hond welkom",
    "voorbeeld": {"naam": "Jouw B&B", "foto": "assets/uploads/2022/12/overnachten-in-nijmegen-1-533x400.webp", "kenmerken": ["ontbijt", "eigen badkamer"], "actie": "Derde nacht gratis"},
    "knop_voorbeeld": "kamer boeken, route, bellen",
}, {
    "slug": "camping",
    "listdom": set(),
    "bron_csv": "camping-aangevuld.csv",
    "plaatsen": {"Lent", "Nijmegen", "Oosterhout"},
    "naam": "Campings in Nijmegen",
    "enkelvoud": "Camping",
    "groep": "Overnachten",
    "soorten": {"Camping"},
    "schema": "Campground",
    "beschrijving": "Campings, camperplaatsen en vakantieparken in de gemeente Nijmegen.",
    "intro": "<p>Kamperen in Nijmegen kan, ook al ligt de stad aan de Waal en niet aan zee. Er zijn een paar campings en camperplaatsen in en direct rond de stad, ideaal tijdens de Vierdaagse of voor een fietsvakantie.</p><p>Op deze pagina vind je de campings in de gemeente Nijmegen. Meer campings in de regio staan in ons artikel over campings rond Nijmegen.</p>",
    "faq": [
        ("Zijn er campings rond Nijmegen?",
         "Ja, vooral richting Groesbeek, Berg en Dal en de Ooijpolder. Zie ons artikel over campings rond Nijmegen."),
    ],
    "artikelen": ["campings-rond-nijmegen"],
    "blogs": ["campings-rond-nijmegen"],
    "meervoud": "campings",
    "blogonderwerp": "kamperen",
    "filtervoorbeeld": "camperplaatsen, trekkershutten of hond welkom",
    "voorbeeld": {"naam": "Jouw camping", "foto": "assets/uploads/2022/12/nijmegen-camping-533x400.webp", "kenmerken": ["kampeerplaatsen", "hond welkom"], "actie": "Vroegboekkorting"},
    "knop_voorbeeld": "plek reserveren, route, bellen",
}, {
    "slug": "kledingwinkel",
    "listdom": set(),
    "bron_csv": "kledingwinkel-aangevuld.csv",
    "plaatsen": {"Lent", "Nijmegen", "Oosterhout"},
    "naam": "Kledingwinkels in Nijmegen",
    "enkelvoud": "Kledingwinkel",
    "groep": "Winkelen",
    "soorten": {"Kledingwinkel"},
    "schema": "ClothingStore",
    "beschrijving": "Kleding-, schoenen- en modewinkels in Nijmegen: boetieks, ketens en duurzame mode.",
    "intro": "<p>Winkelen in Nijmegen betekent de Broerstraat, de Ziekerstraat en de Lange Hezelstraat, met ketens en vooral veel eigen boetieks. In de wijken en in Lent zitten ook goede kledingzaken.</p><p>Op deze pagina vind je alle kledingwinkels in Nijmegen.</p>",
    "faq": [
        ("Zijn de winkels in Nijmegen op zondag open?",
         "Veel winkels in de binnenstad zijn op zondagmiddag open. Filter op zondag open."),
    ],
    "artikelen": [],
    "blogs": [],
    "meervoud": "kledingwinkels",
    "blogonderwerp": "mode",
    "filtervoorbeeld": "dames, schoenen of duurzaam",
    "voorbeeld": {"naam": "Jouw winkel", "foto": "assets/uploads/2026/02/Nijmegen-de-oudste-stad-met-de-jongste-energie-533x400.webp", "kenmerken": ["dames", "duurzaam"], "actie": "Nieuwe collectie binnen"},
    "knop_voorbeeld": "collectie, route, webshop",
}, {
    "slug": "tweedehands-winkel",
    "listdom": set(),
    "bron_csv": "tweedehands-winkel-aangevuld.csv",
    "plaatsen": {"Lent", "Nijmegen", "Oosterhout"},
    "naam": "Kringloop- en vintagewinkels in Nijmegen",
    "enkelvoud": "Winkel",
    "de_woord": False,
    "groep": "Winkelen",
    "soorten": {"Kringloop en vintage"},
    "schema": "Store",
    "beschrijving": "Kringloopwinkels, vintagewinkels en antiekzaken in Nijmegen.",
    "intro": "<p>Op zoek naar een vintage jas, een tweedehands kast of een stukje antiek? Nijmegen heeft grote kringloopwinkels en kleine vintagezaken in de binnenstad en de Hazenkamp.</p><p>Op deze pagina vind je alle kringloop- en vintagewinkels in Nijmegen.</p>",
    "faq": [
        ("Kan ik spullen brengen naar de kringloop?",
         "Bij de meeste kringloopwinkels wel. Filter op spullen brengen."),
    ],
    "artikelen": ["parels-vinden-in-nijmeegse-kringloopwinkels"],
    "blogs": ["parels-vinden-in-nijmeegse-kringloopwinkels"],
    "meervoud": "winkels",
    "blogonderwerp": "tweedehands",
    "filtervoorbeeld": "vintage kleding, antiek of meubels",
    "voorbeeld": {"naam": "Jouw winkel", "foto": "assets/uploads/2022/12/nijmegen-antiekwinkel-533x400.webp", "kenmerken": ["kringloop", "vintage kleding"], "actie": "Elke week nieuwe spullen"},
    "knop_voorbeeld": "openingstijden, route, spullen brengen",
}, {
    "slug": "woonwinkel",
    "listdom": set(),
    "bron_csv": "woonwinkel-aangevuld.csv",
    "plaatsen": {"Lent", "Nijmegen", "Oosterhout"},
    "naam": "Woonwinkels in Nijmegen",
    "enkelvoud": "Woonwinkel",
    "groep": "Winkelen",
    "soorten": {"Woonwinkel"},
    "schema": "FurnitureStore",
    "beschrijving": "Woonwinkels, meubelzaken, keuken- en badkamerwinkels in Nijmegen.",
    "intro": "<p>Nieuw ingericht na een verhuizing, of eindelijk die bank vervangen: in Nijmegen vind je woonwinkels in de binnenstad en grote meubelzaken op de woonboulevards.</p><p>Op deze pagina vind je alle woonwinkels in Nijmegen.</p>",
    "faq": [
        ("Bezorgen woonwinkels in Nijmegen?",
         "De meeste meubelzaken wel. Filter op bezorgen."),
    ],
    "artikelen": ["verhuizen-en-de-woonkamer-opnieuw-inrichten", "al-meer-dan-55-jaar-een-begrip-in-de-regio-hoe-latour-tuinmeubelen-uitgroeide-tot-loungesetspecialist"],
    "blogs": ["verhuizen-en-de-woonkamer-opnieuw-inrichten"],
    "meervoud": "woonwinkels",
    "blogonderwerp": "wonen",
    "filtervoorbeeld": "meubels, verlichting of keukens",
    "voorbeeld": {"naam": "Jouw woonwinkel", "foto": "assets/uploads/2023/06/meubelmaker-nijmegen-533x400.webp", "kenmerken": ["meubels", "verlichting"], "actie": "Gratis advies aan huis"},
    "knop_voorbeeld": "showroom, route, webshop",
}, {
    "slug": "juwelier",
    "listdom": set(),
    "bron_csv": "juwelier-aangevuld.csv",
    "plaatsen": {"Lent", "Nijmegen", "Oosterhout"},
    "naam": "Juweliers in Nijmegen",
    "enkelvoud": "Juwelier",
    "groep": "Winkelen",
    "soorten": {"Juwelier"},
    "schema": "JewelryStore",
    "beschrijving": "Juweliers, goudsmeden en horlogewinkels in Nijmegen.",
    "intro": "<p>Trouwringen laten maken, een horloge laten repareren of een cadeau met glans: in Nijmegen zitten juweliers en goudsmeden die vaak zelf ontwerpen.</p><p>Op deze pagina vind je alle juweliers in Nijmegen.</p>",
    "faq": [
        ("Kan ik in Nijmegen trouwringen laten maken?",
         "Ja, filter op trouwringen of goudsmid."),
    ],
    "artikelen": ["ga-eens-naar-de-juwelier-om-te-shinen"],
    "blogs": ["ga-eens-naar-de-juwelier-om-te-shinen"],
    "meervoud": "juweliers",
    "blogonderwerp": "sieraden",
    "filtervoorbeeld": "trouwringen, horloges of reparatie",
    "voorbeeld": {"naam": "Jouw juwelier", "foto": "assets/uploads/2023/05/juwelier-nijmegen-533x400.webp", "kenmerken": ["trouwringen", "reparatie"], "actie": "Gratis graveren"},
    "knop_voorbeeld": "afspraak maken, collectie, route",
}, {
    "slug": "bloemist",
    "listdom": set(),
    "bron_csv": "bloemist-aangevuld.csv",
    "plaatsen": {"Lent", "Nijmegen", "Oosterhout"},
    "naam": "Bloemisten in Nijmegen",
    "enkelvoud": "Bloemist",
    "groep": "Winkelen",
    "soorten": {"Bloemist"},
    "schema": "Florist",
    "beschrijving": "Bloemisten, plantenwinkels en tuincentra in Nijmegen, ook voor bezorgen en rouwwerk.",
    "intro": "<p>Een boeket voor een verjaardag, bloemen voor een bruiloft of een mooi rouwstuk: in Nijmegen zitten bloemisten in elke wijk, en veel bezorgen ook.</p><p>Op deze pagina vind je alle bloemisten in Nijmegen.</p>",
    "faq": [
        ("Bezorgen bloemisten in Nijmegen?",
         "De meeste wel, vaak dezelfde dag. Filter op bezorgen."),
    ],
    "artikelen": ["bloemist-nijmegen-waar-kun-je-terecht"],
    "blogs": ["bloemist-nijmegen-waar-kun-je-terecht"],
    "meervoud": "bloemisten",
    "blogonderwerp": "bloemen",
    "filtervoorbeeld": "bezorgen, rouwwerk of planten",
    "voorbeeld": {"naam": "Jouw bloemist", "foto": "assets/uploads/2022/12/bloemen-kopen-bij-de-bloemist-533x400.webp", "kenmerken": ["bezorgen", "rouwwerk"], "actie": "Vandaag besteld, vandaag bezorgd"},
    "knop_voorbeeld": "bestellen, route, bellen",
}, {
    "slug": "hobbywinkel",
    "listdom": set(),
    "bron_csv": "hobbywinkel-aangevuld.csv",
    "plaatsen": {"Lent", "Nijmegen", "Oosterhout"},
    "naam": "Hobby- en speelgoedwinkels in Nijmegen",
    "enkelvoud": "Winkel",
    "de_woord": False,
    "groep": "Winkelen",
    "soorten": {"Hobbywinkel"},
    "schema": "HobbyShop",
    "beschrijving": "Hobby-, creatief-, speelgoed- en muziekwinkels in Nijmegen.",
    "intro": "<p>Garen en stoffen, een nieuw bordspel, modelbouw of een gitaar: in Nijmegen zitten gespecialiseerde winkels voor elke hobby, vaak met workshops erbij.</p><p>Op deze pagina vind je alle hobby-, speelgoed- en muziekwinkels in Nijmegen.</p>",
    "faq": [
        ("Geven hobbywinkels in Nijmegen workshops?",
         "Een aantal wel. Filter op workshops."),
    ],
    "artikelen": ["7-populaire-hobbys-voor-senioren-in-nijmegen"],
    "blogs": ["7-populaire-hobbys-voor-senioren-in-nijmegen"],
    "meervoud": "winkels",
    "blogonderwerp": "hobby",
    "filtervoorbeeld": "stoffen en garen, spellen of muziekinstrumenten",
    "voorbeeld": {"naam": "Jouw winkel", "foto": "assets/uploads/2023/11/hobbys-modelspoorbouw-in-nijmegen-533x400.webp", "kenmerken": ["knutselen", "workshops"], "actie": "Gratis workshop bij aankoop"},
    "knop_voorbeeld": "assortiment, route, webshop",
}, {
    "slug": "parfumerie",
    "listdom": set(),
    "bron_csv": "parfumerie-aangevuld.csv",
    "plaatsen": {"Lent", "Nijmegen", "Oosterhout"},
    "naam": "Parfumerieën in Nijmegen",
    "enkelvoud": "Parfumerie",
    "groep": "Winkelen",
    "soorten": {"Parfumerie"},
    "schema": "Store",
    "beschrijving": "Parfumerieën en cosmeticawinkels in Nijmegen.",
    "intro": "<p>Een nieuwe geur, advies over huidverzorging of een cadeau: in de Nijmeegse binnenstad zitten parfumerieën en cosmeticawinkels, van ketens tot zelfstandige zaken met nichemerken.</p><p>Op deze pagina vind je alle parfumerieën in Nijmegen.</p>",
    "faq": [
        ("Kan ik een parfum eerst testen?",
         "Ja, in de winkel kun je testen en krijg je vaak proefjes mee."),
    ],
    "artikelen": ["laat-je-verleiden-door-de-geuren-uit-de-parfumerieen-van-nijmegen"],
    "blogs": ["laat-je-verleiden-door-de-geuren-uit-de-parfumerieen-van-nijmegen"],
    "meervoud": "parfumerieën",
    "blogonderwerp": "parfum en cosmetica",
    "filtervoorbeeld": "natuurlijke cosmetica of advies",
    "voorbeeld": {"naam": "Jouw parfumerie", "foto": "assets/uploads/2026/02/Nijmegen-de-oudste-stad-met-de-jongste-energie-533x400.webp", "kenmerken": ["parfum", "natuurlijke cosmetica"], "actie": "Gratis huidanalyse"},
    "knop_voorbeeld": "assortiment, route, webshop",
}, {
    "slug": "elektronica",
    "listdom": set(),
    "bron_csv": "elektronica-aangevuld.csv",
    "plaatsen": {"Lent", "Nijmegen", "Oosterhout"},
    "naam": "Elektronicawinkels en reparatie in Nijmegen",
    "enkelvoud": "Winkel",
    "de_woord": False,
    "groep": "Winkelen",
    "soorten": {"Elektronica"},
    "schema": "ElectronicsStore",
    "beschrijving": "Elektronicawinkels en reparatiezaken voor telefoons, computers en witgoed in Nijmegen.",
    "intro": "<p>Een gebarsten scherm, een laptop die niet meer opstart of een nieuwe wasmachine: in Nijmegen zitten elektronicawinkels en reparateurs die je vaak dezelfde dag helpen.</p><p>Op deze pagina vind je alle elektronicawinkels en reparatiezaken in Nijmegen.</p>",
    "faq": [
        ("Waar laat ik mijn telefoon repareren in Nijmegen?",
         "Filter op reparatie en telefoons."),
    ],
    "artikelen": [],
    "blogs": [],
    "meervoud": "winkels",
    "blogonderwerp": "elektronica",
    "filtervoorbeeld": "telefoons, reparatie of witgoed",
    "voorbeeld": {"naam": "Jouw winkel", "foto": "assets/uploads/2022/11/pc-gaming-markt-in-nijmegen-533x400.webp", "kenmerken": ["reparatie", "telefoons"], "actie": "Reparatie klaar terwijl je wacht"},
    "knop_voorbeeld": "reparatie aanmelden, route, webshop",
}, {
    "slug": "fietsenwinkel",
    "listdom": set(),
    "bron_csv": "fietsenwinkel-aangevuld.csv",
    "plaatsen": {"Lent", "Nijmegen", "Oosterhout"},
    "naam": "Fietsenwinkels in Nijmegen",
    "enkelvoud": "Fietsenwinkel",
    "groep": "Winkelen",
    "soorten": {"Fietsenwinkel"},
    "schema": "BikeStore",
    "beschrijving": "Fietsenwinkels, fietsenmakers en fietsverhuur in Nijmegen, Lent en Oosterhout.",
    "intro": "<p>Nijmegen is fietsstad: met de fiets ben je overal snel, ook over de Snelbinder naar Lent. Voor een nieuwe fiets, een e-bike of een lekke band vind je fietsenwinkels en fietsenmakers in elke wijk.</p><p>Op deze pagina vind je alle fietsenwinkels in Nijmegen.</p>",
    "faq": [
        ("Kan ik in Nijmegen een fiets huren?",
         "Ja, een paar fietsenwinkels verhuren fietsen. Filter op fietsverhuur."),
    ],
    "artikelen": [],
    "blogs": [],
    "meervoud": "fietsenwinkels",
    "blogonderwerp": "fietsen",
    "filtervoorbeeld": "e-bikes, reparatie of fietsverhuur",
    "voorbeeld": {"naam": "Jouw fietsenwinkel", "foto": "assets/uploads/2026/02/Nijmegen-de-oudste-stad-met-de-jongste-energie-533x400.webp", "kenmerken": ["e-bikes", "reparatie"], "actie": "Gratis haal- en brengservice"},
    "knop_voorbeeld": "reparatie aanmelden, route, webshop",
}, {
    "slug": "boekhandel",
    "listdom": set(),
    "bron_csv": "boekhandel-aangevuld.csv",
    "plaatsen": {"Lent", "Nijmegen", "Oosterhout"},
    "naam": "Boekhandels in Nijmegen",
    "enkelvoud": "Boekhandel",
    "groep": "Winkelen",
    "soorten": {"Boekhandel"},
    "schema": "BookStore",
    "beschrijving": "Boekhandels, antiquariaten en stripwinkels in Nijmegen.",
    "intro": "<p>Nijmegen is een studentenstad met een rijke boekentraditie: van grote boekhandels in de binnenstad tot antiquariaten en stripwinkels, vaak met lezingen en signeersessies.</p><p>Op deze pagina vind je alle boekhandels in Nijmegen.</p>",
    "faq": [
        ("Zijn er tweedehands boekwinkels in Nijmegen?",
         "Ja, filter op tweedehands boeken."),
    ],
    "artikelen": ["books-4-life-viert-125-jarig-bestaan-met-feestje-op-laatste-dag-van-de-boekenweek-2024"],
    "blogs": [],
    "meervoud": "boekhandels",
    "blogonderwerp": "boeken",
    "filtervoorbeeld": "tweedehands boeken, strips of kinderboeken",
    "voorbeeld": {"naam": "Jouw boekhandel", "foto": "assets/uploads/2024/03/Books-4-Life-viert-125-jarig-bestaan-met-feestje-op-laatste-dag-van-de-Boekenweek-2024-533x400.webp", "kenmerken": ["nieuwe boeken", "kinderboeken"], "actie": "Lezing deze maand"},
    "knop_voorbeeld": "boek bestellen, route, agenda",
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
            "website": met_schema(m.get("lsd_website", "")),
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


def met_schema(url):
    """'www.voorbeeld.nl' -> 'https://www.voorbeeld.nl' (anders wordt het een relatieve link)."""
    url = (url or "").strip()
    return url if not url or re.match(r"https?://", url) else "https://" + url.lstrip("/")


def osm_uit_csv(pad, soorten, plaatsen=("Nijmegen",)):
    uit = []
    for x in csv.DictReader(open(pad, encoding="utf-8")):
        if x["soort"] in soorten and x["plaats"] in plaatsen:
            uit.append({"naam": x["naam"], "adres": x["adres"].rstrip(", "), "postcode": x["postcode"], "plaats": x["plaats"],
                        "telefoon": x["telefoon"], "website": met_schema(x["website"]), "lat": x["lat"], "lon": x["lon"],
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


def bedrijf_pagina(b, cat, anderen, root="../../", berichten=()):
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
    if berichten:
        out.append('        <section class="gids-sectie">\n          <h2>In het nieuws</h2>\n          <ul class="archieflijst">')
        out.extend('            <li><time datetime="%s">%s</time> <a href="%snieuwsoverzicht/%s/">%s</a></li>'
                   % (x["datum"][:10], esc(datum_tijd_nl(x["datum"])), root, x["slug"], esc(x["titel"])) for x in berichten[:5])
        out.append("          </ul>\n        </section>")
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
    # Betalende bedrijven (partner, uitgelicht) krijgen een grote marker met hun foto, buiten de bolletjes
    punten = [[b["naam"], round(float(b["lat"]), 6), round(float(b["lon"]), 6), "%sbedrijvengids/%s/" % (root, b["slug"]), adresregel(b), g]
              + ([1, foto_url(b.get("foto") or "", root)] if b.get("uitgelicht") else [])
              for g, b in bedrijven if b["lat"]]
    data = json.dumps({"groepen": groepen, "punten": punten}, ensure_ascii=False).replace("</", "<\\/")
    return ('%s          <div id="gidskaart" class="gidskaart" role="region" aria-label="Kaart met bedrijven"></div>\n'
            '          <script type="application/json" id="kaartdata">%s</script>\n'
            '          <script src="%sassets/js/kaart.js?v=6" defer></script>'
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
    """Correcties van de redactie (data/bedrijvengids-correcties.json): naam, adres, postcode, ligging, extra vestiging,
    geen_adres (zonder adres en niet op de kaart)."""
    corr = json.loads(pad.read_text(encoding="utf-8")) if pad.exists() else {}
    for b in bedrijven:
        b.update({k: v for k, v in corr.get(b["slug"], {}).items() if k in ("naam", "adres", "postcode", "plaats", "lat", "lon", "extra_vestiging")})
        if corr.get(b["slug"], {}).get("geen_adres"):
            # Werkt vanuit huis of bij de klant: alleen de plaats, niet op de kaart
            b.update({"adres": "", "postcode": "", "lat": "", "lon": ""})


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


def homepage_bijwerken(groepen, aantal=8):
    """De bedrijven op de homepage, tussen <!-- bedrijven --> en <!-- /bedrijven --> in index.html: de partners en
    andere betalende bedrijven (besluit Frans, 24-10-2026). Elke dag een andere volgorde, zodat iedereen aan de beurt komt."""
    rang = {"hoofdpartner": 0, "partner": 1, "uitgelicht": 2}
    gezien, kandidaten = set(), []
    for groep, cats in groepen:
        for cat, gids, overig in cats:
            for b in gids + overig:
                if b.get("uitgelicht") and b["slug"] not in gezien:
                    gezien.add(b["slug"])
                    kandidaten.append((rang.get(b.get("pakket"), 3), groep, b))
    dag = datetime.date.today().toordinal()
    kandidaten.sort(key=lambda x: (x[0], hash_dag(x[2]["slug"], dag)))
    kaarten = []
    for _, groep, b in kandidaten[:aantal]:
        foto = '<img src="%s" alt="" loading="lazy">' % esc(foto_url(b["foto"], "./")) if b.get("foto") else ""
        kaarten.append('          <article class="kaart"><a href="./bedrijvengids/%s/">%s<div class="kaart__tekst"><div class="label">%s</div>'
                       '<h3>%s</h3><p>%s</p></div></a></article>' % (b["slug"], foto, esc(groep), esc(b["naam"]), esc(adresregel(b))))
    blok = '        <div class="raster">\n%s\n        </div>\n        <p class="gids-verder"><a href="./bedrijvengids/">Naar de bedrijvengids</a></p>' % "\n".join(kaarten)
    pad = ROOT / "index.html"
    t, n = re.subn(r"([ \t]*)<!-- bedrijven -->.*?<!-- /bedrijven -->",
                   lambda m: "%s<!-- bedrijven -->\n%s\n%s<!-- /bedrijven -->" % (m.group(1), blok, m.group(1)), pad.read_text(encoding="utf-8"), flags=re.S)
    if n and kaarten:
        pad.write_text(t, encoding="utf-8")


def hash_dag(slug_, dag):
    """Vaste, maar elke dag andere volgorde (hash() van Python verschilt per run)."""
    return hashlib.md5(("%s-%d" % (slug_, dag)).encode()).hexdigest()


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
        # Een partner of betalend bedrijf valt nooit automatisch weg, alleen als de redactie dat besluit.
        weg = [b for b in gids + overig if scan.get(b["slug"], {}).get("status") == "verwijderd"
               and not (b.get("uitgelicht") and scan[b["slug"]].get("reden", "").startswith("automatisch"))
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
    # Nieuwsberichten over een bedrijf komen op zijn pagina (tools/nieuws.py bepaalt welke)
    per_bedrijf = nieuws.koppelingen(nieuws.laad(), [(b["slug"], b.get("website")) for _, g, o in gebouwd for b in g + o])
    for cat, gids, overig in gebouwd:
        extra = [b for c, g, o in gebouwd if c is not cat for b in g + o if cat["slug"] in b.get("ook_in", [])]
        artikelen = [(s_, titel_van(s_)) for s_ in cat["artikelen"] if titel_van(s_)]
        schrijf("bedrijvengids-categorie/%s" % cat["slug"], categorie_pagina(cat, gids, overig + extra, artikelen))
        for b in gids + overig:
            anderen = [x for x in gids if x is not b] + [x for x in overig if x is not b]
            schrijf("bedrijvengids/%s" % b["slug"], bedrijf_pagina(b, cat, anderen, berichten=per_bedrijf.get(b["slug"], ())))
        blog_blokken(cat, gids + overig + extra)
        groepen.setdefault(cat["groep"], []).append((cat, gids, overig + extra))
    if xml_.exists():
        pad.write_text(json.dumps(opgeslagen, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    schrijf_redirects(alle_weg, [(oud, cat["slug"]) for cat in CATEGORIEEN for oud in sorted(cat["listdom"]) if oud != cat["slug"]])
    (ROOT / "data" / "bedrijvengids-vermeldingen.json").write_text(
        json.dumps(alle_vermeldingen, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    schrijf("bedrijvengids", start_pagina(list(groepen.items())))
    homepage_bijwerken(list(groepen.items()))
    # Pagina's die bij geen enkele categorie meer horen en geen doorverwijzing hebben (bijvoorbeeld een dubbel, of een
    # cafetaria die volgens de scan bij afhaal hoort) haal ik weg; ze zijn nooit als echte vermelding online geweest
    bewaren = {b["slug"] for _, gids, overig in (x for cats in groepen.values() for x in cats) for b in gids + overig}
    bewaren |= {b["slug"] for b, _ in alle_weg}
    for map_ in (ROOT / "bedrijvengids").iterdir():
        if map_.is_dir() and map_.name not in bewaren:
            shutil.rmtree(map_)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "/mnt/project-files")
