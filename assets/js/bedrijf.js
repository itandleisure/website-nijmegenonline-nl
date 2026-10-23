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
  // Fotocarrousel: pijlen schuiven één foto op; zonder JavaScript kun je gewoon scrollen of vegen
  document.querySelectorAll(".gidsfotos").forEach(function (c) {
    var rij = c.querySelector(".gidsfotos__rij");
    var vorige = c.querySelector(".gidsfotos__pijl--vorige"), volgende = c.querySelector(".gidsfotos__pijl--volgende");
    function stap() { var f = rij.querySelector("img"); return f ? f.getBoundingClientRect().width + 8 : rij.clientWidth; }
    function knoppen() {
      vorige.hidden = rij.scrollLeft < 5;
      volgende.hidden = rij.scrollLeft + rij.clientWidth > rij.scrollWidth - 5;
    }
    vorige.addEventListener("click", function () { rij.scrollBy({ left: -stap(), behavior: "smooth" }); });
    volgende.addEventListener("click", function () { rij.scrollBy({ left: stap(), behavior: "smooth" }); });
    rij.addEventListener("scroll", knoppen, { passive: true });
    window.addEventListener("resize", knoppen);
    knoppen();
  });
})();
