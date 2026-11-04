"""Maakt per betalende klant een rapport met weergaven en kliks, voor de mail aan de klant.

Bron: Google Analytics 4 (property 337370292). De site stuurt al per bedrijfspagina de gebeurtenissen
  bedrijf_bekeken            bij elke weergave van /bedrijvengids/<slug>/      (assets/js/bedrijf.js)
  bedrijf_klik  soort=...    bij een klik op website, telefoon, route, google of de actieknop
  partner_vertoning/_klik    voor banners in de partnerbalk, met partner=<id>  (partners/slider.js)
  bedrijf_in_lijst           als een uitgelichte kaart in een lijst in beeld komt, met bedrijf=<slug> (partials/footer.html)

Weergaven en het totaal aan kliks halen we op via het paginapad, dat werkt altijd. Voor kliks per soort en
voor de banners en de vertoningen in lijsten moeten in Analytics de aangepaste dimensies "soort", "partner" en "bedrijf" bestaan (Beheer →
Aangepaste definities → Aangepaste dimensie maken, bereik Gebeurtenis, parameter soort / partner / bedrijf).
Analytics vult die pas vanaf het moment van aanmaken. Ontbreken ze, dan laat het rapport die regels weg.

Toegang: het serviceaccount uit GA_SERVICE_ACCOUNT_JSON (of GSC_SERVICE_ACCOUNT_JSON, hetzelfde account als
voor de statistiekpagina) moet in Analytics de rol Lezer hebben op de property.

Gebruik:
  python tools/klantrapport.py --bedrijf harbor-gym                 rapport over de afgelopen 12 maanden
  python tools/klantrapport.py --alle                               alle bedrijven uit data/bedrijvengids-pakketten.json
  python tools/klantrapport.py --bedrijf harbor-gym --partner haantje --van 2026-01-01 --tot 2026-03-31
  python tools/klantrapport.py --bedrijf harbor-gym --voorbeeld     opmaak bekijken met verzonnen cijfers, zonder Analytics
De rapporten komen als HTML (geschikt voor e-mail) in rapporten/<slug>.html; die map staat niet in git.
"""
import argparse
import base64
import datetime
import html
import json
import os
import pathlib
import random
import sys

import requests

ROOT = pathlib.Path(__file__).resolve().parent.parent
PROPERTY = os.environ.get("GA4_PROPERTY_ID", "337370292")
API = "https://analyticsdata.googleapis.com/v1beta/properties/%s:runReport" % PROPERTY
SOORTEN = [("website", "Kliks naar je website"), ("telefoon", "Kliks op je telefoonnummer"),
           ("route", "Routes gepland"), ("google", "Kliks naar je Google-profiel"),
           ("actieknop", "Kliks op je actieknop")]
MAANDEN = ["januari", "februari", "maart", "april", "mei", "juni", "juli", "augustus", "september",
           "oktober", "november", "december"]


class GeenDimensie(Exception):
    pass


def token():
    info = os.environ.get("GA_SERVICE_ACCOUNT_JSON") or os.environ.get("GSC_SERVICE_ACCOUNT_JSON")
    if not info:
        sys.exit("GA_SERVICE_ACCOUNT_JSON (of GSC_SERVICE_ACCOUNT_JSON) ontbreekt. Gebruik --voorbeeld om de opmaak te zien.")
    if "{" not in info:
        info = base64.b64decode(info.strip()).decode()
    from google.auth.transport.requests import Request
    from google.oauth2 import service_account
    cred = service_account.Credentials.from_service_account_info(
        json.loads(info[info.find("{"):info.rfind("}") + 1]),
        scopes=["https://www.googleapis.com/auth/analytics.readonly"])
    cred.refresh(Request())
    return cred.token


def vraag(tok, van, tot, dimensies, filters, metriek="eventCount"):
    """Eén runReport; filters = {dimensie: [waarden]}. Geeft {(dimensiewaarden...): aantal}."""
    expr = [{"filter": {"fieldName": d, "inListFilter": {"values": w}}} for d, w in filters.items()]
    body = {"dateRanges": [{"startDate": van.isoformat(), "endDate": tot.isoformat()}],
            "dimensions": [{"name": d} for d in dimensies], "metrics": [{"name": metriek}],
            "dimensionFilter": {"andGroup": {"expressions": expr}}, "limit": 10000}
    r = requests.post(API, headers={"Authorization": "Bearer " + tok}, json=body, timeout=120)
    if r.status_code == 400 and "customEvent:" in r.text:
        raise GeenDimensie(r.json().get("error", {}).get("message", r.text))
    r.raise_for_status()
    return {tuple(v["value"] for v in rij["dimensionValues"]): int(rij["metricValues"][0]["value"])
            for rij in r.json().get("rows", [])}


def cijfers(tok, slug, partner, van, tot):
    pad = "/bedrijvengids/%s/" % slug
    uit = {"weergaven": 0, "bezoekers": 0, "lijst": None, "kliks": 0, "soorten": None, "banner": None}
    basis = vraag(tok, van, tot, ["eventName"], {"pagePath": [pad], "eventName": ["bedrijf_bekeken", "bedrijf_klik", "page_view"]})
    # bedrijf_bekeken is de eigen teller; page_view als vangnet voor de periode voordat bedrijf.js er stond
    uit["weergaven"] = basis.get(("bedrijf_bekeken",), 0) or basis.get(("page_view",), 0)
    uit["kliks"] = basis.get(("bedrijf_klik",), 0)
    # unieke bezoekers van de bedrijfspagina (totalUsers over de hele periode, niet opgeteld per dag)
    uit["bezoekers"] = vraag(tok, van, tot, ["pagePath"], {"pagePath": [pad]}, "totalUsers").get((pad,), 0)
    try:
        lijst = vraag(tok, van, tot, ["eventName"], {"customEvent:bedrijf": [slug], "eventName": ["bedrijf_in_lijst"]})
        uit["lijst"] = lijst.get(("bedrijf_in_lijst",), 0)
    except GeenDimensie as e:
        print("  vertoningen in lijsten overgeslagen: %s" % e, file=sys.stderr)
    try:
        per = vraag(tok, van, tot, ["customEvent:soort"], {"pagePath": [pad], "eventName": ["bedrijf_klik"]})
        uit["soorten"] = {k[0]: n for k, n in per.items()}
    except GeenDimensie as e:
        print("  kliks per soort overgeslagen: %s" % e, file=sys.stderr)
    if partner:
        try:
            b = vraag(tok, van, tot, ["eventName"], {"customEvent:partner": [partner],
                                                       "eventName": ["partner_vertoning", "partner_klik"]})
            uit["banner"] = {"vertoningen": b.get(("partner_vertoning",), 0), "kliks": b.get(("partner_klik",), 0)}
        except GeenDimensie as e:
            print("  banner overgeslagen: %s" % e, file=sys.stderr)
    return uit


def voorbeeldcijfers(slug, partner):
    r = random.Random(slug)
    w = r.randint(600, 2400)
    soorten = {"website": int(w * r.uniform(.08, .14)), "telefoon": int(w * r.uniform(.02, .05)),
               "route": int(w * r.uniform(.03, .07)), "google": int(w * r.uniform(.01, .03))}
    return {"weergaven": w, "bezoekers": int(w * r.uniform(.6, .8)), "lijst": w * r.randint(4, 9),
            "kliks": sum(soorten.values()), "soorten": soorten,
            "banner": {"vertoningen": r.randint(20000, 60000), "kliks": r.randint(80, 300)} if partner else None}


def bedrijfsinfo(slug):
    gids = json.loads((ROOT / "data" / "bedrijvengids.json").read_text())
    for cat in gids.values():
        for b in cat.get("gids", []):
            if b.get("slug") == slug:
                return b
    sys.exit("Onbekend bedrijf: %s (zie data/bedrijvengids.json)" % slug)


def datum(d):
    return "%d %s %d" % (d.day, MAANDEN[d.month - 1], d.year)


def verschil(nu, toen):
    if toen is None:
        return ""
    if not toen:
        return '<span style="color:#6b7280">nieuw</span>' if nu else ""
    p = round((nu - toen) / toen * 100)
    kleur = "#15803d" if p >= 0 else "#b45309"
    return '<span style="color:%s">%s%d%% t.o.v. vorige periode</span>' % (kleur, "+" if p >= 0 else "", p)


def rij(label, nu, toen):
    return ('<tr><td style="padding:10px 0;border-bottom:1px solid #e5e7eb">%s<br><small>%s</small></td>'
            '<td style="padding:10px 0;border-bottom:1px solid #e5e7eb;text-align:right;font-size:22px;font-weight:700">%s</td></tr>'
            % (html.escape(label), verschil(nu, toen), "{:,}".format(nu).replace(",", ".")))


LEGENDA = [
    ("lijst", "In beeld in onze lijsten", "Hoe vaak je bedrijf zichtbaar was in een categorie van de bedrijvengids, "
     "bijvoorbeeld bij Restaurants. We tellen pas als je kaart echt op het scherm stond, en één keer per bezoek aan die pagina."),
    ("weergaven", "Weergaven van je pagina", "Hoe vaak je eigen pagina in de bedrijvengids is geopend. Opent iemand hem twee keer, "
     "dan telt dat twee keer."),
    ("bezoekers", "Unieke bezoekers", "Hoeveel verschillende mensen je pagina hebben bekeken. Iemand die vaker terugkomt, telt één keer "
     "(per apparaat en browser)."),
    ("kliks", "Kliks", "Hoe vaak een bezoeker op je pagina doorklikte: naar je website, op je telefoonnummer, voor een route of naar "
     "je Google-profiel. Een klik op je telefoonnummer betekent dat iemand op bellen drukte; of het gesprek tot stand kwam, zien we niet."),
    ("banner", "Banner", "Vertoningen: hoe vaak je banner in beeld kwam op onze site. Kliks: hoe vaak erop geklikt werd."),
    ("verschil", "t.o.v. vorige periode", "Het verschil met de even lange periode daarvoor."),
]


def legenda(nu):
    """Korte uitleg onder de cijfers, alleen voor de regels die in het rapport staan."""
    toon = {"weergaven", "bezoekers", "kliks", "verschil"} | ({"lijst"} if nu["lijst"] is not None else set()) | (
        {"banner"} if nu["banner"] else set())
    items = "".join('<p style="margin:0 0 6px"><b>%s:</b> %s</p>' % (html.escape(n), html.escape(u))
                    for k, n, u in LEGENDA if k in toon)
    return ('<div style="font-size:13px;color:#4b5563;margin-top:20px;padding:14px 16px;background:#f9fafb;border-radius:6px">'
            '<p style="margin:0 0 8px;font-weight:700;color:#111827">Wat betekenen deze cijfers?</p>%s'
            '<p style="margin:8px 0 0">Alle cijfers komen uit Google Analytics en zijn gemeten, niet geschat. Bezoekers met een '
            'adblocker tellen niet mee, dus de werkelijke aantallen liggen iets hoger.</p></div>' % items)


def rapport(b, pakket, nu, toen, van, tot, voorbeeld):
    regels = []
    if nu["lijst"] is not None:
        regels.append(rij("In beeld in onze lijsten", nu["lijst"], toen and toen["lijst"]))
    regels += [rij("Weergaven van je pagina", nu["weergaven"], toen and toen["weergaven"]),
               rij("Unieke bezoekers van je pagina", nu["bezoekers"], toen and toen["bezoekers"]),
               rij("Kliks op je pagina, totaal", nu["kliks"], toen and toen["kliks"])]
    if nu["soorten"] is not None:
        for sleutel, label in SOORTEN:
            if nu["soorten"].get(sleutel):
                regels.append(rij(label, nu["soorten"][sleutel], toen and (toen["soorten"] or {}).get(sleutel, 0)))
    if nu["banner"]:
        regels.append(rij("Vertoningen van je banner", nu["banner"]["vertoningen"], toen and (toen["banner"] or {}).get("vertoningen")))
        regels.append(rij("Kliks op je banner", nu["banner"]["kliks"], toen and (toen["banner"] or {}).get("kliks")))
    melding = ('<p style="background:#fef3c7;padding:10px 12px;border-radius:6px"><b>Voorbeeld:</b> deze cijfers zijn verzonnen '
               'om de opmaak te laten zien.</p>') if voorbeeld else ""
    url = "https://www.nijmegenonline.nl/bedrijvengids/%s/" % b["slug"]
    return """<!doctype html>
<html lang="nl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Je cijfers op NijmegenOnline</title></head>
<body style="margin:0;background:#f3f4f6;font-family:Arial,Helvetica,sans-serif;color:#111827">
<div style="max-width:560px;margin:0 auto;background:#fff;padding:28px 28px 20px">
<p style="margin:0 0 4px;color:#b91c1c;font-weight:700">NijmegenOnline</p>
<h1 style="margin:0 0 6px;font-size:22px">Zo vaak ben je gevonden, %(naam)s</h1>
<p style="margin:0 0 18px;color:#4b5563">%(pakket)s · %(van)s t/m %(tot)s</p>
%(melding)s
<table style="width:100%%;border-collapse:collapse;font-size:15px">%(regels)s</table>
%(legenda)s
<p><a href="%(url)s" style="display:inline-block;background:#b91c1c;color:#fff;padding:10px 16px;border-radius:6px;text-decoration:none">Bekijk je pagina</a></p>
<p style="font-size:13px;color:#6b7280">Iets aanpassen aan je pagina, een nieuwe actie of foto's? Antwoord op deze mail.</p>
</div></body></html>
""" % {"naam": html.escape(b["naam"]), "pakket": html.escape(pakket.capitalize()), "van": datum(van), "tot": datum(tot),
       "melding": melding, "regels": "\n".join(regels), "url": url, "legenda": legenda(nu)}


def mailen(inhoud, onderwerp):
    """Stuurt het rapport naar de redactie. Het Apps Script (actie 'rapport') mailt alleen naar
    redactie@nijmegenonline.nl; een klantadres kan hier niet worden meegegeven."""
    sys.path.insert(0, str(ROOT / "tools"))
    from paginas import GOOGLE_FORM_URL
    r = requests.post(GOOGLE_FORM_URL, data={"actie": "rapport", "sleutel": os.environ["NIEUWS_SLEUTEL"],
                                             "onderwerp": onderwerp, "html": inhoud}, timeout=120)
    r.raise_for_status()
    antwoord = r.json()
    if not antwoord.get("ok"):
        raise RuntimeError("mailen mislukt: %s" % antwoord)


def main():
    a = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    a.add_argument("--bedrijf", action="append", default=[], help="slug uit /bedrijvengids/<slug>/")
    a.add_argument("--alle", action="store_true", help="alle bedrijven met een pakket")
    a.add_argument("--partner", help="id uit partners/partners.json voor de bannercijfers (standaard: de partner waarvan de id in de slug staat)")
    a.add_argument("--van", type=datetime.date.fromisoformat)
    a.add_argument("--tot", type=datetime.date.fromisoformat)
    a.add_argument("--voorbeeld", action="store_true", help="verzonnen cijfers, zonder Analytics")
    a.add_argument("--uit", default=str(ROOT / "rapporten"))
    a.add_argument("--mail", action="store_true",
                   help="mail elk rapport naar de redactie (redactie@nijmegenonline.nl) via het Apps Script; nooit naar de klant. Nodig: NIEUWS_SLEUTEL")
    args = a.parse_args()

    pakketten = json.loads((ROOT / "data" / "bedrijvengids-pakketten.json").read_text())
    slugs = args.bedrijf or ([s for s in pakketten if not s.startswith("_")] if args.alle else [])
    if not slugs:
        a.error("geef --bedrijf <slug> of --alle")
    tot = args.tot or datetime.date.today() - datetime.timedelta(days=1)
    van = args.van or tot - datetime.timedelta(days=364)
    lengte = (tot - van).days + 1
    vorig_tot, vorig_van = van - datetime.timedelta(days=1), van - datetime.timedelta(days=lengte)
    tok = None if args.voorbeeld else token()
    map_ = pathlib.Path(args.uit)
    map_.mkdir(parents=True, exist_ok=True)
    partners = json.loads((ROOT / "partners" / "partners.json").read_text())["partners"]
    for slug in slugs:
        b = bedrijfsinfo(slug)
        # banner: --partner, anders de partner waarvan de id in de slug staat (de-bruijn → de-bruijn-lunchen-op-de-markt)
        partner = args.partner or next((p["id"] for p in partners if p["id"] in slug), None)
        pakket = (pakketten.get(slug) or {}).get("pakket", "gratis")
        if args.voorbeeld:
            nu = voorbeeldcijfers(slug, partner)
            f = random.Random(slug + "-vorig").uniform(.75, .95)
            toen = {"weergaven": int(nu["weergaven"] * f), "bezoekers": int(nu["bezoekers"] * f), "lijst": int(nu["lijst"] * f),
                    "kliks": int(nu["kliks"] * f),
                    "soorten": {k: int(v * f) for k, v in nu["soorten"].items()},
                    "banner": {k: int(v * f) for k, v in nu["banner"].items()} if nu["banner"] else None}
        else:
            nu = cijfers(tok, slug, partner, van, tot)
            toen = cijfers(tok, slug, partner, vorig_van, vorig_tot)
        pad = map_ / ("%s.html" % slug)
        pad.write_text(rapport(b, pakket, nu, toen, van, tot, args.voorbeeld))
        print("%s: %d weergaven, %d kliks → %s" % (slug, nu["weergaven"], nu["kliks"], pad))
        if args.mail:
            mailen(pad.read_text(), "Klantrapport %s (%s t/m %s)%s" % (b["naam"], van.isoformat(), tot.isoformat(),
                                                                       " [VOORBEELD]" if args.voorbeeld else ""))
            print("  gemaild naar de redactie")


if __name__ == "__main__":
    main()
