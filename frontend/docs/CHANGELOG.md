# 📜 Frontend Changelog — vivizoo

> **Alle Änderungen, Entscheidungen und gefundene Bugs — chronologisch dokumentiert.**

---

## 2026-08-06 — Initial Implementation (Core Prototype)

### Phase 0: Planung & Architektur

| Zeit | Aktion | Begründung |
|------|--------|-----------|
| 16:36 | `frontend/` Ordnerstruktur erstellt (`core/`, `ui/`, `docs/`, `assets/`) | Dreischicht-Architektur: klare Trennung von Backend und DB |
| 16:38 | `README.md`, `requirements.txt` erstellt | Modul-Dokumentation, Dependency-Liste |
| 16:43 | `FRONTEND_ARCHITECTURE.md` (von Erik) analysiert | UI-Design-Spezifikation als zweite Quelle |
| 16:45 | Cross-Comparison: FRONTEND_ARCHITECTURE.md vs `backend_core_plan.md` vs README | **10 Konflikte identifiziert** (siehe unten) |
| 16:54 | `IMPLEMENTATION_PLAN.md` erstellt (1021 Zeilen) | Autoritative Implementierungsanleitung für KI-Agenten |
| 16:59 | Bewertungskriterien aus Projekt-Spezifikation extrahiert und als ⚠️ GRADING REQUIREMENTS Section eingefügt | Kein Punkteverlust durch vergessene Artefakte |
| 17:02 | `KI_REFLEXION.md` Template erstellt | Vorlage für Erik's Reflexion (5 Punkte) |
| 17:03 | `frontend_class_diagram.md` — Mermaid Klassendiagramm | 10 Punkte Design-Visualisierung |

### 🔍 Konflikt-Resolutionen (10 Entscheidungen)

| # | Konflikt | Quelle A | Quelle B | Entscheidung | Begründung |
|---|----------|----------|----------|-------------|-----------|
| 1 | 5 vs 3 Futtertypen | FRONTEND_ARCHITECTURE (5) | backend_core_plan (3: MEAT/PLANTS/FISH) | **3 Typen** | Backend ist Single Source of Truth |
| 2 | 4-Phasen Tag/Nacht vs simple toggle | FRONTEND_ARCHITECTURE (4 Phasen) | backend_core_plan (nur `zoo_open: bool`) | **Simple Toggle** | Backend Phase 1 hat keine time_of_day |
| 3 | Animal `stage` Feld | FRONTEND_ARCHITECTURE zeigt "Alter · Stadium" | backend_core_plan (kein stage in Phase 1) | **Hardcoded "Erwachsen"** | Backend liefert das Feld nicht |
| 4 | Heal-Button braucht Medikamente | FRONTEND_ARCHITECTURE (Medikamenten-Gate) | backend_core_plan (God-mode, kein Medicine-Inventar) | **Kein Medikamenten-Check** | God-mode in Phase 1 |
| 5 | Enclosure-Daten | FRONTEND_ARCHITECTURE (erwartet vom Backend) | backend_core_plan (kein `enclosures_on_map[]`) | **Hardcoded ENCLOSURE_DEFS** | Fallback bis Backend das Feld liefert |
| 6 | UpgradePanel, DecoSprite, Drag&Drop | FRONTEND_ARCHITECTURE (Extended) | backend_core_plan (Phase 3) | **Nicht implementiert** | Anti-Implementation Checklist |
| 7 | Monolith vs Modular | FRONTEND_ARCHITECTURE (ein main_window.py) | README/Plan (modular: 20+ Dateien) | **Modular** | SRP, eine Klasse pro Datei (Bewertungskriterium) |
| 8 | `enclosure_id` Feld | FRONTEND_ARCHITECTURE (implizit erwartet) | backend_core_plan (nicht in animals_on_map) | **Backend-Dependency R1** | Als kritische Anfrage an Backend-Team dokumentiert |
| 9 | `name` Feld in animals_on_map | FRONTEND_ARCHITECTURE (braucht es für Labels) | backend_core_plan (nur in entity_info) | **Backend-Dependency R2** | Ebenfalls an Backend-Team |
| 10 | Tick-Loop (wer ruft engine.tick()?) | Beide Pläne hatten Unklarheiten | — | **Controller.advance_tick() Pattern** | Kapselt beide Modi (Manuell/Auto-Timer) |

---

### Phase 1: Code-Implementierung (Stage A–E)

#### Stage A: Foundation

| Datei | Zeit | Anmerkungen |
|-------|------|-----------|
| `core/constants.py` | 17:13 | Alle Farben, Dimensionen, Species-Mappings, Enclosure-Definitionen |
| `ui/styled_widgets.py` | 17:14 | `styled_button()`, `styled_label()` — `styled_card()` deferred (Phase 3) |
| `assets/ascii_lion.py` | 17:15 | 40-Zeilen ASCII Art |
| `assets/ascii_lion_small.py` | 17:15 | 15-Zeilen kompakte Version für Info-Panel |

#### Stage B: Map Sprites

| Datei | Zeit | Anmerkungen |
|-------|------|-----------|
| `ui/animal_sprite.py` | 17:16 | `AnimalSprite(QGraphicsEllipseItem)` — später refactored (callback statt signal) |
| `ui/lion_sprite.py` | 17:16 | `AsciiLionSprite(QGraphicsPixmapItem)` + Pixmap-Cache |
| `ui/visitor_sprite.py` | 17:17 | `VisitorSprite` 5×5px Punkte |
| `ui/enclosure_item.py` | 17:17 | `EnclosureItem` — später komplett umgeschrieben |

#### Stage C: Map Container

| Datei | Zeit | Anmerkungen |
|-------|------|-----------|
| `ui/zoo_scene.py` | 17:18 | `ZooScene` — Entity-Dictionaries, `update_entities()` Batching, Lighting |
| `ui/zoo_view.py` | 17:18 | `ZooGraphicsView` — Zoom/Pan/Hover/Click |

#### Stage D: UI-Panels

| Datei | Zeit | Anmerkungen |
|-------|------|-----------|
| `ui/chat_view.py` | 17:19 | `ChatlogWidget` — 500 Nachrichten Cap, HTML-Formatierung |
| `ui/entity_info_panel.py` | 17:19 | `EntityInfoPanel` — HP/Hunger/Wohlbefinden ProgressBars |
| `ui/action_panel.py` | 17:20 | `ActionPanel` — 6 Buttons (feed_all, feed_one, heal, clean, cremate, ticket) |
| `ui/shop_panel.py` | 17:20 | `ShopPanel` — Futter/Tiere/Ticketpreis Kauf-Sektionen |
| `ui/event_banner.py` | 17:21 | Stub — immer hidden in Phase 1 |

#### Stage E: Top-Level Wiring

| Datei | Zeit | Anmerkungen |
|-------|------|-----------|
| `core/frontend_controller.py` | 17:21 | `FrontendController` — Bridge zu `SimulationEngine`, graceful null-engine |
| `core/main_window.py` | 17:23 | `ZooMainWindow` — 1400×900 Layout, Toolbar, Tick-Loop, Signal-Routing |
| `main.py` | 17:23 | Entry Point — QSS Dark Theme (~150 Zeilen), `_create_demo_engine()` |

---

### 🐛 Bugs Gefunden & Behoben

#### Bug 1: `pyqtSignal` auf non-QObject Basisklassen (KRITISCH)

**Symptom:**
```
TypeError: EnclosureItem cannot be converted to PyQt6.QtCore.QObject
```

**Ursache:** In Qt6 sind `QGraphicsEllipseItem`, `QGraphicsPixmapItem`, und `QGraphicsRectItem` **KEINE QObject-Subklassen**. `pyqtSignal` kann nur auf QObject-Klassen definiert werden.

**Betroffene Dateien:**
- `ui/animal_sprite.py` — `entity_hovered` / `entity_unhovered` Signals
- `ui/lion_sprite.py` — `entity_hovered` / `entity_unhovered` Signals  
- `ui/enclosure_item.py` — `enclosure_clicked` Signal

**Fix:** Alle drei Sprites von Signals auf **Callback-Pattern** umgestellt:
- `set_hover_callback(fn)` / `set_unhover_callback(fn)` auf Animal- und Lion-Sprites
- `set_click_callback(fn)` auf EnclosureItem
- `ZooMainWindow._wire_sprite_callbacks()` setzt die Callbacks nach jedem Sprite-Batch

**Impact:** `main_window.py` musste `_connect_signals()` und `_update_sprites()` angepasst werden. `zoo_scene.py` brauchte keine Änderung (es leitet nur `update_entities` durch).

---

#### Bug 2: `QPainter().fontMetrics()` Crash mit Offscreen-Plattform (MITTEL)

**Symptom:**
```
QPainter::fontMetrics: Painter not active
```

**Ursache:** `_render_lion_pixmap()` in `lion_sprite.py` rief `QPainter().fontMetrics()` auf, um Textgröße zu messen. Im Headless/Offscreen-Modus ist kein aktiver Painter verfügbar.

**Fix:** `QPainter().fontMetrics()` → `QFontMetrics(font)`. `QFontMetrics` benötigt keinen aktiven Painter und funktioniert auch ohne Display.

**Betroffene Datei:** `ui/lion_sprite.py`

---

#### Bug 3: `libGL.so.1` fehlt (INFRASTRUKTUR)

**Symptom:**
```
ImportError: libGL.so.1: cannot open shared object file
```

**Ursache:** PyQt6 benötigt OpenGL-Bibliotheken. Im Devcontainer (Headless Linux) sind diese nicht standardmäßig installiert.

**Fix:** `sudo apt-get install -y libgl1`

---

#### Bug 4: `libEGL.so.1` fehlt (INFRASTRUKTUR)

**Symptom:**
```
ImportError: libEGL.so.1: cannot open shared object file
```

**Ursache:** Gleiche wie Bug 3 — PyQt6 braucht EGL für Rendering.

**Fix:** `sudo apt-get install -y libegl1`

---

#### Bug 5: Buttons nicht anklickbar — `setProperty()` ohne `style().unpolish()` (KRITISCH)

**Symptom:** Buttons im ActionPanel und ShopPanel reagierten nicht auf Hover (kein Farbwechsel) und lösten keine Aktionen bei Klick aus. Nur einige wenige Buttons funktionierten.

**Ursache:** `styled_button()` setzte Properties via `setProperty("accent", True)` — aber Qt6 wertet QSS-Selektoren wie `QPushButton[accent="true"]` nur dann neu aus, wenn `style().unpolish()` + `style().polish()` aufgerufen wird. Ohne diese Aufrufe ignoriert die globale QSS-Stylesheet alle Property-basierten Regeln für diesen Button, inklusive `:hover`, `:pressed`, und `:disabled`.

Das bedeutet konkret:
- `QPushButton[accent="true"] { background: #3fb950; }` wurde **nie angewandt**
- `QPushButton:hover { background: #30363d; }` wurde **nie angewandt** (weil Button nicht im Stylesheet-System registriert war)
- `QPushButton:disabled { ... }` wurde **nie angewandt**

**Fix:** In `styled_button()` nach `setProperty()` folgende Zeilen hinzugefügt:
```python
button.style().unpolish(button)
button.style().polish(button)
```

**Betroffene Dateien:** `ui/styled_widgets.py` (Zeile 67-69)

**Betroffene Buttons:** Alle Buttons die via `styled_button()` erstellt wurden:
- ActionPanel: feed_all, feed_one, heal, clean
- ShopPanel: Kaufen (Futter, Tiere), Übernehmen (Ticket)
- main_window.py: Pause-Button (verwendet inline QSS, daher nicht betroffen)

---

#### Bug 6: PyQt6 Installation Permission (INFRASTRUKTUR)

**Symptom:**
```
PermissionError: [Errno 13] Permission denied: '/opt/venv/lib/python3.14/site-packages/PyQt6'
```

**Ursache:** Der Devcontainer hat ein geschütztes `/opt/venv`-Verzeichnis. `pip install` ohne `sudo` scheitert. Mit `sudo pip install` wurde PyQt6 ins System-Python (`/usr/local/lib/python3.14/site-packages`) installiert, was vom aktuellen Python-Interpreter gefunden wird.

**Fix:** `sudo pip install PyQt6` installiert ins globale site-packages. Das System-Python (`/usr/local/bin/python`) kann PyQt6 importieren. `QT_QPA_PLATFORM=offscreen` wird für headless Tests benötigt.

**Nebenwirkung:** Bei `pip install PyQt6>=6.5.0` (aus requirements.txt) wurde das `>=6.5.0` teilweise als Dateiname interpretiert. Resultat: Eine leere Datei `=6.5.0` im Projekt-Root. Diese wurde gelöscht.

---

### 📋 Scope Audit — Passt die Implementierung zum Backend Phase 1?

#### ✅ Im Backend Phase 1 API definiert → Frontend implementiert

| Backend API | Frontend Implementierung | Status |
|-------------|------------------------|--------|
| `engine.tick()` | `controller.advance_tick()` → ruft `engine.tick()` | ✅ OK |
| `engine.get_game_state()` | `controller.get_state()` → `_tick()` pollt jede 100ms | ✅ OK |
| `engine.get_entity_info(id)` | `controller.get_entity_info(id)` → `EntityInfoPanel.show_entity()` | ✅ OK |
| `engine.get_chat_messages()` | `controller.get_chat_messages()` → `ChatlogWidget.append_messages()` | ✅ OK |
| `execute_action("feed_all")` | ActionPanel Button "Alle Tiere füttern" | ✅ OK |
| `execute_action("feed_one", animal_id)` | ActionPanel Button "Ausgewähltes füttern" | ✅ OK |
| `execute_action("heal", animal_id)` | ActionPanel Button "Tier heilen" (kein Medicine-Gate, wie in §2.4 entschieden) | ✅ OK |
| `execute_action("buy_food", type, amount)` | ShopPanel Sektion "Futter kaufen" | ✅ OK |
| `execute_action("buy_animal", species)` | ShopPanel Sektion "Tiere kaufen" | ✅ OK |
| `execute_action("clean", enclosure_id)` | ActionPanel Button "Gehege reinigen" | ✅ OK |

#### ⚠️ Nicht im Backend Phase 1 API definiert — Frontend hat es trotzdem

| Frontend Feature | Backend Status | Risiko | Empfehlung |
|-----------------|---------------|--------|-----------|
| `start_cremation` Button | **Nicht in Phase 1 API** | Mittel — `execute_action("start_cremation")` wird fehlschlagen | Entweder aus ActionPanel entfernen ODER Backend bittet um Implementierung |
| `set_ticket_price` Button + Slider | **Nicht in Phase 1 API** | Mittel — `execute_action("set_ticket_price")` wird fehlschlagen | Dito |

#### ❌ Im Backend Phase 1 explizit deferred → Frontend hat es NICHT implementiert

| Feature | Status |
|---------|--------|
| 4-Phasen Tag/Nacht (nur `zoo_open: bool`) | ✅ Simple Toggle implementiert |
| Animal `stage` Feld | ✅ Hardcoded "Erwachsen" |
| `get_stats()` Charts | ✅ Nicht implementiert |
| Staff Auto-Jobs | ✅ Nicht implementiert (God-mode only) |
| Behaviour Komposition | ✅ Nicht implementiert |
| EnvironmentFactor (Wetter) | ✅ Nicht implementiert |
| EventScheduler | ✅ Nicht implementiert |
| MEDICINE Inventory | ✅ Nicht implementiert |
| UpgradePanel | ✅ Nicht implementiert |
| DecoSprite | ✅ Nicht implementiert |
| Drag & Drop | ✅ Nicht implementiert |
| Save/Load | ✅ Nicht implementiert |
| Baby animals | ✅ Nicht implementiert |

---

### 📁 Änderungen außerhalb `frontend/`

| Datei | Änderung | Begründung |
|-------|----------|-----------|
| `README.md` | `Eric` → `Erik` (Rechtschreibung) | Name korrigiert |
| `=6.5.0` (root) | Erstellt durch pip, dann gelöscht | War Artefakt von `pip install PyQt6>=6.5.0` — `>=6.5.0` wurde als Dateiname interpretiert |
| System-Packages | `libgl1`, `libegl1` via `apt` installiert | Notwendig für PyQt6 im Headless-Container |

**Keine Änderungen an `backend/` oder `db/`.**

---

## 2026-08-06 — Tier 1 Visual Upgrade

### Änderungen

| # | Feature | Datei(en) | Beschreibung |
|---|---------|-----------|-------------|
| 1 | **Gradient Theme** | `constants.py`, `main.py` | 6 neue Farbkonstanten (`C_BG_MID`, `C_BG_PANEL2`, `C_BG_CARD2`, `C_ACCENT_GLOW`, `C_RED_GLOW`, `C_GOLD_GLOW`). QSS mit `qlineargradient` für MainWindow, Toolbar, Buttons, Group Boxes, Inputs. Kein flaches Design mehr — Tiefeneffekt durch Farbverläufe. |
| 2 | **Shadow System** | `main_window.py` | `_drop_shadow()` Hilfsfunktion + `QGraphicsDropShadowEffect` auf Tab-Widget, EntityInfoPanel, ChatlogWidget. 16px Blur, 4px Offset. Erzeugt Karten-Depth ("schwebende" Panels). |
| 3 | **Button Glow** | `main.py` QSS | Accent-Buttons: hellgrüner Glow-Rand (`C_ACCENT_GLOW`). Danger-Buttons: hellroter Glow-Rand (`C_RED_GLOW`). Hover: Border wechselt zu Weiß. Pressed: dunklere Farbe. Alle Buttons mit `qlineargradient` statt flat color. |
| 4 | **Progress Bar Enhancement** | `main.py` QSS, `entity_info_panel.py` | Höhe von 16px auf 18px erhöht. Border-Radius 4px. `QProgressBar::chunk` border-radius 3px. |
| 5 | **Enclosure Beautification** | `enclosure_item.py`, `constants.py` | Biome-spezifische Farbverläufe (`BIOME_COLORS_LIGHT` + `QLinearGradient`). Enclosure-Rechtecke haben jetzt einen helleren oberen Rand der nach unten abdunkelt — erzeugt Raumtiefe. Kein flacher Farbklecks mehr. |

### Impact
- **Vorher:** Flaches GitHub-Dark-Theme, keine Tiefe, keine Schatten, Buttons unsichtbar
- **Nachher:** Gradient-basierte Oberfläche mit weichen Schlagschatten, leuchtenden Buttons, atmosphärischen Einfassungen — "Game-Like"

### Keine Änderungen an Backend/DB — rein visuelles Upgrade

---

## 2026-08-06 — Tier 2 Game Feel Upgrade

### Änderungen

| # | Feature | Datei(en) | Beschreibung |
|---|---------|-----------|-------------|
| 6 | **Hover Highlight** | `animal_sprite.py` | Sprites grow from 18→21px on hover with a white glow ring (2px pen). Snaps back on leave. No animation framework needed — instant, game-like pop effect. Dead animals are excluded (no hover feedback). |
| 7 | **Score Popups** | `main_window.py` | Floating text overlay on successful God-mode actions. Red "-" prefix for purchases (buy_food, buy_animal), green "✓" for care actions (feed, heal). Fades out over 2 seconds via `QPropertyAnimation` on opacity. Auto-hides after animation. |
| 8 | **Toolbar Enhancement** | `main_window.py` | Emoji icons on every toolbar label: 📅 Tag, 💰 Budget, ⭐ Reputation, 😊 Happiness, 🔓/🔒 Open/Closed, 🏃 Speed. Tab labels: 🎮 Aktionen, 🛒 Shop. Statusbar: 🐾 Tiere, 👥 Besucher, 🏠 Gehege, 🟢 Bereit. |

### Impact
- **Vorher:** Statische Sprites ohne Hover-Feedback, keine visuelle Bestätigung von Aktionen, Toolbar mit reinen Text-Labels
- **Nachher:** Sprites "poppen" bei Hover mit weißem Glow-Ring, Aktionen zeigen animierte Einblendungen, Toolbar ist emoji-reich und sofort lesbar — **Game Feel**

### Keine Änderungen an Backend/DB — rein visuelles Upgrade

---

## 2026-08-06 — Tier 3 Atmosphere Upgrade

### Änderungen

| # | Feature | Datei(en) | Beschreibung |
|---|---------|-----------|-------------|
| 9 | **Dot-Grid Map Background** | `zoo_scene.py` | 40px dot-grid pattern via `QImage`/`QPainter` brush. Ein Punkt pro 40×40px-Rasterzelle in `C_BG_MID`. Erzeugt Game-Map-Ästhetik (wie eine taktische Karte). Keine externen Assets nötig. |
| 10 | **Ambient Particles** | `zoo_scene.py` (new `_Particle` class) | 30 kleine schwebende Punkte die langsam nach oben driften und am oberen Rand wieder unten erscheinen. Unter Besuchern, über Tieren in der Z-Order. Sorgt für lebendige Atmosphäre ("Staub im Sonnenlicht"). |
| 11 | **Smooth Day/Night Transition** | `zoo_scene.py` | Statt instant Toggle: `QVariantAnimation` (800ms, InOutCubic) fadet den Overlay zwischen transparent (Tag) und dunkel (Nacht). `_on_lighting_step()` aktualisiert `QGraphicsRectItem.setOpacity()`. `QGraphicsItem` ist kein QObject → `QVariantAnimation` statt `QPropertyAnimation`. |

### Bug Fix (Tier 3)
- **QVariantAnimation statt QPropertyAnimation:** `QGraphicsRectItem` ist kein QObject — `QPropertyAnimation(self._lighting_overlay, b"opacity")` schlug mit `TypeError` fehl. Fix: `QVariantAnimation` mit manuellem `valueChanged` → `setOpacity()` Handler. Derselbe Effekt, Qt6-kompatibel.
- **QPen(Qt.PenStyle.NoPen):** `setPen(Qt.PenStyle.NoPen)` akzeptiert kein `PenStyle`-Enum direkt in Qt6. Fix: `QPen(Qt.PenStyle.NoPen)` wrapper.

### Impact
- **Vorher:** Flacher schwarzer Hintergrund, kein Tiefeneffekt, instant Beleuchtungswechsel
- **Nachher:** Gepunkteter Karten-Hintergrund, sanft schwebende Partikel, weicher 800ms Tag/Nacht-Übergang — **Atmosphäre**

### Keine Änderungen an Backend/DB — rein visuelles Upgrade

---

*Changelog erstellt am 2026-08-06. Wird fortlaufend aktualisiert.*

---

## 2026-08-06 — Phase 1 Bug Fixes & Backend API Alignment

### 🐛 Bugs gefunden & behoben

#### Bug 7: `set_ticket_price` nicht in Backend Phase 1 API (KRITISCH)
**Symptom:** Runtime-Error beim Klick auf "Übernehmen" im ShopPanel — der Backend `ActionHandler` unterstützt `set_ticket_price` nicht.
**Fix:** Ticket-Sektion komplett aus `shop_panel.py` entfernt (QSlider, QLabel, Button, Signal `set_ticket_price`, `_on_set_ticket()` Methode). Zugehörige Signal-Verkabelung in `main_window.py` entfernt.
**Betroffene Dateien:** `ui/shop_panel.py`, `core/main_window.py`

#### Bug 8: `buy_food` Kwarg-Mismatch (KRITISCH)
**Symptom:** Egal welcher Futtertyp im ShopPanel ausgewählt wurde, es wurde immer MEAT gekauft.
**Ursache:** `main_window.py` dispatched `buy_food` mit `food_type=ft`, aber der Backend-Action-Handler erwartet den Parameter als `type=`. Das falsche Keyword wurde stillschweigend ignoriert und `type` fiel auf den Default `MEAT`.
**Fix:** `lambda ft, amt: self._dispatch("buy_food", food_type=ft, ...)` → `lambda ft, amt: self._dispatch("buy_food", type=ft, ...)`.
**Betroffene Datei:** `core/main_window.py`

#### Cleanup: Unused Imports
- `ui/shop_panel.py`: `QSlider`, `Qt`, `QFont`, `C_GOLD` entfernt
- `core/main_window.py`: `QGraphicsOpacityEffect` entfernt, `QToolBar`, `QStatusBar` entfernt (durch Custom Bars ersetzt)

### Scope Audit — Backend API Alignment Check
| Backend Action | Frontend | Status |
|---|---|---|
| `feed_all` | ActionPanel Button | ✅ |
| `feed_one` | ActionPanel Button | ✅ |
| `heal` | ActionPanel Button | ✅ |
| `buy_food(type, amount)` | ShopPanel Food-Sektion | ✅ (kwarg gefixt) |
| `buy_animal(species)` | ShopPanel Tier-Sektion | ✅ |
| `clean(enclosure_id)` | ActionPanel Button | ✅ |
| ~~`set_ticket_price`~~ | ~~ShopPanel Ticket-Sektion~~ | ❌ Entfernt (nicht in API) |

### Keine Änderungen an Backend/DB

---

## 2026-08-06 — Tier 4: Custom Top & Bottom Bars (Visual Upgrade)

### Änderungen

| # | Feature | Datei | Beschreibung |
|---|---------|-------|-------------|
| 12 | **Custom Top Bar** | `main_window.py` | Native `QToolBar` ersetzt durch `QFrame`-basierten Top-Bar mit 6 Glass-Morphism Stat-Chips + Pause-Button. Gradient-Hintergrund (`C_BG_PANEL2`→`C_BG_PANEL`), 1px Bottom-Border (`C_BORDER`), 8px Border-Radius. |
| 13 | **Custom Bottom Bar** | `main_window.py` | Native `QStatusBar` ersetzt durch `QFrame`-basierten Bottom-Bar mit Status-Label + 4 Stat-Chips + Action-Feedback-Chip. Gleicher Gradient-Stil, 1px Top-Border. |
| 14 | **`_make_chip()` Utility** | `main_window.py` | Factory-Funktion für Glass-Morphism Pill-Badge: `QFrame` mit `qlineargradient` (`C_BG_CARD2`→`C_BG_CARD`), 1px `C_BORDER`, 6px Radius, 11px Font. Enthält Icon-QLabel + Value-QLabel in `QHBoxLayout`. Speichert `_val_lbl` und `_accent` als dynamische Attribute für Updates. |
| 15 | **`_update_chip()` Utility** | `main_window.py` | Aktualisiert Value-Text und optional Accent-Farbe eines Chips zur Laufzeit (jeden Tick aufgerufen). |
| 16 | **Dynamic Color-Coding** | `main_window.py` | Alle Stat-Chips wechseln Farbe basierend auf Wert-Bereichen: Budget (grün≥10k/gold≥2k/rot<2k), Happiness (grün≥70/gold≥30/rot<30), Zoo-Status (grün OFFEN/rot GESCHL.), Tiere (grün alle lebend/gold tote vorhanden/rot keine lebend), Action-Feedback (✅ grün/❌ rot). |
| 17 | **Pause Button Restyle** | `main_window.py` | Pause-Button wechselt komplettes Styling on Toggle: grüner Gradient + "⏸ Pause" → roter Gradient + "▶ Start". |
| 18 | **QScrollArea Wrapper** | `main_window.py` | Action- und Shop-Panel in `QScrollArea` mit `widgetResizable=True` und transparentem Hintergrund gewrappt. Verhindert Clipping und weißen Hintergrund. QTabWidget mit `setSizePolicy(Preferred, Expanding)` + `stretch=2` für korrekte vertikale Verteilung. |
| 19 | **Layout Restrukturierung** | `main_window.py` | Von `QGridLayout` zu `QVBoxLayout` (root) → `QHBoxLayout` (body: map + right column) → `QVBoxLayout` (right: tabs + info + chat + banner). Fixed 1400×900 Window, saubere Stretch-Verteilung. |

### Iterative Verfeinerungen (Nutzer-Feedback)

| Iteration | Änderung | Before | After |
|-----------|----------|--------|-------|
| 1 | Bar Höhe | 46px | 36px |
| 2 | Border Dicke | 2px | 1px |
| 3 | Chip Border-Radius | 10px | 8px |
| 4 | Chip Font | 12px | 11px |
| 5 | Chip Padding vertikal | 5px | 3px |
| 6 | Chip Padding horizontal | 12px | 10px |
| 7 | Pause Button Höhe | 32px | 28px |
| 8 | Pause Button Radius | 8px | 6px |
| 9 | Layout Margins | 12,4,12,4 | 10,2,10,2 |
| 10 | Bar Höhe (2. Iteration) | 36px | **30px** |
| 11 | Chip Border-Radius (2.) | 8px | **6px** |
| 12 | Chip Padding vertikal (2.) | 3px | **2px** |
| 13 | Chip Padding horizontal (2.) | 10px | **8px** |
| 14 | QScrollArea Hintergrund | weiß | **transparent** |
| 14a | QScrollArea viewport | `setAutoFillBackground(True)` (default) | **`setAutoFillBackground(False)`** + `"background: transparent"` via `_transparent_scroll()` |

### Impact
- **Vorher:** Native QToolBar mit einfachen QLabels, native QStatusBar mit `showMessage()`. Shop- und Action-Panel teilweise geclippt.
- **Nachher:** Komplett custom QFrame-Bars mit Glass-Morphism Chips, farbcodierten Werten, Action-Feedback, nahtlosen Scroll-Areas. Alle Panels korrekt formatiert. Keine nativ aussehenden Widgets mehr — alles Dark-Forest-Themed.

### Keine Änderungen an Backend/DB — rein visuelles Upgrade

---

*Changelog aktualisiert am 2026-08-06 — Tier 4 + Bug Fixes*

---

## 2026-08-06 — Tier 4 Revisions: QScrollArea Removal & Panel Fixes

### 🐛 QScrollArea / QTabWidget Pane Conflict (KRITISCH)
**Symptome (verschiedene Iterationen):**
1. Shop/Action Panels zeigten weißen Hintergrund im QScrollArea-Viewport
2. QGroupBox-Borders unsichtbar (kein Kontrast zum transparenten Hintergrund)
3. QComboBox-Dropdown-Menüs weiß (Stylesheet-Cascade durch `viewport.setStyleSheet()` gebrochen)

**Root Cause:** `QScrollArea` hat einen internen `QWidget`-Viewport, der eine eigene Paint-Pipeline besitzt und mit dem `QTabWidget::pane` QSS-Hintergrund kollidiert. Jeder Fix-Versuch (transparentes Stylesheet, `setPalette()`) erzeugte neue Nebenwirkungen.

**Final Fix:** QScrollArea-Wrapper komplett entfernt — ActionPanel und ShopPanel werden direkt in die QTabWidget-Tabs gesetzt. Der Tab-Pane-Hintergrund (`C_BG_PANEL`) aus der globalen QSS wird jetzt sauber durchgereicht.

**Zusätzliche Änderungen:**
- `action_panel.py` + `shop_panel.py`: `setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)` + `from PyQt6.QtCore import Qt` hinzugefügt
- `main_window.py`: `_transparent_scroll()` / `_themed_scroll()` Funktionen entfernt, `QScrollArea` Import entfernt
- QTabWidget: `stretch=2` entfernt, `setSizePolicy(Fixed)` statt `Expanding` → Panels rendern in natürlicher Größe, Chatlog füllt restlichen Platz

**Betroffene Dateien:** `core/main_window.py`, `ui/action_panel.py`, `ui/shop_panel.py`

### Keine Änderungen an Backend/DB

---

## 2026-08-06 — ASCII Sprite System: All 3 Species

### Änderungen

| # | Feature | Datei(en) | Beschreibung |
|---|---------|-----------|-------------|
| 20 | **Old ASCII Lion Replaced** | `assets/ascii_lion.py` | Neue 44-zeilige ASCII-Art ersetzt alte 40-zeilige Version. |
| 21 | **Old Files Deleted** | `assets/ascii_lion copy.py`, `assets/ascii_lion_small.py` | Copy-Datei gelöscht (war temporär). `ascii_lion_small.py` gelöscht (wurde nirgends importiert — Dead Code). |
| 22 | **Lion Detail Bump** | `ui/lion_sprite.py` | Render-Font: 5pt → **6pt**, Target-Width: 80px → **100px**. Resultat: 100×59px Pixmap (vorher 80×53). Mehr Glyphen-Details + größeres Sprite auf der Map. |
| 23 | **ASCII Penguin Sprite** | `assets/ascii_penguin.py`, `ui/penguin_sprite.py` | 74-zeiliger ASCII-Pinguin, `AsciiPenguinSprite(QGraphicsPixmapItem)` Klasse. Render: 5pt → 120px Target → 120×108px. Farbe: slate-blue `#7986cb`. Pixmap-Cache (2 Einträge: live + dead red). Hover-Callbacks, Death-State. |
| 24 | **ASCII Giraffe Sprite** | `assets/ascii_giraffe.py`, `ui/giraffe_sprite.py` | 90-zeilige ASCII-Giraffe, `AsciiGiraffeSprite(QGraphicsPixmapItem)` Klasse. Render: 5pt → 100px Target → 100×113px. Farbe: warm sand `#d4a44a`. Pixmap-Cache (2 Einträge: live + dead red). Hover-Callbacks, Death-State. |
| 25 | **Scene Sprite Routing** | `ui/zoo_scene.py` | Neue `elif`-Branches in `update_entities()`: `species == "lion"` → `AsciiLionSprite`, `species == "penguin"` → `AsciiPenguinSprite`, `species == "giraffe"` → `AsciiGiraffeSprite`. Type-Hints um alle drei Klassen erweitert. |

### Sprite Summary

| Species | Asset File | Sprite Class | Pixmap Size | Live Color | Target Width |
|---------|-----------|-------------|-------------|------------|-------------|
| Lion | `ascii_lion.py` | `AsciiLionSprite` | 100×59 | golden `#e8a838` | 100px (6pt) |
| Penguin | `ascii_penguin.py` | `AsciiPenguinSprite` | 120×108 | slate-blue `#7986cb` | 120px (5pt) |
| Giraffe | `ascii_giraffe.py` | `AsciiGiraffeSprite` | 100×113 | warm sand `#d4a44a` | 100px (5pt) |
| *Other* | — | `AnimalSprite` | 18×18 | species color | N/A (circle) |

### Keine Änderungen an Backend/DB

---

## 2026-08-06 — VS Code Launch Configuration

### Änderungen
- `.vscode/launch.json` erstellt mit 2 Debug-Konfigurationen:
  - **🦁 vivizoo — Frontend**: Startet `frontend.main` mit auto-created Demo-Engine (Löwe, Pinguin, Giraffe)
  - **🦁 vivizoo — Frontend (no engine)**: Startet mit `--no-engine` Flag (leeres UI für isolated Testing)
- Beide nutzen `debugpy`, `justMyCode: true`, `cwd: ${workspaceFolder}`

---

*Changelog aktualisiert am 2026-08-06 — Tier 4 Revisions + ASCII Sprites + Launch Config*
