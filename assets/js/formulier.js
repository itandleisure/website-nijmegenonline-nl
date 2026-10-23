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
    var l = v.type === "checkbox" ? v.closest("fieldset").querySelector("legend") : form.querySelector('label[for="' + v.id + '"]');
    return (l ? l.textContent : v.name).replace(/\s*\*\s*$/, "").replace(/\s*\(.*\)$/, "");
  }
  function mailknop() {
    var regels = [];
    form.querySelectorAll("input[id], select[id], textarea[id], fieldset input:checked").forEach(function (v) {
      if (v.type === "file") { if (v.files.length) regels.push(label(v) + ": stuur de foto mee als bijlage"); return; }
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
      if (v.type === "file") return;
      if (v.type === "radio" || v.type === "checkbox") { if (v.value === waarde) v.checked = true; return; }
      v.value = waarde;
    });
  });
  landHint();
  var tijden = openingstijden(form);
  huidigeVermelding(form, tijden);
  form.addEventListener("submit", function (e) {
    e.preventDefault();
    var ontbreekt = Array.prototype.filter.call(form.querySelectorAll("[required]"), function (v) {
      return v.type === "file" ? !v.files.length : !v.value.trim();
    });
    var foto = form.querySelector('input[type="file"]');
    if (foto && foto.files.length && foto.files[0].size > MAX_FOTO) { meld("De foto is groter dan 10 MB. Kies een kleinere foto.", true); foto.focus(); return; }
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
    if (!form.dataset.url) { mailknop(); return; }

    form.pagina.value = location.href;
    form.duur.value = Date.now() - geopend;
    var knop = form.querySelector('button[type="submit"]');
    knop.disabled = true;
    meld("Bezig met versturen...");
    var stop = new AbortController();
    var timer;
    var gegevens = new URLSearchParams();
    var fotoKlaar = foto && foto.files.length ? leesFoto(foto.files[0]) : Promise.resolve("");
    fotoKlaar
      .then(function (data) {
        new FormData(form).forEach(function (waarde, sleutel) {
          if (typeof waarde === "string") gegevens.append(sleutel, waarde);
        });
        if (data.length > 7 * 1024 * 1024) throw new Error("foto");
        if (data) { gegevens.append(foto.name, data); gegevens.append(foto.name + "_naam", foto.files[0].name); }
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
