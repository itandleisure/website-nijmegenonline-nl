// Filters in de agenda, samen te gebruiken:
// - op datum: vandaag, morgen, dit weekend of de komende 7 dagen. Een evenement blijft staan als het op een van die
//   dagen loopt (data-van t/m data-tot op de kaart). De uitgelichte evenementen bovenaan blijven daarbij staan.
// - op plaats (besluit Frans, 2-11-2026): Nijmegen, Wijchen, Kleef, ... (data-plaats op de kaart, ook de uitgelichte).
// ?wanneer=weekend en ?plaats=Wijchen in de URL zetten een filter meteen aan; de plaatspagina's linken zo hierheen.
(function () {
  var blok = document.getElementById("agendafilter");
  if (!blok) return;
  var knoppen = blok.querySelectorAll("button[data-wanneer]");
  var uitkomst = blok.querySelector(".agendafilter__uitkomst");
  var plaatsNav = document.querySelector(".agenda-plaatsen");
  var plaatsKnoppen = plaatsNav ? plaatsNav.querySelectorAll("button[data-plaats]") : [];
  var kaarten = document.querySelectorAll(".agenda-maand .eventkaart");
  var uitgelicht = document.querySelectorAll(".agenda-uitgelicht .uitgelicht");
  var stand = { wanneer: "", plaats: "" };

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
    knoppen.forEach(function (k) { k.setAttribute("aria-pressed", String(k.dataset.wanneer === stand.wanneer)); });
    plaatsKnoppen.forEach(function (k) { k.setAttribute("aria-pressed", String(k.dataset.plaats === plaats)); });
    kaarten.forEach(function (kaart) {
      var past = (!r || (kaart.dataset.van <= tot && kaart.dataset.tot >= van)) && (!plaats || kaart.dataset.plaats === plaats);
      kaart.hidden = !past;
      if (past) zichtbaar++;
    });
    uitgelicht.forEach(function (kaart) { kaart.hidden = !!plaats && kaart.dataset.plaats !== plaats; });
    document.querySelectorAll(".agenda-maand").forEach(function (sectie) {
      sectie.hidden = (!!r || !!plaats) && !sectie.querySelector(".eventkaart:not([hidden])");
    });
    document.querySelectorAll(".agenda-uitgelicht").forEach(function (sectie) {
      sectie.hidden = !!plaats && !sectie.querySelector(".uitgelicht:not([hidden])");
    });
    var gefilterd = !!r || !!plaats;
    uitkomst.hidden = !gefilterd;
    if (gefilterd) uitkomst.textContent = zichtbaar === 0 ? "Geen evenementen gevonden" + (plaats ? " in " + plaats : "") +
      (r ? " voor deze periode." : ".") : zichtbaar + (zichtbaar === 1 ? " evenement" : " evenementen") + " gevonden.";
    try {
      var url = new URL(location.href);
      if (stand.wanneer) url.searchParams.set("wanneer", stand.wanneer); else url.searchParams.delete("wanneer");
      if (plaats) url.searchParams.set("plaats", plaats); else url.searchParams.delete("plaats");
      history.replaceState(null, "", url);
    } catch (e) { /* oude browser: filter werkt, alleen de URL blijft gelijk */ }
  }

  knoppen.forEach(function (k) { k.addEventListener("click", function () { stand.wanneer = k.dataset.wanneer; toepassen(); }); });
  plaatsKnoppen.forEach(function (k) { k.addEventListener("click", function () { stand.plaats = k.dataset.plaats; toepassen(); }); });
  if (plaatsNav) plaatsNav.hidden = false;
  var zoek = new URLSearchParams(location.search);
  var wanneer = zoek.get("wanneer"), plaats = zoek.get("plaats");
  if (wanneer && bereik(wanneer)) stand.wanneer = wanneer;
  if (plaats && Array.prototype.some.call(plaatsKnoppen, function (k) { return k.dataset.plaats === plaats; })) stand.plaats = plaats;
  if (stand.wanneer || stand.plaats) toepassen();
})();
