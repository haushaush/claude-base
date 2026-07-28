# Kennzahlen

## Grundregel

**Keine Zahl ohne Live-Verifikation.** Auch die hier stehenden Werte werden vor Verwendung gegengeprüft — Sozialversicherungsgrößen ändern sich jährlich, Beitragssätze unterjährig.

Verifizierte Zahl im Übergabe-Log immer mit Quelle und Abrufdatum führen.

## Verifiziert — Stand Juli 2026

| Wert | Zahl | Quelle |
|---|---|---|
| Versicherungspflichtgrenze (JAEG) | 77.400 € / Jahr = 6.450 € / Monat | Sozialversicherungsrechengrößen 2026 |
| Beitragsbemessungsgrenze KV | 69.750 € / Jahr = 5.812,50 € / Monat | dito |
| GKV allgemeiner Beitragssatz | 14,6 % | GKV-Spitzenverband |
| Durchschnittlicher Zusatzbeitrag | 2,9 % | dito |
| Summe | Ø 17,5 % | abgeleitet |
| GKV-Höchstbeitrag, Arbeitnehmeranteil | 508,59 € / Monat, ohne Pflege | abgeleitet: 5.812,50 × 17,5 % ÷ 2 |
| BU-Wahrscheinlichkeit | Ø rund 25 %, Spanne 15,8–28,5 % je nach Eintritts- und Renteneintrittsalter; Frauen ab 20 bis 62 rund 20 %. Datenbasis: privat Versicherte, rund 17 Mio. Verträge bei rund 44 Mio. Erwerbstätigen | Deutsche Aktuarvereinigung, „Jeder Vierte wird berufsunfähig" |

Die BU-Zahl nie ohne die Einordnung verwenden. „Jeder Vierte" allein ist angreifbar, mit Quelle und Spanne ist es belastbar.

## Was je Nische verifiziert werden muss

**PKV** — JAEG, BBG, Beitragssatz, durchschnittlicher Zusatzbeitrag. Quellen: Sozialversicherungsrechengrößen des BMAS, GKV-Spitzenverband.

**Zahnzusatz** — Festzuschuss-Systematik und Bonusheft-Stufen, typische Eigenanteile Regelversorgung gegen höherwertig. Quellen: GKV-Spitzenverband, Kassenzahnärztliche Bundesvereinigung.

**BU** — durchschnittliche Erwerbsminderungsrente, Zugangsvoraussetzungen. Quelle: Deutsche Rentenversicherung. Plus DAV für die Wahrscheinlichkeiten.

**TKV** — GOT-Sätze und aktueller Steigerungssatz, typische OP-Kosten. Quellen: Gebührenordnung für Tierärzte, Kostenübersichten von Tierkliniken.

**Rechtsschutz** — RVG-Gebühren und Gerichtskosten zu typischen Streitwerten. Quellen: RVG-Tabellen, Gerichtskostengesetz.

**Wohngebäude** — Elementarschaden-Versicherungsquote, Schadenaufwand nach Naturgefahren, durchschnittliche Schadenhöhe. Quelle: GDV-Naturgefahrenbilanz.

## Wie eine Zahl auf die Seite kommt

1. Suchen, Primärquelle öffnen, Wert und Stand notieren
2. Prüfen, ob der Wert für das Jahr der Kampagne gilt — nicht das Jahr der letzten Meldung
3. Auf der Seite mit Bezugsgröße nennen, nicht nackt: „5.812,50 € im Monat" statt „5.812,50 €"
4. Herleitungen offenlegen, wenn gerechnet wurde („Basis: Beitragsbemessungsgrenze und durchschnittlich 17,5 Prozent Beitragssatz")
5. Quelle und Abrufdatum ins Übergabe-Log

## Zahlen-Hygiene

- Deutsche Formatierung: Punkt als Tausendertrennzeichen, Komma als Dezimaltrennzeichen, `toLocaleString('de-DE')`
- Keine Scheingenauigkeit — „über 30 Jahre" statt „31,4 Jahre"
- Keine kaputten Zahlen: „10.0000 Kunden" oder „1300 Jahre Erfahrung" kommen aus schlampigen Klonen und zerstören sofort die Glaubwürdigkeit
- Runde Marketingzahlen kennzeichnen, wenn sie geschätzt sind
- Jede Zahl auf der Seite muss zu jeder anderen passen — Preisspannen im Funnel, im Hero-Badge und in der Anzeige gehören zusammengeprüft
