// Filters op /vacatures/, samen te gebruiken (tools/vacatures.py zet de data-attributen op elke kaart):
// - knoppen voor soort werk (data-soort)
// - in de regel eronder (besluit Frans, 3-11-2026): zoeken op functie of bedrijf (data-zoek), plaats (data-plaats),
//   dienstverband (data-dienstverband), uren (data-uren: fulltime, parttime en/of weinig), jouw opleiding
//   (data-opleiding: 0 = geen voorkeur t/m 4 = wo; je ziet de vacatures tot en met jouw niveau) en
//   thuiswerken mogelijk (data-thuis).
// ?soort=Horeca, ?plaats=Wijchen, ?dienstverband=Vast, ?uren=parttime, ?opleiding=2, ?thuis=1 en ?zoek=kok in de URL
// zetten een filter meteen aan.
(function () {
  var knoppen = document.querySelectorAll(".vacaturefilter button[data-soort]");
  var meer = document.querySelector(".vacature-meer");
  var keuzes = meer ? meer.querySelectorAll("select[data-filter]") : [];
  var zoekveld = meer ? meer.querySelector("input[data-filter=zoek]") : null;
  var schakel = meer ? meer.querySelector("button[data-extra=thuis]") : null;
  var wis = meer ? meer.querySelector(".agenda-wis") : null;
  var kaarten = document.querySelectorAll(".vacaturelijst .vacaturekaart");
  var uitkomst = document.querySelector(".vacaturefilter__uitkomst");
  if (!kaarten.length) return;
  var NAMEN = ["soort", "plaats", "dienstverband", "uren", "opleiding", "thuis", "zoek"];
  var stand = {};
  NAMEN.forEach(function (n) { stand[n] = ""; });

  function past(k) {
    var d = k.dataset;
    return (!stand.soort || d.soort === stand.soort) && (!stand.plaats || d.plaats === stand.plaats) &&
      (!stand.dienstverband || d.dienstverband === stand.dienstverband) &&
      (!stand.uren || (" " + d.uren + " ").indexOf(" " + stand.uren + " ") >= 0) &&
      (!stand.opleiding || Number(d.opleiding || 0) <= Number(stand.opleiding)) &&
      (!stand.thuis || d.thuis === "1") &&
      (!stand.zoek || stand.zoek.toLowerCase().split(/\s+/).every(function (w) { return d.zoek.indexOf(w) >= 0; }));
  }

  function toepassen() {
    var zichtbaar = 0, aan = NAMEN.some(function (n) { return stand[n]; });
    knoppen.forEach(function (k) { k.setAttribute("aria-pressed", String(k.dataset.soort === stand.soort)); });
    keuzes.forEach(function (s) { s.value = stand[s.dataset.filter]; s.classList.toggle("is-actief", !!s.value); });
    if (schakel) schakel.setAttribute("aria-pressed", String(!!stand.thuis));
    if (zoekveld && zoekveld.value.trim() !== stand.zoek) zoekveld.value = stand.zoek;
    if (wis) wis.hidden = !aan;
    kaarten.forEach(function (k) {
      var ja = past(k);
      k.hidden = !ja;
      if (ja) zichtbaar++;
    });
    if (uitkomst) {
      uitkomst.hidden = !aan;
      uitkomst.textContent = zichtbaar === 0 ? "Geen vacatures gevonden met deze keuze." :
        zichtbaar + (zichtbaar === 1 ? " vacature" : " vacatures") + " gevonden.";
    }
    try {
      var url = new URL(location.href);
      NAMEN.forEach(function (n) { if (stand[n]) url.searchParams.set(n, stand[n]); else url.searchParams.delete(n); });
      history.replaceState(null, "", url);
    } catch (e) { /* oude browser: het filter werkt, alleen de URL blijft gelijk */ }
  }

  document.querySelectorAll(".vacaturefilter").forEach(function (f) { f.hidden = false; });
  if (meer) meer.hidden = false;
  knoppen.forEach(function (k) {
    k.addEventListener("click", function () { stand.soort = k.dataset.soort; toepassen(); });
  });
  keuzes.forEach(function (s) {
    s.addEventListener("change", function () { stand[s.dataset.filter] = s.value; toepassen(); });
  });
  if (zoekveld) zoekveld.addEventListener("input", function () { stand.zoek = zoekveld.value.trim(); toepassen(); });
  if (schakel) schakel.addEventListener("click", function () { stand.thuis = stand.thuis ? "" : "1"; toepassen(); });
  if (wis) wis.addEventListener("click", function () { NAMEN.forEach(function (n) { stand[n] = ""; }); toepassen(); });

  // Filters uit de URL, alleen als die waarde hier ook te kiezen is
  var zoek = new URLSearchParams(location.search);
  NAMEN.forEach(function (n) {
    var w = (zoek.get(n) || "").trim();
    if (!w) return;
    if (n === "zoek" ? !!zoekveld : n === "thuis" ? !!schakel && w === "1" : n === "soort"
        ? Array.prototype.some.call(knoppen, function (k) { return k.dataset.soort === w; })
        : Array.prototype.some.call(keuzes, function (s) {
            return s.dataset.filter === n && Array.prototype.some.call(s.options, function (o) { return o.value === w; });
          })) stand[n] = w;
  });
  if (NAMEN.some(function (n) { return stand[n]; })) toepassen();
})();
