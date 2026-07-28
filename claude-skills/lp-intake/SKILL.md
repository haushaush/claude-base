---
name: lp-intake
description: Briefing für eine neue Landingpage aufnehmen und in ein baubares Briefing überführen. Nutze diesen Skill, wenn ein neuer Kunde oder eine neue Nische ansteht, wenn das Briefing lückenhaft ist, oder wenn du vor dem Bau prüfen willst, ob alles Nötige vorliegt. Recherchiert den Kunden eigenständig im Netz, stellt nur die Fragen, die wirklich blockieren, und gibt ein strukturiertes Briefing plus offene Punkte zurück.
---

# Intake

## Prinzip

Nicht alles fragen. Erst recherchieren, dann nur das fragen, was du nicht selbst herausfinden kannst und was den Bau blockiert.

Ein Intake, der mit fünfzehn Fragen startet, kostet Dennis mehr Zeit als er spart.

## Schritt 1 — Selbst recherchieren

Aus Kundenname und Ort ergibt sich meist:

- vollständige Firmierung und Rechtsform
- Anschrift, Telefon, E-Mail
- vertretener Versicherer, damit Hinweis auf den Status
- Team, Größe, Jahre am Markt
- Google-Bewertungen: Note, Anzahl, echte Rezensionstexte mit Namen und Datum
- bestehende Website: Brand-Farben, Logo, Tonalität, vorhandenes Impressum

`lp-research` delegieren, wenn es mehr als zwei Quellen sind.

Bereits vorhandene Google-Rezensionen sind Gold — sie ersetzen erfundene Trust-Bausteine. Wörtlich übernehmen, Kürzungen kennzeichnen, Quellenhinweis unter die Karten.

## Schritt 2 — Nur die echten Blocker fragen

Frage nur, was Bau oder Rechtssicherheit blockiert:

| Frage | Warum blockierend |
|---|---|
| **Vermittlerstatus** | bestimmt die gesamte erlaubte Copy |
| **Produkt / Nische** | bestimmt Struktur, Filter, Compliance-Profil |
| **Du oder Sie** | zieht sich durch jede Zeile |
| **Preis-Anker und Anzeigenpreis** | Funnel-Preis muss darüber liegen |
| **Brand: Farben, Logo, Font** | sonst baust du zweimal |
| **Gewünschte Funnel-Schritte** | der Kunde hat oft eine feste Vorstellung |

Alles andere — Portraitfoto, Auszeichnungen, Bilder für Kacheln — kann nachgereicht werden. Dafür Fallbacks bauen (Monogramm statt Foto, Icon statt Bild) und im Übergabe-Log listen.

Fragen bündeln, nicht einzeln nachschieben.

## Schritt 3 — Briefing schreiben

```markdown
## Kunde
Name · Firmierung · Anschrift · Telefon · E-Mail
Versicherer · Vermittlerstatus · Jahre am Markt · Team
Google: Note, Anzahl, Stand

## Kampagne
Nische · Zielgruppe · Ansprache · Anzeigenpreis · CPL-Ziel

## Compliance-Rahmen
Erlaubt: …
Verboten: …
Pflicht-Disclaimer: …

## Funnel
Schritte in Reihenfolge, mit Filterkriterien und Beitragsrahmen je Zweig

## Brand
Farben mit Hex · Logo-URL · Font oder Substitut · Signature-Element

## Verifizierte Zahlen
Wert — Quelle — Abrufdatum

## Offene Punkte
Was fehlt, wer liefert, was es blockiert
```

Das Briefing kommt nach `.hermes/memories/kunde-<name>.md`, damit spätere Sessions und Folge-LPs darauf zugreifen.

## Schritt 4 — Vor dem Bau gegenprüfen

- Status geklärt? Sonst nicht bauen.
- Nische geklärt? Sonst nicht bauen.
- Anzeigenpreis bekannt und liegt unter dem niedrigsten Funnel-Preis?
- Ansprache festgelegt?
- Zahlen verifiziert oder als offen markiert?

Erst wenn diese fünf stehen, `lp-build` ziehen.

## Batch

Bei mehreren LPs für denselben Kunden: Prefix und Token-Set konstant halten, jede LP eigenständig durch die Pipeline. Nur bei echten Blockern zurückfragen — Status, Zahl, Farbe, Logo unklar.

Bei mehreren Kunden in derselben Nische: Compliance-Profil und Struktur wiederverwenden, aber Klon-Cleanup als Pflichtschritt behandeln. Der häufigste Produktionsfehler ist der Klon, bei dem der alte Name irgendwo stehen bleibt.
