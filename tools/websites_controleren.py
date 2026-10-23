"""Controleert of de websites in de bedrijvengids nog werken.

Schrijft data/bedrijvengids-websites.json: per bedrijf de uitkomst. tools/bedrijvengids.py laat de link weg bij een
site die niet bestaat (domein onbekend, geen verbinding, 404/410) en gebruikt het adres waar een site naar doorstuurt.
Alleen een onbekend domein of een 404/410 telt als kapot. Een site die bots weert (403, 429, 5xx, verbroken of
trage verbinding) telt als werkend: die opent in een browser meestal wel. Een verdwenen subpagina (404) wordt de
homepage van dezelfde site, als die wel werkt.

Draait via .github/workflows/websites-controleren.yml (vanuit de sandbox van Claude is internet dicht).
"""
import concurrent.futures
import json
import pathlib
import re
import socket
import ssl
import time
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
UIT = ROOT / "data" / "bedrijvengids-websites.json"
AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"


def controleer(url):
    """Geeft (werkt, eind_url, reden)."""
    laatste = ""
    for poging in range(2):
        try:
            verzoek = urllib.request.Request(url, headers={"User-Agent": AGENT, "Accept-Language": "nl"})
            with urllib.request.urlopen(verzoek, timeout=20) as r:
                return True, r.geturl(), "%d" % r.status
        except urllib.error.HTTPError as fout:
            if fout.code in (404, 410):
                home = re.match(r"https?://[^/]+/", url + "/").group(0)
                if home.rstrip("/") != url.rstrip("/"):
                    werkt, eind, reden = controleer(home)
                    if werkt:
                        return True, eind, "subpagina weg (%d), homepage werkt" % fout.code
                return False, url, "pagina bestaat niet (%d)" % fout.code
            return True, url, "%d (weert mogelijk bots)" % fout.code
        except urllib.error.URLError as fout:
            reden = fout.reason
            if isinstance(reden, socket.gaierror):
                return False, url, "domein bestaat niet"
            if isinstance(reden, ssl.SSLError) and url.startswith("https://"):
                laatste = "certificaat klopt niet"
                url = "http://" + url[8:]
                continue
            laatste = str(reden)[:100]
        except (socket.timeout, TimeoutError, ConnectionError, OSError) as fout:
            laatste = str(fout)[:100] or "geen antwoord"
        time.sleep(3)
    # Geen antwoord of verbinding verbroken: vaak een site die bots weert; de link laten staan
    return True, url, "twijfel: " + (laatste or "geen antwoord")


def main():
    gids = json.loads((ROOT / "data" / "bedrijvengids.json").read_text(encoding="utf-8"))
    bedrijven = [b for cat in gids.values() for b in cat["gids"] + cat["overig"] if b.get("website")]
    uit = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        for b, (werkt, eind, reden) in zip(bedrijven, pool.map(lambda b: controleer(b["website"].strip()), bedrijven)):
            uit[b["slug"]] = {"website": b["website"], "werkt": werkt, "eind_url": eind, "reden": reden,
                              "gecontroleerd": time.strftime("%Y-%m-%d")}
            if not werkt:
                print("%-40s %s  (%s)" % (b["slug"], b["website"], reden))
    kapot = sum(1 for x in uit.values() if not x["werkt"])
    if kapot > len(uit) / 3:
        # Zoveel kapotte sites tegelijk is eerder een storing bij ons dan bij de bedrijven: niets aanpassen
        raise SystemExit("%d van de %d sites werken niet; dat lijkt een netwerkstoring, niets opgeslagen" % (kapot, len(uit)))
    UIT.write_text(json.dumps(uit, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print("%d sites gecontroleerd, %d werken niet" % (len(uit), sum(1 for x in uit.values() if not x["werkt"])))


if __name__ == "__main__":
    main()
