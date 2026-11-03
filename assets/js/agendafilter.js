// Filters in de agenda, samen te gebruiken:
// - op datum: vandaag, morgen, dit weekend of de komende 7 dagen. Een evenement blijft staan als het op een van die
//   dagen loopt (data-van t/m data-tot op de kaart). De uitgelichte evenementen bovenaan blijven daarbij staan.
// - in de regel eronder (tools/agenda.py, meerfilter): een keuzelijst voor plaats (besluit Frans, 2-11-2026) en
//   voor soort, en aan/uit-knoppen Gratis (ook vrije gift) en Leuk voor kinderen (besluit Frans, 3-11-2026).
//   Op de kaart: data-plaats, data-soort, data-gratis en data-kinderen; ook de uitgelichte kaarten.
// ?wanneer=weekend, ?plaats=Wijchen, ?soort=Muziek, ?gratis=1 en ?kinderen=1 in de URL zetten een filter meteen aan;
// de plaatspagina's linken zo hierheen.
(function () {
  var blok = document.getElementById("agendafilter");
  if (!blok) return;
  var knoppen = blok.querySelectorAll("button[data-wanneer]");
  var meer = document.querySelector(".agenda-meer");
  var keuzes = meer ? meer.querySelectorAll("select[data-filter]") : [];
  var schakels = meer ? meer.querySelectorAll("button[data-extra]") : [];
  var wis = meer ? meer.querySelector(".agenda-wis") : null;
  var uitkomst = document.querySelector(".agendafilter__uitkomst");
  var kaarten = document.querySelectorAll(".agenda-maand .eventkaart");
  var uitgelicht = document.querySelectorAll(".agenda-uitgelicht .uitgelicht");
  var stand = { wanneer: "", plaats: "", soort: "", gratis: false, kinderen: false };

  function iso(d) {
    return d.getFullYear() + "-" + ("0" + (d.getMonth() + 1)).slice(-2) + "-" + ("0" + d.getDate()).slice(-2);
  }
  function plus(d, n) { var x = new Date(d); x.setDate(x.getDate() + n); return x; }

  function bereik(wanneer) {
    var nu = new Date(); nu.setHours(12, 0, 0, 0);
    if (wanneer === "vandaag") return [nu, nu];
    if (wanneer === "morgen") return [plus(nu, 1), plus(nu, 1)];
    if (wanneer === "week") return [nu, plus(nu, 6)];
    if (wanneer === "weekend") {
      var dag = nu.getDay(); // 0 = zondag, 5 = vrijdag, 6 = zaterdag
      if (dag === 0) return [nu, nu];
      if (dag === 6) return [nu, plus(nu, 1)];
      var vrijdag = plus(nu, 5 - dag);
      return [dag === 5 ? nu : vrijdag, plus(vrijdag, 2)];
    }
    return null;
  }

  // Plaats, soort, gratis en kinderen gelden voor alle kaarten, ook de uitgelichte
  function pastMeer(kaart) {
    return (!stand.plaats || kaart.dataset.plaats === stand.plaats) && (!stand.soort || kaart.dataset.soort === stand.soort) &&
      (!stand.gratis || kaart.dataset.gratis === "1") && (!stand.kinderen || kaart.dataset.kinderen === "1");
  }

  function toepassen() {
    var r = bereik(stand.wanneer), van = r && iso(r[0]), tot = r && iso(r[1]), zichtbaar = 0;
    var meerAan = !!stand.plaats || !!stand.soort || stand.gratis || stand.kinderen;
    knoppen.forEach(function (k) { k.setAttribute("aria-pressed", String(k.dataset.wanneer === stand.wanneer)); });
    keuzes.forEach(function (s) { s.value = stand[s.dataset.filter]; s.classList.toggle("is-actief", !!s.value); });
    schakels.forEach(function (k) { k.setAttribute("aria-pressed", String(stand[k.dataset.extra])); });
    if (wis) wis.hidden = !meerAan && !r;
    kaarten.forEach(function (kaart) {
      var past = (!r || (kaart.dataset.van <= tot && kaart.dataset.tot >= van)) && pastMeer(kaart);
      kaart.hidden = !past;
      if (past) zichtbaar++;
    });
    uitgelicht.forEach(function (kaart) { kaart.hidden = !pastMeer(kaart); });
    document.querySelectorAll(".agenda-maand").forEach(function (sectie) {
      sectie.hidden = (!!r || meerAan) && !sectie.querySelector(".eventkaart:not([hidden])");
    });
    document.querySelectorAll(".agenda-uitgelicht").forEach(function (sectie) {
      sectie.hidden = meerAan && !sectie.querySelector(".uitgelicht:not([hidden])");
    });
    var gefilterd = !!r || meerAan;
    if (uitkomst) {
      uitkomst.hidden = !gefilterd;
      if (gefilterd) uitkomst.textContent = zichtbaar === 0 ? "Geen evenementen gevonden. Probeer een ander filter."
        : zichtbaar + (zichtbaar === 1 ? " evenement" : " evenementen") + " gevonden.";
    }
    try {
      var url = new URL(location.href);
      ["wanneer", "plaats", "soort"].forEach(function (x) { if (stand[x]) url.searchParams.set(x, stand[x]); else url.searchParams.delete(x); });
      ["gratis", "kinderen"].forEach(function (x) { if (stand[x]) url.searchParams.set(x, "1"); else url.searchParams.delete(x); });
      history.replaceState(null, "", url);
    } catch (e) { /* oude browser: filter werkt, alleen de URL blijft gelijk */ }
  }

  knoppen.forEach(function (k) { k.addEventListener("click", function () { stand.wanneer = k.dataset.wanneer; toepassen(); }); });
  keuzes.forEach(function (s) { s.addEventListener("change", function () { stand[s.dataset.filter] = s.value; toepassen(); }); });
  schakels.forEach(function (k) { k.addEventListener("click", function () { stand[k.dataset.extra] = !stand[k.dataset.extra]; toepassen(); }); });
  if (wis) wis.addEventListener("click", function () {
    stand = { wanneer: "", plaats: "", soort: "", gratis: false, kinderen: false };
    toepassen();
  });
  if (meer) meer.hidden = false;

  var zoek = new URLSearchParams(location.search);
  var wanneer = zoek.get("wanneer");
  if (wanneer && bereik(wanneer)) stand.wanneer = wanneer;
  keuzes.forEach(function (s) {
    var w = zoek.get(s.dataset.filter);
    if (w && Array.prototype.some.call(s.options, function (o) { return o.value === w; })) stand[s.dataset.filter] = w;
  });
  schakels.forEach(function (k) { if (zoek.get(k.dataset.extra) === "1") stand[k.dataset.extra] = true; });
  if (stand.wanneer || stand.plaats || stand.soort || stand.gratis || stand.kinderen) toepassen();
})();
