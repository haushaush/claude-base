# Onepage-Runtime — acht Fallen

Alle acht erzeugen eine leere, verzerrte oder falsch gerenderte Section, **ohne dass `last_error` etwas meldet**. Vor der ersten Vibe-Section lesen.

## 1. `onepage-kit` existiert nicht

Der Import `from 'onepage-kit'` kompiliert, wirft live aber `Module not found` — die Section bleibt komplett leer.

```tsx
import { crm } from 'onepage';   // richtig
```

## 2. framer-motion animiert nicht

`initial`/`animate` und besonders `whileInView` bleiben im Anfangszustand hängen. Der Inhalt steht im DOM, ist aber unsichtbar. Keine framer-motion-Entrances. Stattdessen CSS-`@keyframes`, Zähler über `requestAnimationFrame`, `prefers-reduced-motion` per Media-Query.

## 3. Tool-Calls schlagen still fehl

Antwortet `create_siteui_package` oder `edit_files` mit `upstream_failure` oder einem Proxy-Fehler, ist die Änderung manchmal trotzdem angekommen — oder das Paket wurde mit leerem Stub-`index.tsx` angelegt.

Nach jedem Fehler den Ist-Zustand neu lesen (`list_siteui_packages`, `read_siteui_files`, `get_file_content`). Nicht blind wiederholen.

`edit_files` und `edit_siteui_files` erwarten parallele Arrays gleicher Länge (`files`, `old_str`, `new_str`), und jeder `old_str` muss **genau einmal** matchen.

## 4. Umbenannte Controls erben alte Werte

Wird ein Control-Key in `package.json` umbenannt, übernimmt die Section-Instanz den alten gespeicherten Wert auf den neuen Key — der neue `default` greift nicht.

Beim Umbenennen einen komplett neuen, nie verwendeten Key wählen (`intro` → `intro2`, nicht `intro` → `lead`). Im gerenderten DOM über `data-op-ctrl` prüfen, welcher Wert tatsächlich ankommt.

Das gilt auch für Arrays: Ein geänderter `default` in einem bestehenden Array-Control wird nicht sichtbar.

## 5. Erster Klick geht verloren

Die Section wird verzögert hydratisiert; der erste Klick nach dem Laden landet oft im Leeren. Im Test hilft ein kurzer Scroll vor der ersten Interaktion. Für echte Seiten: einmal auf einem echten Gerät gegenprüfen und im Übergabe-Log erwähnen.

## 6. Trennlinien-Padding

Das Muster

```css
.item { padding: 22px 24px 0 0; border-right: 1px solid …; }
```

gibt der *nächsten* Spalte `padding-left: 0` — ihr Text klebt an der vertikalen Linie. Tritt reproduzierbar auf und fällt Kunden sofort auf.

```css
.item { padding: 22px 24px; border-right: 1px solid …; }
.item:first-child { padding-left: 0; }
.item:last-child  { border-right: 0; padding-right: 0; }
```

Im Mobile-Breakpoint (Linie wird `border-bottom`) die `:first-child`-Regel mitziehen.

## 7. `stroke-dasharray` bricht bei `preserveAspectRatio="none"`

Zusammen mit `vector-effect="non-scaling-stroke"` wird die Dash-Länge in Screen-Units gemessen, die Pfadlänge aber in User-Units. Ergebnis: das letzte Liniensegment fehlt dauerhaft.

Stattdessen die Plot-Gruppe einsweepen:

```css
@keyframes sweepIn { from { clip-path: inset(0 100% 0 0); } to { clip-path: inset(0 0 0 0); } }
```

SVG-`<text>` in solchen Charts ebenfalls vermeiden — wird verzerrt. Labels als absolut positionierte HTML-Spans über dem SVG.

## 8. Scroll-Reveal — das einzig tragfähige Muster

Drei Beobachtungen, die zusammengehören:

**Reine CSS-Animation mit `animation: … both` startet beim ersten Paint**, nicht beim Scrollen. Auf einer langen Seite ist sie vorbei, bevor der Nutzer unten ankommt. Die Section wirkt statisch — genau die Beschwerde, die man dann bekommt.

**`IntersectionObserver` funktioniert** (nachgemessen), aber die Section wird erst hydratisiert, wenn der Nutzer scrollt. Läuft JS gar nicht, bleibt ein `opacity: 0`-Ausgangszustand **dauerhaft unsichtbar**. Ein versteckter Basiszustand ist deshalb gefährlich.

**Lösung:** Basiszustand = Endzustand. Die Animation nur unter einer `.in`-Klasse und mit `animation-fill-mode: backwards`.

```css
/* sichtbar, auch ohne JS */
.plot { }
.in .plot { animation: sweepIn 1.35s cubic-bezier(.34,.68,.34,1) .3s backwards; }
```

`backwards` heißt: während der Delay-Phase gilt der From-Zustand, nach dem Ende fällt das Element auf den sichtbaren Basiszustand zurück.

`.in` per `useLayoutEffect` setzen, nicht `useEffect` — sonst blitzt der fertige Zustand einmal auf, bevor die Animation von vorn beginnt.

```tsx
const useIso = typeof window !== 'undefined' ? useLayoutEffect : useEffect;
```

Dazu beim Mount prüfen, ob das Element schon im Viewport liegt (`getBoundingClientRect`), plus Safety-Timeout von etwa 2,5 Sekunden, falls der Observer nie feuert.

---

## Beim Testen

`window.scrollTo` löst im Testbrowser **keine Scroll-Events** aus. Animationen und Scroll-Reveals mit echtem Maus-Scroll prüfen, sonst hältst du eine funktionierende Animation für kaputt.

Für die Mobilansicht funktioniert der Iframe-Trick (`<iframe width="390">` auf die Live-URL). Achtung: Im Iframe wird die Section oft **nie** hydratisiert, weil keine Nutzerinteraktion stattfindet — was dort unsichtbar bleibt, ist damit noch nicht kaputt, aber es ist der beste Test dafür, ob der Nicht-JS-Fallback greift.

## Bewährte Animations-Bausteine

| Baustein | Technik |
|---|---|
| Count-up | `requestAnimationFrame`, easeOutQuart, `toLocaleString('de-DE')`, Endwert exakt setzen |
| Kreis-Ring | SVG `stroke-dashoffset` über CSS-Transition, `<linearGradient>` als Stroke |
| Balken | `width: 0 → Ziel%` über Transition |
| Akkordeon | `grid-template-rows: 0fr → 1fr`, nur eins offen, `aria-expanded`, Plus/Minus-Icon |
| Timeline | Schiene über `scaleY`, Nodes mit Spring-Pop, Desktop zweispaltig, Mobile Schiene links |
| Sticky-Stacking | `position: sticky` mit inkrementellem `top` — bricht, wenn ein Parent `overflow: hidden` hat |
| Foto-Slot | `<img onerror>` mit Fallback-Div (Monogramm) |
| Sticky Header | `position: fixed` — funktioniert nur, wenn kein Vorfahr `transform`, `filter` oder `perspective` gesetzt hat. Vorher prüfen |
