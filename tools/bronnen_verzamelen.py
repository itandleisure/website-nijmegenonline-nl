"""Bedrijven voor een categorie van de bedrijvengids verzamelen uit OpenStreetMap en Overture Maps.

Stap 1 van de standaard in de README. Schrijft in de projectbestanden (advies/osm-bedrijvengids/):
- <categorie>-aangevuld.csv: de bedrijven in de gemeente Nijmegen met een eigen website (zelfde kolommen als
  sportscholen-aangevuld.csv, zodat tools/bedrijvengids.py ze leest)
- <categorie>-uitgefilterd.csv: wat er meteen af valt, met de reden (permanent gesloten, geen eigen website,
  onbetrouwbare bron, naam hoort bij een andere categorie); dubbelen worden samengevoegd

Bedrijven die bij een eerdere categorie zijn gescand en volgens de scan bij deze categorie horen (bijvoorbeeld een
lunchroom tussen de restaurants), komen er ook in; hun scan wordt hergebruikt.

Overture wordt eenmalig per release opgehaald (alle plaatsen rond Nijmegen, ±18.000) en lokaal bewaard.

Gebruik: python tools/bronnen_verzamelen.py restaurant [/mnt/project-files]
Vraagt: pip install duckdb
"""
import csv
import json
import math
import pathlib
import re
import sys
import unicodedata

ROOT = pathlib.Path(__file__).resolve().parent.parent
RELEASE = "2026-10-21.0"
# Gemeente Nijmegen: Nijmegen, Lent en Oosterhout (postcodes zijn te ruim, dus op plaatsnaam)
PLAATSEN = {"nijmegen", "lent", "oosterhout"}

# Per categorie: welke OSM-categorie en welke Overture-soorten erbij horen
BRONNEN = {
    "restaurant": {
        "osm": {"Restaurants"},
        "overture": lambda basis, soort: basis == "restaurant" and soort not in (
            "cafeteria", "bakery", "ice_cream_shop", "sandwich_shop", "fast_food_restaurant", "chocolatier", "candy_store",
            "cupcake_shop", "donut_shop", "bagel_shop", "delicatessen", "japanese_confectionery_shop", "doner_kebab_restaurant"),
        "soort": "Restaurant",
        # Naam zegt al dat het een andere categorie is: niet scannen (scheelt kosten), wel in de lijst met de reden
        "andere_soort": r"bakker|cafetaria|snack|friture|frituur|afhaal|shoarma|kebab|d[oö]ner|broodje|backwerk|bagels|"
                        r"burger king|mcdonald|kfc|domino|new york pizza|subway|febo|ijssalon|gelato|koffie|coffee|lunchroom|"
                        r"bezorg|catering|kiosk",
    },
    "lunch": {
        "osm": {"Lunch, koffie en ontbijt"},
        "overture": lambda basis, soort: soort in (
            "cafe", "coffee_shop", "sandwich_shop", "breakfast_and_brunch_restaurant", "salad_bar", "tea_room", "bagel_shop"),
        "soort": "Lunchroom",
        "andere_soort": r"bakker|bakery|cafetaria|snack|friture|frituur|shoarma|kebab|d[oö]ner|burger king|mcdonald|kfc|"
                        r"ijssalon|gelato|bubble|boba|kiosk|catering|internet",
    },
}

# Een link naar zo'n site is geen eigen website: dan valt het bedrijf af (standaard: geen eigen site = niet in de gids)
GEEN_EIGEN_SITE = ("facebook.com", "instagram.com", "thuisbezorgd.nl", "tripadvisor", "detelefoongids.nl", "google.com",
                   "goo.gl", "linktr.ee", "ubereats.com", "deliveroo", "iens.nl", "thefork", "eet.nu", "yelp.",
                   "booking.com", "wix.com/", "telefoonboek.nl", "openingstijden.", "foursquare.com", "zomato.com", "linkedin.com")

KEUKEN = {
    "italian": "Italiaans", "pizza": "Italiaans", "sushi": "Japans", "japanese": "Japans", "chinese": "Chinees",
    "dim_sum": "Chinees", "asian": "Aziatisch", "asian_fusion": "Aziatisch", "thai": "Thais", "vietnamese": "Vietnamees",
    "indian": "Indiaas", "indonesian": "Indonesisch", "surinamese": "Surinaams", "french": "Frans", "greek": "Grieks",
    "turkish": "Turks", "spanish": "Spaans", "tapas": "Spaans", "mexican": "Mexicaans", "texmex": "Mexicaans",
    "taco": "Mexicaans", "middle_eastern": "Midden-Oosters", "lebanese": "Midden-Oosters", "syrian": "Midden-Oosters",
    "moroccan": "Marokkaans", "steak_house": "Steakhouse", "steakhouse": "Steakhouse", "burger": "Burgers",
    "pancake": "Pannenkoeken", "vegetarian": "Vegetarisch", "vegan": "Vegan", "korean": "Koreaans",
    "american": "Amerikaans", "caribbean": "Caribisch", "afghani": "Afghaans", "seafood": "Vis",
    "mediterranean": "Mediterraan", "european": "Europees", "international": "Internationaal", "regional": "Hollands",
}


def sleutel(naam):
    tekst = unicodedata.normalize("NFKD", naam).encode("ascii", "ignore").decode().lower()
    tekst = re.sub(r"\b(restaurant|nijmegen|eetcafe|grand cafe|de|het|t)\b", "", tekst)
    return re.sub(r"[^a-z0-9]", "", tekst)


def afstand(a, b):
    """Meters tussen twee punten (lat, lon); op deze schaal is een platte benadering genoeg."""
    dy = (float(a[0]) - float(b[0])) * 111_000
    dx = (float(a[1]) - float(b[1])) * 111_000 * math.cos(math.radians(51.84))
    return math.hypot(dx, dy)


def domein(url):
    return re.sub(r"^https?://(www\.)?([^/]+).*$", r"\2", (url or "").lower())


def eigen_site(urls):
    for u in urls or []:
        if u and not any(x in u.lower() for x in GEEN_EIGEN_SITE):
            return u.strip()
    return ""


def dubbel(a, b):
    """Zelfde bedrijf: dichtbij en (bijna) dezelfde naam of dezelfde website."""
    if not (a["lat"] and b["lat"]):
        return a["naam"] == b["naam"] and a["adres"] == b["adres"]
    if a["website"] and domein(a["website"]) == domein(b["website"]) and a["adres"] and a["adres"].lower() == b["adres"].lower():
        return True   # zelfde site en adres, ook als de ligging (slecht gegeocodeerd) ver uit elkaar ligt
    meters = afstand((a["lat"], a["lon"]), (b["lat"], b["lon"]))
    ka, kb = sleutel(a["naam"]), sleutel(b["naam"])
    if meters < 150 and ka == kb:
        return True
    if meters < 60 and min(len(ka), len(kb)) >= 4 and (ka in kb or kb in ka):
        return True
    return bool(meters < 60 and a["website"] and domein(a["website"]) == domein(b["website"]) and eigen_site([a["website"]]))


def postcode(pc):
    m = re.match(r"^\s*(\d{4})\s*([A-Za-z]{2})\s*$", pc or "")
    return "%s %s" % (m.group(1), m.group(2).upper()) if m else (pc or "").strip()


def adres(tekst):
    """Overture schrijft adressen soms in hoofdletters: 'MOLENSTRAAT 12' wordt 'Molenstraat 12'."""
    tekst = (tekst or "").strip().rstrip(",")
    return tekst.title() if tekst.isupper() else tekst


def overture_laden(bron):
    """Eenmalig per release: alle plaatsen rond Nijmegen uit Overture (S3, zonder account)."""
    import duckdb
    pad = bron / "advies" / "osm-bedrijvengids" / ("overture-nijmegen-%s.parquet" % RELEASE)
    c = duckdb.connect()
    if not pad.exists():
        c.sql("INSTALL httpfs; LOAD httpfs;")
        c.sql("CREATE OR REPLACE SECRET anoniem (TYPE s3, KEY_ID '', SECRET '', REGION 'us-west-2')")
        c.sql("""COPY (SELECT id, names.primary naam, confidence, websites, phones, addresses, operating_status, basic_category,
                 taxonomy, bbox.xmin lon, bbox.ymin lat, sources
                 FROM read_parquet('s3://overturemaps-us-west-2/release/%s/theme=places/type=place/*')
                 WHERE bbox.xmin BETWEEN 5.74 AND 5.96 AND bbox.ymin BETWEEN 51.77 AND 51.90) TO '%s'""" % (RELEASE, pad))
    return c.sql("SELECT naam, confidence, websites, phones, addresses, operating_status, basic_category, taxonomy.primary, "
                 "lon, lat, sources[1].dataset FROM '%s'" % pad).fetchall()


def uit_andere_scans(categorie, soort):
    """Bedrijven uit een eerder gescande categorie die volgens de scan hierbij horen (niet_in die categorie)."""
    gids = json.loads((ROOT / "data" / "bedrijvengids.json").read_text(encoding="utf-8"))
    scan = json.loads((ROOT / "data" / "bedrijvengids-scan.json").read_text(encoding="utf-8"))
    uit = []
    for cat, inhoud in gids.items():
        for b in inhoud["overig"]:
            s = scan.get(b["slug"], {})
            if cat in (s.get("niet_in") or {}) and s.get("hoofdcategorie") == categorie and s.get("status") != "verwijderd":
                uit.append({"soort": soort, "naam": b["naam"], "adres": b["adres"], "postcode": b["postcode"], "plaats": b["plaats"],
                            "gemeente": "Nijmegen", "website": b["website"], "telefoon": b["telefoon"], "bron": b.get("bron", ""),
                            "betrouwbaarheid": "", "ook_in_openstreetmap": "", "lat": b["lat"], "lon": b["lon"],
                            "keuken": b.get("keuken", ""), "terras": "", "status": "", "uit_scan": cat})
    return uit


def main(categorie, bron):
    bron = pathlib.Path(bron)
    regels = BRONNEN[categorie]
    # Eerst de bedrijven die al gescand zijn: die gaan voor bij het samenvoegen, zodat hun naam en adres (en dus de
    # url en de scan) gelijk blijven
    kandidaten, uit = uit_andere_scans(categorie, regels["soort"]), []

    def weg(b, reden):
        uit.append(dict(b, reden=reden))

    for x in csv.DictReader(open(bron / "advies" / "osm-bedrijvengids" / "osm-bedrijven-regio-nijmegen.csv", encoding="utf-8")):
        if x["categorie"] not in regels["osm"] or x["gemeente"] != "Nijmegen":
            continue
        kandidaten.append({"soort": regels["soort"], "naam": x["naam"], "adres": adres(x["adres"]), "postcode": postcode(x["postcode"]),
                           "plaats": x["plaats"] or "Nijmegen", "gemeente": "Nijmegen", "website": x["website"], "telefoon": x["telefoon"],
                           "bron": "OpenStreetMap", "betrouwbaarheid": "", "ook_in_openstreetmap": "ja", "lat": x["lat"], "lon": x["lon"],
                           "keuken": "; ".join(dict.fromkeys(KEUKEN.get(k.strip(), "") for k in x["keuken"].split(";") if KEUKEN.get(k.strip()))),
                           "terras": "ja" if x["terras"] == "yes" else "", "status": ""})
    for naam, zeker, sites, tels, adressen, status, basis, soort, lon, lat, dataset in overture_laden(bron):
        a = (adressen or [{}])[0] or {}
        if not naam or (a.get("locality") or "").lower() not in PLAATSEN or not regels["overture"](basis, soort or ""):
            continue
        kandidaten.append({"soort": regels["soort"], "naam": naam, "adres": adres(a.get("freeform")), "postcode": postcode(a.get("postcode")),
                           "plaats": (a.get("locality") or "").title(), "gemeente": "Nijmegen",
                           "website": eigen_site(sites) or (sites or [""])[0], "telefoon": (tels or [""])[0],
                           "bron": "Overture (%s)" % dataset, "betrouwbaarheid": "%.2f" % zeker, "ook_in_openstreetmap": "nee",
                           "lat": "%.6f" % lat, "lon": "%.6f" % lon,
                           "keuken": KEUKEN.get(re.sub(r"_restaurant$", "", soort or ""), ""), "terras": "", "status": status or ""})

    # Dubbelen samenvoegen. Volgorde: al gescand, dan OSM (handmatig bijgehouden), dan Overture op betrouwbaarheid;
    # de latere vult website en telefoon aan.
    kandidaten.sort(key=lambda b: (not b.get("uit_scan"), b["bron"] != "OpenStreetMap", -float(b["betrouwbaarheid"] or 1)))
    gehouden = []
    for b in kandidaten:
        zelfde = next((g for g in gehouden if dubbel(g, b)), None)
        if zelfde:
            if b["bron"] == "OpenStreetMap":
                zelfde["ook_in_openstreetmap"] = "ja"
            for veld in ("website", "telefoon", "keuken", "postcode"):
                if not zelfde[veld] or (veld == "website" and not eigen_site([zelfde[veld]])):
                    zelfde[veld] = b[veld] or zelfde[veld]
            if b["status"] == "permanently_closed" and not zelfde.get("uit_scan"):
                zelfde["status"] = zelfde["status"] or b["status"]
            continue
        gehouden.append(b)

    houden = []
    for b in gehouden:
        if b.get("uit_scan"):
            houden.append(b)   # al gecontroleerd en gescand
        elif b["status"] == "permanently_closed":
            weg(b, "permanent gesloten volgens Overture")
        elif not b["website"]:
            weg(b, "geen website")
        elif not eigen_site([b["website"]]):
            weg(b, "geen eigen website (alleen %s)" % domein(b["website"]))
        elif regels.get("andere_soort") and re.search(regels["andere_soort"], b["naam"].lower()):
            weg(b, "hoort bij een andere categorie (naam: %s)" % re.search(regels["andere_soort"], b["naam"].lower()).group(0))
        elif b["betrouwbaarheid"] and float(b["betrouwbaarheid"]) < 0.5:
            weg(b, "onzekere bron (betrouwbaarheid %s)" % b["betrouwbaarheid"])
        else:
            houden.append(b)

    map_ = bron / "advies" / "osm-bedrijvengids"
    velden = ["soort", "naam", "adres", "postcode", "plaats", "gemeente", "website", "telefoon", "bron", "betrouwbaarheid",
              "ook_in_openstreetmap", "lat", "lon", "keuken", "terras", "status"]
    for naam, rijen, extra in (("%s-aangevuld.csv" % categorie, houden, []), ("%s-uitgefilterd.csv" % categorie, uit, ["reden"])):
        with open(map_ / naam, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=velden + extra, extrasaction="ignore")
            w.writeheader()
            w.writerows(sorted(rijen, key=lambda b: b["naam"].lower()))
    print("%s: %d gehouden (%d al gescand bij een andere categorie), %d uitgefilterd"
          % (categorie, len(houden), sum(1 for b in houden if b.get("uit_scan")), len(uit)))
    for reden in sorted({b["reden"].split(" (")[0] for b in uit}):
        print("  %-45s %d" % (reden, sum(1 for b in uit if b["reden"].startswith(reden))))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "/mnt/project-files")
