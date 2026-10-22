// Kaart van de bedrijvengids: Leaflet met OpenStreetMap-tegels, punten die dicht bij elkaar liggen worden een bolletje met een getal.
// Gegevens staan in <script type="application/json" id="kaartdata">: {groepen: [...], punten: [[naam, lat, lon, url, adres, groep], ...]}
(function () {
  var el = document.getElementById("gidskaart");
  var bron = document.getElementById("kaartdata");
  if (!el || !bron || !window.L) return;
  var data = JSON.parse(bron.textContent);
  var kaart = L.map(el, { scrollWheelZoom: false }).setView([51.8426, 5.8528], 13);
  L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap-bijdragers</a>'
  }).addTo(kaart);
  var lagen = {};
  data.groepen.forEach(function (g) { lagen[g] = L.markerClusterGroup({ showCoverageOnHover: false, maxClusterRadius: 45 }); });
  data.punten.forEach(function (p) {
    var pop = document.createElement("div");
    var a = document.createElement("a");
    a.href = p[3]; a.textContent = p[0];
    var adres = document.createElement("div");
    adres.textContent = p[4];
    pop.appendChild(a); pop.appendChild(adres);
    L.marker([p[1], p[2]]).bindPopup(pop).addTo(lagen[p[5]]);
  });
  var knoppen = document.getElementById("kaartgroepen");
  function zet(g, aan) {
    if (aan) kaart.addLayer(lagen[g]); else kaart.removeLayer(lagen[g]);
  }
  data.groepen.forEach(function (g, i) {
    zet(g, i === 0);
    if (!knoppen) return;
    var b = document.createElement("button");
    b.type = "button"; b.textContent = g; b.setAttribute("aria-pressed", i === 0 ? "true" : "false");
    b.onclick = function () {
      var aan = b.getAttribute("aria-pressed") !== "true";
      b.setAttribute("aria-pressed", aan ? "true" : "false");
      zet(g, aan);
    };
    knoppen.appendChild(b);
  });
  if (data.punten.length) {
    kaart.fitBounds(data.punten.map(function (p) { return [p[1], p[2]]; }), { padding: [20, 20], maxZoom: 15 });
  }
})();
