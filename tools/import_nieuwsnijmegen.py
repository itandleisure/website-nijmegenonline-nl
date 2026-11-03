"""Zet het nieuwsarchief van nieuwsnijmegen.nl over naar /nieuwsoverzicht/<slug>/ (akkoord Frans 2-11-2026).

nieuwsnijmegen.nl (WordPress) had 7.269 berichten uit 2006 t/m januari 2024, elk op nieuwsnijmegen.nl/<slug>/. Ze
krijgen hier dezelfde slug, zodat één 301-regel op de oude server elk adres naar het juiste bericht stuurt
(zie docs/nieuwsnijmegen-htaccess.txt). Het oude subdomein nieuws.nijmegenonline.nl gebruikte dezelfde slugs.

Stappen:
1. Ophalen (--ophalen): alle berichten en uitgelichte foto's via de WordPress-API naar de bronmap
   (posts-<n>.json, media/m<n>.json). Alleen nodig zolang nieuwsnijmegen.nl nog op WordPress draait; de bronmap
   in de projectmap is daarna de back-up.
2. Foto's: alleen foto's die nog werken komen mee, als webp in assets/uploads/nieuwsnijmegen/. Het logo van
   nieuwsnijmegen.nl (uitgelicht bij ruim 6.000 berichten) en de foto's op nieuws.nijmegenonline.nl en
   www.nijmegenonline.nl/wp-content (al jaren een 404) vallen weg; die berichten krijgen de archieffoto.
3. Tekst opschonen met dezelfde regels als de WordPress-artikelen (import_wordpress.schoon). Links naar andere
   berichten op nieuwsnijmegen.nl of nieuws.nijmegenonline.nl wijzen naar het nieuwe adres; links naar oude
   adressen die niet meer bestaan worden gewone tekst.
4. Resultaat: data/nieuws-archief.json. tools/nieuws.py bouwt er pagina's van, naast data/nieuws.json (die de
   aanmeldingen en de nieuwsbrief gebruiken, en die dus klein blijft).

Berichten met een slug die al in data/nieuws.json of data/nieuws-verwijderd.json staat, slaat dit over: die
keuze is al gemaakt.

Gebruik: python tools/import_nieuwsnijmegen.py [--ophalen] [bronmap]
         (standaard /mnt/project-files/bron/nieuwsnijmegen)
"""
import concurrent.futures
import glob
import hashlib
import html
import io
import json
import pathlib
import re
import sys
import unicodedata
import urllib.parse
import urllib.request

from bs4 import BeautifulSoup
from PIL import Image

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import build  # noqa: E402
from import_wordpress import ROOT, SITE, schoon  # noqa: E402

OUD = "https://nieuwsnijmegen.nl"
OUDE_HOSTS = {"nieuwsnijmegen.nl", "www.nieuwsnijmegen.nl", "nieuws.nijmegenonline.nl"}
SITE_HOSTS = {"nijmegenonline.nl", "www.nijmegenonline.nl"}
UIT = ROOT / "data" / "nieuws-archief.json"
FOTOMAP = ROOT / "assets" / "uploads" / "nieuwsnijmegen"
# Uitgelichte "foto's" die geen foto zijn: het logo en het standaardplaatje van nieuwsnijmegen.nl
GEEN_FOTO = {5, 115790}
MAX_BREED = 1200
VELDEN = ("id,date,modified,slug,link,title,content,featured_media,"
          "yoast_head_json.title,yoast_head_json.description")


def haal(url, pogingen=3):
    for n in range(pogingen):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "NijmegenOnline-import"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except Exception:
            if n == pogingen - 1:
                raise


def ophalen(bron):
    bron.mkdir(parents=True, exist_ok=True)
    (bron / "media").mkdir(exist_ok=True)
    pagina, ids = 1, set()
    while True:
        try:
            data = haal("%s/wp-json/wp/v2/posts?per_page=100&page=%d&_fields=%s" % (OUD, pagina, VELDEN))
        except urllib.error.HTTPError as e:
            if e.code == 400:  # voorbij de laatste pagina
                break
            raise
        posts = json.loads(data)
        if not posts:
            break
        (bron / ("posts-%d.json" % pagina)).write_bytes(data)
        ids.update(p["featured_media"] for p in posts if p["featured_media"])
        pagina += 1
    ids = sorted(ids - GEEN_FOTO)
    for n in range(0, len(ids), 100):
        data = haal("%s/wp-json/wp/v2/media?per_page=100&include=%s&_fields=id,source_url,alt_text"
                    % (OUD, ",".join(map(str, ids[n:n + 100]))))
        (bron / "media" / ("m%d.json" % (n // 100 + 1))).write_bytes(data)
    print("%d pagina's berichten en %d foto-id's opgehaald naar %s" % (pagina - 1, len(ids), bron))


def lees(bron):
    posts = [p for f in sorted(glob.glob(str(bron / "posts-*.json"))) for p in json.load(open(f, encoding="utf-8"))]
    media = {m["id"]: m for f in glob.glob(str(bron / "media" / "*.json")) for m in json.load(open(f, encoding="utf-8"))}
    return posts, media


def oud_pad(url):
    """'slug' als url een bericht-adres op een van de oude nieuwsdomeinen is, anders None."""
    u = urllib.parse.urlparse(html.unescape(url.strip()))
    if u.netloc.lower() not in OUDE_HOSTS and not (u.netloc.lower() in SITE_HOSTS and u.path.startswith("/nieuws/")):
        return None
    delen = [d for d in u.path.split("/") if d]
    if u.netloc.lower().endswith("nijmegenonline.nl") and delen[:1] == ["nieuws"]:
        delen = delen[1:]  # nog ouder: www.nijmegenonline.nl/nieuws/<slug>/
    if len(delen) == 1 and not u.query:
        return urllib.parse.unquote(delen[0]).lower()
    if not delen and re.match(r"p=\d+$", u.query or ""):
        return "?" + u.query
    return ""


def fotobestand(url):
    """Lokaal pad (relatief aan ROOT) voor een foto van een oude site: assets/uploads/nieuwsnijmegen/<pad>.webp"""
    u = urllib.parse.urlparse(url)
    pad = urllib.parse.unquote(u.path)
    pad = pad.split("/wp-content/uploads/", 1)[1] if "/wp-content/uploads/" in pad else (
        "extern/%s-%s" % (hashlib.md5(url.encode()).hexdigest()[:10], pad.rsplit("/", 1)[-1]))
    pad = re.sub(r"[^\w./-]+", "-", pad)
    return "assets/uploads/nieuwsnijmegen/" + pad.rsplit(".", 1)[0] + ".webp"


def foto_omzetten(url, cache):
    """Download + webp. Geeft het lokale pad of None als de foto niet (meer) bestaat."""
    doel = ROOT / fotobestand(url)
    if doel.exists():
        return fotobestand(url)
    try:
        bestand = cache / re.sub(r"[^\w.-]+", "_", url.split("://", 1)[1])[-180:]
        if not bestand.exists():
            bestand.write_bytes(haal(url, 2))
        im = Image.open(io.BytesIO(bestand.read_bytes()))
        im = im.convert("RGBA" if im.mode in ("RGBA", "LA", "P") else "RGB")
    except Exception:
        return None
    if im.width < 60 or im.height < 60:  # pixels en knopjes
        return None
    if im.width > MAX_BREED:
        im = im.resize((MAX_BREED, round(im.height * MAX_BREED / im.width)), Image.LANCZOS)
    doel.parent.mkdir(parents=True, exist_ok=True)
    im.save(doel, "WEBP", quality=78, method=6)
    return fotobestand(url)


def groot(url):
    """WordPress-verkleining (-300x200) terug naar het origineel."""
    return re.sub(r"-\d+x\d+(\.\w+)$", r"\1", url)


def nieuwe_slug(slug):
    """Twee oude slugs hebben een ² of º (procent-gecodeerd); hier gewone letters, met een eigen 301-regel."""
    slug = unicodedata.normalize("NFKD", urllib.parse.unquote(slug)).encode("ascii", "ignore").decode()
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9_-]", "-", slug.lower())).strip("-")


def bestaat_op_site(url, kaart):
    """Bestaat een link naar www.nijmegenonline.nl hier (als pagina of als 301 in _redirects)?"""
    pad = urllib.parse.urlparse(url).path or "/"
    return build.bestaat(build.eindadres(pad, kaart)) or (pad.rstrip("/") + "/") in kaart


def bewerk_links(content, slugs, kaart):
    """Links en foto's in de ruwe WordPress-tekst, vóór het opschonen."""
    content = content.replace("<![CDATA[", "").replace("]]>", "")  # resten van een oude import (349 berichten)
    soup = BeautifulSoup(content, "html.parser")
    for a in soup.find_all("a", href=True):
        slug = oud_pad(a["href"])
        if slug is None:
            # oude pagina's van nijmegenonline.nl uit 2007-2012 (zp-foto, .php) bestaan al lang niet meer
            href = a["href"].strip()
            host = urllib.parse.urlparse(href).netloc.lower()
            if (host in SITE_HOSTS or (href.startswith("/") and not href.startswith("//"))) and not bestaat_op_site(href, kaart):
                a.unwrap()
            continue
        if slug in slugs:
            a["href"] = "%s/nieuwsoverzicht/%s/" % (SITE, slugs[slug])
        else:  # oud adres zonder bericht, of een klikbare foto naar het origineel op de oude site
            a.unwrap()
    return str(soup)


def main(args):
    bron = pathlib.Path(next((a for a in args if not a.startswith("--")), "/mnt/project-files/bron/nieuwsnijmegen"))
    if "--ophalen" in args:
        ophalen(bron)
    posts, media = lees(bron)
    bestaand = {b["slug"] for b in json.load(open(ROOT / "data" / "nieuws.json", encoding="utf-8"))}
    verwijderd = ROOT / "data" / "nieuws-verwijderd.json"
    bestaand |= set(json.load(open(verwijderd, encoding="utf-8"))) if verwijderd.exists() else set()
    posts = [p for p in posts if p["slug"] not in bestaand]
    # oude slug (gedecodeerd, kleine letters) -> nieuwe slug
    slugs = {urllib.parse.unquote(p["slug"]).lower(): nieuwe_slug(p["slug"]) for p in posts}

    # Alle foto's: uitgelicht + in de tekst. Eén keer downloaden, parallel.
    kaart = build.doorverwijzingen()
    teksten = {p["id"]: bewerk_links(p["content"]["rendered"], slugs, kaart) for p in posts}
    urls = set()
    for t in teksten.values():
        urls.update(groot(html.unescape(u)) for u in re.findall(r'<img[^>]+?src="(https?://[^"]+)"', t))
    for p in posts:
        m = media.get(p["featured_media"])
        if m and p["featured_media"] not in GEEN_FOTO:
            urls.add(m["source_url"])
    cache = bron / "uploads"
    cache.mkdir(exist_ok=True)
    with concurrent.futures.ThreadPoolExecutor(12) as pool:
        lokaal = dict(zip(sorted(urls), pool.map(lambda u: foto_omzetten(u, cache), sorted(urls))))
    werkt = sum(1 for v in lokaal.values() if v)
    print("%d foto's gevonden, %d werken nog en staan nu als webp in %s" % (len(urls), werkt, FOTOMAP.relative_to(ROOT)))

    def img(m):
        tag = m.group(0)
        src = re.search(r'src="([^"]+)"', tag)
        doel = lokaal.get(groot(html.unescape(src.group(1)))) if src else None
        if not doel:
            return ""
        tag = re.sub(r'\s(?:srcset|sizes|class|style|width|height)="[^"]*"', "", tag)
        return tag.replace(src.group(0), 'src="%s/%s"' % (SITE, doel))

    berichten = []
    for p in posts:
        titel = html.unescape(p["title"]["rendered"]).strip()
        tekst = re.sub(r"<img\b[^>]*>", img, teksten[p["id"]])
        tekst = schoon(tekst, set(), "../../", False, titel).strip()
        tekst = re.sub(r'src="%s/(assets/uploads/nieuwsnijmegen/[^"]+)"' % re.escape(SITE), r'src="../../\1"', tekst)
        m = media.get(p["featured_media"])
        foto = lokaal.get(m["source_url"]) if m and p["featured_media"] not in GEEN_FOTO else None
        if not foto:  # dan de eerste foto uit de tekst
            eerste = re.search(r'src="\.\./\.\./(assets/uploads/nieuwsnijmegen/[^"]+)"', tekst)
            foto = eerste.group(1) if eerste else None
        yoast = p.get("yoast_head_json") or {}
        seo = re.sub(r"\s+[-–|]\s+Nieuws Nijmegen$", "", html.unescape(yoast.get("title") or "")).strip()
        berichten.append({
            "slug": nieuwe_slug(p["slug"]),
            "titel": titel,
            "seo_titel": seo or titel,
            "beschrijving": html.unescape(yoast.get("description") or "").strip(),
            "datum": p["date"],
            "gewijzigd": p["modified"],
            "foto": "%s/%s" % (SITE, foto) if foto else "",
            "tekst": tekst,
            "bron": "nieuwsnijmegen.nl",
        })
        if berichten[-1]["slug"] != p["slug"]:
            berichten[-1]["oude_slug"] = urllib.parse.unquote(p["slug"])
    berichten.sort(key=lambda b: (b["datum"], b["slug"]), reverse=True)
    UIT.write_text("[\n" + ",\n".join(json.dumps(b, ensure_ascii=False) for b in berichten) + "\n]\n", encoding="utf-8")
    print("%d berichten van nieuwsnijmegen.nl naar %s (%d met eigen foto), %d overgeslagen (al op de site)"
          % (len(berichten), UIT.relative_to(ROOT), sum(1 for b in berichten if b["foto"]), len(bestaand & {p["slug"] for p in lees(bron)[0]})))


if __name__ == "__main__":
    main(sys.argv[1:])
