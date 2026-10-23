"""Datacheck voor de redactie (stap 5 van de standaard in de README): één lijst per categorie met alles waar Frans
over moet beslissen, en wat er automatisch is uitgefilterd en waarom.

Leest data/bedrijvengids.json, -scan.json, -websites.json en (als die er is) advies/osm-bedrijvengids/<categorie>-uitgefilterd.csv.
Schrijft docs/datacheck-<categorie>-<jaar-maand>.md en een volledige lijst als CSV in de projectbestanden.

Gebruik: python tools/datacheck.py restaurant [/mnt/project-files]
"""
import csv
import json
import pathlib
import re
import sys
import time
import unicodedata

ROOT = pathlib.Path(__file__).resolve().parent.parent


TWIJFEL = r"gesloten|gestopt|verhuisd|tijdelijk|twijfel|onzeker|niet zeker|onduidelijk|verouderd|andere vestiging|ander adres|wijkt af|klopt niet"


def plat(tekst):
    tekst = unicodedata.normalize("NFKD", tekst or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]", "", tekst)


def straat_nummer(adres):
    """'Lange Hezelstraat 59' -> ('langehezelstraat', '59'); het huisnummer zonder toevoeging."""
    m = re.match(r"^\s*(.*?)\s+(\d+)", adres or "")
    return (plat(m.group(1)), m.group(2)) if m else (plat(adres), "")


def adres_wijkt_af(b, op_site):
    if not op_site or not b["adres"]:
        return False
    straat, nr = straat_nummer(b["adres"])
    site = plat(op_site)
    return straat not in site or (nr and not re.search(r"(?<!\d)%s(?!\d)" % nr, op_site))


def tabel(koppen, rijen):
    if not rijen:
        return "_Geen._\n"
    uit = ["| " + " | ".join(koppen) + " |", "|" + "---|" * len(koppen)]
    uit += ["| " + " | ".join(str(c).replace("|", "/").replace("\n", " ") for c in r) + " |" for r in rijen]
    return "\n".join(uit) + "\n"


def main(categorie, bron):
    bron = pathlib.Path(bron)
    alle = json.loads((ROOT / "data" / "bedrijvengids.json").read_text(encoding="utf-8"))
    gids = alle[categorie]
    scan = json.loads((ROOT / "data" / "bedrijvengids-scan.json").read_text(encoding="utf-8"))
    sites = json.loads((ROOT / "data" / "bedrijvengids-websites.json").read_text(encoding="utf-8"))
    # Bedrijven die al bij een eerdere categorie staan (en daar niet uitgefilterd zijn) tellen hier niet mee
    elders = set()
    for cat in list(alle)[:list(alle).index(categorie)]:
        elders |= {b["slug"] for b in alle[cat]["gids"] + alle[cat]["overig"] if cat not in (scan.get(b["slug"], {}).get("niet_in") or {})}
    bedrijven = [b for b in gids["gids"] + gids["overig"] if b["slug"] not in elders]
    volledig = []   # (naam, adres, website, uitkomst, reden)

    vooraf = []
    pad = bron / "advies" / "osm-bedrijvengids" / ("%s-uitgefilterd.csv" % categorie)
    if pad.exists():
        vooraf = list(csv.DictReader(open(pad, encoding="utf-8")))
        volledig += [(x["naam"], x["adres"], x["website"], "niet verzameld", x["reden"]) for x in vooraf]

    dood, auto, ander, fout, nog, online, afwijkend, opmerkingen = [], [], [], [], [], [], [], []
    for b in sorted(bedrijven, key=lambda b: b["naam"].lower()):
        s = scan.get(b["slug"], {})
        w = sites.get(b["slug"], {})
        if w and not w.get("werkt") and w.get("website") == b.get("website"):
            dood.append((b["naam"], b["website"], w["reden"]))
            volledig.append((b["naam"], b["adres"], b["website"], "uit de gids", "website werkt niet: " + w["reden"]))
        elif s.get("status") == "verwijderd":
            auto.append((b["naam"], b["website"], s.get("reden", "")))
            volledig.append((b["naam"], b["adres"], b["website"], "uit de gids", s.get("reden", "")))
        elif categorie in (s.get("niet_in") or {}):
            ander.append((b["naam"], b["website"], s["niet_in"][categorie].replace("automatisch: ", "")))
            volledig.append((b["naam"], b["adres"], b["website"], "andere categorie", s["niet_in"][categorie]))
        elif s.get("status") == "fout":
            fout.append((b["naam"], b["website"], s.get("fout", "")[:120]))
            volledig.append((b["naam"], b["adres"], b["website"], "nog niet gescand", "fout bij het scannen"))
        elif not s:
            nog.append((b["naam"], b["website"], ""))
            volledig.append((b["naam"], b["adres"], b["website"], "nog niet gescand", ""))
        else:
            online.append(b)
            volledig.append((b["naam"], b["adres"], b["website"], "in de gids (concept)", s.get("opmerkingen", "")))
            if adres_wijkt_af(b, s.get("adres_op_site")):
                afwijkend.append((b["naam"], "%s, %s" % (b["adres"], b["postcode"]), s["adres_op_site"]))
            # Alleen opmerkingen waar een beslissing uit volgt; de rest staat in de volledige CSV
            if re.search(TWIJFEL, s.get("opmerkingen", ""), re.I):
                opmerkingen.append((b["naam"], s["opmerkingen"]))

    redenen = {}
    for x in vooraf:
        r = x["reden"].split(" (")[0]
        redenen[r] = redenen.get(r, 0) + 1
    maand = time.strftime("%Y-%m")
    uit = ["# Datacheck %s (%s)\n" % (categorie, time.strftime("%d-%m-%Y")),
           "Alles wat er met de verzamelde bedrijven is gebeurd, in één lijst. Wat automatisch is uitgefilterd staat er met de reden bij; "
           "zet je iets terug, dan zet ik de status in `data/bedrijvengids-scan.json` weer op voorstel. "
           "De volledige lijst per bedrijf staat in de projectbestanden: `bedrijvengids/datacheck-%s-%s.csv`.\n" % (categorie, maand),
           "## Samenvatting\n",
           tabel(["", "Aantal"], [("Gevonden in oude gids, OpenStreetMap en Overture", len(vooraf) + len(bedrijven))]
                 + [("Meteen niet meegenomen: " + r, n) for r, n in sorted(redenen.items(), key=lambda x: -x[1])]
                 + [("Website werkt niet", len(dood)), ("Automatisch verwijderd na de scan", len(auto)),
                    ("Hoort bij een andere categorie (komt daar later terug)", len(ander)), ("Fout bij het scannen", len(fout)),
                    ("Nog niet gescand", len(nog)), ("**In de gids, met tekst als concept**", len(online))]),
           "## 1. Adres op hun eigen site wijkt af\n", tabel(["Bedrijf", "Bij ons", "Op hun site"], afwijkend),
           "## 2. Opmerkingen uit de scan (twijfel over kenmerken, openingstijden of of ze open zijn)\n",
           tabel(["Bedrijf", "Opmerking"], opmerkingen),
           "## 3. Automatisch verwijderd na de scan\n", tabel(["Bedrijf", "Website", "Reden"], auto),
           "## 4. Hoort bij een andere categorie\n", tabel(["Bedrijf", "Website", "Volgens de scan"], ander),
           "## 5. Website werkt niet\n", tabel(["Bedrijf", "Website", "Uitkomst"], dood),
           "## 6. Fout bij het scannen (wordt bij de volgende scan opnieuw geprobeerd)\n", tabel(["Bedrijf", "Website", "Fout"], fout + nog),
           "## 7. Meteen niet meegenomen bij het verzamelen\n",
           "Permanent gesloten volgens Overture, of zonder eigen website. De lijst staat in `advies/osm-bedrijvengids/%s-uitgefilterd.csv`.\n" % categorie,
           tabel(["Bedrijf", "Adres", "Reden"], [(x["naam"], x["adres"], x["reden"]) for x in vooraf if "gesloten" in x["reden"]])]
    doc = ROOT / "docs" / ("datacheck-%s-%s.md" % (categorie, maand))
    doc.write_text("\n".join(uit), encoding="utf-8")
    (bron / "bedrijvengids").mkdir(exist_ok=True)
    with open(bron / "bedrijvengids" / ("datacheck-%s-%s.csv" % (categorie, maand)), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["bedrijf", "adres", "website", "uitkomst", "reden"])
        w.writerows(sorted(volledig, key=lambda r: r[0].lower()))
    print("%s: %d in de gids, %d adressen wijken af, %d opmerkingen; %s" % (categorie, len(online), len(afwijkend), len(opmerkingen), doc))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "/mnt/project-files")
