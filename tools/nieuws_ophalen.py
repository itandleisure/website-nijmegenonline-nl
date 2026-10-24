"""Haalt de doorgestuurde nieuwsmails op uit nieuws@nijmegenonline.nl en stuurt ze naar het Google Apps Script.

Zo werkt de flow (zie ook tools/google-formulier/Code.gs, nieuwsOntvangen):
1. Iemand mailt nieuws naar redactie@nijmegenonline.nl; de redactie stuurt de mail door naar nieuws@nijmegenonline.nl.
2. Elke 15 minuten draait dit script (.github/workflows/nieuws-ophalen.yml). Per mail haalt het de tekst eruit (ook
   uit een doorgestuurde mail als bijlage en uit pdf- en Word-bijlagen) en de foto's (verkleind, logo's en iconen
   eruit, de grootste liggende eerst), en stuurt dat naar het script.
3. Het script zet het in het tabblad Nieuws, laat Claude er een nieuwsbericht van schrijven en mailt de redactie de
   knop "Bekijken en beoordelen". Na goedkeuring zet tools/aanmeldingen.py het bericht op de site.
   Begint het onderwerp met "Agenda" (of "Evenement"), dan wordt het een evenement: Claude haalt datum, tijden,
   locatie en tekst eruit en het komt in het tabblad Evenementen, verder net als een aangemeld evenement.
4. De mail gaat naar de map Verwerkt. Mails van een afzender buiten NIEUWS_AFZENDERS gaan naar de map Genegeerd.
   Lukt het versturen niet, dan blijft de mail in de inbox en komt hij de volgende keer opnieuw aan de beurt.

Omgeving: NIEUWS_MAIL_SERVER, NIEUWS_MAIL_GEBRUIKER, NIEUWS_MAIL_WACHTWOORD (de mailbox, via IMAP),
NIEUWS_SLEUTEL (zelfde waarde als in het Apps Script, zie maakNieuwsSleutel), en optioneel NIEUWS_AFZENDERS:
domeinen of adressen die mogen aanleveren, met komma's (standaard nijmegenonline.nl).

Gebruik: python tools/nieuws_ophalen.py              mails ophalen en versturen
         python tools/nieuws_ophalen.py --test       alleen inloggen en tellen wat er in de mailbox staat
         python tools/nieuws_ophalen.py --bestand x.eml   een opgeslagen mail uitlezen en tonen, niets versturen
"""
import email
import email.policy
import hashlib
import imaplib
import io
import json
import os
import pathlib
import re
import ssl
import sys
import urllib.parse
import urllib.request
from email.utils import parseaddr

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

VERWERKT = "Verwerkt"
GENEGEERD = "Genegeerd"
MIN_ZIJDE = 300        # kleinere afbeeldingen zijn logo's, iconen of handtekeningen
MAX_ZIJDE = 1600
MAX_FOTOS = 6
MAX_TEKST = 30000


# ---------- Mail uitlezen ----------

def html_naar_tekst(inhoud):
    from bs4 import BeautifulSoup
    soep = BeautifulSoup(inhoud, "html.parser")
    for weg in soep(["style", "script", "head"]):
        weg.decompose()
    for br in soep.find_all("br"):
        br.replace_with("\n")
    tekst = soep.get_text("\n")
    return re.sub(r"\n\s*\n\s*(\n\s*)+", "\n\n", tekst)


def lichaam(bericht):
    """De tekst van een mail: liefst de platte tekst, anders de HTML zonder opmaak."""
    deel = bericht.get_body(preferencelist=("plain", "html"))
    if deel is None:
        return ""
    try:
        inhoud = deel.get_content()
    except (LookupError, ValueError):
        inhoud = deel.get_payload(decode=True).decode("utf-8", "replace")
    tekst = html_naar_tekst(inhoud) if deel.get_content_type() == "text/html" else inhoud
    return re.sub(r"[ \t]+\n", "\n", tekst).strip()


def kop(bericht):
    regels = []
    for veld in ("From", "Date", "Subject"):
        if bericht[veld]:
            regels.append("%s: %s" % ({"From": "Van", "Date": "Datum", "Subject": "Onderwerp"}[veld], bericht[veld]))
    return "\n".join(regels)


def pdf_tekst(data):
    from pypdf import PdfReader
    return "\n".join((p.extract_text() or "") for p in PdfReader(io.BytesIO(data)).pages[:20])


def word_tekst(data):
    import docx
    return "\n".join(p.text for p in docx.Document(io.BytesIO(data)).paragraphs)


def foto(data):
    """Afbeelding als jpeg van hooguit MAX_ZIJDE px, of None als het een klein plaatje (logo, icoon) is."""
    from PIL import Image, ImageOps
    try:
        im = Image.open(io.BytesIO(data))
        im = ImageOps.exif_transpose(im)
    except Exception:
        return None
    if min(im.size) < MIN_ZIJDE:
        return None
    im = im.convert("RGB")
    im.thumbnail((MAX_ZIJDE, MAX_ZIJDE))
    uit = io.BytesIO()
    im.save(uit, "JPEG", quality=85)
    breed, hoog = im.size
    return {"data": uit.getvalue(), "score": breed * hoog * (1.3 if breed >= hoog else 1)}


def lees_mail(ruw):
    """Geeft (afzender, doel, onderwerp, berichtid, tekst, fotos) van een doorgestuurde mail. Doel is "evenement"
    als de redactie het onderwerp met Agenda of Evenement begon, anders "nieuws"."""
    bericht = email.message_from_bytes(ruw, policy=email.policy.default)
    afzender = parseaddr(str(bericht["From"] or ""))[1].lower()
    onderwerp = str(bericht["Subject"] or "").strip()
    doel = "evenement" if re.match(r"(agenda|evenement)\b", onderwerp, re.I) else "nieuws"
    if doel == "evenement":
        onderwerp = re.sub(r"^(agenda|evenement)\b\s*[:\-]?\s*", "", onderwerp, flags=re.I)
    onderwerp = re.sub(r"^\s*((fwd?|fw|doorst|tr|wg)\s*:\s*)+", "", onderwerp, flags=re.I).strip()
    berichtid = str(bericht["Message-ID"] or "").strip() or hashlib.sha1(ruw).hexdigest()

    delen = [lichaam(bericht)]
    fotos, gezien = [], set()
    for deel in bericht.walk():
        soort = deel.get_content_type()
        if soort == "message/rfc822":
            # Doorgestuurd als bijlage: de oorspronkelijke mail met zijn eigen kop
            binnen = deel.get_payload(0) if deel.is_multipart() else None
            if binnen is not None:
                delen.append("--- Doorgestuurde mail ---\n%s\n\n%s" % (kop(binnen), lichaam(binnen)))
            continue
        if deel.is_multipart() or not (deel.get_filename() or soort.startswith("image/")):
            continue
        data = deel.get_payload(decode=True) or b""
        naam = deel.get_filename() or "bijlage"
        try:
            if soort.startswith("image/"):
                f = foto(data)
                vingerafdruk = hashlib.sha1(data).hexdigest()
                if f and vingerafdruk not in gezien:
                    gezien.add(vingerafdruk)
                    f["naam"] = re.sub(r"\.\w+$", "", naam) + ".jpg"
                    fotos.append(f)
            elif soort == "application/pdf" or naam.lower().endswith(".pdf"):
                delen.append("--- Bijlage %s ---\n%s" % (naam, pdf_tekst(data)))
            elif naam.lower().endswith(".docx"):
                delen.append("--- Bijlage %s ---\n%s" % (naam, word_tekst(data)))
        except Exception as fout:  # een kapotte bijlage mag de rest niet tegenhouden
            print("  Bijlage %s overgeslagen: %s" % (naam, fout))
    fotos.sort(key=lambda f: f["score"], reverse=True)
    tekst = "\n\n".join(d.strip() for d in delen if d and d.strip())[:MAX_TEKST]
    return afzender, doel, onderwerp, berichtid, tekst, fotos[:MAX_FOTOS]


def toegestaan(afzender):
    lijst = [x.strip().lower() for x in os.environ.get("NIEUWS_AFZENDERS", "nijmegenonline.nl").split(",") if x.strip()]
    return any(afzender == x or afzender.endswith("@" + x) for x in lijst)


# ---------- Mailbox ----------

def verbind():
    host = re.sub(r":\d+$", "", os.environ["NIEUWS_MAIL_SERVER"].strip())
    try:
        m = imaplib.IMAP4_SSL(host, 993, timeout=60)
    except OSError as fout:
        print("Poort 993 lukt niet (%s), nu poort 143 met STARTTLS" % fout)
        m = imaplib.IMAP4(host, 143, timeout=60)
        m.starttls(ssl.create_default_context())
    m.login(os.environ["NIEUWS_MAIL_GEBRUIKER"].strip(), os.environ["NIEUWS_MAIL_WACHTWOORD"])
    return m


def mapnaam(m, naam):
    """Sommige mailservers willen submappen van de inbox als INBOX.Verwerkt; dat volgen we."""
    _, regels = m.list()
    for regel in regels or []:
        r = re.match(r'\(.*?\) "(.)" "?([^"]*)"?$', (regel or b"").decode("utf-8", "replace"))
        if r and r.group(2).upper().startswith("INBOX" + r.group(1)):
            return "INBOX" + r.group(1) + naam
    return naam


def verplaats(m, uid, naar):
    if "MOVE" in m.capabilities:
        m.uid("MOVE", uid, naar)
    else:
        m.uid("COPY", uid, naar)
        m.uid("STORE", uid, "+FLAGS", r"(\Deleted)")
        m.expunge()


def versturen(soort, onderwerp, berichtid, tekst, fotos):
    import base64
    from paginas import GOOGLE_FORM_URL
    gegevens = urllib.parse.urlencode({
        "actie": "nieuws",
        "soort": soort,
        "sleutel": os.environ["NIEUWS_SLEUTEL"],
        "berichtid": berichtid,
        "onderwerp": onderwerp,
        "tekst": tekst,
        "fotos": json.dumps([{"naam": f["naam"], "type": "image/jpeg", "data": base64.b64encode(f["data"]).decode()}
                             for f in fotos]),
    }).encode()
    # Claude schrijft het bericht terwijl we wachten; dat kan een paar minuten duren
    with urllib.request.urlopen(urllib.request.Request(GOOGLE_FORM_URL, data=gegevens), timeout=360) as r:
        antwoord = json.loads(r.read().decode("utf-8"))
    if not antwoord.get("ok"):
        raise RuntimeError("het Google-script weigerde: %s" % antwoord.get("fout"))
    return antwoord


def main():
    if "--bestand" in sys.argv:
        afzender, soort, onderwerp, berichtid, tekst, fotos = lees_mail(open(sys.argv[sys.argv.index("--bestand") + 1], "rb").read())
        print("Van: %s (%s)\nSoort: %s\nOnderwerp: %s\nID: %s\nFoto's: %s\n\n%s" % (
            afzender, "toegestaan" if toegestaan(afzender) else "niet toegestaan", soort, onderwerp, berichtid,
            ", ".join("%s (%d kB)" % (f["naam"], len(f["data"]) // 1024) for f in fotos) or "geen", tekst))
        return
    m = verbind()
    m.select("INBOX")
    _, data = m.uid("SEARCH", None, "ALL")
    uids = data[0].split() if data and data[0] else []
    if "--test" in sys.argv:
        print("Ingelogd. In de inbox staan %d mail(s)." % len(uids))
        print("Mappen: " + ", ".join((r or b"").decode("utf-8", "replace").rsplit(" ", 1)[-1] for r in m.list()[1] or []))
        m.logout()
        return
    verwerkt, genegeerd = mapnaam(m, VERWERKT), mapnaam(m, GENEGEERD)
    for naam in (verwerkt, genegeerd):
        m.create(naam)  # bestaat hij al, dan geeft de server een fout terug en gebeurt er niets
    fouten = 0
    for uid in uids:
        _, inhoud = m.uid("FETCH", uid, "(BODY.PEEK[])")
        ruw = next((x[1] for x in inhoud if isinstance(x, tuple)), b"")
        afzender, soort, onderwerp, berichtid, tekst, fotos = lees_mail(ruw)
        if not toegestaan(afzender):
            print("Genegeerd (afzender %s): %s" % (afzender, onderwerp))
            verplaats(m, uid, genegeerd)
            continue
        try:
            antwoord = versturen(soort, onderwerp, berichtid, tekst, fotos)
        except Exception as fout:  # deze mail blijft in de inbox en komt de volgende keer opnieuw
            print("::warning::Niet verstuurd, volgende keer opnieuw: %s (%s)" % (onderwerp, fout))
            fouten += 1
            continue
        print("Verstuurd (%s): %s (%d foto's)%s" % (soort, onderwerp, len(fotos), " (was er al)" if antwoord.get("dubbel") else ""))
        verplaats(m, uid, verwerkt)
    m.logout()
    print("Nieuwsmails: %d in de inbox, %d niet gelukt" % (len(uids), fouten))
    if fouten and fouten == len(uids):
        sys.exit(1)


if __name__ == "__main__":
    main()
