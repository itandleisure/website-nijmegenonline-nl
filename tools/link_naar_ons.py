"""Pagina /link-naar-ons/: bedrijven uit de bedrijvengids halen hier een badge of tekstlink voor hun eigen website.

Met ?bedrijf=<slug> staat het bedrijf al gekozen en wijst de code naar zijn eigen pagina in de gids; die link staat
in de mail aan de bedrijven en op elke bedrijfspagina (knop bij "Is dit jouw bedrijf?"). Bedrijven uit een top-lijst
(data/badge-aanraders.json, tools/badges.py) krijgen ook de groene badge "Aanrader van NijmegenOnline", met een link
naar die lijst.

De link is een vriendelijk verzoek, geen voorwaarde: een vermelding blijft gratis, ook zonder link. Google ziet een
verplichte link in ruil voor een vermelding als linkruil; een vrijwillige badge is een gewone, natuurlijke link.

Gebruik: python tools/badges.py && python tools/link_naar_ons.py && python tools/build.py
"""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from paginas import EMAIL, pagina  # noqa: E402

STIJL = """
  <style>
    .badgekeuze { display: grid; gap: 12px; margin: 12px 0 20px; }
    .badgekeuze label { display: flex; align-items: center; gap: 14px; padding: 12px; border: 2px solid var(--rand); border-radius: var(--radius); cursor: pointer; background: var(--wit); }
    .badgekeuze label:has(input:checked) { border-color: var(--blauw); background: var(--licht); }
    .badgekeuze img { width: 200px; height: auto; flex: none; }
    .badgekeuze span { font-size: 0.95em; }
    @media (max-width: 600px) { .badgekeuze label { flex-wrap: wrap; } .badgekeuze span { flex: 1 1 100%; } }
    .badgecode { width: 100%; min-height: 110px; font: 13px/1.45 ui-monospace, Menlo, Consolas, monospace; padding: 10px; border: 1px solid var(--rand); border-radius: var(--radius); background: var(--licht); }
    .badgezoek input { width: 100%; padding: 11px 14px; font: inherit; border: 1px solid var(--rand); border-radius: 999px; }
    .badgezoek ul { list-style: none; padding: 0; margin: 8px 0 0; }
    .badgezoek li button { all: unset; cursor: pointer; display: block; padding: 8px 12px; border-radius: 8px; }
    .badgezoek li button:hover, .badgezoek li button:focus { background: var(--licht); }
    .badgegekozen { padding: 12px 16px; background: var(--licht); border-radius: var(--radius); }
    .badgevoorbeeld { padding: 16px; border: 1px dashed var(--rand); border-radius: var(--radius); margin: 8px 0 12px; }
    .knop--licht { background: var(--blauw); box-shadow: none; border: 0; cursor: pointer; font: inherit; font-weight: 700; }
  </style>"""

INHOUD = """        <h1>Laat zien dat je op NijmegenOnline staat</h1>
        <div class="inhoud-tekst">
          <p>Staat je bedrijf in de <a href="../bedrijvengids/">bedrijvengids</a>? Laat het zien op je eigen website, met een badge of een gewone link. Bezoekers zien dat je in Nijmegen bekend bent, en met één klik komen ze bij je vermelding met adres, openingstijden en kaart.</p>
          <p>Je vermelding is en blijft gratis, ook zonder link. Maar een link naar ons waarderen we enorm: zo kunnen we de gids gratis houden voor alle Nijmeegse ondernemers.</p>

          <h2>1. Kies je bedrijf</h2>
          <div class="badgegekozen" id="gekozen" hidden></div>
          <div class="badgezoek" id="zoekblok">
            <label for="badgezoek">Naam van je bedrijf</label>
            <input id="badgezoek" type="search" placeholder="Bijvoorbeeld: Harbor Gym" autocomplete="off">
            <ul id="badgeresultaten"></ul>
          </div>

          <h2>2. Kies een badge</h2>
          <div class="badgekeuze" id="badgekeuze">
            <label><input type="radio" name="badge" value="te-vinden-op-nijmegenonline" checked> <img src="../assets/img/badge/te-vinden-op-nijmegenonline.png" alt="Te vinden op NijmegenOnline" width="200" height="73"> <span>Blauw, past op de meeste sites</span></label>
            <label><input type="radio" name="badge" value="te-vinden-op-nijmegenonline-licht"> <img src="../assets/img/badge/te-vinden-op-nijmegenonline-licht.png" alt="Te vinden op NijmegenOnline" width="200" height="73"> <span>Licht, voor een donkere of drukke achtergrond</span></label>
            <label id="keuzeaanrader" hidden><input type="radio" name="badge" value="aanrader-van-nijmegenonline"> <img src="../assets/img/badge/aanrader-van-nijmegenonline.png" alt="Aanrader van NijmegenOnline" width="200" height="73"> <span id="aanradertekst">Je staat in een van onze top-lijsten</span></label>
            <label><input type="radio" name="badge" value="tekst"> <span><strong>Alleen een tekstlink</strong>, zonder plaatje</span></label>
          </div>

          <h2>3. Kopieer de code</h2>
          <p>Zo ziet het eruit:</p>
          <div class="badgevoorbeeld" id="voorbeeld"></div>
          <label for="badgecode">Code voor je website</label>
          <textarea class="badgecode" id="badgecode" readonly></textarea>
          <p><button type="button" class="knop knop--licht" id="kopieer">Kopieer de code</button> <span id="gekopieerd" role="status"></span></p>

          <h2>Waar zet je de code?</h2>
          <ul>
            <li><strong>WordPress</strong>: voeg in de footer of op je contactpagina een blok <em>Aangepaste HTML</em> toe en plak de code erin.</li>
            <li><strong>Wix, Squarespace, Jimdo, Shopify</strong>: gebruik een blok voor HTML of code, of zet de afbeelding los op je site en koppel hem aan het adres van je vermelding (<span id="adres">je pagina in de bedrijvengids</span>).</li>
            <li><strong>Een webbouwer</strong>: stuur hem deze pagina door, dan is het zo geregeld.</li>
          </ul>
          <p>De afbeeldingen los downloaden: <a href="../assets/img/badge/te-vinden-op-nijmegenonline.png" download>blauw</a>, <a href="../assets/img/badge/te-vinden-op-nijmegenonline-licht.png" download>licht</a>, <a href="../assets/img/badge/aanrader-van-nijmegenonline.png" download>aanrader</a>.</p>

          <h2>Vragen</h2>
          <ul>
            <li><strong>Moet ik linken om in de gids te blijven?</strong> Nee. Je vermelding blijft gratis staan, met of zonder link.</li>
            <li><strong>Klopt je vermelding niet meer?</strong> Pas hem aan via de knop <em>Dit is mijn bedrijf</em> op je pagina in de gids, of mail naar <a href="mailto:{email}">{email}</a>.</li>
            <li><strong>Niet gevonden?</strong> Dan sta je nog niet in de gids. <a href="../bedrijf-aanmelden/">Meld je bedrijf gratis aan</a>.</li>
          </ul>
        </div>
        <script>
        (function () {{
          var SITE = "https://www.nijmegenonline.nl/";
          var bedrijf = null, aanraders = {{}}, alle = null;
          var $ = function (id) {{ return document.getElementById(id); }};
          function esc(t) {{ return String(t).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;"); }}
          function code() {{
            var soort = document.querySelector('input[name="badge"]:checked').value;
            var naam = bedrijf ? bedrijf.naam : "";
            var href = bedrijf ? SITE + "bedrijvengids/" + bedrijf.slug + "/" : SITE + "bedrijvengids/";
            var lijst = bedrijf && aanraders[bedrijf.slug] ? aanraders[bedrijf.slug][0] : null;
            if (soort === "tekst") {{
              return '<a href="' + href + '">' + (naam ? esc(naam) + " op NijmegenOnline" : "Bekijk ons op NijmegenOnline") + "</a>";
            }}
            var alt = naam ? esc(naam) + " is te vinden op NijmegenOnline" : "Te vinden op NijmegenOnline";
            if (soort === "aanrader-van-nijmegenonline" && lijst) {{
              href = lijst.url;
              alt = esc(naam) + ": aanrader in " + esc(lijst.titel) + " op NijmegenOnline";
            }}
            return '<a href="' + href + '"><img src="' + SITE + "assets/img/badge/" + soort + '.png" alt="' + alt + '" width="200" height="73"></a>';
          }}
          function toon() {{
            var c = code();
            $("badgecode").value = c;
            $("voorbeeld").innerHTML = c.replace(/<a /, '<a target="_blank" rel="noopener" ');
            $("adres").textContent = bedrijf ? SITE + "bedrijvengids/" + bedrijf.slug + "/" : "je pagina in de bedrijvengids";
          }}
          function kies(b) {{
            bedrijf = b;
            var lijst = aanraders[b.slug];
            $("gekozen").hidden = false;
            $("gekozen").innerHTML = "<strong>" + esc(b.naam) + "</strong> · " + esc(b.categorie) + ' · <a href="../bedrijvengids/' + b.slug + '/">bekijk je vermelding</a> · <button type="button" class="knop--licht" style="all:unset;cursor:pointer;text-decoration:underline" id="ander">ander bedrijf</button>';
            $("ander").onclick = function () {{ bedrijf = null; $("gekozen").hidden = true; $("zoekblok").hidden = false; $("keuzeaanrader").hidden = true; toon(); $("badgezoek").focus(); }};
            $("zoekblok").hidden = true;
            $("keuzeaanrader").hidden = !lijst;
            if (lijst) {{
              $("aanradertekst").textContent = "Je staat in " + lijst.map(function (l) {{ return l.titel; }}).join(" en ") + ". Deze badge linkt naar die lijst.";
              $("keuzeaanrader").querySelector("input").checked = true;
            }} else if (document.querySelector('input[name="badge"]:checked').value === "aanrader-van-nijmegenonline") {{
              document.querySelector('input[name="badge"]').checked = true;
            }}
            toon();
          }}
          function laadBedrijven() {{
            if (alle) return Promise.resolve(alle);
            return fetch("../data/bedrijven-zoek.json").then(function (r) {{ return r.json(); }}).then(function (rijen) {{
              alle = rijen.map(function (r) {{ return {{ slug: r[0], naam: r[1], plaats: r[4], categorie: r[6] }}; }});
              return alle;
            }});
          }}
          $("badgezoek").addEventListener("input", function () {{
            var q = this.value.trim().toLowerCase();
            laadBedrijven().then(function (lijst) {{
              var ul = $("badgeresultaten");
              ul.innerHTML = "";
              if (q.length < 2) return;
              lijst.filter(function (b) {{ return b.naam.toLowerCase().indexOf(q) > -1; }}).slice(0, 8).forEach(function (b) {{
                var li = document.createElement("li"), knop = document.createElement("button");
                knop.type = "button";
                knop.innerHTML = "<strong>" + esc(b.naam) + "</strong> · " + esc(b.categorie) + ", " + esc(b.plaats);
                knop.onclick = function () {{ ul.innerHTML = ""; kies(b); }};
                li.appendChild(knop);
                ul.appendChild(li);
              }});
            }});
          }});
          document.querySelectorAll('input[name="badge"]').forEach(function (r) {{ r.addEventListener("change", toon); }});
          $("kopieer").onclick = function () {{
            var veld = $("badgecode");
            veld.select();
            (navigator.clipboard ? navigator.clipboard.writeText(veld.value) : Promise.reject()).catch(function () {{ document.execCommand("copy"); }});
            $("gekopieerd").textContent = "Gekopieerd!";
            setTimeout(function () {{ $("gekopieerd").textContent = ""; }}, 2500);
          }};
          toon();
          var slug = new URLSearchParams(location.search).get("bedrijf");
          fetch("../data/badge-aanraders.json").then(function (r) {{ return r.json(); }}).catch(function () {{ return {{}}; }}).then(function (a) {{
            aanraders = a;
            if (!slug) return;
            laadBedrijven().then(function (lijst) {{
              var b = lijst.filter(function (x) {{ return x.slug === slug; }})[0];
              if (b) kies(b);
            }});
          }});
        }})();
        </script>""".format(email=EMAIL)


def main():
    beschrijving = ("Sta je in de bedrijvengids van NijmegenOnline? Zet een badge of link op je eigen website. "
                    "Kies je bedrijf en kopieer de code.")
    html = pagina("Laat zien dat je op NijmegenOnline staat", beschrijving, "link-naar-ons", "Link naar ons", INHOUD,
                  extra=STIJL)
    d = ROOT / "link-naar-ons"
    d.mkdir(exist_ok=True)
    (d / "index.html").write_text(html, encoding="utf-8")
    print("link-naar-ons/ geschreven")


if __name__ == "__main__":
    main()
