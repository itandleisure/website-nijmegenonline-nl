// Carrousel met bedrijven in de gidsen (/thema/...): drie tegelijk, schuift elke 7 seconden door, stopt bij aanwijzen.
(function () {
  document.querySelectorAll(".gidscarrousel").forEach(function (blok) {
    var rij = blok.querySelector(".gidscarrousel__rij");
    if (!rij) return;
    function schuif(richting) {
      var eind = rij.scrollLeft + rij.clientWidth >= rij.scrollWidth - 4;
      if (richting > 0 && eind) rij.scrollTo({ left: 0, behavior: "smooth" });
      else rij.scrollBy({ left: richting * rij.clientWidth, behavior: "smooth" });
    }
    blok.querySelectorAll(".gidscarrousel__knop").forEach(function (k) {
      k.addEventListener("click", function () { schuif(Number(k.dataset.richting)); });
    });
    var stil = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    var pauze = false;
    blok.addEventListener("mouseenter", function () { pauze = true; });
    blok.addEventListener("mouseleave", function () { pauze = false; });
    blok.addEventListener("focusin", function () { pauze = true; });
    if (!stil && rij.scrollWidth > rij.clientWidth + 4) {
      setInterval(function () { if (!pauze && !document.hidden) schuif(1); }, 7000);
    }
  });
})();
