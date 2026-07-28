# onepage-runtime

Acht Fallen beim Bau von Onepage-Vibe-Sections. Alle erzeugen eine leere, verzerrte oder falsch gerenderte Section, **ohne dass `last_error` etwas meldet**.

1. **`onepage-kit` existiert nicht.** Import kompiliert, wirft live `Module not found`, Section bleibt leer. → `import { crm } from 'onepage';`
2. **framer-motion animiert nicht.** Inhalt im DOM, aber `opacity: 0` bleibt stehen. → CSS-Keyframes, `requestAnimationFrame`.
3. **Tool-Calls schlagen still fehl.** `upstream_failure` heißt nicht, dass nichts passiert ist. → Nach jedem Fehler Ist-Zustand neu lesen, nicht wiederholen.
4. **Umbenannte Controls erben alte Werte.** Neuer `default` greift nicht. → Komplett neuen Key wählen, im DOM über `data-op-ctrl` prüfen.
5. **Erster Klick nach dem Laden geht verloren.** Verzögerte Hydration. → Auf echtem Gerät gegenprüfen.
6. **Trennlinien-Padding.** `padding: X Y 0 0` + `border-right` lässt den Text der nächsten Spalte an der Linie kleben. → Symmetrisch plus `:first-child`/`:last-child`-Ausnahme.
7. **`stroke-dasharray` bricht bei `preserveAspectRatio="none"`.** Letztes Segment fehlt dauerhaft. → `clip-path`-Sweep statt Dash-Draw. SVG-`<text>` meiden, Labels als HTML.
8. **Scroll-Reveal.** CSS-`both` startet beim ersten Paint, ist also bei langen Seiten vorbei, bevor jemand hinscrollt. IntersectionObserver funktioniert, aber ohne Hydration bleibt ein `opacity:0`-Basiszustand dauerhaft unsichtbar. → Basiszustand = Endzustand, Animation nur unter `.in` mit `animation-fill-mode: backwards`, `.in` per `useLayoutEffect`, plus Viewport-Check beim Mount und Safety-Timeout.

**Beim Testen:** `window.scrollTo` löst keine Scroll-Events aus. Animationen mit echtem Maus-Scroll prüfen.

Siehe [[onepage-tooling]], [[feedback-dennis]].
