// Kaart van de bedrijvengids: Leaflet met OpenStreetMap-tegels, punten die dicht bij elkaar liggen worden een bolletje met een getal.
// Gegevens staan in <script type="application/json" id="kaartdata">:
// {groepen: [...], iconen: {categorie: svg-inhoud}, punten: [[naam, lat, lon, url, adres, groep, categorie, (1, foto bij partners)], ...]}
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
  // Eigen markers in de huisstijl: een groen rondje met het icoon van de categorie, en bolletjes met het aantal
  var iconen = data.iconen || {}, punten = {};
  function svg(inhoud) {
    return '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' + (inhoud || "") + "</svg>";
  }
  function punt(cat) {
    if (!punten[cat]) {
      punten[cat] = L.divIcon({ className: "kaartpunt", html: "<span>" + svg(iconen[cat]) + "</span>", iconSize: [28, 28], iconAnchor: [14, 14], popupAnchor: [0, -12] });
    }
    return punten[cat];
  }
  function bolletje(cluster) {
    var n = cluster.getChildCount();
    var maat = n < 10 ? 34 : n < 50 ? 42 : 50;
    return L.divIcon({ className: "kaartbol", html: "<span>" + n + "</span>", iconSize: [maat, maat] });
  }
  // Per groep: de bolletjes met gratis vermeldingen, en daarboven de partners los en groter
  var bollen = {}, partners = {};
  data.groepen.forEach(function (g) {
    bollen[g] = L.markerClusterGroup({ showCoverageOnHover: false, maxClusterRadius: 45, iconCreateFunction: bolletje });
    partners[g] = L.layerGroup();
    lagen[g] = L.layerGroup([bollen[g], partners[g]]);
  });
  function partnerpunt(p) {
    // Een kaartspeld met de foto van de partner (of een ster als er geen foto is) en een label eronder
    var foto = p[8] ? '<img src="' + p[8].replace(/"/g, "&quot;") + '" alt="" onerror="this.remove()">' : "";
    return L.divIcon({ className: "kaartpartner",
                       html: '<span class="kaartpartner__speld"><span class="kaartpartner__foto">' + foto + '</span></span>' +
                             '<span class="kaartpartner__label">Partner</span>',
                       iconSize: [60, 102], iconAnchor: [30, 68], popupAnchor: [0, -64] });
  }
  data.punten.forEach(function (p) {
    var pop = document.createElement("div");
    var a = document.createElement("a");
    a.href = p[3]; a.textContent = p[0];
    var adres = document.createElement("div");
    adres.textContent = p[4];
    pop.appendChild(a); pop.appendChild(adres);
    if (p[7]) {
      L.marker([p[1], p[2]], { icon: partnerpunt(p), title: p[0], zIndexOffset: 1000 }).bindPopup(pop).addTo(partners[p[5]]);
    } else {
      L.marker([p[1], p[2]], { icon: punt(p[6]), title: p[0] }).bindPopup(pop).addTo(bollen[p[5]]);
    }
  });
  var knoppen = document.getElementById("kaartgroepen");
  function zet(g, aan) {
    if (aan) kaart.addLayer(lagen[g]); else kaart.removeLayer(lagen[g]);
  }
  data.groepen.forEach(function (g, i) {
    zet(g, i === 0);
    if (!knoppen) return;
    var b = document.createElement("button");
    b.type = "button"; b.innerHTML = svg(iconen["groep:" + g]) + " "; b.appendChild(document.createTextNode(g)); b.setAttribute("aria-pressed", i === 0 ? "true" : "false");
    b.onclick = function () {
      var aan = b.getAttribute("aria-pressed") !== "true";
      b.setAttribute("aria-pressed", aan ? "true" : "false");
      zet(g, aan);
    };
    knoppen.appendChild(b);
  });
  // Inzoomen op de gemeente Nijmegen: een paar bedrijven ver weg (verhuisd, hoofdkantoor) zouden de kaart anders tot
  // heel Nederland uitzoomen. Ligt er niets in de gemeente, dan alle punten.
  var alle = data.punten.map(function (p) { return [p[1], p[2]]; });
  var dichtbij = alle.filter(function (p) { return p[0] > 51.78 && p[0] < 51.885 && p[1] > 5.74 && p[1] < 5.94; });
  if (alle.length) {
    var grenzen = L.latLngBounds(dichtbij.length ? dichtbij : alle);
    var zoom = Math.min(15, kaart.getBoundsZoom(grenzen, false, L.point(40, 40)));
    // In de gemeente minstens zoom 12, zodat je de stad ziet en niet de hele regio
    kaart.setView(grenzen.getCenter(), dichtbij.length ? Math.max(zoom, 12) : zoom);
  }
})();
