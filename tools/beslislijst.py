"""Eén beslislijst per groep van de bedrijvengids (stap 5 van de standaard in de README).

Bij een groep met honderden bedrijven vraag ik Frans niet per bedrijf, maar per soort geval: wat ik overneem, wat ik
weghaal en waar hij een regel voor moet kiezen. De datacheck per categorie (tools/datacheck.py) blijft de volledige lijst.

Schrijft docs/beslislijst-<groep>-<jaar-maand>.md.
Gebruik: python tools/beslislijst.py zakelijk
"""
import collections
import json
import pathlib
import re
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from datacheck import adres_wijkt_af, tabel  # noqa: E402

GROEPEN = {
    "zakelijk": ("Zakelijk en diensten", ["marketingbureau", "accountant-boekhouder", "advocatenkantoor", "notaris", "hypotheekadviseur",
                                          "verzekeraar", "uitzendbureau", "opleiding-en-training", "rijschool", "fotograaf", "autobedrijf",
                                          "kinderopvang", "taxi", "begrafenis", "hondentraining"]),
    "wonen": ("Wonen en klussen", ["aannemersbedrijf", "schilder", "loodgieter", "hovenier", "zonnepanelen", "meubelmaker", "makelaar",
                                   "dakdekker", "slotenmaker", "elektricien", "verhuisbedrijf", "schoonmaakbedrijf"]),
    "beauty": ("Beauty en wellness", ["kapper", "massagesalon", "wellness", "permanente-make-up", "schoonheidssalon", "nagelsalon",
                                      "pedicure", "tattoo"]),
    "uitgaan": ("Uitgaan", ["uitjes", "musea", "podia", "bioscoop", "galerie", "zaalverhuur"]),
    "eten": ("Eten en drinken (rest)", ["bakkerij", "bierbrouwerij", "afhaal", "catering", "ijssalon"]),
    "sport": ("Sport (rest)", ["dansschool", "yoga", "vechtsport", "zwembad", "padel", "sportvereniging"]),
    "gezondheid": ("Gezondheid en welzijn", ["fysiotherapeut", "dietist", "psycholoog", "coach", "alternatief", "opticien", "huisarts",
                                             "dierenarts", "tandarts"]),
    "overnachten-winkelen": ("Overnachten en Winkelen", ["hotel", "bed-and-breakfast", "camping", "kledingwinkel", "tweedehands-winkel",
                                                         "woonwinkel", "juwelier", "bloemist", "hobbywinkel", "parfumerie", "elektronica",
                                                         "fietsenwinkel", "boekhandel"]),
}

# Vragen die niet uit de data volgen, per groep bovenaan de lijst
VRAGEN = {
    "zakelijk": [
        "**G. Grafisch ontwerpers en IT-bedrijven.** Die heb ik niet als eigen categorie opgenomen. De scan vond er een paar "
        "tussen de marketingbureaus (zie E). Mijn voorstel: grafisch ontwerpers bij de marketingbureaus laten, IT-bedrijven "
        "voorlopig niet. Of wil je er een eigen pagina voor?",
    ],
}

IN_GEMEENTE = r"\b65[0-4]\d\s?[a-z]{2}\b|nijmegen|\blent\b|oosterhout"
GEEN_LOCATIE = r"thuisadres|postadres|geen (straat)?adres|geen fysieke|geen (vaste |eigen )?(locatie|vestiging|praktijk|winkel)|alleen online|aan huis werk|op locatie bij de klant|niet op de site bevestigd"


def main(groep):
    titel, categorieen = GROEPEN[groep]
    alle = json.loads((ROOT / "data" / "bedrijvengids.json").read_text(encoding="utf-8"))
    scan = json.loads((ROOT / "data" / "bedrijvengids-scan.json").read_text(encoding="utf-8"))
    sites = json.loads((ROOT / "data" / "bedrijvengids-websites.json").read_text(encoding="utf-8"))
    volgorde = list(alle)
    gezien = set()
    for cat in volgorde[:min(volgorde.index(c) for c in categorieen)]:
        gezien |= {b["slug"] for b in alle[cat]["gids"] + alle[cat]["overig"] if cat not in (scan.get(b["slug"], {}).get("niet_in") or {})}

    telling, overnemen, buiten, geen_plek, redenen, ander, nog = [], [], [], [], collections.Counter(), [], []
    for cat in categorieen:
        n = collections.Counter()
        for b in alle[cat]["gids"] + alle[cat]["overig"]:
            if b["slug"] in gezien:
                continue
            gezien.add(b["slug"])
            s, w = scan.get(b["slug"], {}), sites.get(b["slug"], {})
            if w and not w.get("werkt") and w.get("website") == b.get("website"):
                n["site werkt niet"] += 1
            elif s.get("status") == "verwijderd":
                n["automatisch weg"] += 1
                redenen[re.sub(r"^automatisch: ", "", s.get("reden", "")).split(" (")[0]] += 1
            elif cat in (s.get("niet_in") or {}):
                n["andere categorie"] += 1
                ander.append((b["naam"], cat, s["niet_in"][cat].replace("automatisch: ", "")[:120]))
            elif not s or s.get("status") == "fout":
                n["nog niet gescand"] += 1
                nog.append((b["naam"], cat))
            else:
                n["in de gids"] += 1
                op_site, opm = s.get("adres_op_site") or "", s.get("opmerkingen") or ""
                rij = (b["naam"], cat, "%s, %s" % (b["adres"], b["postcode"]), op_site or "", opm[:180])
                if op_site and not re.search(r"\d", op_site) or not op_site and re.search(GEEN_LOCATIE, opm, re.I):
                    geen_plek.append(rij)   # alleen "Nijmegen" of niets op de site
                elif adres_wijkt_af(b, re.sub(r"\bSt\.? ", "Sint ", op_site)):
                    (overnemen if re.search(IN_GEMEENTE, op_site, re.I) else buiten).append(rij)
        telling.append((cat, n["in de gids"], n["automatisch weg"], n["site werkt niet"], n["andere categorie"], n["nog niet gescand"]))

    totaal = sum(t[1] for t in telling)
    uit = ["# %s: beslissingen voor Frans (%s)\n" % (titel, time.strftime("%d-%m-%Y")),
           "Na het verzamelen, de websitecheck en de scan staan er **%d bedrijven** als concept in de gids. "
           "Bij zoveel bedrijven vraag ik niet per bedrijf, maar per soort geval. Antwoord per letter, bijvoorbeeld "
           "\"A goed, B weg, C houden\". De volledige lijst per categorie staat in `docs/datacheck-<categorie>-%s.md`.\n" % (totaal, time.strftime("%Y-%m")),
           *(["## Eerst een vraag\n"] + VRAGEN[groep] + [""] if groep in VRAGEN else []),
           "## Per categorie\n",
           tabel(["Categorie", "In de gids", "Automatisch weg", "Site werkt niet", "Andere categorie", "Nog niet gescand"], telling),
           "## A. Adres op hun eigen site is anders, maar wel in Nijmegen: neem ik over (%d)\n" % len(overnemen),
           "Meestal verhuisd binnen de stad of een ander huisnummer. Ik zet het adres van hun eigen site in de gids.\n",
           tabel(["Bedrijf", "Categorie", "Bij ons", "Op hun site"], [r[:4] for r in overnemen]),
           "## B. Adres op hun eigen site ligt buiten de gemeente: haal ik weg (%d)\n" % len(buiten),
           "Verhuisd naar Wijchen, Beuningen of verder. Wil je er een paar houden, noem ze dan.\n",
           tabel(["Bedrijf", "Categorie", "Bij ons", "Op hun site"], [r[:4] for r in buiten]),
           "## C. Geen vaste plek in Nijmegen: houden of weghalen? (%d)\n" % len(geen_plek),
           "Vaak zzp'ers die vanuit huis of bij de klant werken. Mijn voorstel: **houden**, maar zonder adres op de kaart, "
           "alleen met de plaats. Of zeg \"C weg\".\n",
           tabel(["Bedrijf", "Categorie", "Opmerking uit de scan"], [(r[0], r[1], r[4]) for r in geen_plek]),
           "## D. Automatisch weggehaald na de scan\n",
           "Ter info. Zet je een reden terug, dan komen die bedrijven weer in de gids.\n",
           tabel(["Reden", "Aantal"], redenen.most_common()),
           "## E. Hoort bij een andere categorie (%d)\n" % len(ander),
           "Ter info: deze komen in de categorie die bij ze past, of vallen af als die er niet is.\n",
           tabel(["Bedrijf", "Stond bij", "Volgens de scan"], ander),
           "## F. Nog niet gescand (%d)\n" % len(nog),
           "Een fout bij het scannen; die probeer ik bij de volgende scan opnieuw.\n",
           tabel(["Bedrijf", "Categorie"], nog)]
    doc = ROOT / "docs" / ("beslislijst-%s-%s.md" % (groep, time.strftime("%Y-%m")))
    doc.write_text("\n".join(uit), encoding="utf-8")
    print("%s: %d in de gids; A %d, B %d, C %d, E %d, F %d; %s" % (groep, totaal, len(overnemen), len(buiten), len(geen_plek),
                                                                   len(ander), len(nog), doc))


if __name__ == "__main__":
    main(sys.argv[1])
