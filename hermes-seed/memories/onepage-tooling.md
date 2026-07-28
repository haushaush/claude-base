# onepage-tooling

**Vor dem ersten Bau:** `onepage_skill_list`, dann relevante Skills mit `onepage_skill_get` lesen, alle Teile. Die Onepage-Skills sind die Autorität für DSL-Syntax und Tool-Reihenfolge — nicht raten. Der Server erzwingt das teilweise (`skill_required`).

**Bau-Reihenfolge:** `create_site` → `create_page` → Standard-Sections via `create_section` (OnepageML) → animierte via `create_vibe_section` → Funnel + `create_crm_form` → `update_page_settings` → `update_site_settings` → QA → `publish_page`.

**Nach jedem Section-Edit** den Stand neu lesen (`get_section`, `get_page_overview`).

**`edit_files` / `edit_siteui_files`** erwarten parallele Arrays gleicher Länge (`files`, `old_str`, `new_str`); jeder `old_str` muss genau einmal matchen.

**Farben:** nur HEX, auch mit Alpha (`#ffffff1a`). Kein `rgb()`/`rgba()`.

**Controls:** jeder nutzersichtbare String gehört in `onepage.control`. Deutsche Labels. Array-Controls für Wiederholtes. Faustregel: Wenn Dennis eine Änderung nicht ohne dich machen kann, fehlt ein Control.

**Nicht per MCP steuerbar:** Meta-Pixel, Domain-DNS, Tracking-Event-Konfiguration, Kundenabnahme. Als manuelle To-dos übergeben, nie als erledigt melden.

Siehe [[onepage-runtime]].
