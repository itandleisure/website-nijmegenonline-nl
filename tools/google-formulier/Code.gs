/* Formulieren NijmegenOnline → Google Sheet + e-mail
   ---------------------------------------------------------------
   Dit script hoort bij een Google Sheet (Extensies → Apps Script).
   - Elk formulier van nijmegenonline.nl komt als nieuwe regel in een eigen tabblad:
     Contact en Partners.
   - Er gaat meteen een e-mail naar ONTVANGER (antwoorden gaat rechtstreeks naar de invuller).
   - Regels ouder dan de bewaartermijn per tabblad worden elke nacht automatisch verwijderd (privacy).

   Eenmalig: kies bovenin de functie "installeer" en klik op Uitvoeren (geeft toestemming
   en zet de nachtelijke opruimtaak aan). Daarna: Implementeren → Nieuwe implementatie → Web-app,
   "Uitvoeren als: ik", "Toegang: iedereen". Zet de /exec-URL in GOOGLE_FORM_URL in tools/paginas.py.

   Script gewijzigd? Implementeren → Implementaties beheren → bewerken → Nieuwe versie
   (dan blijft de URL gelijk). */

var ONTVANGER = 'redactie@nijmegenonline.nl';
var AFZENDER_NAAM = 'Website NijmegenOnline';

// Per formuliertype: tabblad, kolommen, bewaartermijn en onderwerp van de mail
var FORMULIEREN = {
  contact: {
    tabblad: 'Contact', bewaarMaanden: 12, onderwerp: 'Contactformulier',
    velden: [['naam', 'Naam'], ['email', 'E-mail'], ['telefoon', 'Telefoon'], ['onderwerp', 'Onderwerp'], ['bericht', 'Bericht']]
  },
  partner: {
    tabblad: 'Partners', bewaarMaanden: 24, onderwerp: 'Aanmelding partner',
    velden: [['naam', 'Naam'], ['bedrijf', 'Bedrijf'], ['email', 'E-mail'], ['telefoon', 'Telefoon'],
      ['pakket', 'Pakket'], ['bericht', 'Toelichting']]
  }
};

// Ontvangt een formulier van de website
function doPost(e) {
  var p = (e && e.parameter) || {};
  var lijsten = (e && e.parameters) || {};   // meerdere waarden, bijv. aangevinkte keuzes

  // Verborgen veld ingevuld of binnen 3 seconden na openen verstuurd = spambot: doen alsof het gelukt is.
  // "duur" is de invultijd in milliseconden, gemeten in de browser (onafhankelijk van de klok).
  if (p.website || (p.duur !== undefined && p.duur !== '' && parseInt(p.duur, 10) < 3000)) return antwoord({ ok: true });

  var type = schoon(p.form, 40);
  var cfg = FORMULIEREN[type];
  if (!cfg) return antwoord({ ok: false, fout: 'onbekend formulier' });

  var g = {};
  cfg.velden.forEach(function (v) {
    var sleutel = v[0];
    var waarden = lijsten[sleutel] || lijsten[sleutel + '[]'];
    g[sleutel] = waarden && waarden.length > 1 ? schoon(waarden.join(', '), 1000) : schoon(p[sleutel] || p[sleutel + '[]'], 5000);
  });
  g.pagina = schoon(p.page || p.pagina, 300);

  // Controles (gelijk aan verzenden.php)
  var fouten = [];
  if (!g.naam) fouten.push('naam');
  if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(g.email)) fouten.push('email');
  if (type === 'contact' && !g.bericht) fouten.push('bericht');
  if (type === 'partner') {
    if (!g.bedrijf) fouten.push('bedrijf');
    if (!g.telefoon) fouten.push('telefoon');
  }
  if (fouten.length) return antwoord({ ok: false, fout: 'velden', velden: fouten });

  // 1. Opslaan in de spreadsheet (slot voorkomt dat twee inzendingen tegelijk botsen)
  var slot = LockService.getScriptLock();
  slot.waitLock(10000);
  try {
    blad(cfg).appendRow([new Date(), g.pagina].concat(cfg.velden.map(function (v) {
      return veiligVoorSheet(g[v[0]]);
    })));
  } finally {
    slot.releaseLock();
  }

  // 2. E-mail sturen. Lukt dat niet, dan staat de inzending in ieder geval al in de spreadsheet.
  try {
    var extra = ': ' + (g.bedrijf || g.naam);
    stuurMail(cfg, g, cfg.onderwerp + extra);
  } catch (fout) {
    console.error('Mail versturen mislukt: ' + fout);
  }

  return antwoord({ ok: true });
}

// Openen van de web-app-link in de browser: laat zien dat het script werkt
function doGet() {
  return ContentService.createTextOutput('Formulier-ontvanger NijmegenOnline is actief.');
}

// Eenmalig uitvoeren: maakt de tabbladen aan en zet de nachtelijke opruimtaak aan
function installeer() {
  Object.keys(FORMULIEREN).forEach(function (k) { blad(FORMULIEREN[k]); });
  var bestaat = ScriptApp.getProjectTriggers().some(function (t) {
    return t.getHandlerFunction() === 'opruimen';
  });
  if (!bestaat) {
    ScriptApp.newTrigger('opruimen').timeBased().everyDays(1).atHour(3).create();
  }
  opruimen();
}

// Verwijdert per tabblad de regels die ouder zijn dan de bewaartermijn
function opruimen() {
  Object.keys(FORMULIEREN).forEach(function (k) {
    var cfg = FORMULIEREN[k];
    var sheet = blad(cfg);
    var laatste = sheet.getLastRow();
    if (laatste < 2) return;
    var grens = new Date();
    grens.setMonth(grens.getMonth() - cfg.bewaarMaanden);
    var datums = sheet.getRange(2, 1, laatste - 1, 1).getValues();
    // Van onder naar boven, zodat regelnummers niet verschuiven
    for (var i = datums.length - 1; i >= 0; i--) {
      var d = datums[i][0];
      if (d instanceof Date && d < grens) sheet.deleteRow(i + 2);
    }
  });
}

function blad(cfg) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheetByName(cfg.tabblad);
  if (!sheet) {
    var kolommen = ['Datum', 'Pagina'].concat(cfg.velden.map(function (v) { return v[1]; }));
    sheet = ss.insertSheet(cfg.tabblad);
    sheet.appendRow(kolommen);
    sheet.getRange(1, 1, 1, kolommen.length).setFontWeight('bold');
    sheet.setFrozenRows(1);
    sheet.getRange('A:A').setNumberFormat('dd-mm-yyyy hh:mm');
  }
  return sheet;
}

function stuurMail(cfg, g, onderwerp) {
  var rijen = cfg.velden.map(function (v) { return [v[1], g[v[0]]]; }).concat([['Pagina', g.pagina]]);
  var html = '<table cellpadding="6" style="border-collapse:collapse;font-family:Arial,sans-serif;font-size:14px">' +
    rijen.filter(function (r) { return r[1]; }).map(function (r) {
      return '<tr><th align="left" valign="top" style="background:#EEF7E6">' + r[0] + '</th><td>' +
        html_(r[1]).replace(/\n/g, '<br>') + '</td></tr>';
    }).join('') + '</table>' +
    '<p style="font-family:Arial,sans-serif;font-size:12px;color:#777">Deze inzending staat ook in de Google Sheet "' +
    html_(SpreadsheetApp.getActiveSpreadsheet().getName()) + '", tabblad "' + cfg.tabblad + '".</p>';
  MailApp.sendEmail({
    to: ONTVANGER,
    replyTo: g.email,
    name: AFZENDER_NAAM,
    subject: onderwerp,
    htmlBody: html
  });
}

function antwoord(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON);
}

function schoon(waarde, max) {
  return String(waarde || '').trim().slice(0, max);
}

// Voorkomt dat tekst die met = + - @ begint als formule wordt uitgevoerd, en dat Sheets
// de voorloopnul van een telefoonnummer weghaalt (0612... wordt anders 612...)
function veiligVoorSheet(tekst) {
  return /^[=+\-@]/.test(tekst) || /^0\d/.test(tekst) ? "'" + tekst : tekst;
}

function html_(tekst) {
  return String(tekst || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}
