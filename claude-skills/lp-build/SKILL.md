---
name: lp-build
description: Baut eine komplette Ads-Landingpage in Onepage — Struktur, Copy, animierte Sections, Funnel, CRM-Formular, Seiteneinstellungen, QA. Nutze diesen Skill für jede Bau- oder Umbauarbeit an einer LP: neue Seite anlegen, Section ergänzen oder überarbeiten, Funnel-Schritte ändern, Animation bauen, vor dem Publish prüfen. Enthält die Pflicht-Sectionreihenfolge, die Winning- und Anti-Patterns, den Onepage-Runtime-Katalog und das QA-Gate. NICHT für Compliance-Urteile (dafür lp-compliance) und nicht fürs Erstbriefing (dafür lp-intake).
---

# LP bauen

## Bevor du das erste Tool anfasst

1. `onepage_skill_list`, dann die relevanten Skills mit `onepage_skill_get` lesen — die Onepage-Skills sind die Autorität für DSL-Syntax und Tool-Reihenfolge. Nicht raten. Große Skills kommen in Teilen, alle Teile holen.
2. `.hermes/memories/onepage-runtime.md` lesen. Acht Fallen, die still zu kaputten Sections führen.
3. Vermittlerstatus und Nische stehen fest? Wenn nein → `lp-intake`, nicht bauen.

## Bau-Reihenfolge

1. `create_site` oder bestehendes Projekt über `list_sites`/`get_site`
2. `create_page` für Startseite und rechtliche Unterseite
3. Standard-Content-Sections über `create_section` mit OnepageML
4. Animierte und interaktive Sections über `create_vibe_section` — alles, was OnepageML nicht nativ kann: Count-ups, Ringe, Balken, Timelines, Tarifkarten, Akkordeons, Sticky-Stacking, Reveal-Choreografien
5. Funnel: Schritte, Filterlogik, `create_crm_form`
6. `update_page_settings` — Slug, SEO-Titel, Meta-Description, OG-Image, Indexierung
7. `update_site_settings` — Sprache DE, Favicon, Banner aus, Cookie-Banner
8. Self-QA (`references/qa-gate.md`), dann `publish_page`

Nach jedem erfolgreichen Section-Edit den Stand neu lesen (`get_section`, `get_page_overview`), bevor du weiter editierst.

## Referenzen — ziehe die passende, wenn du an der Stelle bist

| Datei | Wofür |
|---|---|
| `references/struktur.md` | Pflicht-Sectionreihenfolge, Winning-Patterns, Anti-Patterns, Copy-Muster je Section |
| `references/funnel.md` | Schrittaufbau, Filterlogik, Consent, Tracking-Spezifikation, Preis-Anchoring |
| `references/design.md` | Section-Bau-Standard, Token-System, bewährte Animations-Patterns |
| `references/onepage-runtime.md` | Acht Runtime-Fallen — **vor der ersten Vibe-Section lesen** |
| `references/qa-gate.md` | Checkliste A–G vor publish, Klon-Cleanup, Definition von „erledigt" |

## Die vier Regeln, die du auch ohne Referenzdatei einhältst

**Root immer full-width.** `width:100%; padding:0; margin:0`. Kein Außen-Padding, keine max-width um das Gesamtelement. Onepage bestimmt Breite und Außenabstand. Internes Card-Padding ist in Ordnung, `max-width:60ch` am `<p>` auch.

**`text-align:left` explizit** auf Root und alle Kinder (`#prefix *`). Onepage zentriert global.

**ID-scoped CSS** unter einem eigenen Prefix je Section.

**Mobile first.** Basis-CSS ist die Mobilansicht (360–390 px), Desktop kommt über `@media (min-width: …)`. Nicht umgekehrt. Jede Section wird bei 360 px geprüft, bevor sie als fertig gilt.

## Wenn eine Section „nicht funktioniert"

Reihenfolge der Verdächtigen, nach Häufigkeit:

1. Import aus `onepage-kit` statt `onepage` → Section komplett leer
2. framer-motion → Inhalt im DOM, aber unsichtbar
3. Scroll-Reveal mit `opacity:0`-Basiszustand → bleibt unsichtbar, wenn nicht hydratisiert
4. Umbenannter Control-Key erbt den alten gespeicherten Wert
5. Ein Tool-Call meldete `upstream_failure`, die Änderung ist aber angekommen

Details in `references/onepage-runtime.md`. Nach jedem Fehler den Ist-Zustand neu lesen, nicht blind wiederholen.

## Selbstverifikation vor „fertig"

Rendern und ansehen — Desktop **und** 360 px. Bei Reveal, Count-up oder Stacking kurz warten. Prüfen: Overlap, Cropping, weiß auf weiß, Proportionen, Left-Align auch unter zentriertem Parent, Mobile-Umbruch. Fehler fixen, neu prüfen.

Für den Render-Check `lp-render-qa` delegieren, wenn die Seite mehr als drei Sections hat.

Wichtig beim Testen: `window.scrollTo` löst im Testbrowser keine Scroll-Events aus — Animationen mit echtem Maus-Scroll prüfen, sonst hältst du eine funktionierende Animation für kaputt.
