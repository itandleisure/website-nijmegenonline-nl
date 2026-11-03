// Filters op /vacatures/: soort werk en plaats, samen te gebruiken (tools/vacatures.py zet data-soort en data-plaats
// op elke kaart). ?soort=Horeca en ?plaats=Wijchen in de URL zetten een filter meteen aan.
(function () {
  var filters = document.querySelectorAll(".vacaturefilter");
  if (!filters.length) return;
  var kaarten = document.querySelectorAll(".vacaturelijst .vacaturekaart");
  var uitkomst = document.querySelector(".vacaturefilter__uitkomst");
  var stand = { soort: "", plaats: "" };

  function toepassen() {
    var zichtbaar = 0;
    document.querySelectorAll(".vacaturefilter button").forEach(function (k) {
      var naam = "soort" in k.dataset ? "soort" : "plaats";
      k.setAttribute("aria-pressed", String(k.dataset[naam] === stand[naam]));
    });
    kaarten.forEach(function (kaart) {
      var past = (!stand.soort || kaart.dataset.soort === stand.soort) && (!stand.plaats || kaart.dataset.plaats === stand.plaats);
      kaart.hidden = !past;
      if (past) zichtbaar++;
    });
    var gefilterd = !!(stand.soort || stand.plaats);
    if (uitkomst) {
      uitkomst.hidden = !gefilterd;
      uitkomst.textContent = zichtbaar === 0 ? "Geen vacatures gevonden met deze keuze." :
        zichtbaar + (zichtbaar === 1 ? " vacature" : " vacatures") + " gevonden.";
    }
    try {
      var url = new URL(location.href);
      ["soort", "plaats"].forEach(function (n) { if (stand[n]) url.searchParams.set(n, stand[n]); else url.searchParams.delete(n); });
      history.replaceState(null, "", url);
    } catch (e) { /* oude browser: het filter werkt, alleen de URL blijft gelijk */ }
  }

  filters.forEach(function (f) {
    f.hidden = false;
    f.querySelectorAll("button").forEach(function (k) {
      k.addEventListener("click", function () {
        var naam = "soort" in k.dataset ? "soort" : "plaats";
        stand[naam] = k.dataset[naam];
        toepassen();
      });
    });
  });
  var zoek = new URLSearchParams(location.search);
  ["soort", "plaats"].forEach(function (n) {
    var w = zoek.get(n);
    if (w && document.querySelector('.vacaturefilter button[data-' + n + '="' + w.replace(/"/g, "") + '"]')) stand[n] = w;
  });
  if (stand.soort || stand.plaats) toepassen();
})();
