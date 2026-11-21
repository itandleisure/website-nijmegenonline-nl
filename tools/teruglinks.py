"""Houdt bij welke bedrijven uit de bedrijvengids op hun eigen website naar NijmegenOnline linken.

Haalt van elk bedrijf met een website de homepage op (daar staat een badge meestal, in de footer) en zoekt naar een
link naar nijmegenonline.nl. Schrijft data/bedrijvengids-teruglinks.json: per bedrijf (slug) of er een link is, of
het de badge is, of de link nofollow heeft, en wanneer we de link voor het eerst en het laatst zagen. Een link die
verdwijnt, houdt zijn "eerst_gezien" niet: dan staat "link" op false en "weg_sinds" op de datum.

Draait elke maandag via .github/workflows/teruglinks.yml. Overzicht als CSV: python tools/teruglinks.py --csv uit.csv
"""
import concurrent.futures
import csv
import datetime
import json
import pathlib
import re
import sys
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
UIT = ROOT / "data" / "bedrijvengids-teruglinks.json"
AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
LINK = re.compile(r"<a\b[^>]*href=[\"']?(https?:)?//(www\.)?nijmegenonline\.nl[^\"'\s>]*[^>]*>(.*?)</a>", re.I | re.S)


def ophalen(url):
    verzoek = urllib.request.Request(url, headers={"User-Agent": AGENT, "Accept-Language": "nl,en;q=0.8"})
    with urllib.request.urlopen(verzoek, timeout=20) as r:
        return r.read(3_000_000).decode("utf-8", "replace")


def controleer(slug, site):
    try:
        html = ophalen(site)
    except Exception as e:  # noqa: BLE001 - elke fout telt als "niet bereikbaar"
        return slug, {"bereikbaar": False, "fout": type(e).__name__}
    links = list(LINK.finditer(html))
    if not links:
        return slug, {"bereikbaar": True, "link": False}
    tag = links[0].group(0)
    return slug, {"bereikbaar": True, "link": True,
                  "badge": any("assets/img/badge/" in m.group(0) for m in links),
                  "nofollow": all(re.search(r"rel=[\"'][^\"']*(nofollow|sponsored|ugc)", m.group(0), re.I) for m in links),
                  "naar": re.search(r"href=[\"']?([^\"'\s>]+)", tag).group(1)}


def main():
    vandaag = datetime.date.today().isoformat()
    vermeldingen = json.loads((ROOT / "data" / "bedrijvengids-vermeldingen.json").read_text(encoding="utf-8"))
    oud = json.loads(UIT.read_text(encoding="utf-8")) if UIT.exists() else {}
    taken = {s: v["site"] for s, v in vermeldingen.items() if not s.startswith("_") and v.get("site")}
    uit = {"_uitleg": oud.get("_uitleg") or (
        "Welke bedrijven uit de bedrijvengids op hun homepage naar nijmegenonline.nl linken (tools/teruglinks.py, "
        "elke maandag). badge: de link is onze badge; nofollow: alle links hebben rel=nofollow/sponsored/ugc.")}
    with concurrent.futures.ThreadPoolExecutor(24) as pool:
        for slug, r in pool.map(lambda kv: controleer(*kv), taken.items()):
            vorig = oud.get(slug, {})
            r["site"] = taken[slug]
            r["gecontroleerd"] = vandaag
            if r.get("link"):
                r["eerst_gezien"] = vorig.get("eerst_gezien") if vorig.get("link") else vandaag
            elif not r["bereikbaar"] and vorig.get("link"):
                r = dict(vorig, gecontroleerd=vandaag, bereikbaar=False)  # site even plat: link niet meteen weg
            elif vorig.get("link"):
                r["weg_sinds"] = vandaag
            uit[slug] = r
    UIT.write_text(json.dumps(uit, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    rijen = [v for k, v in uit.items() if not k.startswith("_")]
    print("%d websites, %d bereikbaar, %d linken naar ons (%d met badge)" % (
        len(rijen), sum(1 for v in rijen if v.get("bereikbaar")), sum(1 for v in rijen if v.get("link")),
        sum(1 for v in rijen if v.get("badge"))))


def naar_csv(pad):
    vermeldingen = json.loads((ROOT / "data" / "bedrijvengids-vermeldingen.json").read_text(encoding="utf-8"))
    uit = json.loads(UIT.read_text(encoding="utf-8"))
    with open(pad, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["bedrijf", "categorie", "linkt_naar_ons", "badge", "nofollow", "eerst_gezien", "weg_sinds",
                    "website", "pagina_in_gids"])
        for slug, r in sorted(uit.items()):
            if slug.startswith("_"):
                continue
            v = vermeldingen.get(slug, {})
            w.writerow([v.get("bedrijf", slug), v.get("categorie", ""),
                        "ja" if r.get("link") else ("onbekend" if not r.get("bereikbaar") else "nee"),
                        "ja" if r.get("badge") else "", "ja" if r.get("nofollow") else "",
                        r.get("eerst_gezien", ""), r.get("weg_sinds", ""), r.get("site", ""), v.get("url", "")])


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--csv":
        naar_csv(sys.argv[2])
    else:
        main()
