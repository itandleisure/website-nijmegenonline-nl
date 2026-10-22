// Filter op kenmerk in de bedrijvengids (bijv. senioren, hyrox). Een bedrijf blijft staan als het alle gekozen kenmerken heeft.
(function () {
  var blok = document.getElementById("gidsfilter");
  if (!blok) return;
  var knoppen = blok.querySelectorAll("button[data-kenmerk]");
  var uitkomst = blok.querySelector(".gidsfilter__uitkomst");
  var kaarten = document.querySelectorAll(".gids .bedrijflijst .bedrijfkaart");

  function toepassen() {
    var gekozen = [];
    knoppen.forEach(function (k) { if (k.getAttribute("aria-pressed") === "true") gekozen.push(k.dataset.kenmerk); });
    var zichtbaar = 0;
    kaarten.forEach(function (kaart) {
      var eigen = (kaart.dataset.kenmerken || "").split("|");
      var past = gekozen.every(function (k) { return eigen.indexOf(k) !== -1; });
      kaart.hidden = !past;
      if (past) zichtbaar++;
    });
    // Een lijst zonder treffers verdwijnt helemaal, met kop en al
    document.querySelectorAll(".gids .bedrijflijst").forEach(function (lijst) {
      var sectie = lijst.closest(".gids-sectie");
      if (sectie) sectie.hidden = gekozen.length > 0 && !lijst.querySelector(".bedrijfkaart:not([hidden])");
    });
    uitkomst.hidden = gekozen.length === 0;
    uitkomst.innerHTML = zichtbaar === 1 ? "1 sportschool gevonden." : zichtbaar + " sportscholen gevonden.";
    if (gekozen.length) {
      var wis = document.createElement("button");
      wis.type = "button";
      wis.textContent = "Wis filter";
      wis.addEventListener("click", function () {
        knoppen.forEach(function (k) { k.setAttribute("aria-pressed", "false"); });
        toepassen();
      });
      uitkomst.appendChild(document.createTextNode(" "));
      uitkomst.appendChild(wis);
    }
  }

  knoppen.forEach(function (k) {
    k.addEventListener("click", function () {
      k.setAttribute("aria-pressed", k.getAttribute("aria-pressed") === "true" ? "false" : "true");
      toepassen();
    });
  });

  // ?kenmerk=senioren in de link zet het filter meteen aan
  var vooraf = new URLSearchParams(location.search).get("kenmerk");
  if (vooraf) {
    knoppen.forEach(function (k) { if (k.dataset.kenmerk === vooraf) k.setAttribute("aria-pressed", "true"); });
    toepassen();
  }
})();
