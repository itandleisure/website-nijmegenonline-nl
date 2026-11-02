"""Eenmalig (en later opnieuw te draaien): aanbieders uit de agenda en nieuwsberichten aan bedrijven in de gids koppelen.

- Elke aanbieder in data/aanbieders.json krijgt een "plaats" (uit het adres of de naam).
- Een aanbieder krijgt automatisch een "bedrijf" als de sleutel of de naam precies overeenkomt met een bedrijf in de
  gids (data/bedrijvengids-vermeldingen.json).
- Voor de rest maakt het script een lijst met voorstellen voor de redactie: docs/koppellijst-<jaar-maand>.md. Daarin
  staan ook de nieuwsberichten die een bedrijf uit de gids bij naam noemen. Wat de redactie besluit, gaat met de hand in
  data/aanbieders.json ("bedrijf") of data/nieuws.json ("bedrijven"); een aanbieder die een plek is (kerk, park,
  binnenstad) krijgt "bedrijf": "" en blijft gewoon een locatie.

Besluit Frans (2-11-2026, na de eerste lijst):
- Dubbele aanbieders worden samengevoegd: data/aanbieders-samengevoegd.json ({"oude-sleutel": "nieuwe-sleutel"}). De
  evenementen gaan naar de nieuwe aanbieder, de oude verdwijnt uit data/aanbieders.json en /event-location/<oud>/ verwijst
  met een 301 door (tools/agenda.py). Een nieuwe sleutel die nog niet bestaat, krijgt de naam en plaats van de eerste oude.
- Elke aanbieder heet "naam plus plaats": Boskapel Nijmegen, Bottendaal Nijmegen (koppeling.naam_met_plaats). De locatie
  van de evenementen gaat mee als die gelijk was aan de oude naam.

Gebruik: python tools/koppelen.py            (schrijft de automatische koppelingen en de lijst)
"""
import collections
import datetime
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import koppeling  # noqa: E402
from aanmeldingen import naam_sleutel  # noqa: E402

# Woorden in de naam van een aanbieder die op een plek wijzen, niet op een bedrijf
PLEK = re.compile(r"kerk|kapel|begraafplaats|binnenstad|centrum|\bpark|plein|wijk|stad\b|tuinen|bottendaal|heuvel|"
                  r"kazerne|\bstraat|door heel|diverse|markt\b|bos\b|polder|kade|dijk", re.I)


# Namen in de gids die te algemeen zijn om in een andere naam te zoeken
GENERIEK = {"atelier", "studio", "museum", "theater", "podium", "winkel", "kerk", "galerie", "nijmegen"}


def naam_woorden(naam):
    return [w for w in re.split(r"[^\w]+", naam.lower()) if w and w not in ("de", "het", "t", "the", "een")]


def domein(url):
    m = re.match(r"^(?:[a-z]+://)?(?:www\.)?([^/:?#]+)", (url or "").strip().lower())
    return m.group(1) if m else ""


def voorstel(slug, info, evenementen, vermeldingen, per_naam, per_domein):
    """(bedrijf-sleutel, reden) of (None, reden)."""
    if slug in vermeldingen:
        return slug, "zelfde sleutel"
    k = naam_sleutel(info["naam"])
    if k and k in per_naam:
        return per_naam[k], "zelfde naam"
    # Een kerk, park of binnenstad is een plek; een organisator met een website daar is niet de plek zelf
    if PLEK.search(info["naam"]):
        return None, ""
    for e in evenementen:
        for veld in ("website", "link"):
            d = domein(e.get(veld))
            if d and d in per_domein:
                return per_domein[d], "website van een evenement (%s)" % d
    # De ene naam zit helemaal in de andere ("Hortus Nijmegen" en "Stichting Hortus Nijmegen"). Zonder de plaats die we
    # achter de naam zetten: anders zit "Ds Nijmegen" in "Thiemeloods Nijmegen".
    plaats = "Kleve" if info.get("plaats") == "Kleef" else info.get("plaats") or ""
    if plaats and info["naam"].endswith(" " + plaats):
        kaal = info["naam"][:-len(plaats) - 1]
        # Eén los woord ("Kasteel") zit te vaak toevallig in een andere naam
        k = naam_sleutel(kaal) if len(naam_woorden(kaal)) >= 2 else ""
    if len(k) >= 6:
        binnen = sorted(s for n, s in per_naam.items() if len(n) >= 6 and n not in GENERIEK and (k in n or n in k))
        if len(binnen) == 1:
            return binnen[0], "de ene naam zit in de andere"
    return None, ""


def samenvoegen(aanbieders, evenementen):
    """Voegt dubbele aanbieders samen volgens data/aanbieders-samengevoegd.json."""
    pad = ROOT / "data" / "aanbieders-samengevoegd.json"
    naar = json.loads(pad.read_text(encoding="utf-8")) if pad.exists() else {}
    for oud, nieuw in sorted(naar.items()):
        if oud not in aanbieders:
            continue
        info = aanbieders.pop(oud)
        if nieuw not in aanbieders:
            aanbieders[nieuw] = {k: v for k, v in info.items() if k in ("naam", "adres", "plaats", "bedrijf")}
        for e in evenementen:
            if e.get("aanbieder") == oud:
                e["aanbieder"] = nieuw
                if not e.get("locatie") or e["locatie"] == info["naam"]:
                    e["locatie"] = aanbieders[nieuw]["naam"]


def namen_met_plaats(aanbieders, evenementen):
    for slug, info in aanbieders.items():
        nieuw = koppeling.naam_met_plaats(info["naam"], info.get("plaats"))
        if nieuw != info["naam"]:
            for e in evenementen:
                if e.get("aanbieder") == slug and e.get("locatie", "").strip().rstrip(".") in (info["naam"], info["naam"].rstrip(".")):
                    e["locatie"] = nieuw
            info["naam"] = nieuw


def main():
    vermeldingen = koppeling.laad_vermeldingen()
    aanbieders = json.load(open(ROOT / "data" / "aanbieders.json", encoding="utf-8"))
    evenementen = json.load(open(ROOT / "data" / "evenementen.json", encoding="utf-8"))
    berichten = json.load(open(ROOT / "data" / "nieuws.json", encoding="utf-8"))
    per_naam = {naam_sleutel(v["bedrijf"]): s for s, v in sorted(vermeldingen.items())}
    per_domein = collections.defaultdict(list)
    for s, v in vermeldingen.items():
        if domein(v.get("site")):
            per_domein[domein(v["site"])].append(s)
    # Een domein dat bij meer bedrijven hoort (een keten, een platform) zegt niets
    per_domein = {d: s[0] for d, s in per_domein.items() if len(s) == 1}

    samenvoegen(aanbieders, evenementen)
    automatisch, lijst, plekken, open_ = [], [], [], []
    for slug, info in sorted(aanbieders.items()):
        eigen = [e for e in evenementen if e.get("aanbieder") == slug]
        if not info.get("plaats"):
            meest = collections.Counter(koppeling.plaats_van_evenement(e, aanbieders) for e in eigen).most_common(1)
            info["plaats"] = (koppeling.plaats_van(info.get("adres") or "") or koppeling.plaats_van(info["naam"])
                              or (meest[0][0] if meest else "Nijmegen"))
        if "bedrijf" in info:   # al besloten (ook "" = een plek, niet koppelen)
            continue
        b, reden = voorstel(slug, info, eigen, vermeldingen, per_naam, per_domein)
        if b and reden in ("zelfde sleutel", "zelfde naam"):
            info["bedrijf"] = b
            automatisch.append((slug, info, b, reden, len(eigen)))
        elif b:
            lijst.append((slug, info, b, reden, len(eigen)))
        elif PLEK.search(info["naam"]):
            plekken.append((slug, info, len(eigen)))
        else:
            open_.append((slug, info, len(eigen)))
    namen_met_plaats(aanbieders, evenementen)
    (ROOT / "data" / "evenementen.json").write_text(json.dumps(evenementen, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    (ROOT / "data" / "aanbieders.json").write_text(json.dumps(dict(sorted(aanbieders.items())), ensure_ascii=False, indent=1) + "\n",
                                                   encoding="utf-8")

    # Nieuwsberichten die een bedrijf uit de gids bij naam noemen. Alleen namen van minstens twee woorden (zonder
    # lidwoord): losse woorden als "Woensdag" of "Glaswerk" staan te vaak toevallig in een tekst.
    nieuws_voorstel = []
    for b in berichten:
        tekst = re.sub(r"<[^>]+>", " ", b["titel"] + " " + b["tekst"])
        al = set(b.get("bedrijven", []))
        gevonden = [s for s, v in vermeldingen.items() if s not in al and len(naam_woorden(v["bedrijf"])) >= 2
                    and re.search(r"(?<!\w)%s(?!\w)" % re.escape(v["bedrijf"]), tekst, re.I)]
        if gevonden:
            nieuws_voorstel.append((b, sorted(gevonden)))

    maand = datetime.date.today().strftime("%Y-%m")
    regels = ["# Koppellijst: agenda en nieuws aan de bedrijvengids (%s)" % maand, "",
              "Gemaakt door `tools/koppelen.py`. Automatisch gekoppeld (zelfde sleutel of naam): %d aanbieders. "
              "Hieronder wat de redactie nog moet beslissen. Een besluit gaat in `data/aanbieders.json`: "
              '`"bedrijf": "<sleutel>"` om te koppelen, `"bedrijf": ""` voor een plek die niet gekoppeld wordt.' % len(automatisch), "",
              "## Voorstel: koppelen aan dit bedrijf", "",
              "| Aanbieder | Plaats | Evenementen | Voorstel | Waarom |", "| --- | --- | --- | --- | --- |"]
    regels += ["| %s (`%s`) | %s | %d | [%s](%s/bedrijvengids/%s/) (`%s`) | %s |"
               % (i["naam"], s, i["plaats"], n, vermeldingen[b]["bedrijf"], koppeling.SITE, b, b, r) for s, i, b, r, n in lijst]
    regels += ["", "## Lijkt een plek: niet koppelen, alleen de plaats", "",
               "| Aanbieder | Plaats | Evenementen |", "| --- | --- | --- |"]
    regels += ["| %s (`%s`) | %s | %d |" % (i["naam"], s, i["plaats"], n) for s, i, n in plekken]
    regels += ["", "## Geen bedrijf gevonden in de gids", "",
               "Een plek, of een bedrijf dat (nog) niet in de gids staat. Staat het er wel in, zet dan de sleutel erbij.", "",
               "| Aanbieder | Plaats | Evenementen |", "| --- | --- | --- |"]
    regels += ["| %s (`%s`) | %s | %d |" % (i["naam"], s, i["plaats"], n) for s, i, n in open_]
    regels += ["", "## Nieuwsberichten die een bedrijf uit de gids noemen", "",
               'Klopt het, zet de sleutel dan in `"bedrijven"` van het bericht in `data/nieuws.json`.', "",
               "| Bericht | Noemt |", "| --- | --- |"]
    regels += ["| [%s](%s/nieuwsoverzicht/%s/) | %s |" % (b["titel"], koppeling.SITE, b["slug"], ", ".join(
        "[%s](%s/bedrijvengids/%s/) (`%s`)" % (vermeldingen[s]["bedrijf"], koppeling.SITE, s, s) for s in g)) for b, g in nieuws_voorstel]
    regels += ["", "## Automatisch gekoppeld", "", "| Aanbieder | Bedrijf | Waarom |", "| --- | --- | --- |"]
    regels += ["| %s (`%s`) | [%s](%s/bedrijvengids/%s/) | %s |" % (i["naam"], s, vermeldingen[b]["bedrijf"], koppeling.SITE, b, r)
               for s, i, b, r, n in automatisch]
    pad = ROOT / "docs" / ("koppellijst-%s.md" % maand)
    pad.write_text("\n".join(regels) + "\n", encoding="utf-8")
    print("Aanbieders: %d automatisch gekoppeld, %d voorstellen, %d plekken, %d zonder bedrijf; %d nieuwsberichten met een "
          "voorstel. Lijst: %s" % (len(automatisch), len(lijst), len(plekken), len(open_), len(nieuws_voorstel), pad.relative_to(ROOT)))


if __name__ == "__main__":
    main()
