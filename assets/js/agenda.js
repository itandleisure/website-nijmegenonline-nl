// Agenda: filteren op plaats (tools/agenda.py zet data-plaats op elke kaart). ?plaats=Wijchen in de url kiest
// de plaats meteen, zodat de plaatspagina's ernaar kunnen linken. Zonder JavaScript blijft de hele agenda staan.
(function () {
  var nav = document.querySelector(".agenda-plaatsen");
  if (!nav) return;
  var knoppen = nav.querySelectorAll("button");
  var leeg = document.querySelector(".agenda-leeg");
  function kies(plaats) {
    var gevonden = false;
    knoppen.forEach(function (k) { k.setAttribute("aria-pressed", String(k.dataset.plaats === plaats)); });
    document.querySelectorAll(".eventkaart[data-plaats], .uitgelicht[data-plaats]").forEach(function (kaart) {
      kaart.hidden = !!plaats && kaart.dataset.plaats !== plaats;
    });
    // Maanden en blokken zonder zichtbare kaart verbergen
    document.querySelectorAll(".agenda-maand, .agenda-uitgelicht").forEach(function (blok) {
      var zichtbaar = Array.prototype.some.call(blok.querySelectorAll("[data-plaats]"), function (k) { return !k.hidden; });
      blok.hidden = !zichtbaar;
      gevonden = gevonden || zichtbaar;
    });
    if (leeg) leeg.hidden = gevonden || !plaats;
    var url = new URL(location.href);
    if (plaats) url.searchParams.set("plaats", plaats); else url.searchParams.delete("plaats");
    history.replaceState(null, "", url);
  }
  knoppen.forEach(function (k) {
    k.addEventListener("click", function () { kies(k.dataset.plaats); });
  });
  nav.hidden = false;
  var gevraagd = new URLSearchParams(location.search).get("plaats");
  if (gevraagd && Array.prototype.some.call(knoppen, function (k) { return k.dataset.plaats === gevraagd; })) kies(gevraagd);
})();
