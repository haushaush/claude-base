---
name: lp-accessibility
description: Barrierefreiheit einer Landingpage nach WCAG 2.1 AA / BFSG prüfen und
  herstellen — Kontraste, Tastaturbedienung, Formularlabels, Fokus, Alt-Texte,
  Überschriftenhierarchie, Erklärung zur Barrierefreiheit. Nutze das bei jedem
  neuen LP-Bau vor dem Livegang, bei Reviews bestehender Seiten, und immer wenn
  von Barrierefreiheit, BFSG, WCAG, Kontrast, Screenreader oder Tastaturbedienung
  die Rede ist.
---

# Barrierefreiheit für Landingpages

Prüfmaßstab ist **WCAG 2.1 Level AA** (über EN 301 549). Das BFSG gilt seit dem
28.06.2025 und richtet sich an private Anbieter digitaler Dienstleistungen an
Verbraucher. Eine LP mit Lead-Formular fällt regelmäßig darunter.

Ausgenommen sind Kleinstunternehmen — unter 10 Mitarbeitenden **und** höchstens
2 Mio. € Jahresumsatz. Bei einer Versicherungsagentur ist das die erste Frage,
die zu klären ist, und zwar beim Kunden, nicht durch Schätzung.

**Kein Rechtsrat.** Ob eine konkrete Seite in den Geltungsbereich fällt, ist
eine juristische Bewertung. Diese Prüfliste stellt die technische Qualität
sicher; die Einordnung gehört zum Kunden und ggf. zu dessen Anwalt. Nie
gegenüber dem Kunden behaupten, eine Seite sei „BFSG-konform" — sondern
benennen, was geprüft wurde und was offen ist.

## Prüfliste

Der Reihe nach. Jeder Punkt bekommt bestanden / verletzt / nicht anwendbar,
mit Fundstelle.

### Kontrast
- Fließtext gegen Hintergrund mindestens **4.5:1**
- Große Schrift (ab 24px, oder ab 18.66px fett) mindestens **3:1**
- Bedienelemente und ihre Zustände, Icons mit Bedeutung, Formularrahmen: **3:1**
- Text auf Bildern: gegen den **hellsten Bereich** hinter dem Text messen, nicht
  gegen den Durchschnitt. Hero-Bilder mit Textoverlay sind die häufigste
  Verletzung überhaupt.
- Platzhaltertext in Feldern zählt mit — der ist fast immer zu hell.

### Tastatur
- Jede Interaktion ohne Maus erreichbar: Formular, Buttons, Akkordeons,
  Slider, Cookie-Banner, Modals
- Fokus **sichtbar**, mindestens 3:1 gegen die Umgebung. `outline: none` ohne
  Ersatz ist ein Verstoß, kein Stilmittel.
- Reihenfolge folgt der visuellen Anordnung
- Keine Tastaturfalle: aus jedem Element kommt man mit Tab wieder heraus
- Modals: Fokus wandert hinein, bleibt drin, Escape schließt, Fokus kehrt zurück

### Formulare
Das ist der Teil, an dem eine Lead-LP wirklich hängt.
- Jedes Feld hat ein **sichtbares Label**. Platzhalter sind kein Label —
  sie verschwinden beim Tippen.
- Label programmatisch verknüpft (`for`/`id` oder umschließend)
- Pflichtfelder nicht nur farblich markiert
- Fehlermeldungen: als Text, in Feldnähe, mit Hinweis **wie** zu korrigieren ist.
  Nicht nur roter Rahmen.
- Fehler werden Screenreadern angekündigt (`aria-live` oder Fokus auf die Meldung)
- `autocomplete`-Attribute bei Name, E-Mail, Telefon
- Einwilligungstexte (DSGVO) sind Teil des Formulars und müssen dieselben
  Kontrastwerte erfüllen — Mikro-Grau im Consent ist Standard und falsch

### Struktur
- Genau ein `h1`, danach keine Ebene überspringen
- Überschriften beschreiben Inhalt, sind nicht nur groß gesetzt
- Sinnvoller Seitentitel
- `lang="de"` gesetzt
- Landmarks vorhanden (`header`, `main`, `nav`, `footer`)

### Bilder und Medien
- Inhaltstragende Bilder: Alt-Text, der die **Funktion** beschreibt
- Dekorative Bilder: leeres `alt=""`, nicht weglassen
- Kein Text in Bildern, wo Text möglich ist
- Video: Untertitel, kein Autoplay mit Ton

### Bewegung
- Nichts blinkt öfter als dreimal pro Sekunde
- Autoplay-Karussells lassen sich anhalten
- `prefers-reduced-motion` respektiert — bei Reveal-Animationen der Punkt, den
  man am leichtesten vergisst

### Zoom und Reflow
- 200 % Textzoom ohne Verlust von Inhalt oder Funktion
- 320px Breite ohne horizontales Scrollen
- Bei 400 % Zoom noch bedienbar

### Erklärung zur Barrierefreiheit
Das BFSG verlangt eine Erklärung auf der Seite: aktueller Stand, bekannte
Einschränkungen, Kontaktweg für Barriere-Meldungen. Fehlt sie, ist auch eine
technisch saubere Seite unvollständig. Prüfen, ob sie existiert und verlinkt ist.

## Vorgehen

1. Statisch prüfen, was ohne Rendering geht: Struktur, Alt-Texte, Labels,
   `lang`, Farbwerte aus den Design-Tokens
2. Kontraste rechnerisch prüfen, nicht nach Augenmaß — die 4.5:1-Grenze liegt
   dort, wo etwas noch „gut lesbar" aussieht
3. Was nur im Rendering sichtbar ist (Fokus, Reflow, Bewegung), an
   `lp-render-qa` übergeben statt zu raten
4. Befunde nach Schwere sortiert berichten: blockierend / sollte / kosmetisch

## Bericht

Kurz, mit Fundstelle. Beispiel:

```
BLOCKIEREND
- Hero-CTA: #FFFFFF auf #F2A93B = 2.1:1, nötig 4.5:1 (Section 1)
- Formular Feld "Telefon": kein Label, nur Platzhalter (Section 4)

SOLLTE
- Reveal-Blöcke ignorieren prefers-reduced-motion (Sections 3-7)

OFFEN
- Erklärung zur Barrierefreiheit nicht auffindbar
- Kleinstunternehmens-Ausnahme beim Kunden ungeklärt
```

Nie „barrierefrei" als Ergebnis melden. Gemeldet wird, was geprüft wurde,
was verletzt ist und was offen bleibt.
