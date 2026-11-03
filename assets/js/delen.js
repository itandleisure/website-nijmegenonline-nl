// Knop "Deel of kopieer link" op evenementpagina's (tools/agenda.py, delen_html): het deelmenu van de telefoon,
// of anders de link kopiëren.
document.querySelectorAll("[data-delen]").forEach(function (knop) {
  knop.addEventListener("click", function () {
    var url = knop.dataset.delen, titel = knop.dataset.titel;
    if (navigator.share) { navigator.share({ title: titel, url: url }).catch(function () {}); return; }
    var klaar = function () { var oud = knop.textContent; knop.textContent = "Link gekopieerd"; setTimeout(function () { knop.textContent = oud; }, 2000); };
    if (navigator.clipboard) navigator.clipboard.writeText(url).then(klaar, function () { prompt("Kopieer de link:", url); });
    else prompt("Kopieer de link:", url);
  });
});
