# Design- und Section-Bau-Standard

## Root-Regeln für jede selbst gebaute Section

1. **Root immer** `width:100%; padding:0; margin:0`. Kein Außen-Padding, keine max-width, keine Zentrierung um das Gesamtelement. Onepage bestimmt Breite und Außenabstand. Internes Card-Padding ok, `max-width:60ch` am `<p>` ok.
2. **`text-align:left` explizit** auf Root **und** alle Kinder (`#prefix *`). Onepage zentriert global.
3. **ID-scoped CSS** unter `#prefix-xyz`, eigener Prefix je Section.
4. **Reveal + `prefers-reduced-motion`-Fallback** in jeder animierten Section (Endzustand sofort).
5. **Mobile-Check bei 360 px Pflicht**, zusätzlich Desktop.
6. **Keine Emoji-Icons** als Struktur. Saubere Inline-SVG-Icons, ein zentrales Icon-Set als `@siteui`-Paket.

## Mobile first, konkret

Basis-CSS ist die Mobilansicht. Desktop kommt über `@media (min-width: …)`. Nicht mit `max-width` nach unten korrigieren — das führt zu Regeln, die sich gegenseitig aufheben, und man merkt es erst auf dem Gerät.

Ein Breakpoint reicht meistens (720 px oder 760 px). Ein zweiter bei 1000 px nur, wenn ein echter Layoutwechsel nötig ist.

Reihenfolge auf Mobile ist eine inhaltliche Entscheidung, keine technische: Was zuerst gelesen werden muss, steht zuerst. Bei Grid-Layouts über `grid-template-areas` steuern, nicht über DOM-Reihenfolge — sonst kollidiert es mit dem Desktop-Layout.

## Token-System je Kunde

Ein CSS-Variablen-Set aus der Kundenpalette plus abgeleiteten Shades, Tints, Line- und Muted-Werten. Onepage stellt `--color-kit-key1`, `--color-kit-key2`, `--color-kit-dark`, `--color-kit-light`, `--color-kit-white`, `--color-kit-black` und `--font-kit-header-font` / `--font-kit-text-font` bereit — die nutzen, mit Fallback.

**Nur HEX**, auch mit Alpha (`#ffffff1a`). Kein `rgb()`, kein `rgba()`.

**Schrift:** Hausschriften sind meist proprietär. Substitut ist Manrope (Headlines 600–700, Body 400–500, Stat-Zahlen 800), außer der Kunde nennt eine andere. Für Seriosität in Versicherung funktioniert eine Serif für Headlines (z. B. Newsreader) plus Manrope im Text sehr gut.

Onepage hostet Schriften selbst über `onecdn.io` — kein Google-Fonts-Abruf, das gehört so in die Datenschutzerklärung.

## Kartensystem

**Light-Cards:** reines Weiß, dünne Outline, weicher Schatten.
**Hervorhebung / Premium:** dunkle Marken-Gradient-Card mit radialem Glow.

Nischen- oder Markenfarbe konsequent. Problem- und Negativaussagen über Größe und ruhige Markenoptik lösen, nicht über Alarm-Rot, wenn die Marke das nicht hergibt.

## Wiederverwendbare Primitives

Ein Satz `@siteui`-Pakete je Site spart massiv Zeit und hält die Seite konsistent. Bewährtes Set:

`text` · `title` · `mark` (Logo-Signature) · `icon` · `card` · `badge` · `button` · `choicetile` · `field` · `steprail` · `checkitem` · `accordionitem` · `quote` · `sectionhead` · `comparerow` · `tickbox`

Sie werden einmal pro Site kompiliert und von allen Sections importiert. Änderung am Primitive wirkt überall — entsprechend vorsichtig editieren.

## Controls

Jeder nutzersichtbare String gehört als Control in die `package.json` unter `onepage.control`. Gruppen und Tabs nutzen, sonst wird das Panel unbedienbar.

Array-Controls für alles Wiederholte (Punkte, Karten, Schritte, Zitate, FAQ). `hideWhen`-Ausdrücke, um irrelevante Felder auszublenden.

Deutsche Labels, weil Dennis und die Kunden im Builder arbeiten.

Faustregel: Wenn Dennis eine Änderung nicht ohne dich machen kann, fehlt ein Control.

## Signature

Jede Kundenseite bekommt ein wiedererkennbares Element, das sich aus der Marke ableitet — meist eine Form aus dem Logo, die als Eyebrow-Glyph, Watermark und Listen-Marker wiederkehrt. Das ist der Unterschied zwischen „sauber gebaut" und „sieht nach diesem Kunden aus".

Ein Signature-Element, nicht drei. Der Rest bleibt ruhig.
