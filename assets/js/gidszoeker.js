// Zoekbalk op /bedrijvengids/: zoek een bedrijf op naam, categorie, straat, postcode of plaats (verzoek Frans, 5-11-2026).
// De lijst (data/bedrijven-zoek.json, gemaakt door tools/bedrijvengids.py via tools/koppeling.py) laadt pas als iemand
// het veld aanraakt. Kolommen: sleutel, naam, adres, postcode, plaats, website, categorie.
// Categorieën die bij de zoektekst passen komen uit de lijst "Categorieën" op dezelfde pagina.
// Zonder JavaScript gaat het formulier naar de gewone zoekpagina (zoeken/?q=).
(function () {
  var blok = document.querySelector("[data-gidszoeker]");
  if (!blok) return;
  var SCRIPT = document.currentScript;
  var form = blok.querySelector("form");
  var invoer = blok.querySelector('input[type="search"]');
  var lijst = blok.querySelector(".gidszoeker__lijst");
  var status = blok.querySelector(".gidszoeker__status");
  var MAX = 10;
  var bedrijven = null, laden = null, actief = -1;

  function sleutel(t) {
    return String(t || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();
  }
  var categorieen = [].map.call(document.querySelectorAll(".gidsgroepen a"), function (a) {
    return { naam: a.textContent.trim(), href: a.href, sleutel: sleutel(a.textContent) };
  });
  function laad() {
    if (!laden) {
      laden = fetch(new URL("../../data/bedrijven-zoek.json", SCRIPT.src))
        .then(function (r) { return r.json(); })
        .then(function (rijen) {
          bedrijven = rijen.map(function (r) {
            return { rij: r, naam: sleutel(r[1]), cat: sleutel(r[6]), alles: " " + sleutel([r[1], r[6], r[2], r[3], r[3].replace(/\s/g, ""), r[4]].join(" ")) };
          });
          toon();
        })
        .catch(function () { bedrijven = []; });
    }
    return laden;
  }
  function sluit() {
    lijst.hidden = true;
    invoer.setAttribute("aria-expanded", "false");
    invoer.removeAttribute("aria-activedescendant");
    actief = -1;
  }
  function regel(href, hoofd, onder, extra) {
    var li = document.createElement("li");
    li.setAttribute("role", "option");
    li.id = "gidszoeker-" + lijst.children.length;
    if (extra) li.className = extra;
    var a = document.createElement("a");
    a.href = href;
    a.tabIndex = -1;
    var s = document.createElement("strong");
    s.textContent = hoofd;
    a.appendChild(s);
    if (onder) {
      var sp = document.createElement("span");
      sp.textContent = onder;
      a.appendChild(sp);
    }
    li.appendChild(a);
    lijst.appendChild(li);
  }
  function toon() {
    var q = sleutel(invoer.value);
    var woorden = q.split(" ").filter(Boolean);
    lijst.innerHTML = "";
    if (q.length < 2) { sluit(); status.textContent = ""; return; }
    if (!bedrijven) { laad(); return; }
    // Bedrijven: elk woord moet ergens voorkomen (naam, categorie, adres, postcode of plaats), bij voorkeur aan het begin van een woord
    var treffers = bedrijven.filter(function (b) {
      return woorden.every(function (w) { return b.alles.indexOf(w) !== -1; });
    }).map(function (b) {
      var score = b.naam === q ? 0 : b.naam.indexOf(q) === 0 ? 1 : (" " + b.naam).indexOf(" " + woorden[0]) !== -1 ? 2
        : b.naam.indexOf(woorden[0]) !== -1 ? 3 : b.cat.indexOf(woorden[0]) === 0 ? 4 : 5;
      woorden.forEach(function (w) { if (b.alles.indexOf(" " + w) === -1) score += 2; });
      return { b: b, score: score };
    }).sort(function (x, y) { return x.score - y.score || x.b.naam.localeCompare(y.b.naam); });
    var cats = categorieen.filter(function (c) {
      return woorden.every(function (w) { return (" " + c.sleutel).indexOf(" " + w) !== -1; });
    }).slice(0, 3);
    cats.forEach(function (c) { regel(c.href, c.naam, "Categorie: alle bedrijven", "gidszoeker__cat"); });
    treffers.slice(0, MAX).forEach(function (t) {
      var r = t.b.rij;
      regel(new URL("../../bedrijvengids/" + r[0] + "/", SCRIPT.src).href, r[1],
        [r[6], [r[2], r[4]].filter(Boolean).join(", ")].filter(Boolean).join(" · "));
    });
    if (!treffers.length && !cats.length) {
      var li = document.createElement("li");
      li.className = "gidszoeker__niets";
      li.appendChild(document.createTextNode("Geen bedrijf gevonden. "));
      var a = document.createElement("a");
      a.href = form.action + "?q=" + encodeURIComponent(invoer.value.trim());
      a.textContent = "Zoek op de hele site";
      li.appendChild(a);
      lijst.appendChild(li);
    } else if (treffers.length > MAX) {
      var meer = document.createElement("li");
      meer.className = "gidszoeker__meer";
      meer.textContent = "En nog " + (treffers.length - MAX) + " andere. Typ verder om te verfijnen.";
      lijst.appendChild(meer);
    }
    status.textContent = treffers.length === 1 ? "1 bedrijf gevonden" : treffers.length + " bedrijven gevonden";
    lijst.hidden = false;
    invoer.setAttribute("aria-expanded", "true");
    actief = -1;
  }
  function opties() { return lijst.querySelectorAll('[role="option"]'); }
  function kies(i) {
    var o = opties();
    if (!o.length) return;
    actief = (i + o.length) % o.length;
    o.forEach(function (li, j) { li.setAttribute("aria-selected", j === actief ? "true" : "false"); });
    invoer.setAttribute("aria-activedescendant", o[actief].id);
    o[actief].scrollIntoView({ block: "nearest" });
  }

  invoer.addEventListener("focus", laad);
  invoer.addEventListener("input", toon);
  invoer.addEventListener("keydown", function (e) {
    if (e.key === "ArrowDown") { e.preventDefault(); if (lijst.hidden) toon(); kies(actief + 1); }
    else if (e.key === "ArrowUp") { e.preventDefault(); kies(actief - 1); }
    else if (e.key === "Escape") { sluit(); }
  });
  // Enter: het gekozen (of anders het eerste) resultaat openen; zonder resultaten naar de zoekpagina
  form.addEventListener("submit", function (e) {
    var o = opties();
    var doel = o[actief >= 0 ? actief : 0];
    if (doel && !lijst.hidden) { e.preventDefault(); location.href = doel.querySelector("a").href; }
  });
  document.addEventListener("click", function (e) { if (!blok.contains(e.target)) sluit(); });
})();
