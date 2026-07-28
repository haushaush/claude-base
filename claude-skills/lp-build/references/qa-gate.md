# QA-Gate

Vor jedem `publish_page` selbst durchlaufen. **(M)** = manuell durch Dennis oder Lara, nicht durch dich erledigbar.

## Klon-Cleanup — Pflichtschritt eins

Wenn die Seite von einer bestehenden geklont wurde: Welcher Kunde war vorher drauf? Dann **alle** Vorkommen ersetzen — Name, Logo, Bilder, Berater-Geschlecht, Produktversprechen — auf allen Seiten, im Funnel, im Impressum, im Footer, in den Fehlermeldungen und auf der Dankesseite.

Prüfung: den Namen des Vorgängers im gerenderten Text der Live-Seite suchen. Kein Treffer = Teil von „erledigt".

Besonders häufig übersehen: Consent-Text, OG-Description, Seitentitel im Browser-Tab, Alt-Texte.

## A — Projekt

Titel passt · richtige Startseite · Sprache DE · Favicon · Onepage-Banner aus · Indexierung nach Standard · Query-Parameter-Weiterleitung aus

## B — Domain

Kunden-Domain verbinden **(M)** oder kurze Marken-Subdomain (`kunde.onepage.me`). Nach einer Subdomain-Änderung: alte URL testen, sie liefert 404, und alle Referenzen in Doku und Anzeigen nachziehen.

## C — Integration

Analytics an · **Pixel nur durch Lara (M)** · Cookie-Banner aktiv und Richtlinie-Link korrekt · Kollaboration leer

## D — Rechtliche Unterseite

Seitenlink und Indexierung an · Titel „Impressum und Datenschutz | [Kunde]" · Sharing-Bild · H-Tags · Alt-Texte · **kein alter Kunde im Impressum** · Footer-Links und Logo korrekt · alle Pflichtangaben vorhanden (siehe `lp-compliance`)

## E — Startseite und weitere

SEO-Claim mit Kundenname · Sharing-Bild · H-Tags in sinnvoller Hierarchie · alle Button-Connections korrekt (Scroll-to-Section, Unterseite) · Handy und Desktop visuell konsistent · Überschriften nicht zu lang

## F — Funnel

Tracking-Spec gesetzt oder dokumentiert · alle Schritte erforderlich · „weiter nach Auswahl" bei Kacheln · Frage im visuellen Fokus · alle Onboarding-Schritte enthalten · **Preis Kontaktseite > Anzeigenpreis** · Consent vorhanden und Link korrekt · Filterlogik für jeden Pfad durchgespielt · Dankesseite stimmig

## G — Global

Duzen/Siezen einheitlich · **richtiges Brand-Logo**, kein fremdes · Berater-Name und -Geschlecht korrekt · Preise über die ganze Seite konsistent · keine Top-Nav · keine Emoji-Struktur-Icons · Info-Dichte schlank · Zahlen seriös · einmal komplett durchgescrollt, Desktop und 360 px

## Render-Check

Nicht nur die Checkliste abhaken — die Seite tatsächlich ansehen:

- Desktop **und** 360 px
- Bei Reveal, Count-up und Stacking kurz warten und mit echtem Scroll testen
- Overlap, Cropping, weiß auf weiß, Proportionen, Left-Align unter zentriertem Parent, Mobile-Umbruch
- Trennlinien: klebt irgendwo Text an einer Linie?
- Fehler fixen, neu prüfen

Ab drei Sections an `lp-render-qa` delegieren.

## „Erledigt" heißt

- Klon-Cleanup sauber
- QA A–G durch
- Render-Check auf beiden Größen bestanden
- Pixel hinterlegt **(M, Lara)**
- Tracking feuert, View Content und Contact getestet **(M, Dennis)**
- Alle Links und Buttons funktionieren
- Funnel-Logik und Filter geprüft
- Preis-Anchoring korrekt
- Ansprache einheitlich
- Zweithaken durch eine zweite Person
- Kundenabnahme **(M)**

Erst dann publishen und übergeben.

## Übergabe-Log

Jede Übergabe enthält:

1. Was gebaut wurde, in einem Absatz
2. Welche Zahlen verwendet wurden, mit Quelle und Abrufdatum
3. Welche Compliance-Entscheidungen getroffen wurden und warum
4. Die manuellen Rest-To-dos, nach Verantwortlichem sortiert
5. Was offen bleibt und wen es blockiert

Kein „fertig" ohne diese fünf Punkte.
