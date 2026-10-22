// Bedrijfspagina in de gids: weergave en kliks (website, telefoon, route, actieknop) naar Google Analytics,
// voor het rapport aan betalende bedrijven. Doet niets als gtag er niet is.
(function () {
  var script = document.currentScript;
  var bedrijf = script && script.getAttribute("data-bedrijf");
  function meld(actie, extra) {
    if (typeof window.gtag !== "function") return;
    var gegevens = { bedrijf: bedrijf };
    for (var k in extra || {}) gegevens[k] = extra[k];
    window.gtag("event", actie, gegevens);
  }
  meld("bedrijf_bekeken");
  document.querySelectorAll("[data-klik]").forEach(function (a) {
    a.addEventListener("click", function () { meld("bedrijf_klik", { soort: a.getAttribute("data-klik") }); });
  });
})();
