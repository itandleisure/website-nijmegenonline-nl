"""Soort, toegang, prijs en kenmerken van een evenement, voor de filters in de agenda.

Nieuwe aanmeldingen krijgen deze gegevens uit het formulier (evenement-aanmelden, zie tools/paginas.py en
tools/google-formulier/Code.gs). Voor evenementen zonder die gegevens (alles van vóór november 2026, en evenementen
die per mail binnenkomen) leidt dit script ze af uit de titel en de tekst. Dat gebeurt één keer: tools/agenda.py vult
alleen ontbrekende velden aan en schrijft ze terug in data/evenementen.json. Klopt er iets niet, pas het dan daar aan;
een ingevuld veld wordt nooit overschreven.

Velden in data/evenementen.json:
  soort       één van SOORTEN
  toegang     "gratis", "vrije gift", "betaald" of "" (onbekend)
  prijs       laagste prijs per persoon in euro als tekst ("12,50"), alleen bij betaald, of ""
  kenmerken   lijst met sleutels uit KENMERKEN, bijv. ["kinderen", "museumkaart"]

Gebruik: python tools/evenement_indeling.py [--alles]   (zonder --alles: alleen ontbrekende velden; toont een overzicht)
"""
import collections
import html
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "evenementen.json"

# Soort evenement: de keuzelijst in het formulier en de knoppen in de agenda (in deze volgorde)
SOORTEN = ["Muziek", "Theater en dans", "Film", "Expositie", "Lezing en rondleiding", "Workshop en cursus", "Markt",
           "Feest en festival", "Sport en beweging", "Eten en drinken", "Spel en quiz", "Overig"]
TOEGANG = ["gratis", "vrije gift", "betaald"]
# Sleutel in de data -> tekst bij het vinkje in het formulier
KENMERKEN = {
    "kinderen": "Leuk voor kinderen",
    "korting": "Korting voor studenten, CJP of 65+",
    "kinderprijs": "Kinderprijs",
    "museumkaart": "Museumkaart geldig",
    "inclusief": "Inclusief eten of drinken",
    "reserveren": "Reserveren of aanmelden verplicht",
}
KENMERK_SLEUTEL = {v.lower(): k for k, v in KENMERKEN.items()}

# Volgorde telt: de eerste soort die past wint. Eerst de duidelijke woorden in de titel (STERK), dan de rest (REGELS),
# daarna een paar sterke woorden in de tekst (TEKST_REGELS).
STERK = [
    ("Overig", r"herdenking"),
    ("Film", r"\bfilm|bioscoop|cinema|documentaire"),
    ("Muziek", r"concert|\bkoor\b|kamerkoor|orkest|recital|evensong|cantate|requiem"),
    ("Expositie", r"expositie|\bexpo\b|tentoonstelling|exhibition"),
    ("Workshop en cursus", r"workshop|cursus|masterclass|open repetitie"),
    ("Lezing en rondleiding", r"lezing|rondleiding|tours?\b|stadswandeling|debat|symposium|thema.?avond"),
    ("Spel en quiz", r"quiz|bridge|arcade|pok[eé]mon"),
    ("Markt", r"markt|braderie|brocante|rommel|beurs"),
    ("Theater en dans", r"theater|voorstelling|cabaret|toneel|musical"),
    ("Feest en festival", r"festival|feest|fest\b|party|carnaval|kermis|oktoberfest|halloween|disco"),
]
REGELS = [
    ("Feest en festival", r"koningsdag|dansavond|danscaf|dansen zoals|\bdans(en|schoen| mee| en)|silent disco|"
                          r"bevrijdingsdag|kerstmert|sinterklaas|familiedag|\bdag van\b|after work|extase|vrijdagshow|"
                          r"troost"),
    ("Theater en dans", r"opera|ballet|comedy|stand.?up|poppen|\bdans(voorstelling|theater)|cirque|circus|mime|vertel"),
    ("Spel en quiz", r"\bspel|game|bingo|schaak|escape|treasure hunt|speurtocht|zomerpaspoort|highscore"),
    ("Sport en beweging", r"\bloop\b|run\b|hardloop|wandeltocht|fietstocht|toernooi|kampioenschap|sport|yoga|zwem|"
                          r"voetbal|vierdaagse(?!feest)|marathon|bootcamp|beach|eredivisie|rad(erlebnis|tour)"),
    ("Workshop en cursus", r"\bles\b|lessen|training|scratch|reparatie|repair|\bmaak\b|knutsel|meezing|druk met|"
                           r"zentangle|healing|lenteklaar|nldoet|vrijwilliger"),
    ("Lezing en rondleiding", r"wandeling|caf[eé]:|\w+caf[eé]\b|(science|geschiedenis|filosofisch|bastei|taal)\s?caf|"
                              r"gesprek|presentatie|verhal|aan het woord|excursie|open dag|monumentendag|"
                              r"boekpresentatie|voorlezen|college|open (joodse )?huizen|toekomst van|stolpersteine|"
                              r"anne frank|hygi[eë]ne|smaak van vrijheid|vertelt"),
    ("Expositie", r"ateliers?\b|kunstroute|beelden|galerie|schilderijen|fotografie|experience|museum|kunstkring|"
                  r"open tuin|zuiderkapel|kijk je ogen uit"),
    ("Eten en drinken", r"proeverij|\bwijn|\bbier|diner|high.?tea|brunch|\bfood|culinair|wine|lunch|borrel"),
    ("Muziek", r"\bkoor|koren|\bband\b|jazz|blues|live.?muziek|ensemble|singer|songwriter|optreden|zingt|klinkt|"
               r"\brock|pop\b|kamermuziek|\bdj\b|trio|kwartet|duo\b|zangeres|zanger|pianist|organist|orgel|muzikaal|"
               r"muziek|\bsessie|jam\b|mis\b|vespers|tribute|unplugged|acoustic|akoestisch|koper|konsort|psalm|"
               r"rhythm|harmon|\blive\b|triptones|triesto|animal spirits|billy in"),
]
# Op de tekst alleen sterke woorden, anders wordt alles "Muziek" of "Expositie"
TEKST_REGELS = [
    ("Muziek", r"\bconcert|live.?muziek|optreden van|treedt op|treden op|speelt (de|het|een)|\bband\b|zangeres|zanger"),
    ("Expositie", r"expositie|tentoonstelling|exposeert|is te zien"),
    ("Lezing en rondleiding", r"lezing|rondleiding|vertelt over|spreker"),
    ("Workshop en cursus", r"workshop|cursus"),
    ("Theater en dans", r"voorstelling|theater"),
]
# Plekken waar bijna alles live muziek is (aanbieder-slug uit data/aanbieders.json)
MUZIEKPLEKKEN = {"de-brauerij", "doornroosje", "de-onderbroek", "merleyn"}
SPELPLEKKEN = {"pop-culture-arcade"}

BEDRAG = re.compile(r"(?:€|eur(?:o)?\.?)\s?(\d{1,3}(?:[.,]\d{1,2})?)(?:\s?,-)?|(\d{1,3}(?:[.,]\d{2})?)\s?(?:euro|€)", re.I)
PRIJSZIN = re.compile(r"entree|ticket|kaart|prijs|kosten|toegang|eintritt|bijdrage|p\.p\.|per persoon|deelname|€|euro", re.I)
GEEN_PRIJS = re.compile(r"goedkoper|korting|reductie|abonnement|parkeren|parkeer|statiegeld|garderobe|consumptie(bon|munt)", re.I)
GRATIS = re.compile(r"(gratis|vrije|kosteloos|free)\s*(toegang|entree|te bezoeken|toegankelijk|access|entrance|admission)|"
                    r"(toegang|entree|deelname|bezoek)\s*(is\s*)?(geheel\s*|helemaal\s*)?(gratis|vrij|kosteloos)|"
                    r"vrij toegankelijk|eintritt (ist )?frei|freier eintritt|is gratis\b|gratis bij te wonen|"
                    r"gratis en voor niets|\bgratis\b(?!\s*(parkeren|parkeer|koffie|drankje|consumptie|hapje|"
                    r"wifi|programma|magazine|boekje))", re.I)
VRIJE_GIFT = re.compile(r"vrije gift|vrijwillige bijdrage|collecte|pay what|naar draagkracht|donatie (is )?welkom|"
                        r"bijdrage naar keuze|freiwillige spende|hutcollecte", re.I)
KENMERK_REGELS = {
    "kinderen": r"kinder(?!opvang|prijs|ticket)|\bkids\b|familie|gezin|jong en oud|voor het hele gezin|kindvriendelijk|"
                r"(kinderen|kids) (vanaf|tot|t/m|van) \d|peuters|kleuters|basisschool|\bjeugd",
    "korting": r"\bcjp\b|studenten\s*(betalen|€|\d|korting|tarief)|studenten(prijs|tarief|korting)|65\+|"
               r"(met|op vertoon van)\s*\w*\s*pas|stadspas|meedoen.?pas|ooievaarspas|korting",
    "kinderprijs": r"kinderprijs|kinderticket|kinderen\s*(t/m|tot|onder)\s*\d+\s*(jaar)?\s*(gratis|€|betalen)|"
                   r"kinderen\s*(betalen|€)|familieticket|gezinsticket",
    "museumkaart": r"museumkaart",
    "inclusief": r"(incl\.?|inclusief|inbegrepen)\s*[^.]{0,40}(consumptie|koffie|thee|drankje|hapje|diner|lunch|"
                 r"buffet|eten|borrel|wijn)|(koffie|thee|drankje|lunch|diner)\s*(is\s*)?inbegrepen",
    "reserveren": r"(reserveren|aanmelden|inschrijven|registreren)\s*(is\s*)?(verplicht|noodzakelijk|nodig|vereist|"
                  r"gewenst|noodzakelijk)|vol\s*=\s*vol|alleen (op|na) (reservering|aanmelding)|"
                  r"beperkt aantal plaatsen",
}


def platte_tekst(e):
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", e.get("tekst") or "")).split())


def soort_van(e):
    titel = e.get("titel", "")
    if e.get("aanbieder") in SPELPLEKKEN:
        return "Spel en quiz"
    for soort, r in STERK + REGELS:
        if re.search(r, titel, re.I):
            return soort
    if e.get("aanbieder") in MUZIEKPLEKKEN:
        return "Muziek"
    tekst = platte_tekst(e)
    for soort, r in TEKST_REGELS:
        if re.search(r, tekst, re.I):
            return soort
    return "Overig"


def bedrag(tekst):
    """De laagste prijs per persoon in zinnen over entree of tickets, als tekst ("12,50" of "15"), of ""."""
    gevonden = []
    for zin in re.split(r"(?<=[.!?])\s+|\n|;|•|\|", tekst):
        if not PRIJSZIN.search(zin) or GEEN_PRIJS.search(zin):
            continue
        for m in BEDRAG.finditer(zin):
            waarde = float((m.group(1) or m.group(2)).replace(",", "."))
            if 0 < waarde <= 250:
                gevonden.append(waarde)
    if not gevonden:
        return ""
    laagste = min(gevonden)
    return ("%d" % laagste) if laagste == int(laagste) else ("%.2f" % laagste).replace(".", ",")


def toegang_van(e):
    tekst = e.get("titel", "") + ". " + platte_tekst(e)
    prijs = bedrag(tekst)
    if VRIJE_GIFT.search(tekst) and not prijs:
        return "vrije gift", ""
    if prijs:
        return "betaald", prijs
    if GRATIS.search(tekst):
        return "gratis", ""
    if re.search(r"tickets?\s*(zijn|via|bij|op|kopen|kosten)|kaarten\s*(zijn|via|bij|kopen|kosten)|voorverkoop|"
                 r"entreeprijs|toegangsprijs|aan de kassa", tekst, re.I):
        return "betaald", ""
    return "", ""


def kenmerken_van(e):
    tekst = e.get("titel", "") + ". " + platte_tekst(e)
    return [k for k, r in KENMERK_REGELS.items() if re.search(r, tekst, re.I)]


def aanvullen(e, alles=False):
    """Vult ontbrekende velden aan (of alles opnieuw met alles=True). Geeft True als er iets veranderde."""
    oud = {k: e.get(k) for k in ("soort", "toegang", "prijs", "kenmerken")}
    if alles or "soort" not in e:
        e["soort"] = soort_van(e)
    if alles or "toegang" not in e:
        e["toegang"], prijs = toegang_van(e)
        if alles or "prijs" not in e:
            e["prijs"] = prijs
    e.setdefault("prijs", "")
    if alles or "kenmerken" not in e:
        e["kenmerken"] = kenmerken_van(e)
    return any(e.get(k) != v for k, v in oud.items())


def prijslabel(e):
    """Korte tekst voor de kaart in de agenda: "Gratis", "Vrije gift", "Vanaf € 15", "Betaald" of ""."""
    t = e.get("toegang", "")
    if t == "gratis":
        return "Gratis"
    if t == "vrije gift":
        return "Vrije gift"
    if t == "betaald":
        return ("€ %s" if e.get("prijs_vast") else "Vanaf € %s") % e["prijs"] if e.get("prijs") else ""
    return ""


def uit_formulier(a):
    """De velden uit een aanmelding via het formulier (tools/aanmeldingen.py). Ontbreekt iets, dan vult agenda.py
    het later aan met de regels hierboven."""
    uit = {}
    soort = (a.get("soort") or "").strip()
    if soort in SOORTEN:
        uit["soort"] = soort
    toegang = (a.get("toegang") or "").strip().lower()
    if toegang in TOEGANG:
        uit["toegang"] = toegang
        prijs = re.sub(r"[^\d,.]", "", a.get("prijs") or "").replace(".", ",")
        uit["prijs"] = prijs.rstrip(",") if toegang == "betaald" else ""
        if re.fullmatch(r"\d+,\d", uit["prijs"]):
            uit["prijs"] += "0"
        if uit["prijs"].endswith(",00"):
            uit["prijs"] = uit["prijs"][:-3]
        if not re.fullmatch(r"\d+(,\d\d)?", uit["prijs"]):
            uit["prijs"] = ""
    if "kenmerken" in a:
        gekozen = [x.strip().lower() for x in re.split(r",\s*(?=[A-Z])|\|", a.get("kenmerken") or "") if x.strip()]
        # Code.gs voegt meerdere vinkjes samen met ", "; de teksten zelf bevatten ook komma's, dus op de bekende teksten zoeken
        tekst = (a.get("kenmerken") or "").lower()
        uit["kenmerken"] = [k for k, v in KENMERKEN.items() if v.lower() in tekst or v.lower() in gekozen]
    return uit


def main(argv):
    alles = "--alles" in argv
    evenementen = json.load(open(DATA, encoding="utf-8"))
    n = sum(aanvullen(e, alles) for e in evenementen)
    if n:
        DATA.write_text(json.dumps(evenementen, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print("%d evenementen aangevuld" % n)
    print(collections.Counter(e["soort"] for e in evenementen).most_common())
    print(collections.Counter(e["toegang"] or "onbekend" for e in evenementen).most_common())
    print(collections.Counter(k for e in evenementen for k in e["kenmerken"]).most_common())


if __name__ == "__main__":
    main(sys.argv[1:])
