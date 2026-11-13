// Formulieren: met data-url gaat de inzending naar het Google Apps Script (Sheet + mail naar de redactie,
// zie tools/google-formulier/Code.gs). Zonder url, of als Google niet reageert, opent het mailprogramma
// van de bezoeker met het bericht al ingevuld. Een foto (input type=file) gaat als data-URL mee; het script
// zet hem in Google Drive.
var SCRIPT = document.currentScript;
var MAX_FOTO = 10 * 1024 * 1024;   // het origineel; verkleind blijft er hooguit een paar honderd kB over
var MAX_PX = 1600;
// Leest de foto als data-URL en maakt hem eerst kleiner (max. 1600 px, jpg), zodat het versturen snel gaat.
// Lukt verkleinen niet, dan gaat het origineel mee.
function leesFoto(bestand) {
  return new Promise(function (ok, fout) {
    var r = new FileReader();
    r.onload = function () {
      var img = new Image();
      img.onload = function () {
        var schaal = Math.min(1, MAX_PX / Math.max(img.width, img.height));
        if (schaal === 1 && bestand.size < 1024 * 1024) { ok(r.result); return; }
        var c = document.createElement("canvas");
        c.width = Math.round(img.width * schaal);
        c.height = Math.round(img.height * schaal);
        var ctx = c.getContext("2d");
        ctx.fillStyle = "#fff";   // doorzichtige PNG (logo) op wit
        ctx.fillRect(0, 0, c.width, c.height);
        ctx.drawImage(img, 0, 0, c.width, c.height);
        try { ok(c.toDataURL("image/jpeg", 0.85)); } catch (e) { ok(r.result); }
      };
      img.onerror = function () { ok(r.result); };
      img.src = r.result;
    };
    r.onerror = fout;
    r.readAsDataURL(bestand);
  });
}
document.querySelectorAll("form.formulier").forEach(function (form) {
  var geopend = Date.now();
  var melding = form.querySelector(".formulier__melding");
  function meld(tekst, fout) {
    melding.hidden = false;
    melding.textContent = tekst;
    melding.classList.toggle("formulier__melding--fout", !!fout);
  }
  function label(v) {
    var l = v.type === "checkbox" || v.type === "radio" ? v.closest("fieldset").querySelector("legend") : form.querySelector('label[for="' + v.id + '"]');
    return (l ? l.textContent : v.name).replace(/\s*\*\s*$/, "").replace(/\s*\(.*\)$/, "");
  }
  function mailknop() {
    var regels = [];
    form.querySelectorAll("input[id], select[id], textarea[id], fieldset input:checked").forEach(function (v) {
      if (v.type === "file") { if (v.files.length) regels.push(label(v) + (v.files.length > 1 ? ": stuur de foto's mee als bijlage" : ": stuur de foto mee als bijlage")); return; }
      if (v.value.trim()) regels.push(label(v) + ": " + v.value.trim());
    });
    location.href = "mailto:" + form.dataset.email + "?subject=" + encodeURIComponent(form.dataset.onderwerp) +
      "&body=" + encodeURIComponent(regels.join("\n"));
    meld("Je mailprogramma wordt geopend met je bericht. Verstuur het daar.");
  }
  // Einddatum vanzelf gelijk aan de begindatum (de meeste evenementen duren één dag)
  var datum = form.querySelector('[name="datum"]'), einddatum = form.querySelector('[name="einddatum"]');
  if (datum && einddatum) {
    datum.addEventListener("change", function () {
      if (!einddatum.value || einddatum.value < datum.value) einddatum.value = datum.value;
      einddatum.min = datum.value;
    });
  }
  // Met een landkeuze: het voorbeeld onder de postcode past zich aan het land aan
  var land = form.querySelector('select[name="land"]');
  var pcHint = form.querySelector("[data-postcode-hint]");
  function landHint() {
    if (!land || !pcHint) return;
    pcHint.textContent = land.value === "Duitsland" ? "5 cijfers, bijvoorbeeld 47533." : "Bijvoorbeeld 6511 AB.";
  }
  if (land) land.addEventListener("change", landHint);
  // Velden vooraf invullen vanuit de url, bijvoorbeeld de knop "Dit is mijn bedrijf" in de bedrijvengids
  new URLSearchParams(location.search).forEach(function (waarde, sleutel) {
    if (["form", "pagina", "duur", "website"].indexOf(sleutel) !== -1) return;
    form.querySelectorAll('[name="' + sleutel.replace(/[^\w-]/g, "") + '"]').forEach(function (v) {
      if (v.type === "file" || v.hasAttribute("data-nooit-vooraf")) return;   // toestemming (nieuwsbrief) nooit via een link aanvinken
      if (v.type === "radio" || v.type === "checkbox") { if (v.value === waarde) v.checked = true; return; }
      v.value = waarde;
    });
  });
  landHint();
  var bijschrift = fotobron(form);
  var tijden = openingstijden(form);
  huidigeVermelding(form, tijden);
  form.addEventListener("submit", function (e) {
    e.preventDefault();
    var ontbreekt = Array.prototype.filter.call(form.querySelectorAll("[required]"), function (v) {
      if (v.type === "radio") return !form.querySelector('input[name="' + v.name + '"]:checked');
      if (v.type === "checkbox") return !v.checked;   // verplicht vinkje, zoals de verklaring over de foto's
      return v.type === "file" ? !v.files.length : !v.value.trim();
    }).filter(function (v, i, alle) {   // een groep keuzes telt één keer
      return v.type !== "radio" || alle.findIndex(function (w) { return w.name === v.name; }) === i;
    });
    var foto = form.querySelector('input[type="file"]');
    // Met "multiple" (bedrijvengids) mogen er meer foto's mee, hooguit data-max; de eerste is de hoofdfoto
    var bestanden = foto ? Array.prototype.slice.call(foto.files) : [];
    var maxFotos = foto && foto.multiple ? parseInt(foto.dataset.max, 10) || 5 : 1;
    if (bestanden.length > maxFotos) { meld("Kies hooguit " + maxFotos + " foto's.", true); foto.focus(); return; }
    if (bestanden.some(function (b) { return b.size > MAX_FOTO; })) {
      meld(bestanden.length > 1 ? "Een van de foto's is groter dan 10 MB. Kies een kleinere foto." : "De foto is groter dan 10 MB. Kies een kleinere foto.", true);
      foto.focus(); return;
    }
    if (ontbreekt.length) { meld("Vul alle velden met een * in.", true); ontbreekt[0].focus(); return; }
    var email = Array.prototype.filter.call(form.querySelectorAll('input[type="email"]'), function (v) {
      return (v.required || v.value.trim()) && !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(v.value.trim());
    })[0];
    if (email) { meld("Controleer het e-mailadres.", true); email.focus(); return; }
    var pc = form.querySelector("[data-postcode]");
    if (pc && pc.value.trim()) {
      var waarde = pc.value.trim().toUpperCase();
      var nl = waarde.match(/^(\d{4})\s*([A-Z]{2})$/);
      var de = /^\d{5}$/.test(waarde);
      var fout = land && land.value === "Duitsland" ? (de ? "" : "Een Duitse postcode heeft 5 cijfers, bijvoorbeeld 47533.")
        : land ? (nl ? "" : "Controleer de postcode, bijvoorbeeld 6511 AB.")
        : (nl || de ? "" : "Controleer de postcode, bijvoorbeeld 6511 AB (of 5 cijfers in Duitsland).");
      if (fout) { meld(fout, true); pc.focus(); return; }
      pc.value = nl ? nl[1] + " " + nl[2] : waarde;
    }
    var begin = form.querySelector('[name="datum"]'), eind = form.querySelector('[name="einddatum"]');
    if (begin && eind) {
      var tb = form.querySelector('[name="starttijd"]'), te = form.querySelector('[name="eindtijd"]');
      if (eind.value + (te ? te.value : "") < begin.value + (tb ? tb.value : "")) {
        meld("Het einde ligt voor het begin. Controleer de datums en tijden.", true); eind.focus(); return;
      }
    }
    if (bijschrift) bijschrift();
    if (!form.dataset.url) { mailknop(); return; }

    form.pagina.value = location.href;
    form.duur.value = Date.now() - geopend;
    var knop = form.querySelector('button[type="submit"]');
    knop.disabled = true;
    meld("Bezig met versturen...");
    var stop = new AbortController();
    var timer;
    var gegevens = new URLSearchParams();
    Promise.all(bestanden.map(leesFoto))
      .then(function (fotos) {
        new FormData(form).forEach(function (waarde, sleutel) {
          if (typeof waarde === "string") gegevens.append(sleutel, waarde);
        });
        // De eerste als "foto", de andere als "foto_2", "foto_3" enzovoort (Code.gs zet ze in Drive)
        fotos.forEach(function (data, i) {
          if (data.length > 7 * 1024 * 1024) throw new Error("foto");
          var veld = i ? foto.name + "_" + (i + 1) : foto.name;
          gegevens.append(veld, data);
          gegevens.append(veld + "_naam", bestanden[i].name);
        });
        timer = setTimeout(function () { stop.abort(); }, 90000);
        return fetch(form.dataset.url, { method: "POST", body: gegevens, signal: stop.signal });
      })
      .then(function (r) { return r.json(); })
      .then(function (res) {
        clearTimeout(timer);
        if (!res.ok) throw new Error(res.fout || "mislukt");
        form.reset();
        meld(form.dataset.bedankt || "Bedankt! We hebben je bericht ontvangen en nemen snel contact met je op.");
      })
      .catch(function (e) {
        if (e && e.message === "foto") {
          meld("Deze foto kunnen we niet verkleinen en is te groot. Kies een jpg of png kleiner dan 5 MB.", true);
          return;
        }
        if (e && e.name === "AbortError") {
          // Google is traag, maar de inzending komt meestal toch aan: niet nog eens laten mailen
          form.reset();
          meld("Je bericht is verstuurd, maar het bevestigen duurde lang. Heb je binnen een dag niets van ons gehoord? Mail dan naar " + form.dataset.email + ".");
          return;
        }
        meld("Versturen lukte niet. We openen je mailprogramma, dan kun je het bericht daar versturen.", true);
        setTimeout(mailknop, 1500);
      })
      .then(function () { knop.disabled = false; });
  });
});

// Verplicht bijschrift bij de foto: Eigen foto, Rechtenvrije afbeelding of Fotocredits bij: (naam verplicht).
// Het naamveld verschijnt alleen bij fotocredits. Het bijschrift zelf gaat mee in het verborgen veld "bijschrift",
// zoals het onder de foto op de evenementpagina komt: "Eigen foto", "Rechtenvrije afbeelding" of "Foto: Naam".
function fotobron(form) {
  var groep = form.querySelector("[data-fotobron]");
  if (!groep) return;
  var blok = form.querySelector("[data-fotocredit]");
  var naam = blok.querySelector("input");
  var uit = form.querySelector('input[type="hidden"][name="bijschrift"]');
  var keuzes = groep.querySelectorAll('input[type="radio"]');
  var credits = keuzes[keuzes.length - 1];
  function bijwerken() {
    blok.hidden = !credits.checked;
    naam.required = credits.checked;
    var gekozen = groep.querySelector("input:checked");
    uit.value = !gekozen ? "" : gekozen === credits ? (naam.value.trim() ? "Foto: " + naam.value.trim() : "") : gekozen.value;
  }
  groep.addEventListener("change", function () { bijwerken(); if (credits.checked) naam.focus(); });
  naam.addEventListener("input", bijwerken);
  form.addEventListener("reset", function () { setTimeout(bijwerken, 0); });
  bijwerken();
  return bijwerken;
}

// Openingstijden per dag, zoals bij Google. Het tekstveld zelf blijft (verborgen) bestaan en krijgt
// één regel per dag ("ma 09:00-17:00" of "ma gesloten"); zo hoeft het Apps Script niets te weten van dit schema.
// Een ingevulde waarde uit de url ("ma-vr 07:00-22:00, za 09:00-16:00") wordt over de dagen verdeeld.
function openingstijden(form) {
  var veld = form.querySelector('textarea[name="openingstijden"]');
  if (!veld) return;
  var DAGEN = ["ma", "di", "wo", "do", "vr", "za", "zo"];
  var NAMEN = ["Maandag", "Dinsdag", "Woensdag", "Donderdag", "Vrijdag", "Zaterdag", "Zondag"];
  var schema = document.createElement("div");
  schema.className = "openingstijden";
  var rijen = DAGEN.map(function (dag, i) {
    var rij = document.createElement("div");
    rij.className = "openingstijden__dag";
    rij.innerHTML = '<span>' + NAMEN[i] + '</span>' +
      '<input type="time" aria-label="' + NAMEN[i] + ' open vanaf"><span aria-hidden="true">tot</span>' +
      '<input type="time" aria-label="' + NAMEN[i] + ' open tot">' +
      '<label><input type="checkbox"> gesloten</label>';
    schema.appendChild(rij);
    var t = rij.querySelectorAll('input[type="time"]');
    return { dag: dag, open: t[0], dicht: t[1], dicht_: rij.querySelector('input[type="checkbox"]') };
  });
  var kopie = document.createElement("button");
  kopie.type = "button";
  kopie.className = "openingstijden__kopie";
  kopie.textContent = "Maandag overnemen voor dinsdag t/m vrijdag";
  schema.appendChild(kopie);
  var noot = document.createElement("input");
  noot.type = "text";
  noot.className = "openingstijden__noot";
  noot.setAttribute("aria-label", "Bijzonderheden over de openingstijden");
  noot.placeholder = "Bijzonderheden, bijvoorbeeld: op feestdagen gesloten";
  schema.appendChild(noot);
  veld.hidden = true;
  veld.parentNode.insertBefore(schema, veld);

  function bijwerken() {
    var regels = [];
    rijen.forEach(function (r) {
      r.open.disabled = r.dicht.disabled = r.dicht_.checked;
      if (r.dicht_.checked) regels.push(r.dag + " gesloten");
      else if (r.open.value && r.dicht.value) regels.push(r.dag + " " + r.open.value + "-" + r.dicht.value);
    });
    if (noot.value.trim()) regels.push(noot.value.trim());
    veld.value = regels.join("\n");
  }
  function inlezen(tekst) {
    var rest = [];
    tekst.split(/[,;\n]+/).forEach(function (deel) {
      var m = deel.trim().toLowerCase().match(/^(ma|di|wo|do|vr|za|zo)[a-z]*(?:\s*(?:-|t\/m|tot)\s*(ma|di|wo|do|vr|za|zo)[a-z]*)?:?\s+(.*)$/);
      var tijd = m && m[3].match(/^(\d{1,2})[:.](\d{2})\s*(?:-|–|tot)\s*(\d{1,2})[:.](\d{2})/);
      var dicht = m && /gesloten|dicht/.test(m[3]);
      if (!m || !(tijd || dicht)) { if (deel.trim()) rest.push(deel.trim()); return; }
      var van = DAGEN.indexOf(m[1]), tot = m[2] ? DAGEN.indexOf(m[2]) : van;
      for (var i = van; i <= tot; i++) {
        rijen[i].dicht_.checked = !!dicht && !tijd;
        if (tijd) {
          rijen[i].open.value = ("0" + tijd[1]).slice(-2) + ":" + tijd[2];
          rijen[i].dicht.value = tijd[3] === "24" ? "23:59" : ("0" + tijd[3]).slice(-2) + ":" + tijd[4];
        }
      }
    });
    noot.value = rest.join(", ");
  }
  kopie.addEventListener("click", function () {
    for (var i = 1; i < 5; i++) {
      rijen[i].open.value = rijen[0].open.value;
      rijen[i].dicht.value = rijen[0].dicht.value;
      rijen[i].dicht_.checked = rijen[0].dicht_.checked;
    }
    bijwerken();
  });
  schema.addEventListener("input", bijwerken);
  schema.addEventListener("change", bijwerken);
  form.addEventListener("reset", function () { setTimeout(bijwerken, 0); });
  if (veld.value.trim()) inlezen(veld.value);
  bijwerken();
  return function (tekst) { inlezen(tekst); bijwerken(); };
}

// "Dit is mijn bedrijf": de huidige tekst, openingstijden en foto uit de gids alvast in het formulier zetten
// (data/bedrijvengids-vermeldingen.json, gemaakt door tools/bedrijvengids.py). Wat al in de url stond, blijft staan.
function huidigeVermelding(form, tijden) {
  var slug = new URLSearchParams(location.search).get("vermelding");
  if (!slug || !SCRIPT || !form.querySelector('[name="vermelding"]')) return;
  fetch(new URL("../../data/bedrijvengids-vermeldingen.json", SCRIPT.src))
    .then(function (r) { return r.json(); })
    .then(function (alle) {
      var v = alle[slug];
      if (!v) return;
      var oms = form.querySelector('[name="omschrijving"]');
      if (oms && !oms.value.trim() && v.omschrijving) oms.value = v.omschrijving;
      var mail = form.querySelector('[name="bedrijfsmail"]');
      if (mail && !mail.value.trim() && v.bedrijfsmail) mail.value = v.bedrijfsmail;
      var veld = form.querySelector('textarea[name="openingstijden"]');
      if (veld && !veld.value.trim() && v.openingstijden && tijden) tijden(v.openingstijden);
      var foto = form.querySelector('input[type="file"]');
      if (foto && v.foto) {
        var huidig = document.createElement("div");
        huidig.className = "huidigefoto";
        huidig.innerHTML = '<img alt="Huidige foto"><span>Dit is je huidige foto. Kies hieronder een andere als je hem wilt vervangen.</span>';
        huidig.querySelector("img").src = v.foto;
        foto.parentNode.insertBefore(huidig, foto);
      }
    })
    .catch(function () {});
}

// "Zoek je bedrijf": kies het bedrijf uit de bedrijvengids, zodat een evenement (en straks een vacature) eraan
// gekoppeld is (besluit Frans, 2-11-2026). De lijst (data/bedrijven-zoek.json, gemaakt door tools/bedrijvengids.py)
// laadt pas als iemand begint te typen. Het gekozen bedrijf gaat als sleutel mee in het verborgen veld "bedrijf"; lege
// velden zoals website en adres worden alvast ingevuld. ?bedrijf=<sleutel> in de url kiest het bedrijf meteen.
document.querySelectorAll("[data-bedrijfzoeker]").forEach(function (blok) {
  var form = blok.closest("form");
  var invoer = blok.querySelector('input[type="search"]');
  var lijst = blok.querySelector(".bedrijfzoeker__lijst");
  var verborgen = blok.querySelector('input[name="bedrijf"]');
  var gekozen = blok.querySelector(".bedrijfzoeker__gekozen");
  var zoek = blok.querySelector(".bedrijfzoeker__zoek");
  var vullen = JSON.parse(blok.getAttribute("data-vullen") || "{}");   // veldnaam -> kolom in de lijst
  var KOLOM = { naam: 1, adres: 2, postcode: 3, plaats: 4, site: 5 };
  var bedrijven = null, laden = null, treffers = [], actief = -1;
  function sleutel(t) {
    return String(t || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();
  }
  function laad() {
    if (!laden) {
      laden = fetch(new URL("../../data/bedrijven-zoek.json", SCRIPT.src))
        .then(function (r) { return r.json(); })
        .then(function (rijen) {
          bedrijven = rijen.map(function (r) { return { rij: r, naam: sleutel(r[1]), alles: sleutel(r[1] + " " + r[4] + " " + r[2]) }; });
          return bedrijven;
        })
        .catch(function () { bedrijven = []; return bedrijven; });
    }
    return laden;
  }
  function sluit() {
    lijst.hidden = true;
    invoer.setAttribute("aria-expanded", "false");
    actief = -1;
  }
  function toon() {
    var woorden = sleutel(invoer.value).split(" ").filter(Boolean);
    if (!bedrijven || !woorden.length || sleutel(invoer.value).length < 2) { sluit(); return; }
    var q = woorden.join(" ");
    treffers = bedrijven.filter(function (b) {
      return woorden.every(function (w) { return b.alles.indexOf(w) !== -1; });
    }).map(function (b) {
      // Begint met de zoektekst eerst, dan een woord dat ermee begint, dan de rest
      var score = b.naam.indexOf(q) === 0 ? 0 : (" " + b.naam).indexOf(" " + woorden[0]) !== -1 ? 1 : 2;
      return { b: b, score: score };
    }).sort(function (x, y) { return x.score - y.score || x.b.naam.localeCompare(y.b.naam); })
      .slice(0, 8).map(function (x) { return x.b.rij; });
    lijst.innerHTML = "";
    if (!treffers.length) {
      var leeg = document.createElement("li");
      leeg.className = "bedrijfzoeker__niets";
      // Nog niet in de gids: eerst (gratis) aanmelden, in een nieuw tabblad zodat dit formulier blijft staan
      leeg.appendChild(document.createTextNode("Niet gevonden. "));
      var aanmaken = document.createElement("a");
      aanmaken.href = new URL("../../bedrijf-aanmelden/", SCRIPT.src).href;
      aanmaken.target = "_blank";
      aanmaken.rel = "noopener";
      aanmaken.textContent = "Meld je bedrijf of organisatie eerst gratis aan";
      leeg.appendChild(aanmaken);
      leeg.appendChild(document.createTextNode(", of laat dit veld leeg."));
      leeg.addEventListener("mousedown", function (e) { if (e.target !== aanmaken) e.preventDefault(); });
      aanmaken.addEventListener("mousedown", function (e) { e.preventDefault(); });
      lijst.appendChild(leeg);
    }
    treffers.forEach(function (r, i) {
      var li = document.createElement("li");
      li.id = invoer.id + "-optie-" + i;
      li.setAttribute("role", "option");
      li.textContent = r[1];
      var regel = document.createElement("span");
      regel.textContent = [r[2], r[4]].filter(Boolean).join(", ") + (r[6] ? " · " + r[6] : "");
      li.appendChild(regel);
      li.addEventListener("mousedown", function (e) { e.preventDefault(); kies(r); });
      lijst.appendChild(li);
    });
    lijst.hidden = false;
    invoer.setAttribute("aria-expanded", "true");
    actief = -1;
  }
  function markeer(i) {
    var items = lijst.querySelectorAll('[role="option"]');
    if (!items.length) return;
    actief = (i + items.length) % items.length;
    items.forEach(function (li, j) { li.setAttribute("aria-selected", String(j === actief)); });
    invoer.setAttribute("aria-activedescendant", items[actief].id);
    items[actief].scrollIntoView({ block: "nearest" });
  }
  function kies(r) {
    verborgen.value = r[0];
    gekozen.querySelector("strong").textContent = r[1];
    gekozen.querySelector(".bedrijfzoeker__regel").textContent = [r[2], r[4]].filter(Boolean).join(", ");
    gekozen.hidden = false;
    zoek.hidden = true;
    sluit();
    Object.keys(vullen).forEach(function (veld) {
      var v = form.querySelector('[name="' + veld + '"]');
      var waarde = r[KOLOM[vullen[veld]]];
      if (v && waarde && !v.value.trim()) v.value = waarde;
    });
  }
  function opnieuw() {
    verborgen.value = "";
    gekozen.hidden = true;
    zoek.hidden = false;
    invoer.value = "";
    invoer.focus();
  }
  invoer.addEventListener("focus", laad);
  invoer.addEventListener("input", function () { laad().then(toon); });
  invoer.addEventListener("keydown", function (e) {
    if (e.key === "ArrowDown") { e.preventDefault(); if (lijst.hidden) toon(); markeer(actief + 1); }
    else if (e.key === "ArrowUp") { e.preventDefault(); markeer(actief - 1); }
    else if (e.key === "Enter") { if (!lijst.hidden && treffers.length) { e.preventDefault(); kies(treffers[Math.max(actief, 0)]); } }
    else if (e.key === "Escape") { sluit(); }
  });
  invoer.addEventListener("blur", function () { setTimeout(sluit, 150); });
  gekozen.querySelector("button").addEventListener("click", opnieuw);
  form.addEventListener("reset", function () { setTimeout(function () { verborgen.value = ""; gekozen.hidden = true; zoek.hidden = false; }, 0); });
  // Vooraf gekozen via de url (knop op de bedrijfspagina)
  if (verborgen.value) {
    laad().then(function (alle) {
      var b = alle.filter(function (x) { return x.rij[0] === verborgen.value; })[0];
      if (b) kies(b.rij); else verborgen.value = "";
    });
  }
});
