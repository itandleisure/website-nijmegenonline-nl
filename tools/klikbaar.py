"""Maakt webadressen en e-mailadressen in de tekst van een pagina klikbaar.

In evenementen, nieuws, persberichten en bedrijfsbeschrijvingen staan vaak adressen als gewone tekst, zoals
"Ticketlink: https://debrauerij.nl/event/jeroen-kramer/" of "Mail naar info@voorbeeld.nl". tools/build.py
haalt elke pagina hier doorheen, zodat bestaande en nieuwe teksten vanzelf klikbare links krijgen.

- Alleen tekst binnen <main> (de inhoud van de pagina), niet in menu, zijbalk of footer.
- Tekst die al in een link, knop, script, code of formulierveld staat blijft zoals hij is. Daardoor kan build.py
  vaker draaien zonder dat er links dubbel worden gemaakt.
- Herkend worden adressen die beginnen met http://, https:// of www., en e-mailadressen.
  Losse domeinnamen zonder www. (zoals "debrauerij.nl") niet: dat geeft te veel vergissingen.
- Links naar andere sites openen in een nieuw tabblad met rel="nofollow noopener", net als de andere links
  in teksten die bezoekers zelf aanleveren. Links naar nijmegenonline.nl blijven in hetzelfde tabblad
  (build.py maakt ze daarna relatief). Een oud adres van nijmegenonline.nl dat niet meer bestaat (zoals
  /nieuwsbrief.htm) blijft gewone tekst, zodat er geen dode links bijkomen. E-mailadressen worden een mailto:-link.
"""
import html as html_lib
import re
import urllib.parse

DELEN = re.compile(r"(<!--.*?-->|<[^>]*>)", re.S)
TAG = re.compile(r"<(/?)([a-zA-Z][\w-]*)")
# in deze elementen nooit iets veranderen
OVERSLAAN = {"a", "script", "style", "code", "pre", "textarea", "button", "select", "option", "svg", "noscript",
             "template", "title", "kbd", "samp"}
LEEG = {"br", "img", "hr", "input", "meta", "link", "source", "wbr", "col", "area", "base", "embed", "param", "track"}
# &amp; mag in een adres voorkomen, andere entiteiten (&nbsp; &lt; &quot; ...) sluiten het adres af
TEKEN = r"(?:[^\s<>\"'&]|&amp;)"
ADRES = re.compile(
    r"(?<![\w@/.:-])(?P<url>(?:https?://|www\.)%s+)" % TEKEN
    + r"|(?<![\w.+-])(?P<mail>[\w.+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,})(?![\w-])",
    re.I,
)
EIND = ".,;:!?'\"”’»…"
INTERN = re.compile(r"^https?://(?:www\.)?nijmegenonline\.nl(?:[/?#]|$)", re.I)


def _knip(url):
    """Haalt leestekens aan het eind van het adres af ("zie www.x.nl." of "(https://x.nl)")."""
    rest = ""
    while url:
        if url[-1] in EIND:
            rest, url = url[-1] + rest, url[:-1]
        elif url[-1] == ")" and url.count("(") < url.count(")"):
            rest, url = url[-1] + rest, url[:-1]
        elif url.endswith("&amp;"):
            rest, url = "&amp;" + rest, url[:-5]
        else:
            break
    return url, rest


def _link(m, bestaat=None):
    if m.group("mail"):
        adres = m.group("mail").rstrip(".")
        return '<a href="mailto:%s">%s</a>%s' % (adres, adres, m.group("mail")[len(adres):])
    tekst, rest = _knip(m.group("url"))
    kaal = re.sub(r"^(?:https?://)?", "", tekst, flags=re.I)
    if not re.match(r"[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}(?:[:/?#]|$)", kaal):
        return m.group(0)  # geen geldige domeinnaam, bijvoorbeeld "www." aan het eind van een zin
    href = tekst if re.match(r"https?://", tekst, re.I) else "https://" + tekst
    href = html_lib.escape(html_lib.unescape(href), quote=True)
    if INTERN.match(href):
        if bestaat and not bestaat(urllib.parse.urlsplit(html_lib.unescape(href)).path or "/"):
            return m.group(0)
        return '<a href="%s">%s</a>%s' % (href, tekst, rest)
    return '<a href="%s" target="_blank" rel="nofollow noopener">%s</a>%s' % (href, tekst, rest)


def maak_klikbaar(html, bestaat=None):
    """Geeft de html terug met klikbare adressen in de tekst binnen <main>.

    bestaat(pad) zegt of een pagina van nijmegenonline.nl bestaat; zonder bestaat worden alle interne adressen een link."""
    if "<main" not in html:
        return html
    stukken = DELEN.split(html)
    in_main = False
    overslaan = []
    for i, stuk in enumerate(stukken):
        if i % 2:  # tag of commentaar
            m = TAG.match(stuk)
            if not m:
                continue
            sluit, naam = m.group(1), m.group(2).lower()
            if naam == "main":
                in_main = not sluit
                overslaan = []
            elif naam in OVERSLAAN:
                if sluit:
                    if naam in overslaan:
                        del overslaan[len(overslaan) - 1 - overslaan[::-1].index(naam):]
                elif not stuk.rstrip(">").endswith("/"):
                    overslaan.append(naam)
            continue
        if in_main and not overslaan and ("://" in stuk or "www." in stuk.lower() or "@" in stuk):
            stukken[i] = ADRES.sub(lambda m: _link(m, bestaat), stuk)
    return "".join(stukken)
