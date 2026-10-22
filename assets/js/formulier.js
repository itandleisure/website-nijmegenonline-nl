// Formulieren: met data-url gaat de inzending naar het Google Apps Script (Sheet + mail naar de redactie,
// zie tools/google-formulier/Code.gs). Zonder url, of als Google niet reageert, opent het mailprogramma
// van de bezoeker met het bericht al ingevuld.
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
      if (v.value.trim()) regels.push(label(v) + ": " + v.value.trim());
    });
    location.href = "mailto:" + form.dataset.email + "?subject=" + encodeURIComponent(form.dataset.onderwerp) +
      "&body=" + encodeURIComponent(regels.join("\n"));
    meld("Je mailprogramma wordt geopend met je bericht. Verstuur het daar.");
  }
  form.addEventListener("submit", function (e) {
    e.preventDefault();
    var ontbreekt = Array.prototype.filter.call(form.querySelectorAll("[required]"), function (v) { return !v.value.trim(); });
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
    var timer = setTimeout(function () { stop.abort(); }, 15000);
    fetch(form.dataset.url, { method: "POST", body: new URLSearchParams(new FormData(form)), signal: stop.signal })
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
