"""Een icoon per categorie van de bedrijvengids (besluit Frans, 26-10-2026): op de kaartpinnen, in de categorielijst en
boven de categoriepagina. Eén stijl voor alles: lijntekening, 24x24, lijndikte 2, ronde hoeken, kleur via currentColor.

Een categorie zonder eigen icoon krijgt het icoon van haar groep. Gebruik: icoon(slug) of icoon(slug, groep)."""

# Alleen de inhoud van de svg; de omhulling staat in icoon()
ICONEN = {
    # Eten en drinken
    "restaurant": '<path d="M5 3v18M3 3v5a2 2 0 0 0 4 0V3M19 3c-2 1-3 3-3 6v3h3v9"/>',
    "lunch": '<path d="M4 11h16M5 11a7 7 0 0 1 14 0M3 15h18l-1 4H4z"/>',
    "cafe": '<path d="M7 4h9v9a4.5 4.5 0 0 1-9 0zM16 7h2a2.5 2.5 0 0 1 0 5h-2M5 21h12"/>',
    "koffiezaak": '<path d="M5 9h11v6a4 4 0 0 1-4 4H9a4 4 0 0 1-4-4zM16 10h1.5a2.5 2.5 0 0 1 0 5H16M8 3c0 1.5 1 1.5 1 3M12 3c0 1.5 1 1.5 1 3"/>',
    "bakkerij": '<path d="M3 13c0-3 4-6 9-6s9 3 9 6c0 2-1 3-3 3H6c-2 0-3-1-3-3zM8 10l1 3M12 9v4M16 10l-1 3"/>',
    "bierbrouwerij": '<path d="M6 8h9v12H6zM15 11h2a2 2 0 0 1 2 2v3a2 2 0 0 1-2 2h-2M6 8a3 3 0 0 1 3-3 3 3 0 0 1 5 0 2.5 2.5 0 0 1 1 3"/>',
    "afhaal": '<path d="M5 8h14l-1.5 12h-11zM9 8V6a3 3 0 0 1 6 0v2M9 12h6"/>',
    "catering": '<path d="M3 17h18M5 17a7 7 0 0 1 14 0M12 10V8M10 8h4M8 21h8"/>',
    "ijssalon": '<path d="M8 11l4 10 4-10M8 11a4 4 0 1 1 8 0M8 11h8M10 5a2.5 2.5 0 0 1 4 0"/>',
    "cocktailbar": '<path d="M4 4h16l-8 9zM12 13v7M8 20h8M14 4l2-2"/>',
    "sushi": '<path d="M4 12a8 4 0 0 0 16 0M4 12V8a8 4 0 0 1 16 0v4M4 8a8 4 0 0 0 16 0M9 8a3 1.5 0 0 0 6 0"/>',
    "pizza": '<path d="M12 3l9 16H3zM12 3c3 3 6 5 9 7M12 3c-3 3-6 5-9 7M10 14h.01M14 12h.01M12 17h.01"/>',
    "chinees": '<path d="M4 10h16a8 8 0 0 1-16 0zM5 10l9-7M9 10l9-7M8 19h8"/>',
    "ontbijt-en-brunch": '<path d="M5 9h9v6a4 4 0 0 1-4 4H9a4 4 0 0 1-4-4zM14 10h1.5a2.5 2.5 0 0 1 0 5H14M18 5a2 2 0 1 1 3 2l-3 2"/>',
    "high-tea": '<path d="M6 12h12a6 6 0 0 1-12 0zM18 13h1.5a2 2 0 0 1 0 4H17M4 20h16M12 3c-1 1-1 2 0 3s1 2 0 3"/>',
    "tapas": '<path d="M3 12a4 4 0 0 1 8 0zM13 12a4 4 0 0 1 8 0zM3 12h8M13 12h8M7 12v6M17 12v6M4 20h16"/>',
    "all-you-can-eat": '<path d="M3 12h18M4 12a8 8 0 0 1 16 0M12 4V2M8 16l-1 4M16 16l1 4M9 20h6"/>',
    # Uitgaan en vrije tijd
    "uitjes": '<path d="M4 7h16v4a2 2 0 0 0 0 4v2H4v-2a2 2 0 0 0 0-4zM9 7v10"/>',
    "binnenuitjes": '<path d="M12 3l9 7v11H3V10zM9 21v-6h6v6M10 14h.01M14 14h.01"/>',
    "musea": '<path d="M3 21h18M5 21V10M9 21V10M15 21V10M19 21V10M3 10l9-6 9 6zM3 10h18"/>',
    "podia": '<path d="M3 5h18v10H3zM7 15v4M17 15v4M5 21h14M8 10a4 4 0 0 0 8 0"/>',
    "bioscoop": '<path d="M3 7h18v12H3zM3 11h18M7 7v4M12 7v4M17 7v4M7 15h.01M12 15h.01M17 15h.01"/>',
    "galerie": '<path d="M3 4h18v14H3zM3 14l5-5 4 4 3-3 6 6M15 8h.01M8 22h8"/>',
    "zaalverhuur": '<path d="M4 20V8l8-5 8 5v12M4 20h16M10 20v-5h4v5M8 11h.01M12 11h.01M16 11h.01"/>',
    "sauna": '<path d="M4 12h16v3a4 4 0 0 1-4 4H8a4 4 0 0 1-4-4zM7 9c0-1.5 1-1.5 1-3M12 9c0-1.5 1-1.5 1-3M17 9c0-1.5 1-1.5 1-3M8 19v2M16 19v2"/>',
    # Sport en beweging
    "sportschool": '<path d="M6 8v8M3 10v4M18 8v8M21 10v4M6 12h12"/>',
    "dansschool": '<path d="M12 5a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3zM8 9l4-2 4 3-2 3 3 2-1 6M12 10l-1 5-4 6M8 9l-3 3"/>',
    "yoga": '<path d="M12 6a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3zM12 9v5M12 14l-6 4h4l2-2 2 2h4zM6 11l6-2 6 2"/>',
    "vechtsport": '<path d="M7 11V5a2 2 0 0 1 4 0v6M11 9V4a2 2 0 0 1 4 0v7M15 10V6a2 2 0 0 1 4 0v8a6 6 0 0 1-12 0v-4a2 2 0 0 1 4 0"/>',
    "zwembad": '<path d="M3 18c2 0 2-1.5 4-1.5s2 1.5 4 1.5 2-1.5 4-1.5 2 1.5 4 1.5M3 13c2 0 2-1.5 4-1.5s2 1.5 4 1.5 2-1.5 4-1.5 2 1.5 4 1.5M8 11V5a2 2 0 0 1 4 0M16 11V5a2 2 0 0 0-4 0"/>',
    "padel": '<path d="M14 4a5 5 0 0 1 5 5c0 3-3 5-5 6l-5 5-3-3 5-5c1-2 3-5 6-6zM13 8h.01M15 10h.01M17 8h.01"/>',
    "sportvereniging": '<path d="M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18zM12 3v4l3 2 1 4-3 2h-2l-3-2 1-4 3-2M4 10l3 3M20 10l-3 3M9 20l3-3 3 3"/>',
    # Beauty en wellness
    "kapper": '<path d="M6 8a2 2 0 1 0 0-4 2 2 0 0 0 0 4zM6 20a2 2 0 1 0 0-4 2 2 0 0 0 0 4zM20 4L8 15M14 10l6 10"/>',
    "barbershop": '<path d="M8 4h8v16H8zM8 8l8 4M8 12l8 4M8 16l8-4M8 12l8-4M7 2h10M7 22h10"/>',
    "massagesalon": '<path d="M4 15h16v2H4zM6 17v3M18 17v3M8 15V9a4 4 0 0 1 8 0v6M12 5V3"/>',
    "schoonheidssalon": '<path d="M12 3c-3 4-6 6-6 10a6 6 0 0 0 12 0c0-4-3-6-6-10zM10 16a2 2 0 0 0 2 2"/>',
    "nagelsalon": '<path d="M9 3h6v10a3 3 0 0 1-6 0zM9 7h6M12 16v5M9 21h6"/>',
    "pedicure": '<path d="M6 21c-2-5 0-9 2-12 2-3 5-4 7-3 2 1 1 4-1 6-3 3-4 5-4 9zM5 8a2 2 0 1 0 0-4 2 2 0 0 0 0 4z"/>',
    "permanente-make-up": '<path d="M4 20l3-1 11-11-2-2L5 17zM14 6l2 2M12 4l4-2 4 4-2 4"/>',
    "tattoo": '<path d="M4 20l5-5M9 15l4-9 2 2-9 7zM13 6l4-4 3 3-4 4M8 16l-1-1"/>',
    # Gezondheid en welzijn
    "fysiotherapeut": '<path d="M12 6a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3zM10 8h4l3 5-3 1v7M10 8l-3 5 3 1v7M10 14h4"/>',
    "dietist": '<path d="M12 9c-4 0-6 3-6 6s3 6 6 6 6-3 6-6-2-6-6-6zM12 9c0-3 1-5 3-6M12 9c-1-2-3-3-5-3"/>',
    "psycholoog": '<path d="M9 3a5 5 0 0 0-5 5v3l-2 3h2v3a3 3 0 0 0 3 3h3v1M9 3h3a6 6 0 0 1 6 6v3a5 5 0 0 1-5 5v4M10 9h.01"/>',
    "coach": '<path d="M12 3l2.5 5 5.5.8-4 3.9 1 5.5-5-2.6-5 2.6 1-5.5-4-3.9L9.5 8zM4 21h16"/>',
    "alternatief": '<path d="M12 21c-5-3-8-7-8-11a4 4 0 0 1 8-1 4 4 0 0 1 8 1c0 4-3 8-8 11zM12 9v8M9 13h6"/>',
    "opticien": '<path d="M2 12a4 4 0 0 0 8 0 4 4 0 0 0-8 0zM14 12a4 4 0 0 0 8 0 4 4 0 0 0-8 0zM10 12h4M2 12l2-5M22 12l-2-5"/>',
    "huisarts": '<path d="M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18zM12 8v8M8 12h8"/>',
    "dierenarts": '<path d="M12 21c-3 0-5-2-5-4 0-3 3-4 5-4s5 1 5 4c0 2-2 4-5 4zM7 10a2 2 0 1 0 0-4 2 2 0 0 0 0 4zM17 10a2 2 0 1 0 0-4 2 2 0 0 0 0 4zM4 15a2 2 0 1 0 0-4 2 2 0 0 0 0 4zM20 15a2 2 0 1 0 0-4 2 2 0 0 0 0 4z"/>',
    "tandarts": '<path d="M8 3c2 0 3 1 4 1s2-1 4-1 4 2 4 5c0 2-1 3-2 6s-1 7-3 7-2-5-3-5-1 5-3 5-2-4-3-7-2-4-2-6c0-3 2-5 4-5z"/>',
    # Overnachten
    "hotel": '<path d="M3 21V7l9-4 9 4v14M3 21h18M7 11h2M11 11h2M15 11h2M7 15h2M11 15h2M15 15h2M10 21v-4h4v4"/>',
    "bed-and-breakfast": '<path d="M3 18v-7a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v7M3 18h18M3 18v2M21 18v2M6 9V6h5v3M7 13h3"/>',
    "camping": '<path d="M12 3L2 21h20zM12 3v18M8 21l4-8 4 8"/>',
    # Winkelen
    "kledingwinkel": '<path d="M9 3l3 2 3-2 5 3-2 4-2-1v12H8V9l-2 1-2-4z"/>',
    "tweedehands-winkel": '<path d="M3 12a9 9 0 0 1 15-6.7M21 12a9 9 0 0 1-15 6.7M18 2v4h-4M6 22v-4h4"/>',
    "woonwinkel": '<path d="M5 12V8a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v4M3 12h18v5H3zM5 17v2M19 17v2"/>',
    "juwelier": '<path d="M6 3h12l4 6-10 12L2 9zM2 9h20M9 3l3 6 3-6M8 9l4 12 4-12"/>',
    "bloemist": '<path d="M12 10a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM12 10a3 3 0 1 0 0 6 3 3 0 0 0 0-6zM9 13a3 3 0 1 1 0-6M15 13a3 3 0 1 0 0-6M12 16v6M12 20c0-2 2-3 4-3M12 20c0-2-2-3-4-3"/>',
    "hobbywinkel": '<path d="M4 20l4-1L19 8l-3-3L5 16zM14 7l3 3M4 20l1-4M15 3a2 2 0 0 1 3 0l3 3a2 2 0 0 1 0 3"/>',
    "parfumerie": '<path d="M8 10h8v10a2 2 0 0 1-2 2h-4a2 2 0 0 1-2-2zM10 10V7h4v3M9 4h6M12 4v3M4 6a2 2 0 1 0 0-1"/>',
    "elektronica": '<path d="M7 2h10a2 2 0 0 1 2 2v16a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2zM5 6h14M5 18h14M12 20h.01"/>',
    "fietsenwinkel": '<path d="M6 19a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7zM18 19a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7zM6 15.5L9 8h6l3 7.5M9 8L12 15.5l5-7.5M13 5h3"/>',
    "boekhandel": '<path d="M4 4h6a3 3 0 0 1 3 3v13a2 2 0 0 0-2-2H4zM20 4h-6a3 3 0 0 0-3 3v13a2 2 0 0 1 2-2h7z"/>',
    # Wonen en klussen
    "aannemersbedrijf": '<path d="M3 21h18M5 21V10l7-6 7 6v11M9 21v-6h6v6M12 4V2"/>',
    "schilder": '<path d="M4 4h12v5H4zM16 6h3v6h-8v4M10 16h2v6h-2z"/>',
    "loodgieter": '<path d="M14 3l7 7-3 3-7-7zM12 6l-7 7a3 3 0 0 0 4 4l7-7M4 21l3-3"/>',
    "hovenier": '<path d="M12 21v-8M12 13c-4 0-7-3-7-7 4 0 7 3 7 7zM12 13c4 0 7-3 7-7-4 0-7 3-7 7zM6 21h12"/>',
    "zonnepanelen": '<path d="M4 4h16v11H4zM4 9.5h16M9.5 4v11M14.5 4v11M8 20h8M12 15v5"/>',
    "meubelmaker": '<path d="M5 20V9h14v11M5 9V4h14v5M9 9v11M15 9v11M5 14h14"/>',
    "makelaar": '<path d="M3 11l9-8 9 8M5 10v10h14V10M10 20v-6h4v6M15 8l3-3"/>',
    "dakdekker": '<path d="M2 12l10-8 10 8M5 10v10h14V10M7 10h10M8 14h8"/>',
    "slotenmaker": '<path d="M5 11h14v10H5zM8 11V7a4 4 0 0 1 8 0v4M12 15v3"/>',
    "elektricien": '<path d="M13 2L5 13h6l-1 9 9-12h-6z"/>',
    "verhuisbedrijf": '<path d="M2 7h12v10H2zM14 11h4l3 3v3h-7M6 20a2 2 0 1 0 0-4 2 2 0 0 0 0 4zM17 20a2 2 0 1 0 0-4 2 2 0 0 0 0 4z"/>',
    "schoonmaakbedrijf": '<path d="M6 3h4v9H6zM4 12h8l1 9H3zM14 5h7M14 9h5M14 13h3"/>',
    # Zakelijk en diensten
    "marketingbureau": '<path d="M3 11l15-6v14L3 13zM3 11v2M7 13v6h3M18 9a3 3 0 0 1 0 6"/>',
    "accountant-boekhouder": '<path d="M5 3h14v18H5zM9 7h6M9 11h.01M12 11h.01M15 11h.01M9 14h.01M12 14h.01M15 14h.01M9 17h.01M12 17h3"/>',
    "advocatenkantoor": '<path d="M12 3v18M8 21h8M4 7h16M6 7l-3 7a3 3 0 0 0 6 0zM18 7l-3 7a3 3 0 0 0 6 0z"/>',
    "notaris": '<path d="M6 3h12v18H6zM9 8h6M9 12h6M9 16h3M15 15l2 2 1-3"/>',
    "hypotheekadviseur": '<path d="M3 11l9-8 9 8M5 10v10h14V10M12 12v6M10 14h3a1.5 1.5 0 0 1 0 3h-3"/>',
    "verzekeraar": '<path d="M12 2l8 3v6c0 5-3 9-8 11-5-2-8-6-8-11V5zM9 12l2 2 4-4"/>',
    "uitzendbureau": '<path d="M9 11a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM3 21v-2a4 4 0 0 1 4-4h4a4 4 0 0 1 4 4v2M16 5a3 3 0 0 1 0 6M21 21v-2a4 4 0 0 0-3-3.9"/>',
    "opleiding-en-training": '<path d="M2 9l10-5 10 5-10 5zM6 11v5c3 3 9 3 12 0v-5M22 9v6"/>',
    "rijschool": '<path d="M5 11l2-5h10l2 5M3 11h18v6H3zM6 17v2M18 17v2M7 14h.01M17 14h.01M9 7V4h6v3"/>',
    "fotograaf": '<path d="M4 8h3l2-3h6l2 3h3v11H4zM12 17a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7z"/>',
    "autobedrijf": '<path d="M5 11l2-5h10l2 5M3 11h18v6H3zM6 17v2M18 17v2M7 14h.01M17 14h.01"/>',
    "kinderopvang": '<path d="M12 8a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5zM7 21v-7a5 5 0 0 1 10 0v7M9 21v-4M15 21v-4"/>',
    "taxi": '<path d="M5 11l2-5h10l2 5M3 11h18v6H3zM6 17v2M18 17v2M7 14h.01M17 14h.01M10 6V3h4v3"/>',
    "begrafenis": '<path d="M12 3v18M7 8h10M4 21h16"/>',
    "hondentraining": '<path d="M12 21c-3 0-5-2-5-4 0-3 3-4 5-4s5 1 5 4c0 2-2 4-5 4zM7 10a2 2 0 1 0 0-4 2 2 0 0 0 0 4zM17 10a2 2 0 1 0 0-4 2 2 0 0 0 0 4zM4 15a2 2 0 1 0 0-4 2 2 0 0 0 0 4zM20 15a2 2 0 1 0 0-4 2 2 0 0 0 0 4z"/>',
}

# Per groep een icoon voor categorieën die er zelf geen hebben, en voor de knoppen boven de kaart
GROEPEN = {
    "Eten en drinken": "restaurant", "Uitgaan en vrije tijd": "uitjes", "Sport en beweging": "sportschool",
    "Beauty en wellness": "schoonheidssalon", "Gezondheid en welzijn": "huisarts", "Overnachten": "hotel",
    "Winkelen": "kledingwinkel", "Wonen en klussen": "aannemersbedrijf", "Zakelijk en diensten": "accountant-boekhouder",
}
STANDAARD = '<path d="M12 21s-7-6-7-11a7 7 0 0 1 14 0c0 5-7 11-7 11zM12 13a3 3 0 1 0 0-6 3 3 0 0 0 0 6z"/>'


def inhoud(slug, groep=None):
    return ICONEN.get(slug) or ICONEN.get(GROEPEN.get(groep or "", ""), STANDAARD)


def icoon(slug, groep=None, klasse="icoon"):
    return ('<svg class="%s" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" '
            'stroke-linejoin="round" aria-hidden="true">%s</svg>' % (klasse, inhoud(slug, groep)))
