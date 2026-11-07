/* Webshop NijmegenOnline (tools/webshop.py).
   - Winkelwagen in de browser (localStorage), teller rechtsboven op elke webshoppagina.
   - Afrekenen stuurt de bestelling naar het Google Apps Script (form=bestelling). Dat rekent de prijzen zelf na,
     zet de bestelling in de Sheet en geeft de betaallink van Mollie terug; daarna gaat de klant naar die betaalpagina.
   - De bedankpagina vraagt het script of de betaling binnen is (actie=bestelstatus).
   - Partnerlinks: een klik gaat als "partnerlink" naar Google Analytics. */
(function () {
  var W = window.WEBSHOP || {};
  var SLEUTEL = "no-webshop";

  function lees() {
    try { return JSON.parse(localStorage.getItem(SLEUTEL)) || []; } catch (e) { return []; }
  }
  function bewaar(wagen) {
    try { localStorage.setItem(SLEUTEL, JSON.stringify(wagen)); } catch (e) { /* privévenster: wagen alleen deze pagina */ }
    teller(wagen);
  }
  function teller(wagen) {
    var n = wagen.reduce(function (s, r) { return s + r.aantal; }, 0);
    document.querySelectorAll("[data-webshop-teller]").forEach(function (el) { el.textContent = n; });
  }
  function euro(x) { return "€ " + x.toFixed(2).replace(".", ","); }
  function esc(t) { return String(t).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }
  function meld(el, tekst, fout) { if (!el) return; el.textContent = tekst; el.classList.toggle("fout", !!fout); }
  function sleutel(r) { return r.slug + "|" + JSON.stringify(r.opties); }
  function verzendkosten(wagen, subtotaal) {
    var verzenden = wagen.some(function (r) { return r.verzenden; });
    if (!verzenden || (W.gratisVanaf && subtotaal >= W.gratisVanaf)) return 0;
    return W.verzendkosten || 0;
  }

  teller(lees());

  // In winkelwagen
  document.querySelectorAll("[data-webshop-koop]").forEach(function (form) {
    form.addEventListener("submit", function (ev) {
      ev.preventDefault();
      var opties = {};
      var leeg = null;
      form.querySelectorAll("[data-optie]").forEach(function (veld) {
        var waarde = veld.value.trim();
        if (veld.required && !waarde && !leeg) leeg = veld;
        opties[veld.getAttribute("data-optie")] = waarde;
      });
      var melding = form.querySelector(".webshop-melding");
      if (leeg) { meld(melding, "Vul dit veld in.", true); leeg.focus(); return; }
      var aantal = Math.max(1, Math.min(20, parseInt(form.aantal.value, 10) || 1));
      var wagen = lees();
      var nieuw = { slug: form.dataset.slug, naam: form.dataset.naam, prijs: parseFloat(form.dataset.prijs), opties: opties,
        aantal: aantal, verzenden: form.dataset.verzenden === "1" };
      var bestaand = wagen.filter(function (r) { return sleutel(r) === sleutel(nieuw); })[0];
      if (bestaand) bestaand.aantal = Math.min(20, bestaand.aantal + aantal); else wagen.push(nieuw);
      bewaar(wagen);
      melding.innerHTML = 'Toegevoegd. <a href="' + W.root + 'webshop/winkelwagen/">Naar je winkelwagen</a>';
      melding.classList.remove("fout");
      if (typeof window.gtag === "function") window.gtag("event", "add_to_cart", { currency: "EUR", value: nieuw.prijs * aantal, items: [{ item_id: nieuw.slug, item_name: nieuw.naam, price: nieuw.prijs, quantity: aantal }] });
    });
  });

  // Partnerlinks meten
  document.querySelectorAll("[data-partnerlink]").forEach(function (a) {
    a.addEventListener("click", function () {
      if (typeof window.gtag === "function") window.gtag("event", "partnerlink", { product: a.getAttribute("data-partnerlink"), link_url: a.href });
    });
  });

  // Winkelwagen tonen
  var vak = document.querySelector("[data-webshop-wagen]");
  var afrekenen = document.querySelector("[data-webshop-afrekenen]");
  function toon() {
    var wagen = lees();
    if (!vak) return;
    if (!wagen.length) {
      vak.innerHTML = '<p>Je winkelwagen is leeg. <a href="' + W.root + 'webshop/">Naar de webshop</a></p>';
      if (afrekenen) afrekenen.hidden = true;
      return;
    }
    var subtotaal = wagen.reduce(function (s, r) { return s + r.prijs * r.aantal; }, 0);
    var verzend = verzendkosten(wagen, subtotaal);
    var rijen = wagen.map(function (r, i) {
      var opties = Object.keys(r.opties || {}).filter(function (k) { return r.opties[k]; })
        .map(function (k) { return "<small>" + esc(k) + ": " + esc(r.opties[k]) + "</small>"; }).join("");
      return "<tr><td><a href=\"" + W.root + "webshop/" + esc(r.slug) + "/\">" + esc(r.naam) + "</a>" + opties + "</td>" +
        '<td class="bedrag">' + euro(r.prijs) + "</td>" +
        '<td><input type="number" min="0" max="20" value="' + r.aantal + '" data-rij="' + i + '" aria-label="Aantal"></td>' +
        '<td class="bedrag">' + euro(r.prijs * r.aantal) + '<br><button type="button" data-weg="' + i + '">Verwijderen</button></td></tr>';
    }).join("");
    var gratis = W.gratisVanaf && wagen.some(function (r) { return r.verzenden; }) && verzend
      ? "<small>Gratis verzending vanaf " + euro(W.gratisVanaf) + "</small>" : "";
    vak.innerHTML = '<table class="webshop-wagen"><thead><tr><th>Product</th><th class="bedrag">Prijs</th><th>Aantal</th><th class="bedrag">Totaal</th></tr></thead>' +
      "<tbody>" + rijen + "</tbody><tfoot>" +
      (wagen.some(function (r) { return r.verzenden; }) ? '<tr><td colspan="3">Verzendkosten' + gratis + '</td><td class="bedrag">' + (verzend ? euro(verzend) : "gratis") + "</td></tr>" : "") +
      '<tr><td colspan="3">Totaal (incl. btw)</td><td class="bedrag">' + euro(subtotaal + verzend) + "</td></tr></tfoot></table>";
    if (afrekenen) {
      afrekenen.hidden = false;
      var adres = afrekenen.querySelector("[data-webshop-adres]");
      var verzenden = wagen.some(function (r) { return r.verzenden; });
      adres.hidden = !verzenden;
      adres.querySelectorAll("input").forEach(function (v) { v.required = verzenden; });
    }
  }
  if (vak) {
    toon();
    vak.addEventListener("change", function (ev) {
      var i = ev.target.getAttribute("data-rij");
      if (i === null) return;
      var wagen = lees();
      var n = Math.max(0, Math.min(20, parseInt(ev.target.value, 10) || 0));
      if (n) wagen[i].aantal = n; else wagen.splice(i, 1);
      bewaar(wagen); toon();
    });
    vak.addEventListener("click", function (ev) {
      var i = ev.target.getAttribute("data-weg");
      if (i === null) return;
      var wagen = lees(); wagen.splice(i, 1); bewaar(wagen); toon();
    });
  }

  // Afrekenen
  var geopend = Date.now();
  if (afrekenen) afrekenen.addEventListener("submit", function (ev) {
    ev.preventDefault();
    var melding = afrekenen.querySelector(".webshop-melding");
    var wagen = lees();
    if (!wagen.length) return;
    var pc = afrekenen.postcode;
    if (pc.required) {
      var m = pc.value.trim().toUpperCase().match(/^(\d{4})\s*([A-Z]{2})$/);
      if (!m) { meld(melding, "Controleer de postcode, bijvoorbeeld 6511 AB.", true); pc.focus(); return; }
      pc.value = m[1] + " " + m[2];
    }
    if (!W.url) { meld(melding, "Bestellen kan nog niet. Mail ons je bestelling.", true); return; }
    var gegevens = new URLSearchParams();
    new FormData(afrekenen).forEach(function (waarde, k) { if (typeof waarde === "string") gegevens.append(k, waarde); });
    gegevens.append("form", "bestelling");
    gegevens.append("duur", Date.now() - geopend);
    gegevens.append("regels", JSON.stringify(wagen.map(function (r) { return { slug: r.slug, aantal: r.aantal, opties: r.opties }; })));
    var knop = afrekenen.querySelector('button[type="submit"]');
    knop.disabled = true;
    meld(melding, "Bezig met bestellen...");
    fetch(W.url, { method: "POST", body: gegevens })
      .then(function (r) { return r.json(); })
      .then(function (res) {
        if (!res.ok) throw new Error(res.melding || "Bestellen lukte niet.");
        try { sessionStorage.setItem("no-webshop-laatste", JSON.stringify({ id: res.bestelling, t: res.t, totaal: res.totaal })); } catch (e) { /* geen opslag */ }
        if (typeof window.gtag === "function") window.gtag("event", "begin_checkout", { currency: "EUR", value: res.totaal });
        location.href = res.betaalUrl || (W.root + "webshop/bedankt/?b=" + encodeURIComponent(res.bestelling) + "&t=" + encodeURIComponent(res.t));
      })
      .catch(function (e) {
        meld(melding, (e && e.message && !/fetch|JSON/i.test(e.message) ? e.message : "Bestellen lukte niet.") +
          " Probeer het opnieuw of mail ons.", true);
        knop.disabled = false;
      });
  });

  // Bedankt: status van de betaling
  var bedankt = document.querySelector("[data-webshop-bedankt]");
  if (bedankt) {
    var q = new URLSearchParams(location.search);
    var id = q.get("b"), t = q.get("t");
    if (!id || !t || !W.url) {
      bedankt.innerHTML = "<p>We hebben geen bestelling gevonden. Heb je net betaald? Dan krijg je een bevestiging per e-mail.</p>";
      return;
    }
    var pogingen = 0;
    (function vraag() {
      fetch(W.url + "?actie=bestelstatus&b=" + encodeURIComponent(id) + "&t=" + encodeURIComponent(t))
        .then(function (r) { return r.json(); })
        .then(function (res) {
          if (!res.ok) throw new Error();
          if (res.status === "Betaald" || res.status === "Wacht op betaalverzoek") {
            bewaar([]);
            bedankt.innerHTML = res.status === "Betaald"
              ? "<p><strong>Je betaling is binnen.</strong> Bestelnummer " + esc(id) + ". Je krijgt een bevestiging per e-mail.</p>"
              : "<p><strong>We hebben je bestelling ontvangen</strong> (bestelnummer " + esc(id) + "). Je krijgt binnen een werkdag een betaalverzoek per e-mail.</p>";
            if (res.status === "Betaald" && typeof window.gtag === "function") window.gtag("event", "purchase", { transaction_id: id, currency: "EUR", value: res.totaal });
          } else if (res.status === "Open" && pogingen++ < 5) {
            bedankt.innerHTML = "<p>We wachten nog op de bevestiging van je betaling...</p>";
            setTimeout(vraag, 3000);
          } else {
            bedankt.innerHTML = "<p>Je betaling is nog niet binnen of is afgebroken. Je winkelwagen staat nog klaar.</p>" +
              (res.betaalUrl ? '<p><a class="knop" href="' + esc(res.betaalUrl) + '">Opnieuw betalen</a></p>' : "") +
              '<p><a href="' + W.root + 'webshop/winkelwagen/">Naar je winkelwagen</a></p>';
          }
        })
        .catch(function () {
          bedankt.innerHTML = "<p>We konden de status van je betaling niet ophalen. Je krijgt een bevestiging per e-mail zodra de betaling binnen is.</p>";
        });
    })();
  }
})();
