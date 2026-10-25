"""Meet hoe NijmegenOnline scoort in Google en in AI-antwoorden en bewaart dat versleuteld voor /statistiek/.

Elke run (wekelijks, zie .github/workflows/statistiek.yml) voegt een meetpunt toe:
1. Search Console: klikken, vertoningen en gemiddelde positie per week (16 maanden terug), plus de beste
   zoekwoorden en pagina's van de laatste 28 dagen. Overgeslagen als GSC_SERVICE_ACCOUNT_JSON ontbreekt.
2. Zoekwoorden: positie in Google (top 50, nl-NL) voor de vaste lijst uit data/statistiek-instellingen.json,
   of NijmegenOnline als bron in het AI-overzicht bovenaan staat, en wie er op 1-3 staan (DataForSEO SERP).
3. AI-antwoorden: de vaste vragen aan ChatGPT, Gemini, Perplexity en Claude (met zoeken op internet), en of
   NijmegenOnline genoemd of als bron gelinkt wordt (DataForSEO AI Optimization). Alleen als de vorige
   AI-meting ouder is dan "ai_elke_dagen", omdat dit het duurste deel is.

Alles staat in statistiek/data.json, versleuteld met AES-GCM (sleutel via PBKDF2 uit STATISTIEK_WACHTWOORD).
De repo is openbaar, dus zonder wachtwoord is er niets te lezen; de pagina ontsleutelt in de browser.

Omgeving: STATISTIEK_WACHTWOORD (verplicht), DATAFORSEO_LOGIN + DATAFORSEO_PASSWORD, GSC_SERVICE_ACCOUNT_JSON.
Gebruik: python tools/statistiek.py [--alleen gsc,zoekwoorden,ai] [--ai-forceren]
"""
import base64
import collections
import concurrent.futures
import datetime
import json
import os
import pathlib
import re
import sys
import urllib.parse

import requests
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

ROOT = pathlib.Path(__file__).resolve().parent.parent
INSTELLINGEN = json.loads((ROOT / "data" / "statistiek-instellingen.json").read_text(encoding="utf-8"))
BESTAND = ROOT / "statistiek" / "data.json"
DOMEIN = INSTELLINGEN["domein"]
NAAM = re.compile(r"nijmegen\s?online", re.I)
API = "https://api.dataforseo.com/v3/"
ITERATIES = 250000
VANDAAG = datetime.date.today()


# ---------- versleuteling (zelfde formaat als de pagina met WebCrypto leest) ----------

def sleutel(wachtwoord, zout, iteraties):
    return PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=zout, iterations=iteraties).derive(wachtwoord.encode())


def openen(wachtwoord):
    if not BESTAND.exists():
        return {"zoekwoorden": [], "ai": [], "gsc": None}
    pakket = json.loads(BESTAND.read_text(encoding="utf-8"))
    zout, iv, data = (base64.b64decode(pakket[k]) for k in ("salt", "iv", "data"))
    try:
        return json.loads(AESGCM(sleutel(wachtwoord, zout, pakket["iter"])).decrypt(iv, data, None))
    except InvalidTag:
        sys.exit("statistiek/data.json is met een ander wachtwoord versleuteld dan STATISTIEK_WACHTWOORD. "
                 "Zet het oude wachtwoord terug, of verwijder data.json om opnieuw te beginnen.")


def opslaan(gegevens, wachtwoord):
    zout, iv = os.urandom(16), os.urandom(12)
    data = AESGCM(sleutel(wachtwoord, zout, ITERATIES)).encrypt(iv, json.dumps(gegevens, ensure_ascii=False).encode(), None)
    pakket = {"v": 1, "iter": ITERATIES, "salt": base64.b64encode(zout).decode(), "iv": base64.b64encode(iv).decode(),
              "data": base64.b64encode(data).decode()}
    BESTAND.write_text(json.dumps(pakket) + "\n", encoding="utf-8")


# ---------- DataForSEO ----------

def dataforseo(pad, taak):
    login, wachtwoord = os.environ.get("DATAFORSEO_LOGIN"), os.environ.get("DATAFORSEO_PASSWORD")
    auth = (login, wachtwoord) if login and wachtwoord else None  # zonder: de Claude-proxy vult het in
    for poging in range(3):
        try:
            r = requests.post(API + pad, json=[taak], auth=auth, timeout=180)
            t = r.json()["tasks"][0]
            if t["status_code"] == 20000:
                return t
            fout = t["status_message"]
        except (requests.RequestException, KeyError, ValueError) as e:
            fout = str(e)
    print("  mislukt (%s): %s" % (pad, fout), file=sys.stderr)
    return None


def domein_van(url):
    host = urllib.parse.urlsplit(url or "").hostname or ""
    return host[4:] if host.startswith("www.") else host


def zoekwoord_meten(zoekwoord):
    t = dataforseo("serp/google/organic/live/advanced", {
        "keyword": zoekwoord, "location_code": 2528, "language_code": "nl", "device": "desktop",
        "depth": 50, "load_async_ai_overview": True})
    if not t:
        return zoekwoord, None, 0
    items = (t["result"] or [{}])[0].get("items") or []
    uitslag = {"pos": None, "url": None, "aio": False, "aio_bron": False, "top": []}
    for item in items:
        if item["type"] == "organic":
            d = domein_van(item.get("url"))
            if len(uitslag["top"]) < 3:
                uitslag["top"].append(d)
            if d.endswith(DOMEIN) and uitslag["pos"] is None:
                uitslag["pos"] = item["rank_group"]
                uitslag["url"] = urllib.parse.urlsplit(item["url"]).path
        elif item["type"] == "ai_overview":
            uitslag["aio"] = True
            bronnen = [domein_van(b.get("url")) for b in item.get("references") or []]
            uitslag["aio_bron"] = any(b.endswith(DOMEIN) for b in bronnen)
    return zoekwoord, uitslag, t.get("cost", 0)


def zoekwoorden_meten():
    lijst = [(groep, z) for groep, zoekwoorden in INSTELLINGEN["zoekwoorden"].items() for z in zoekwoorden]
    groep_van = dict((z, g) for g, z in lijst)
    posities, kosten = {}, 0
    with concurrent.futures.ThreadPoolExecutor(8) as pool:
        for zoekwoord, uitslag, prijs in pool.map(zoekwoord_meten, [z for _, z in lijst]):
            kosten += prijs
            if uitslag:
                uitslag["groep"] = groep_van[zoekwoord]
                posities[zoekwoord] = uitslag
    print("Zoekwoorden: %d van %d gemeten, %d in top 10 ($%.2f)" % (
        len(posities), len(lijst), sum(1 for u in posities.values() if u["pos"] and u["pos"] <= 10), kosten))
    return {"datum": VANDAAG.isoformat(), "posities": posities, "kosten": round(kosten, 3)}


def ai_vraag(args):
    vraag, model, (bron, modelnaam) = args
    t = dataforseo("ai_optimization/%s/llm_responses/live" % bron, {
        "user_prompt": vraag, "model_name": modelnaam, "web_search": True})
    if not t:
        return vraag, model, None, 0
    tekst, bronnen = "", []
    for item in ((t["result"] or [{}])[0].get("items") or []):
        if item.get("type") != "message":
            continue
        for sectie in item.get("sections") or []:
            tekst += sectie.get("text") or ""
            for a in sectie.get("annotations") or []:
                # Gemini geeft een doorstuurlink; de echte bron staat dan in direct_url of title
                d = domein_van(a.get("direct_url")) or domein_van(a.get("url"))
                if d.endswith("vertexaisearch.cloud.google.com"):
                    d = (a.get("title") or "").lower().removeprefix("www.")
                if d and d not in bronnen:
                    bronnen.append(d)
    m = NAAM.search(tekst)
    uitslag = {
        "genoemd": bool(m),
        "gelinkt": any(b.endswith(DOMEIN) for b in bronnen),
        "bronnen": bronnen[:15],
        "fragment": " ".join(tekst[max(0, m.start() - 160):m.end() + 160].split()) if m else "",
    }
    return vraag, model, uitslag, t.get("cost", 0)


def ai_meten():
    taken = [(v, m, spec) for v in INSTELLINGEN["ai_vragen"] for m, spec in INSTELLINGEN["ai_modellen"].items()]
    antwoorden, kosten = collections.defaultdict(dict), 0
    with concurrent.futures.ThreadPoolExecutor(6) as pool:
        for vraag, model, uitslag, prijs in pool.map(ai_vraag, taken):
            kosten += prijs
            if uitslag:
                antwoorden[vraag][model] = uitslag
    n = sum(len(v) for v in antwoorden.values())
    zichtbaar = sum(1 for v in antwoorden.values() for u in v.values() if u["genoemd"] or u["gelinkt"])
    print("AI: %d van %d antwoorden, NijmegenOnline in %d ($%.2f)" % (n, len(taken), zichtbaar, kosten))
    return {"datum": VANDAAG.isoformat(), "antwoorden": antwoorden, "kosten": round(kosten, 3)}


# ---------- Search Console ----------

def gsc_meten():
    info = os.environ.get("GSC_SERVICE_ACCOUNT_JSON") or os.environ.get("GA_SERVICE_ACCOUNT_JSON")
    if not info:
        print("Search Console overgeslagen: GSC_SERVICE_ACCOUNT_JSON ontbreekt")
        return None
    from google.auth.transport.requests import Request
    from google.oauth2 import service_account
    cred = service_account.Credentials.from_service_account_info(
        json.loads(info), scopes=["https://www.googleapis.com/auth/webmasters.readonly"])
    cred.refresh(Request())
    url = "https://www.googleapis.com/webmasters/v3/sites/%s/searchAnalytics/query" % urllib.parse.quote(
        INSTELLINGEN["search_console_property"], safe="")

    def vraag(start, eind, dimensie, rijen=25000):
        r = requests.post(url, headers={"Authorization": "Bearer " + cred.token}, timeout=120, json={
            "startDate": start.isoformat(), "endDate": eind.isoformat(), "dimensions": [dimensie], "rowLimit": rijen})
        r.raise_for_status()
        return r.json().get("rows", [])

    eind = VANDAAG - datetime.timedelta(days=3)  # Search Console loopt een paar dagen achter
    weken = collections.OrderedDict()
    for rij in vraag(VANDAAG - datetime.timedelta(days=486), eind, "date"):
        dag = datetime.date.fromisoformat(rij["keys"][0])
        maandag = (dag - datetime.timedelta(days=dag.weekday())).isoformat()
        w = weken.setdefault(maandag, {"week": maandag, "klikken": 0, "vertoningen": 0, "_pos": 0.0, "dagen": 0})
        w["klikken"] += rij["clicks"]
        w["vertoningen"] += rij["impressions"]
        w["_pos"] += rij["position"] * rij["impressions"]
        w["dagen"] += 1
    for w in weken.values():
        w["positie"] = round(w.pop("_pos") / w["vertoningen"], 1) if w["vertoningen"] else None

    def top(dimensie):
        nu = {r["keys"][0]: r for r in vraag(eind - datetime.timedelta(days=27), eind, dimensie, 1000)}
        eerder = {r["keys"][0]: r for r in vraag(eind - datetime.timedelta(days=55), eind - datetime.timedelta(days=28), dimensie, 1000)}
        uit = []
        for sleutelwoord, r in sorted(nu.items(), key=lambda x: -x[1]["clicks"])[:30]:
            oud = eerder.get(sleutelwoord)
            naam = urllib.parse.urlsplit(sleutelwoord).path if dimensie == "page" else sleutelwoord
            uit.append({"naam": naam, "klikken": r["clicks"], "vertoningen": r["impressions"],
                        "positie": round(r["position"], 1), "klikken_eerder": oud["clicks"] if oud else 0})
        return uit

    gsc = {"bijgewerkt": VANDAAG.isoformat(), "tot": eind.isoformat(), "weken": list(weken.values()),
           "zoekwoorden": top("query"), "paginas": top("page")}
    print("Search Console: %d weken, laatste dag met gegevens %s" % (len(weken), max((w["week"] for w in weken.values()), default="-")))
    return gsc


def main():
    wachtwoord = os.environ.get("STATISTIEK_WACHTWOORD")
    if not wachtwoord:
        sys.exit("STATISTIEK_WACHTWOORD ontbreekt")
    alleen = set(sys.argv[sys.argv.index("--alleen") + 1].split(",")) if "--alleen" in sys.argv else {"gsc", "zoekwoorden", "ai"}
    gegevens = openen(wachtwoord)

    if "gsc" in alleen:
        try:
            gsc = gsc_meten()
            if gsc:
                gegevens["gsc"] = gsc
        except Exception as e:  # een Google-storing mag de rest van de meting niet tegenhouden
            print("Search Console mislukt: %s" % e, file=sys.stderr)

    if "zoekwoorden" in alleen:
        meting = zoekwoorden_meten()
        if meting["posities"]:
            gegevens["zoekwoorden"] = [m for m in gegevens["zoekwoorden"] if m["datum"] != meting["datum"]] + [meting]

    if "ai" in alleen:
        vorige = max((m["datum"] for m in gegevens["ai"]), default=None)
        dagen = (VANDAAG - datetime.date.fromisoformat(vorige)).days if vorige else None
        if "--ai-forceren" in sys.argv or dagen is None or dagen >= INSTELLINGEN["ai_elke_dagen"]:
            meting = ai_meten()
            if meting["antwoorden"]:
                gegevens["ai"] = [m for m in gegevens["ai"] if m["datum"] != meting["datum"]] + [meting]
        else:
            print("AI-meting overgeslagen: vorige was %d dagen geleden" % dagen)

    gegevens["bijgewerkt"] = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="minutes")
    opslaan(gegevens, wachtwoord)
    print("Opgeslagen in %s" % BESTAND.relative_to(ROOT))


if __name__ == "__main__":
    main()
