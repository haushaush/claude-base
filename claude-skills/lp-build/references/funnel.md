# Funnel

Der kritischste Teil. Hier entscheidet sich die Conversion, und hier passieren die teuersten Fehler.

## Grundaufbau

```
Quiz-Schritte → Filterlogik → Kontaktdaten/Opt-in → Dankesseite
```

Der Funnel **ist** der Hero, nicht eine Karte im Hero. Er bekommt Überschrift, Subline und Trennlinie wie eine Hero-Section.

## Aufbau je Schritt (mobile first)

```
Sticky Header (Logo, Telefon, Desktop-CTA)
Fortschrittsleiste
Badge-Pill (fetter Teil + leichter Teil)
[nur Schritt 1] Große Headline mit Gewichtskontrast + Subline + Trennlinie
Frage  — ab Schritt 2 ist die Frage selbst die große Headline
Antwortkacheln
Sicherheits- und Zeithinweis
── Trust-Block, volle Breite, UNTER dem Schritt ──
```

**Typografiehierarchie ist Pflicht.** Badge klein und in Caps, Frage groß, Hinweis klein. Die Frage muss der optisch dominante Text sein — sie steht in der Hierarchie über der Seiten-Überschrift.

**Trust-Elemente gehören unter den Schritt, nicht daneben.** Seitlich platzierte Trust-Panels sind nicht conversionfördernd; sie konkurrieren mit der Frage um Aufmerksamkeit.

**Kein Zurück-Button.** Der Funnel läuft nur vorwärts.

## Trust-Block je Schritt

Nicht jeder Schritt braucht einen. Pro Schritt evaluieren: Bewertungen, animierte Statistik, Karten, Kennzahl — oder nichts. Bei Schritten, die reine Dateneingabe sind (Freitext, Geburtsdatum), meist nichts.

Bewährte Typen:

| Typ | Wann |
|---|---|
| Bewertungsleiste (Sterne, hochzählende Note, drei Vorteile) | erster Schritt und Kontaktschritt |
| Zwei bis vier Karten mit Icon und Kurztext | erklärungsbedürftige Auswahl |
| Karte mit hochzählender Kennzahl | wenn eine Zahl das Argument trägt |
| Zwei animierte Balken | Vergleich zweier Zustände |
| Prozentring | ein einzelner Anteil |

Alles animiert, nichts statisch. Karten steigen gestaffelt ein, Icons poppen, Kennzahlen zählen hoch. Statische Karten wirken wie ein unfertiger Entwurf.

Die Trust-Blöcke gehören in zwei Builder-Tabellen (Block je Schritt, Karten je Block), damit Dennis sie ohne Code ändern kann.

## Antwortkacheln

**Große Kacheln** mit Bild- oder Icon-Fläche und Label-Leiste: wenige, gleichrangige Optionen (Ja/Nein, Berufsgruppe, Kinder).
**Breite Zeilen** mit kleinem Icon: Auswahllisten mit vier und mehr Optionen.

Bei Berufs- oder Lebenssituationswahl **Bilder statt Icons** — deutlich höhere Wiedererkennung. Icon bleibt als Fallback, solange kein Bild hochgeladen ist.

Kacheln ohne Weiter-Button: „weiter nach Auswahl" aktivieren. Mehrfachauswahl braucht einen Weiter-Button.

Jeder Abfrageschritt ist **erforderlich**.

## Filterlogik

Ausschlusskriterien filtern *vor* dem Kontaktschritt, nicht danach. Wer nicht infrage kommt, sieht einen freundlichen Ausschluss-Screen mit Telefonnummer — kein Formular.

Typische Filter:

| Nische | Filter |
|---|---|
| PKV | Angestellte unter der Versicherungspflichtgrenze raus · Jahrgang außerhalb der Zielspanne raus |
| TKV | Tier älter als die Annahmegrenze raus (oft 7 oder 8 Jahre) |
| BU | bestimmte Risikoberufe und Altersgrenzen raus |
| Zahnzusatz | laufende Behandlung oder angeratene Maßnahme raus |
| Wohngebäude | Mieter raus |

Die Logik komplett gegenprüfen. Ein falscher Filter kostet entweder Leads oder produziert Müll-Leads — beides teuer.

## Preis-Anchoring

Der Beitragsrahmen erscheint **erst im Opt-in-Schritt**, abgeleitet aus einer vorherigen Antwort (meist Berufsgruppe oder Tarifziel). Als animiert hochzählender „ab"-Betrag, groß, mit Sternchen und Fußnote.

**Der Preis auf der Kontaktdatenseite muss höher sein als der Anzeigenpreis.** Der Anzeigenpreis ist die Vorankündigung, der Funnel-Preis der Anker. Ist die niedrigste Spanne 90 €, muss die Anzeige darunter liegen.

Die volle Spanne nur im Kleingedruckten, plus Disclaimer: unverbindlicher Orientierungswert, kein Angebot, tatsächlicher Beitrag abhängig von Eintrittsalter, Gesundheitszustand und Tarif.

## Opt-in-Schritt

```
Überschrift („Geschafft! Ihr individueller Beitrag:")
ab [hochzählender Betrag] *
Fußnote zum Sternchen
Zwischenüberschrift (Aufforderung zur Kontaktaufnahme)
Info-Box (Datenverwendung) + Warn-Box (gültige Telefonnummer nötig)
4 Felder: Name, E-Mail, Telefon, PLZ — groß, mit Icon, ohne sichtbares Label
Consent-Checkbox mit Link auf /rechtliches
Button, ganze Breite, leichte Puls-Animation, Sublabel „kostenfrei und unverbindlich"
Fineprint
```

Der Button-Puls ist ein Box-Shadow-Ring, der bei Hover pausiert und unter `prefers-reduced-motion` aus ist.

## Consent

- Checkbox vorhanden, nicht vorausgewählt
- Link „Datenschutzbestimmungen" auf die korrekte rechtliche Unterseite
- **Consent-Text muss zum echten Vermittlerstatus passen.** Bei Ausschließlichkeit oder gebundener Vermittlung keine „Weitergabe an Dritte, Makler oder andere Anbieter"
- Die im Funnel erhobenen Felder müssen 1:1 in der Datenschutzerklärung stehen. Ändert sich der Funnel, ändert sich die Datenschutzerklärung mit

## CRM-Formular

`create_crm_form` mit allen Antwortfeldern plus Kontaktdaten plus Consent. Feld-Keys sprechend benennen — sie tauchen im Lead-Export und in der Datenschutzerklärung auf.

Den abgeleiteten Beitragsrahmen als eigenes Feld mitschicken. Der Vertrieb muss vor dem Anruf wissen, welche Erwartung geweckt wurde.

## Tracking-Spezifikation

Pro Schritt festhalten:

- Pixel 1 = Formframe View → **View Content**
- Pixel 2 = Formframe Data → **Contact**

Ist das per MCP nicht setzbar, wird es als manuelles To-do an Dennis und Lara dokumentiert. Nie als erledigt melden.

**Der Pixel darf erst scharf geschaltet werden, wenn das Cookie-Banner aktiv ist und der Pixel-Abschnitt in der Datenschutzerklärung steht.** Sonst fehlt die Einwilligungsgrundlage.

## Gegen-Checks vor publish

- Alle vom Kunden im Onboarding gewünschten Schritte enthalten (einer mehr ist ok, einer weniger nicht)
- Filterlogik durchgespielt, für jeden Pfad
- Preis Kontaktseite > Anzeigenpreis
- Consent-Text passt zum Status, Link zeigt auf die richtige Seite
- Alle Schritte erforderlich
- „weiter nach Auswahl" bei Kachel-Schritten
- Dankesseite stimmig und im gleichen Ton
- Erster Tap auf echtem Gerät — Onepage hydratisiert verzögert, der allererste Klick nach dem Laden geht manchmal ins Leere
