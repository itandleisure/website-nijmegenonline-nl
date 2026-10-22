// Formulieren: met data-url gaat de inzending naar het Google Apps Script (Sheet + mail naar de redactie,
// zie tools/google-formulier/Code.gs). Zonder url, of als Google niet reageert, opent het mailprogramma
// van de bezoeker met het bericht al ingevuld. Een foto (input type=file) gaat als data-URL mee; het script
// zet hem in Google Drive.
var MAX_FOTO = 5 * 1024 * 1024;
function leesFoto(bestand) {
  return new Promise(function (ok, fout) {
    var r = new FileReader();
    r.onload = function () { ok(r.result); };
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
    form.querySelectorAll("input[id], textarea[id], fieldset input:checked").forEach(function (v) {
      if (v.type === "file") { if (v.files.length) regels.push(label(v) + ": stuur de foto mee als bijlage"); return; }
      if (v.value.trim()) regels.push(label(v) + ": " + v.value.trim());
    });
    location.href = "mailto:" + form.dataset.email + "?subject=" + encodeURIComponent(form.dataset.onderwerp) +
      "&body=" + encodeURIComponent(regels.join("\n"));
    meld("Je mailprogramma wordt geopend met je bericht. Verstuur het daar.");
  }
  form.addEventListener("submit", function (e) {
    e.preventDefault();
    var ontbreekt = Array.prototype.filter.call(form.querySelectorAll("[required]"), function (v) {
      return v.type === "file" ? !v.files.length : !v.value.trim();
    });
    var foto = form.querySelector('input[type="file"]');
    if (foto && foto.files.length && foto.files[0].size > MAX_FOTO) { meld("De foto is groter dan 5 MB. Kies een kleinere foto.", true); foto.focus(); return; }
    var email = form.querySelector('input[type="email"]');
    if (ontbreekt.length) { meld("Vul alle velden met een * in.", true); ontbreekt[0].focus(); return; }
    if (email && !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email.value.trim())) { meld("Controleer je e-mailadres.", true); email.focus(); return; }
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
        if (data) { gegevens.append(foto.name, data); gegevens.append(foto.name + "_naam", foto.files[0].name); }
        timer = setTimeout(function () { stop.abort(); }, 30000);
        return fetch(form.dataset.url, { method: "POST", body: gegevens, signal: stop.signal });
      })
      .then(function (r) { return r.json(); })
      .then(function (res) {
        clearTimeout(timer);
        if (!res.ok) throw new Error(res.fout || "mislukt");
        form.reset();
        meld("Bedankt! We hebben je bericht ontvangen en nemen snel contact met je op.");
      })
      .catch(function () {
        meld("Versturen lukte niet. We openen je mailprogramma, dan kun je het bericht daar versturen.", true);
        setTimeout(mailknop, 1500);
      })
      .then(function () { knop.disabled = false; });
  });
});
