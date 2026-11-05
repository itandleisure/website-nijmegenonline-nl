"""Meldt nieuwe en gewijzigde pagina's bij IndexNow (Bing, Yandex, Seznam, Naver en andere deelnemers delen de meldingen).

Bing Webmaster Tools gaf de fout "Some important pages weren't submitted via IndexNow". Dit script:
- vergelijkt de huidige commit met de tag `indexnow-gemeld` (de laatst gemelde stand);
- meldt elke pagina uit sitemap.xml waarvan de index.html sindsdien is toegevoegd of gewijzigd, plus verwijderde pagina's;
- zonder tag (eerste keer) meldt het alle pagina's uit sitemap.xml;
- verplaatst daarna de tag naar de gemelde commit (dat doet de workflow, zie .github/workflows/indexnow.yml).

De sleutel staat in <sleutel>.txt in de hoofdmap; IndexNow controleert dat bestand op www.nijmegenonline.nl.
Per verzoek mogen maximaal 10.000 URL's mee.

Gebruik: python tools/indexnow.py [--commit SHA] [--droog]
"""
import json
import pathlib
import re
import subprocess
import sys
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
SITE = "https://www.nijmegenonline.nl"
HOST = "www.nijmegenonline.nl"
TAG = "indexnow-gemeld"
ENDPOINT = "https://api.indexnow.org/indexnow"
PER_VERZOEK = 10000


def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, check=True, capture_output=True, text=True).stdout


def sleutel():
    for pad in ROOT.glob("*.txt"):
        if re.fullmatch(r"[0-9a-f]{32}", pad.stem) and pad.read_text().strip() == pad.stem:
            return pad.stem
    sys.exit("Geen IndexNow-sleutelbestand (<32 hex-tekens>.txt) in de hoofdmap gevonden.")


def sitemap_urls(commit):
    return set(re.findall(r"<loc>([^<]+)</loc>", git("show", "%s:sitemap.xml" % commit)))


def url_van(pad):
    map_ = pad[: -len("index.html")].rstrip("/")
    return SITE + ("/%s/" % map_ if map_ else "/")


def te_melden(commit):
    urls = sitemap_urls(commit)
    try:
        vorige = git("rev-parse", "--verify", "--quiet", TAG + "^{commit}").strip()
    except subprocess.CalledProcessError:
        vorige = ""
    if not vorige:
        print("Nog niets gemeld: alle %d pagina's uit sitemap.xml." % len(urls))
        return sorted(urls)
    if subprocess.run(["git", "merge-base", "--is-ancestor", commit, vorige], cwd=ROOT).returncode == 0:
        print("Commit %s is al gemeld." % commit[:10])
        return []
    gemeld = set()
    for regel in git("diff", "--name-status", "--no-renames", vorige, commit, "--", "*index.html").splitlines():
        status, pad = regel.split("\t", 1)
        if not pad.endswith("index.html") or pad.startswith(("pagefind/", "statistiek/", "partials/", ".")):
            continue
        url = url_van(pad)
        if status == "D" or url in urls:
            gemeld.add(url)
    print("Sinds %s: %d gewijzigde pagina's." % (vorige[:10], len(gemeld)))
    return sorted(gemeld)


def melden(urls, key):
    for i in range(0, len(urls), PER_VERZOEK):
        deel = urls[i : i + PER_VERZOEK]
        data = json.dumps({"host": HOST, "key": key, "keyLocation": "%s/%s.txt" % (SITE, key), "urlList": deel}).encode()
        verzoek = urllib.request.Request(ENDPOINT, data=data, headers={"Content-Type": "application/json; charset=utf-8"})
        try:
            with urllib.request.urlopen(verzoek, timeout=60) as antwoord:
                print("IndexNow: %d URL's gemeld (HTTP %d)." % (len(deel), antwoord.status))
        except urllib.error.HTTPError as fout:
            # 400 ongeldig verzoek, 403 sleutel klopt niet, 422 URL's horen niet bij de host, 429 te vaak
            sys.exit("IndexNow weigerde de melding: HTTP %d %s" % (fout.code, fout.read().decode(errors="replace")[:300]))


def main():
    args = sys.argv[1:]
    commit = git("rev-parse", args[args.index("--commit") + 1] if "--commit" in args else "HEAD").strip()
    urls = te_melden(commit)
    for url in urls[:20]:
        print("  " + url)
    if len(urls) > 20:
        print("  … en nog %d" % (len(urls) - 20))
    if urls and "--droog" not in args:
        melden(urls, sleutel())


if __name__ == "__main__":
    main()
