# Facebook en Instagram koppelen aan de site

Eenmalig, ongeveer 45 minuten. Daarna plaatst `.github/workflows/social.yml` elke dag zelf een post (zie
`tools/social.py`). Het enige wat de site nodig heeft is één token dat niet verloopt: een token van een
*systeemgebruiker* in Meta Business. Dat kan alleen de beheerder van de Facebookpagina aanmaken.

## 1. Instagram zakelijk maken en aan de pagina koppelen

1. Instagram-app → profiel → ☰ → *Accounttype en tools* → *Overschakelen naar professioneel account* → *Bedrijf*.
   (Staat er al "Professioneel dashboard", dan is dit al gebeurd.)
2. Facebook → de pagina NijmegenOnline → *Instellingen* → *Gekoppelde accounts* → *Instagram* → *Account koppelen*.

## 2. Pagina en Instagram in een Business-portfolio

1. Ga naar <https://business.facebook.com> en maak een Business-portfolio aan als je die nog niet hebt
   (naam: NijmegenOnline of IT & Leisure Solutions).
2. *Instellingen* → *Accounts* → *Pagina's* → *Toevoegen* → de pagina NijmegenOnline.
3. *Accounts* → *Instagram-accounts* → *Toevoegen* → het Instagram-account.

## 3. Een Meta-app maken

1. Ga naar <https://developers.facebook.com/apps> → *App maken*.
2. Naam: `NijmegenOnline site`. Kies bij het gebruik *Overige* en daarna het type *Zakelijk* (Business), en koppel
   de app aan het Business-portfolio van stap 2.
3. Voeg in de app de producten (use cases) toe voor het beheren van een pagina en voor Instagram
   (*Instagram API met Facebook-login*). De app hoeft niet "live" of door Meta beoordeeld te worden: hij plaatst
   alleen op je eigen pagina.

## 4. Systeemgebruiker en token

1. Business-instellingen → *Gebruikers* → *Systeemgebruikers* → *Toevoegen*: naam `site-bot`, rol *Beheerder*.
2. Bij `site-bot` → *Middelen toewijzen*: de pagina (volledige controle), het Instagram-account (volledige
   controle) en de app.
3. *Nieuw token genereren* → kies de app → verloopt: *Nooit* → vink aan:
   `pages_show_list`, `pages_read_engagement`, `pages_manage_posts`, `instagram_basic`,
   `instagram_content_publish`, `business_management`.
4. Kopieer het token (je ziet het maar één keer).

Lukt stap 3 of 4 niet omdat een recht niet te kiezen is, stuur dan een schermafdruk: soms vraagt Meta eerst een
bedrijfsverificatie van het portfolio.

## 5. Token in GitHub zetten

GitHub → deze repository → *Settings* → *Secrets and variables* → *Actions* → *New repository secret*:

- `META_TOKEN`: het token van stap 4.
- `META_PAGE_ID` (optioneel, alleen als het script de verkeerde pagina pakt): het pagina-ID, te vinden op de
  Facebookpagina onder *Info* → *Paginatransparantie*.

`ANTHROPIC_API_KEY` staat er al (wordt ook gebruikt voor de bedrijvengids).

## 6. Testen en aanzetten

1. GitHub → *Actions* → *Social media* → *Run workflow* → stap `plaatsen`. Zolang `aan` op `false` staat, test dit
   alleen de koppeling: in het logboek staat dan "pagina NijmegenOnline, Instagram 1784…". Er wordt niets geplaatst.
2. Zet in `data/social-instellingen.json` `"aan": true` (of vraag Claude dat te doen).
3. De eerste 14 posts komen elke ochtend ook in een GitHub-issue (je krijgt er een mail van). Niets doen = de post gaat
   rond het middaguur online. Sluit je het issue, dan wordt hij overgeslagen. Daarna gaat het helemaal vanzelf.

## Als het misgaat

- Mislukt een run (bijvoorbeeld omdat het token is ingetrokken), dan stuurt GitHub een mail over de mislukte workflow.
  Een nieuw token maken (stap 4.3) en het secret vervangen is genoeg.
- Uitzetten: `"aan": false` in `data/social-instellingen.json`. Alleen Instagram of alleen Facebook:
  `"facebook": false` of `"instagram": false`.
- Een evenement dat van de site wordt verwijderd (`data/evenementen-verwijderd.txt`) haalt het script ook van
  Facebook en, waar Meta dat toestaat, van Instagram. Lukt dat laatste niet, dan staat er een waarschuwing in het
  logboek van de run.
