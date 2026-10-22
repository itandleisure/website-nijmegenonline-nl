/* Formulieren NijmegenOnline → Google Sheet + e-mail
   ---------------------------------------------------------------
   Dit script hoort bij een Google Sheet (Extensies → Apps Script).
   - Elk formulier van nijmegenonline.nl komt als nieuwe regel in een eigen tabblad:
     Contact, Partners, Bedrijven en Evenementen. Meegestuurde foto's komen in Google Drive.
   - Evenementen en bedrijven moeten eerst worden goedgekeurd: de mail heeft een knop Akkoord en een knop
     Afwijzen (of zet zelf "Akkoord" in de kolom Status). Elk uur haalt de website (GitHub Actions,
     tools/aanmeldingen.py) de goedgekeurde aanmeldingen op met ?actie=lijst, zet ze op de site en
     meldt ze terug, waarna de status "Gepubliceerd" wordt.
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
  },
  bedrijf: {
    tabblad: 'Bedrijven', bewaarMaanden: 24, onderwerp: 'Aanmelding bedrijvengids', goedkeuren: true,
    openbaar: ['bedrijf', 'categorie', 'adres', 'site', 'telefoon', 'bedrijfsmail', 'openingstijden', 'omschrijving'],
    velden: [['bedrijf', 'Bedrijf'], ['categorie', 'Soort bedrijf'], ['adres', 'Adres'], ['site', 'Website'],
      ['telefoon', 'Telefoon'], ['bedrijfsmail', 'E-mail bedrijf'], ['openingstijden', 'Openingstijden'],
      ['omschrijving', 'Omschrijving'], ['foto', 'Logo of foto'], ['naam', 'Contactpersoon'], ['email', 'E-mail']]
  },
  evenement: {
    tabblad: 'Evenementen', bewaarMaanden: 12, onderwerp: 'Evenement aangemeld', goedkeuren: true,
    openbaar: ['titel', 'datum', 'starttijd', 'eindtijd', 'omschrijving', 'locatie', 'adres'],
    velden: [['titel', 'Evenement'], ['datum', 'Datum'], ['starttijd', 'Begintijd'], ['eindtijd', 'Eindtijd'],
      ['omschrijving', 'Omschrijving'], ['locatie', 'Locatie'], ['adres', 'Adres'], ['foto', 'Foto'],
      ['naam', 'Naam'], ['email', 'E-mail'], ['notitie', 'Opmerking']]
  }
};

// Map in Google Drive voor meegestuurde foto's (wordt vanzelf aangemaakt)
var FOTOMAP = "NijmegenOnline formulierfoto's";

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
  // Foto als data-URL: opslaan in Drive, in de Sheet en de mail komt de link
  if (/^data:image\/(jpeg|png|webp);base64,/.test(p.foto || '')) {
    try {
      var foto = bewaarFoto(p.foto, schoon(p.foto_naam, 100) || 'foto', g.titel || g.bedrijf || g.naam);
      g.foto = foto.getUrl();
      g.fotoId = foto.getId();
    } catch (fout) {
      console.error('Foto opslaan mislukt: ' + fout);
      g.foto = 'Foto meegestuurd, maar opslaan in Drive mislukte';
    }
  } else {
    g.foto = '';
  }

  // Controles (gelijk aan verzenden.php)
  var fouten = [];
  if (!g.naam) fouten.push('naam');
  if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(g.email)) fouten.push('email');
  if (type === 'contact' && !g.bericht) fouten.push('bericht');
  if (type === 'evenement') {
    ['titel', 'datum', 'starttijd', 'eindtijd', 'omschrijving', 'locatie'].forEach(function (v) { if (!g[v]) fouten.push(v); });
  }
  if (type === 'bedrijf') {
    ['bedrijf', 'categorie', 'adres', 'telefoon', 'omschrijving'].forEach(function (v) { if (!g[v]) fouten.push(v); });
  }
  if (type === 'partner') {
    if (!g.bedrijf) fouten.push('bedrijf');
    if (!g.telefoon) fouten.push('telefoon');
  }
  if (fouten.length) return antwoord({ ok: false, fout: 'velden', velden: fouten });

  // 1. Opslaan in de spreadsheet (slot voorkomt dat twee inzendingen tegelijk botsen)
  var slot = LockService.getScriptLock();
  slot.waitLock(10000);
  try {
    var rij = [new Date(), g.pagina].concat(cfg.velden.map(function (v) {
      return veiligVoorSheet(g[v[0]]);
    }));
    if (cfg.goedkeuren) {
      g.id = Utilities.getUuid().slice(0, 8);
      rij = rij.concat([WACHT, g.id, g.fotoId || '']);
    }
    blad(cfg).appendRow(rij);
  } finally {
    slot.releaseLock();
  }

  // 2. E-mail sturen. Lukt dat niet, dan staat de inzending in ieder geval al in de spreadsheet.
  try {
    var extra = ': ' + (g.titel || g.bedrijf || g.naam);
    stuurMail(cfg, g, cfg.onderwerp + extra);
  } catch (fout) {
    console.error('Mail versturen mislukt: ' + fout);
  }

  return antwoord({ ok: true });
}

var WACHT = 'Wacht op akkoord';

// GET-verzoeken:
//  ?actie=akkoord|afwijzen&type=..&id=..&t=..   knoppen in de mail (t = handtekening, zie teken())
//  ?actie=lijst                                 goedgekeurde aanmeldingen voor de website (alleen openbare velden)
//  ?actie=gepubliceerd&type=..&id=..&t=..       de website meldt dat een aanmelding online staat
//  zonder actie                                 laat zien dat het script werkt
function doGet(e) {
  var p = (e && e.parameter) || {};
  if (p.actie === 'lijst') return antwoord(lijst());
  if (p.actie === 'akkoord' || p.actie === 'afwijzen' || p.actie === 'gepubliceerd') {
    var cfg = FORMULIEREN[p.type];
    if (!cfg || !cfg.goedkeuren || !p.id || p.t !== teken(p.type, p.id)) return pagina('Deze link klopt niet.');
    var nieuw = { akkoord: 'Akkoord', afwijzen: 'Afgewezen', gepubliceerd: 'Gepubliceerd' }[p.actie];
    var oud = zetStatus(cfg, p.id, nieuw);
    if (oud === null) return pagina('Deze aanmelding staat niet (meer) in de spreadsheet.');
    if (p.actie === 'gepubliceerd') return antwoord({ ok: true });
    if (oud === 'Gepubliceerd') return pagina('Deze aanmelding staat al op de website.');
    return pagina(p.actie === 'akkoord'
      ? 'Goedgekeurd. De aanmelding staat binnen een uur op nijmegenonline.nl.'
      : 'Afgewezen. De aanmelding komt niet op de website.');
  }
  return ContentService.createTextOutput('Formulier-ontvanger NijmegenOnline is actief.');
}

// Goedgekeurde, nog niet gepubliceerde aanmeldingen, met foto (base64) en de link om terug te melden
function lijst() {
  var uit = {};
  Object.keys(FORMULIEREN).forEach(function (type) {
    var cfg = FORMULIEREN[type];
    if (!cfg.goedkeuren) return;
    var sheet = blad(cfg);
    var k = kolommen(cfg);
    var rijen = sheet.getLastRow() > 1 ? sheet.getRange(2, 1, sheet.getLastRow() - 1, k.length).getValues() : [];
    uit[type] = rijen.filter(function (r) {
      return String(r[k.indexOf('Status')]).trim().toLowerCase() === 'akkoord';
    }).map(function (r) {
      var item = { id: String(r[k.indexOf('ID')]), ontvangen: r[0] instanceof Date ? r[0].toISOString() : '' };
      cfg.openbaar.forEach(function (veld) {
        var label = cfg.velden.filter(function (v) { return v[0] === veld; })[0][1];
        item[veld] = String(r[k.indexOf(label)]).replace(/^'/, '');
      });
      // Tijden en datums kan Sheets omzetten naar een datum; terugzetten naar tekst
      ['datum', 'starttijd', 'eindtijd'].forEach(function (veld) {
        var waarde = r[k.indexOf((cfg.velden.filter(function (v) { return v[0] === veld; })[0] || [])[1])];
        if (waarde instanceof Date) {
          item[veld] = Utilities.formatDate(waarde, 'Europe/Amsterdam', veld === 'datum' ? 'yyyy-MM-dd' : 'HH:mm');
        }
      });
      var fotoId = String(r[k.indexOf('Foto-ID')] || '');
      if (fotoId) {
        try {
          var blob = DriveApp.getFileById(fotoId).getBlob();
          item.foto = { type: blob.getContentType(), data: Utilities.base64Encode(blob.getBytes()) };
        } catch (fout) {
          console.error('Foto ' + fotoId + ' niet gevonden: ' + fout);
        }
      }
      item.gepubliceerd = ScriptApp.getService().getUrl() + '?actie=gepubliceerd&type=' + type + '&id=' +
        encodeURIComponent(item.id) + '&t=' + teken(type, item.id);
      return item;
    });
  });
  return uit;
}

// Zet de status van een aanmelding; geeft de oude status terug, of null als het ID niet bestaat
function zetStatus(cfg, id, status) {
  var sheet = blad(cfg);
  var k = kolommen(cfg);
  if (sheet.getLastRow() < 2) return null;
  var ids = sheet.getRange(2, k.indexOf('ID') + 1, sheet.getLastRow() - 1, 1).getValues();
  for (var i = 0; i < ids.length; i++) {
    if (String(ids[i][0]) === String(id)) {
      var cel = sheet.getRange(i + 2, k.indexOf('Status') + 1);
      var oud = String(cel.getValue());
      if (oud !== 'Gepubliceerd' || status === 'Gepubliceerd') cel.setValue(status);
      return oud;
    }
  }
  return null;
}

// Handtekening voor de links in de mail, met een geheime sleutel die alleen in dit script staat
function teken(type, id) {
  var props = PropertiesService.getScriptProperties();
  var geheim = props.getProperty('GEHEIM');
  if (!geheim) {
    geheim = Utilities.getUuid() + Utilities.getUuid();
    props.setProperty('GEHEIM', geheim);
  }
  var bytes = Utilities.computeHmacSha256Signature(type + ':' + id, geheim);
  return Utilities.base64EncodeWebSafe(bytes).replace(/=+$/, '').slice(0, 22);
}

function pagina(tekst) {
  return HtmlService.createHtmlOutput('<div style="font-family:Arial,sans-serif;font-size:18px;max-width:560px;margin:60px auto;' +
    'padding:24px;border:2px solid #539c20;border-radius:8px">' + html_(tekst) + '</div>').setTitle('NijmegenOnline');
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

function bewaarFoto(dataUrl, naam, titel) {
  var m = dataUrl.match(/^data:(image\/[a-z]+);base64,(.*)$/);
  var mappen = DriveApp.getFoldersByName(FOTOMAP);
  var map = mappen.hasNext() ? mappen.next() : DriveApp.createFolder(FOTOMAP);
  var bestand = map.createFile(Utilities.newBlob(Utilities.base64Decode(m[2]), m[1],
    Utilities.formatDate(new Date(), 'Europe/Amsterdam', 'yyyy-MM-dd') + ' ' + (titel || '').slice(0, 60) + ' - ' + naam));
  return bestand;
}

function blad(cfg) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheetByName(cfg.tabblad);
  if (!sheet) {
    sheet = ss.insertSheet(cfg.tabblad);
    sheet.setFrozenRows(1);
    sheet.getRange('A:A').setNumberFormat('dd-mm-yyyy hh:mm');
  }
  // Kopregel (ook bijwerken als er kolommen bij zijn gekomen, zoals Status bij een oudere versie)
  var kop = kolommen(cfg);
  if (sheet.getLastColumn() < kop.length || sheet.getRange(1, 1).getValue() !== 'Datum') {
    sheet.getRange(1, 1, 1, kop.length).setValues([kop]).setFontWeight('bold');
    // Datum en tijden als tekst bewaren, zodat Sheets er geen eigen notatie van maakt
    if (cfg.goedkeuren) sheet.getRange(1, 3, sheet.getMaxRows(), cfg.velden.length).setNumberFormat('@');
  }
  return sheet;
}

function kolommen(cfg) {
  return ['Datum', 'Pagina'].concat(cfg.velden.map(function (v) { return v[1]; }))
    .concat(cfg.goedkeuren ? ['Status', 'ID', 'Foto-ID'] : []);
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
  if (cfg.goedkeuren && g.id) {
    var type = Object.keys(FORMULIEREN).filter(function (k) { return FORMULIEREN[k] === cfg; })[0];
    var basis = ScriptApp.getService().getUrl() + '?type=' + type + '&id=' + g.id + '&t=' + teken(type, g.id) + '&actie=';
    var knop = 'display:inline-block;padding:12px 22px;border-radius:6px;font-family:Arial,sans-serif;font-weight:bold;' +
      'text-decoration:none;color:#fff;margin-right:10px;background:';
    html = '<p style="font-family:Arial,sans-serif;font-size:15px">Klopt alles? Met Akkoord komt deze aanmelding ' +
      'binnen een uur vanzelf op nijmegenonline.nl.</p><p>' +
      '<a href="' + basis + 'akkoord" style="' + knop + '#539c20">Akkoord, publiceren</a>' +
      '<a href="' + basis + 'afwijzen" style="' + knop + '#9aa1a9">Afwijzen</a></p>' + html;
    onderwerp = 'Goedkeuren: ' + onderwerp;
  }
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
