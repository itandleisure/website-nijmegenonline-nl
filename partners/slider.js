/*
 * Partnerslider
 * Zet op een pagina:
 *   <link rel="stylesheet" href="…/partners/slider.css">
 *   <div class="partner-slider" data-plaatsing="blog"></div>
 *   <script src="…/partners/slider.js" defer></script>
 * De partners komen uit partners.json naast dit script.
 */
(function () {
  var script = document.currentScript;
  var basis = new URL('.', script.src);
  var WISSEL_MS = 4000;

  function vandaag() {
    return new Date().toISOString().slice(0, 10);
  }

  function isActief(p, plaatsing) {
    var d = vandaag();
    if (p.start && d < p.start) return false;
    if (p.eind && d > p.eind) return false;
    var pl = p.plaatsingen || ['alle'];
    return pl.indexOf('alle') !== -1 || pl.indexOf(plaatsing) !== -1;
  }

  // Gewogen husselen: partners met een hoger gewicht komen vaker vooraan
  function hussel(lijst) {
    return lijst
      .map(function (p) { return { p: p, s: Math.pow(Math.random(), 1 / (p.gewicht || 1)) }; })
      .sort(function (a, b) { return b.s - a.s; })
      .map(function (x) { return x.p; });
  }

  function perKeer() {
    return window.matchMedia('(max-width: 600px)').matches ? 1 : 3;
  }

  function meld(actie, p) {
    if (typeof window.gtag === 'function') {
      window.gtag('event', actie, { partner: p.id, partner_naam: p.naam });
    }
  }

  function bouw(el, partners) {
    var plaatsing = el.getAttribute('data-plaatsing') || 'alle';
    var lijst = hussel(partners.filter(function (p) { return isActief(p, plaatsing); }));
    if (!lijst.length) { el.hidden = true; return; }

    el.innerHTML =
      '<p class="partner-slider__label">Partners</p>' +
      '<div class="partner-slider__venster"><div class="partner-slider__rij"></div></div>' +
      '<div class="partner-slider__stippen"></div>';
    var rij = el.querySelector('.partner-slider__rij');
    var stippen = el.querySelector('.partner-slider__stippen');

    lijst.forEach(function (p) {
      var item = document.createElement('div');
      item.className = 'partner-slider__item';
      var a = document.createElement('a');
      a.href = p.url;
      a.rel = 'sponsored noopener';
      a.target = '_blank';
      if (p.achtergrond) a.style.background = p.achtergrond;
      a.addEventListener('click', function () { meld('partner_klik', p); });
      var img = document.createElement('img');
      img.src = new URL(p.afbeelding, basis).href;
      img.alt = p.naam;
      img.loading = 'lazy';
      a.appendChild(img);
      item.appendChild(a);
      rij.appendChild(item);
    });

    var stap = 0;
    var timer = null;

    function aantalStappen() {
      return Math.max(1, lijst.length - perKeer() + 1);
    }

    function teken() {
      var n = perKeer();
      el.style.setProperty('--per-keer', n);
      if (stap >= aantalStappen()) stap = 0;
      rij.style.transform = 'translateX(' + (-stap * 100 / n) + '%)';
      stippen.innerHTML = '';
      if (aantalStappen() > 1) {
        for (var i = 0; i < aantalStappen(); i++) {
          var b = document.createElement('button');
          b.type = 'button';
          b.setAttribute('aria-label', 'Toon partner ' + (i + 1));
          if (i === stap) b.setAttribute('aria-current', 'true');
          b.addEventListener('click', (function (j) { return function () { stap = j; teken(); }; })(i));
          stippen.appendChild(b);
        }
      }
    }

    function start() {
      stop();
      if (aantalStappen() < 2) return;
      if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
      timer = setInterval(function () { stap = (stap + 1) % aantalStappen(); teken(); }, WISSEL_MS);
    }
    function stop() { if (timer) clearInterval(timer); timer = null; }

    el.addEventListener('mouseenter', stop);
    el.addEventListener('mouseleave', start);
    el.addEventListener('focusin', stop);
    el.addEventListener('focusout', start);
    window.addEventListener('resize', teken);

    teken();
    start();
    lijst.forEach(function (p) { meld('partner_vertoning', p); });
  }

  function init() {
    var sliders = document.querySelectorAll('.partner-slider');
    if (!sliders.length) return;
    fetch(new URL('partners.json', basis), { cache: 'no-cache' })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        sliders.forEach(function (el) { bouw(el, data.partners || []); });
      })
      .catch(function () {
        sliders.forEach(function (el) { el.hidden = true; });
      });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
