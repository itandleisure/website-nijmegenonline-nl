// Filters in de agenda, samen te gebruiken:
// - op datum: vandaag, morgen, dit weekend of de komende 7 dagen. Een evenement blijft staan als het op een van die
//   dagen loopt (data-van t/m data-tot op de kaart). De uitgelichte evenementen bovenaan blijven daarbij staan.
// - op plaats (besluit Frans, 2-11-2026): Nijmegen, Wijchen, Kleef, ... (data-plaats op de kaart, ook de uitgelichte).
// - op soort (Muziek, Expositie, ...), en Gratis (ook vrije gift) en Leuk voor kinderen als aan/uit-knoppen
//   (data-soort, data-gratis en data-kinderen op de kaart; indeling in tools/evenement_indeling.py).
// ?wanneer=weekend, ?plaats=Wijchen, ?soort=Muziek, ?gratis=1 en ?kinderen=1 in de URL zetten een filter meteen aan; de plaatspagina's linken zo hierheen.
(function () {
  var blok = document.getElementById("agendafilter");
  if (!blok) return;
  var knoppen = blok.querySelectorAll("button[data-wanneer]");
  var uitkomst = blok.querySelector(".agendafilter__uitkomst");
  var plaatsNav = document.querySelector(".agenda-plaatsen");
  var plaatsKnoppen = plaatsNav ? plaatsNav.querySelectorAll("button[data-plaats]") : [];
  var soortNav = document.querySelector(".agenda-soorten");
  var soortKnoppen = soortNav ? soortNav.querySelectorAll("button[data-soort]") : [];
  var extraNav = document.querySelector(".agenda-extra");
  var extraKnoppen = extraNav ? extraNav.querySelectorAll("button[data-extra]") : [];
  var kaarten = document.querySelectorAll(".agenda-maand .eventkaart");
  var uitgelicht = document.querySelectorAll(".agenda-uitgelicht .uitgelicht");
  var stand = { wanneer: "", plaats: "", soort: "", gratis: false, kinderen: false };

  // Soort, gratis en kinderen gelden voor alle kaarten, ook de uitgelichte
  function pastSoort(kaart) {
    return (!stand.soort || kaart.dataset.soort === stand.soort) && (!stand.gratis || kaart.dataset.gratis === "1") &&
      (!stand.kinderen || kaart.dataset.kinderen === "1");
  }

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

  function toepassen() {
    var r = bereik(stand.wanneer), van = r && iso(r[0]), tot = r && iso(r[1]), plaats = stand.plaats, zichtbaar = 0;
    var soortAan = !!stand.soort || stand.gratis || stand.kinderen;
    knoppen.forEach(function (k) { k.setAttribute("aria-pressed", String(k.dataset.wanneer === stand.wanneer)); });
    plaatsKnoppen.forEach(function (k) { k.setAttribute("aria-pressed", String(k.dataset.plaats === plaats)); });
    soortKnoppen.forEach(function (k) { k.setAttribute("aria-pressed", String(k.dataset.soort === stand.soort)); });
    extraKnoppen.forEach(function (k) { k.setAttribute("aria-pressed", String(stand[k.dataset.extra])); });
    kaarten.forEach(function (kaart) {
      var past = (!r || (kaart.dataset.van <= tot && kaart.dataset.tot >= van)) && (!plaats || kaart.dataset.plaats === plaats) && pastSoort(kaart);
      kaart.hidden = !past;
      if (past) zichtbaar++;
    });
    uitgelicht.forEach(function (kaart) { kaart.hidden = (!!plaats && kaart.dataset.plaats !== plaats) || !pastSoort(kaart); });
    document.querySelectorAll(".agenda-maand").forEach(function (sectie) {
      sectie.hidden = (!!r || !!plaats || soortAan) && !sectie.querySelector(".eventkaart:not([hidden])");
    });
    document.querySelectorAll(".agenda-uitgelicht").forEach(function (sectie) {
      sectie.hidden = (!!plaats || soortAan) && !sectie.querySelector(".uitgelicht:not([hidden])");
    });
    var gefilterd = !!r || !!plaats || soortAan;
    uitkomst.hidden = !gefilterd;
    if (gefilterd) uitkomst.textContent = zichtbaar === 0 ? "Geen evenementen gevonden" + (plaats ? " in " + plaats : "") +
      (r ? " voor deze periode." : ".") + (soortAan ? " Probeer een ander filter." : "") : zichtbaar + (zichtbaar === 1 ? " evenement" : " evenementen") + " gevonden.";
    try {
      var url = new URL(location.href);
      if (stand.wanneer) url.searchParams.set("wanneer", stand.wanneer); else url.searchParams.delete("wanneer");
      if (plaats) url.searchParams.set("plaats", plaats); else url.searchParams.delete("plaats");
      if (stand.soort) url.searchParams.set("soort", stand.soort); else url.searchParams.delete("soort");
      ["gratis", "kinderen"].forEach(function (x) { if (stand[x]) url.searchParams.set(x, "1"); else url.searchParams.delete(x); });
      history.replaceState(null, "", url);
    } catch (e) { /* oude browser: filter werkt, alleen de URL blijft gelijk */ }
  }

  knoppen.forEach(function (k) { k.addEventListener("click", function () { stand.wanneer = k.dataset.wanneer; toepassen(); }); });
  plaatsKnoppen.forEach(function (k) { k.addEventListener("click", function () { stand.plaats = k.dataset.plaats; toepassen(); }); });
  soortKnoppen.forEach(function (k) { k.addEventListener("click", function () { stand.soort = k.dataset.soort; toepassen(); }); });
  extraKnoppen.forEach(function (k) { k.addEventListener("click", function () { stand[k.dataset.extra] = !stand[k.dataset.extra]; toepassen(); }); });
  if (plaatsNav) plaatsNav.hidden = false;
  if (soortNav) soortNav.hidden = false;
  if (extraNav) extraNav.hidden = false;
  var zoek = new URLSearchParams(location.search);
  var wanneer = zoek.get("wanneer"), plaats = zoek.get("plaats");
  if (wanneer && bereik(wanneer)) stand.wanneer = wanneer;
  if (plaats && Array.prototype.some.call(plaatsKnoppen, function (k) { return k.dataset.plaats === plaats; })) stand.plaats = plaats;
  var soort = zoek.get("soort");
  if (soort && Array.prototype.some.call(soortKnoppen, function (k) { return k.dataset.soort === soort; })) stand.soort = soort;
  extraKnoppen.forEach(function (k) { if (zoek.get(k.dataset.extra) === "1") stand[k.dataset.extra] = true; });
  if (stand.wanneer || stand.plaats || stand.soort || stand.gratis || stand.kinderen) toepassen();
})();
