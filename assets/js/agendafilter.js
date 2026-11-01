// Filter op datum in de agenda: vandaag, morgen, dit weekend of de komende 7 dagen.
// Een evenement blijft staan als het op een van die dagen loopt (data-van t/m data-tot op de kaart).
// De uitgelichte evenementen bovenaan blijven altijd staan. ?wanneer=weekend in de URL zet het filter meteen aan.
(function () {
  var blok = document.getElementById("agendafilter");
  if (!blok) return;
  var knoppen = blok.querySelectorAll("button[data-wanneer]");
  var uitkomst = blok.querySelector(".agendafilter__uitkomst");
  var kaarten = document.querySelectorAll(".agenda-maand .eventkaart");

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

  function toepassen(wanneer) {
    var r = bereik(wanneer), van = r && iso(r[0]), tot = r && iso(r[1]), zichtbaar = 0;
    knoppen.forEach(function (k) { k.setAttribute("aria-pressed", k.dataset.wanneer === (wanneer || "")); });
    kaarten.forEach(function (kaart) {
      var past = !r || (kaart.dataset.van <= tot && kaart.dataset.tot >= van);
      kaart.hidden = !past;
      if (past) zichtbaar++;
    });
    document.querySelectorAll(".agenda-maand").forEach(function (sectie) {
      sectie.hidden = !!r && !sectie.querySelector(".eventkaart:not([hidden])");
    });
    uitkomst.hidden = !r;
    if (r) uitkomst.textContent = zichtbaar === 0 ? "Geen evenementen gevonden voor deze periode."
      : zichtbaar + (zichtbaar === 1 ? " evenement" : " evenementen") + " gevonden.";
    try {
      var url = new URL(location.href);
      if (wanneer) url.searchParams.set("wanneer", wanneer); else url.searchParams.delete("wanneer");
      history.replaceState(null, "", url);
    } catch (e) { /* oude browser: filter werkt, alleen de URL blijft gelijk */ }
  }

  knoppen.forEach(function (k) { k.addEventListener("click", function () { toepassen(k.dataset.wanneer); }); });
  var start = new URLSearchParams(location.search).get("wanneer");
  if (start && bereik(start)) toepassen(start);
})();
