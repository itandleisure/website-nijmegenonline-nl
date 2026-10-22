"""Zet de afbeeldingen van de WordPress-site om naar webp in assets/uploads/.

De pagina's verwijzen nog naar www.nijmegenonline.nl/wp-content/uploads/... Dit script zoekt die
verwijzingen op, leest het origineel uit de download (standaard /mnt/project-files/bron/assets/uploads)
en schrijft een verkleinde webp naar assets/uploads/<zelfde pad>.webp. tools/build.py laat de pagina's
daarna naar die lokale versie wijzen.

Gebruik: python tools/afbeeldingen.py [/pad/naar/uploads]
"""
import pathlib
import re
import sys
import urllib.parse

from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOEL = ROOT / "assets" / "uploads"
URL = re.compile(r'https?://(?:www\.)?nijmegenonline\.nl/wp-content/uploads/([^"\'\s)]+?\.(?:png|jpe?g|gif|webp))', re.I)
MAX_BREED = 1200


def doelpad(rel):
    return DOEL / (rel.rsplit(".", 1)[0] + ".webp")


def main(bron):
    bron = pathlib.Path(bron)
    gevonden = set()
    for page in ROOT.rglob("index.html"):
        if "node_modules" in page.parts:
            continue
        gevonden.update(URL.findall(page.read_text(encoding="utf-8")))
    nieuw = mist = 0
    for rel in sorted(gevonden):
        doel = doelpad(rel)
        if doel.exists():
            continue
        src = bron / urllib.parse.unquote(rel)
        if not src.exists():
            mist += 1
            print("mist:", rel)
            continue
        im = Image.open(src)
        im = im.convert("RGBA" if im.mode in ("RGBA", "LA", "P") else "RGB")
        if im.width > MAX_BREED:
            im = im.resize((MAX_BREED, round(im.height * MAX_BREED / im.width)), Image.LANCZOS)
        doel.parent.mkdir(parents=True, exist_ok=True)
        im.save(doel, "WEBP", quality=78, method=6)
        nieuw += 1
    totaal = sum(f.stat().st_size for f in DOEL.rglob("*.webp"))
    print("%d verwijzingen, %d nieuw omgezet, %d niet gevonden, assets/uploads samen %.1f MB"
          % (len(gevonden), nieuw, mist, totaal / 1e6))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "/mnt/project-files/bron/assets/uploads")
