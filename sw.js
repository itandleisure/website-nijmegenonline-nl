/* Service worker van NijmegenOnline: maakt de site sneller bij een tweede bezoek en laat bezochte pagina's
   ook zonder internet zien. Bewust eenvoudig gehouden, zodat er niets aan onderhouden hoeft te worden:

   - Pagina's: altijd eerst van het netwerk (dus altijd actueel). Lukt dat niet, dan de laatst bekeken versie,
     en anders offline.html.
   - Opmaak, scripts, lettertypes en foto's uit assets/: meteen uit de cache, op de achtergrond ververst.
   - Al het andere (zoekindex, Google Analytics, MailerLite, kaarten) gaat ongewijzigd langs.

   VERSIE wordt door tools/build.py gelijk gehouden met de versie van site.css. Bij een nieuwe versie
   ruimt de browser de oude caches vanzelf op. */
var VERSIE = "36";
var VAST = "no-vast-" + VERSIE;
var PAGINAS = "no-paginas";
var BESTANDEN = "no-bestanden";
var MAX_PAGINAS = 60;
var MAX_BESTANDEN = 250;
var BASIS = new URL("./", self.registration ? self.registration.scope : self.location.href).pathname;

self.addEventListener("install", function (e) {
  e.waitUntil(caches.open(VAST).then(function (c) {
    return c.addAll([
      BASIS + "offline.html",
      BASIS + "assets/css/site.css?v=" + VERSIE,
      BASIS + "assets/img/logo-nijmegenonline.svg",
      BASIS + "assets/fonts/raleway-latin.woff2"
    ]);
  }).then(function () { return self.skipWaiting(); }));
});

self.addEventListener("activate", function (e) {
  e.waitUntil(caches.keys().then(function (namen) {
    return Promise.all(namen.filter(function (n) { return n.indexOf("no-vast-") === 0 && n !== VAST; })
      .map(function (n) { return caches.delete(n); }));
  }).then(function () { return self.clients.claim(); }));
});

function opruimen(naam, max) {
  caches.open(naam).then(function (c) {
    c.keys().then(function (sleutels) {
      for (var i = 0; i < sleutels.length - max; i++) c.delete(sleutels[i]);
    });
  });
}

self.addEventListener("fetch", function (e) {
  var req = e.request;
  if (req.method !== "GET") return;
  var url = new URL(req.url);
  if (url.origin !== self.location.origin || url.pathname.indexOf(BASIS) !== 0) return;
  var pad = url.pathname.slice(BASIS.length);
  if (pad.indexOf("statistiek/") === 0) return;

  if (req.mode === "navigate") {
    e.respondWith(fetch(req).then(function (antwoord) {
      if (antwoord.ok) {
        var kopie = antwoord.clone();
        caches.open(PAGINAS).then(function (c) { c.put(req, kopie); opruimen(PAGINAS, MAX_PAGINAS); });
      }
      return antwoord;
    }).catch(function () {
      return caches.match(req).then(function (bewaard) {
        return bewaard || caches.match(BASIS + "offline.html");
      });
    }));
    return;
  }

  if (pad.indexOf("assets/") === 0) {
    e.respondWith(caches.match(req).then(function (bewaard) {
      var vers = fetch(req).then(function (antwoord) {
        if (antwoord.ok) {
          var kopie = antwoord.clone();
          caches.open(BESTANDEN).then(function (c) { c.put(req, kopie); opruimen(BESTANDEN, MAX_BESTANDEN); });
        }
        return antwoord;
      });
      if (bewaard) { e.waitUntil(vers.catch(function () {})); return bewaard; }
      return vers;
    }));
  }
});
