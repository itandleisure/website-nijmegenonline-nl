"""Bouwt de zoekindex voor zoeken/ met Pagefind (https://pagefind.app) in de map pagefind/.

Draai dit na tools/build.py: build.py zet data-pagefind-body op de pagina's die mee moeten tellen.
Instellingen staan in pagefind.yml. Vereist: pip install "pagefind[bin]"

Gebruik: python tools/zoekindex.py
"""
import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

if __name__ == "__main__":
    # oude bestanden weg, anders blijven fragmenten van verdwenen pagina's in de repo staan
    shutil.rmtree(ROOT / "pagefind", ignore_errors=True)
    sys.exit(subprocess.call([sys.executable, "-m", "pagefind"], cwd=ROOT))
