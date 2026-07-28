---
name: lp-compliance
description: Rechtliche Absicherung von Versicherungs-Landingpages. Nutze diesen Skill VOR dem ersten Section-Bau und noch einmal als Audit vor dem Publish. Klärt, was ein Makler, ein Ausschließlichkeitsvertreter und ein gebundener Vermittler jeweils sagen dürfen, listet die Template-Fallen beim Klonen, den Topic-Mismatch, die nischenspezifischen Verbote (PKV, TKV, BU, Zahnzusatz, Rechtsschutz, Wohngebäude) und die Pflichtangaben in Impressum und Datenschutzerklärung. Auch nutzen, wenn ein einzelner Claim oder eine Zahl auf Zulässigkeit geprüft werden soll.
---

# Compliance

Der wichtigste Block. Ein Fehler hier ist teurer als jede verlorene Conversion.

## Schritt 1 — Vermittlerstatus

Ohne geklärten Status wird nicht gebaut.

| Status | Darf | Darf nicht |
|---|---|---|
| **Makler** (unabhängig) | „unabhängig", Anbieter vergleichen, „neutral", Mehranbieter-Vergleich | — |
| **Ausschließlichkeitsvertreter** | nur **einen** Versicherer nennen und empfehlen | „unabhängig", „Makler", Mehranbieter-Vergleich, Fremd-Logos |
| **Gebundener Vermittler (§ 34d Abs. 7 GewO)** | nur die gebundenen Partner | „unabhängig", „Makler", Mehranbieter-Vergleich |

Bei Ausschließlichkeit gilt zusätzlich: keine Anti-Vergleichsportal-Rhetorik, die implizit Unabhängigkeit behauptet („wir schauen für Sie den ganzen Markt an"). Erlaubt ist die persönliche Beratung als Gegenpol zum Portal — das ist eine Aussage über die Beratungsqualität, nicht über die Marktbreite.

`references/vermittlerstatus.md` hat die Formulierungshilfen und die Impressumspflichten je Status.

## Schritt 2 — Template-Fallen

LPs werden geklont, und Klone tragen fremde Aussagen mit. Immer suchen nach:

- „über X Anbieter vergleichen", „unabhängig", „neutral", „die echten Marktbesten"
- Fremd-Logos
- Platzhalter- oder alte Kundennamen
- Anti-Vergleichsportal-Framing
- unbelegbare Superlative
- **Produktversprechen des Vor-Versicherers** — was bei der Allianz stimmt, ist bei der SIGNAL IDUNA falsch. „Bis zu 6 Monatsbeiträge Rückerstattung" oder „lebenslange Vertragsgarantie" sind konkrete Tarifmerkmale eines bestimmten Hauses.

## Schritt 3 — Topic-Mismatch

Sehr häufig. Geklonte Templates tragen Inhalte aus einem **anderen Produkt**, meist PKV-Vollversicherung. Fremd zu Zahnzusatz, BHV, TKV und anderen sind z. B.:

„Beitragsrückerstattung / Rechnung zurückkaufen" · „Chefarzt, Ein- oder Zweibettzimmer" · „schnellere Facharzttermine" · „Privatpatient werden" · „Selbstbeteiligung 0/10/30 %" · „Wechsel in die PKV"

Inhalt komplett auf das **tatsächliche Produkt** reframen. Ein Zahnzusatz-Funnel, der von Chefarztbehandlung spricht, ist irreführend und damit abmahnbar.

## Schritt 4 — Nische

`references/nischen.md` — je Nische: erlaubte und verbotene Claims, typische Topic-Mismatches, Pflicht-Disclaimer, Filterkriterien, CPL-Korridor.

## Schritt 5 — Zahlen

Belastbare Zahlen (Beiträge, Grenzwerte, Leistungen, Marktdaten, Quoten) **immer live per `web_search` verifizieren**. Erfundene Werte sind abmahnbar.

`references/kennzahlen.md` — welche Anker je Nische gebraucht werden, wo sie herkommen, und die bereits verifizierten Werte mit Quelle und Datum.

Beispielrechnungen brauchen einen Disclaimer: Beispielwerte, variieren je Befund und Tarif, keine Zusicherung.

Preise nur einsetzen, wenn von Dennis bestätigt (Figma, Drive, Rechner).

## Schritt 6 — Rechtliche Unterseite

Vollständiges Impressum plus Datenschutzerklärung. `references/rechtstexte.md` hat die Gliederung, die Pflichtangaben und die Stellen, die nur der Kunde liefern kann.

Zwei Regeln:

**Die im Funnel erhobenen Felder stehen 1:1 in der Datenschutzerklärung.** Ändert sich der Funnel, ändert sich der Text mit.

**Keine internen Bearbeitungshinweise im Live-Text.** Fehlende Pflichtangaben werden als klar erkennbarer Platzhalter geführt (z. B. `D-XXXX-XXXXX-XX`) und im Übergabe-Log als Blocker markiert — nicht stillschweigend weggelassen. Eine fehlende Zeile fällt bei der Abnahme niemandem auf, ein sichtbarer Platzhalter schon.

## Audit vor Publish

Als Delegation an den `lp-compliance`-Subagent mit dieser Frage:

> Prüfe die Live-Seite [URL] für einen [Status] der [Versicherer] in der Nische [X]. Suche nach: verbotenen Claims für diesen Status, Fremd-Logos, Produktversprechen anderer Häuser, Topic-Mismatch, unbelegten Zahlen, Widersprüchen zwischen Funnel-Feldern und Datenschutzerklärung, Preis-Inkonsistenzen. Gib jeden Fund mit Fundstelle und Vorschlag zurück.

## Grenze

Du bist kein Anwalt und schreibst das auch so, wenn es eng wird. Bei echten Zweifelsfällen — neue Werbeform, aggressive Vergleichsaussage, Gesundheitsdaten in ungewohntem Kontext — geht die Entscheidung an Dennis, mit einer klaren Darstellung des Risikos und einer sicheren Alternative.
