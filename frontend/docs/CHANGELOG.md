# 📜 Frontend Changelog — vivizoo

> **All changes, decisions and bugs found — documented chronologically.**

---

## 2026-08-06 — Initial Implementation (Core Prototype)

### Phase 0: Planning & Architecture

On 6 August 2026 the folder structure came first (`core/`, `ui/`,
`docs/`, `assets/`), then the documentation: `FRONTEND_ARCHITECTURE.md` as the
UI draft, the implementation plan as the binding specification and the first
class diagram. Before the first line of code, Erik's UI draft and the
backend plan were read against each other — this turned up **ten conflicts**,
each of which is resolved individually below.

### 🔍 Conflict resolutions (10 decisions)

| # | Conflict | Source A | Source B | Decision | Rationale |
|---|----------|----------|----------|-------------|-----------|
| 1 | 5 vs 3 food types | FRONTEND_ARCHITECTURE (5) | backend_core_plan (3: MEAT/PLANTS/FISH) | **3 types** | Backend is the single source of truth |
| 2 | 4-phase day/night vs simple toggle | FRONTEND_ARCHITECTURE (4 phases) | backend_core_plan (only `zoo_open: bool`) | **Simple toggle** | Backend phase 1 has no time_of_day |
| 3 | Animal `stage` field | FRONTEND_ARCHITECTURE shows "Alter · Stadium" (age · stage) | backend_core_plan (no stage in phase 1) | **Hardcoded "Erwachsen"** (adult) | The backend does not supply the field |
| 4 | Heal button requires medicine | FRONTEND_ARCHITECTURE (medicine gate) | backend_core_plan (god mode, no medicine inventory) | **No medicine check** | God mode in phase 1 |
| 5 | Enclosure data | FRONTEND_ARCHITECTURE (expected from the backend) | backend_core_plan (no `enclosures_on_map[]`) | **Hardcoded ENCLOSURE_DEFS** | Fallback until the backend supplies the field |
| 6 | UpgradePanel, DecoSprite, drag & drop | FRONTEND_ARCHITECTURE (extended) | backend_core_plan (phase 3) | **Not implemented** | Anti-implementation checklist |
| 7 | Monolith vs modular | FRONTEND_ARCHITECTURE (one main_window.py) | README/plan (modular: 20+ files) | **Modular** | SRP, one class per file (assessment criterion) |
| 8 | `enclosure_id` field | FRONTEND_ARCHITECTURE (implicitly expected) | backend_core_plan (not in animals_on_map) | **Backend dependency R1** | Documented as a critical request to the backend team |
| 9 | `name` field in animals_on_map | FRONTEND_ARCHITECTURE (needs it for labels) | backend_core_plan (only in entity_info) | **Backend dependency R2** | Likewise to the backend team |
| 10 | Tick loop (who calls engine.tick()?) | Both plans were unclear | — | **Controller.advance_tick() pattern** | Encapsulates both modes (manual/auto timer) |

---

### Phase 1: Code implementation (stage A–E)

#### Stage A: Foundation

| File | Time | Notes |
|-------|------|-----------|
| `core/constants.py` | 17:13 | All colours, dimensions, species mappings, enclosure definitions |
| `ui/styled_widgets.py` | 17:14 | `styled_button()`, `styled_label()` — `styled_card()` deferred (phase 3) |
| `assets/ascii_lion.py` | 17:15 | 40-line ASCII art |
| `assets/ascii_lion_small.py` | 17:15 | 15-line compact version for the info panel |

#### Stage B: Map Sprites

| File | Time | Notes |
|-------|------|-----------|
| `ui/animal_sprite.py` | 17:16 | `AnimalSprite(QGraphicsEllipseItem)` — refactored later (callback instead of signal) |
| `ui/lion_sprite.py` | 17:16 | `AsciiLionSprite(QGraphicsPixmapItem)` + pixmap cache |
| `ui/visitor_sprite.py` | 17:17 | `VisitorSprite` 5×5px dots |
| `ui/enclosure_item.py` | 17:17 | `EnclosureItem` — rewritten completely later |

#### Stage C: Map Container

| File | Time | Notes |
|-------|------|-----------|
| `ui/zoo_scene.py` | 17:18 | `ZooScene` — entity dictionaries, `update_entities()` batching, lighting |
| `ui/zoo_view.py` | 17:18 | `ZooGraphicsView` — zoom/pan/hover/click |

#### Stage D: UI panels

| File | Time | Notes |
|-------|------|-----------|
| `ui/chat_view.py` | 17:19 | `ChatlogWidget` — 500 message cap, HTML formatting |
| `ui/entity_info_panel.py` | 17:19 | `EntityInfoPanel` — HP/hunger/well-being progress bars |
| `ui/action_panel.py` | 17:20 | `ActionPanel` — 6 buttons (feed_all, feed_one, heal, clean, cremate, ticket) |
| `ui/shop_panel.py` | 17:20 | `ShopPanel` — purchase sections for food/animals/ticket price |
| `ui/event_banner.py` | 17:21 | Stub — always hidden in phase 1 |

#### Stage E: Top-Level Wiring

| File | Time | Notes |
|-------|------|-----------|
| `core/frontend_controller.py` | 17:21 | `FrontendController` — bridge to `SimulationEngine`, graceful null engine |
| `core/main_window.py` | 17:23 | `ZooMainWindow` — 1400×900 layout, toolbar, tick loop, signal routing |
| `main.py` | 17:23 | Entry point — QSS dark theme (~150 lines), `_create_demo_engine()` |

---

### 🐛 Bugs found & fixed

#### Bug 1: `pyqtSignal` on non-QObject base classes (CRITICAL)

**Symptom:**
```
TypeError: EnclosureItem cannot be converted to PyQt6.QtCore.QObject
```

**Cause:** In Qt6, `QGraphicsEllipseItem`, `QGraphicsPixmapItem` and `QGraphicsRectItem` are **NOT QObject subclasses**. `pyqtSignal` can only be defined on QObject classes.

**Affected files:**
- `ui/animal_sprite.py` — `entity_hovered` / `entity_unhovered` signals
- `ui/lion_sprite.py` — `entity_hovered` / `entity_unhovered` signals  
- `ui/enclosure_item.py` — `enclosure_clicked` signal

**Fix:** All three sprites switched from signals to the **callback pattern**:
- `set_hover_callback(fn)` / `set_unhover_callback(fn)` on the animal and lion sprites
- `set_click_callback(fn)` on EnclosureItem
- `ZooMainWindow._wire_sprite_callbacks()` sets the callbacks after every sprite batch

**Impact:** `main_window.py` had to have `_connect_signals()` and `_update_sprites()` adjusted. `zoo_scene.py` needed no change (it only passes `update_entities` through).

---

#### Bug 2: `QPainter().fontMetrics()` crash with the offscreen platform (MEDIUM)

**Symptom:**
```
QPainter::fontMetrics: Painter not active
```

**Cause:** `_render_lion_pixmap()` in `lion_sprite.py` called `QPainter().fontMetrics()` to measure text size. In headless/offscreen mode no active painter is available.

**Fix:** `QPainter().fontMetrics()` → `QFontMetrics(font)`. `QFontMetrics` needs no active painter and works without a display too.

**Affected file:** `ui/lion_sprite.py`

---

#### Bug 3: `libGL.so.1` missing (INFRASTRUCTURE)

**Symptom:**
```
ImportError: libGL.so.1: cannot open shared object file
```

**Cause:** PyQt6 requires OpenGL libraries. In the devcontainer (headless Linux) these are not installed by default.

**Fix:** `sudo apt-get install -y libgl1`

---

#### Bug 4: `libEGL.so.1` missing (INFRASTRUCTURE)

**Symptom:**
```
ImportError: libEGL.so.1: cannot open shared object file
```

**Cause:** Same as bug 3 — PyQt6 needs EGL for rendering.

**Fix:** `sudo apt-get install -y libegl1`

---

#### Bug 5: Buttons not clickable — `setProperty()` without `style().unpolish()` (CRITICAL)

**Symptom:** Buttons in the ActionPanel and ShopPanel did not react to hover (no colour change) and triggered no actions on click. Only a few buttons worked.

**Cause:** `styled_button()` set properties via `setProperty("accent", True)` — but Qt6 only re-evaluates QSS selectors such as `QPushButton[accent="true"]` when `style().unpolish()` + `style().polish()` are called. Without those calls the global QSS stylesheet ignores all property-based rules for that button, including `:hover`, `:pressed` and `:disabled`.

Concretely this means:
- `QPushButton[accent="true"] { background: #3fb950; }` was **never applied**
- `QPushButton:hover { background: #30363d; }` was **never applied** (because the button was not registered in the stylesheet system)
- `QPushButton:disabled { ... }` was **never applied**

**Fix:** In `styled_button()`, the following lines were added after `setProperty()`:
```python
button.style().unpolish(button)
button.style().polish(button)
```

**Affected files:** `ui/styled_widgets.py` (line 67-69)

**Affected buttons:** All buttons created via `styled_button()`:
- ActionPanel: feed_all, feed_one, heal, clean
- ShopPanel: "Kaufen" (buy — food, animals), "Übernehmen" (apply — ticket)
- main_window.py: pause button (uses inline QSS, therefore unaffected)

---

#### Bug 6: PyQt6 installation permission (INFRASTRUCTURE)

**Symptom:**
```
PermissionError: [Errno 13] Permission denied: '/opt/venv/lib/python3.14/site-packages/PyQt6'
```

**Cause:** The devcontainer has a protected `/opt/venv` directory. `pip install` without `sudo` fails. With `sudo pip install`, PyQt6 was installed into the system Python (`/usr/local/lib/python3.14/site-packages`), which is what the current Python interpreter finds.

**Fix:** `sudo pip install PyQt6` installs into the global site-packages. The system Python (`/usr/local/bin/python`) can import PyQt6. `QT_QPA_PLATFORM=offscreen` is required for headless tests.

**Side effect:** With `pip install PyQt6>=6.5.0` (from requirements.txt), the `>=6.5.0` was partly interpreted as a file name. Result: an empty file `=6.5.0` in the project root. It was deleted.

---

### 📋 Scope audit — does the implementation match backend phase 1?

#### ✅ Defined in the backend phase 1 API → implemented in the frontend

| Backend API | Frontend implementation | Status |
|-------------|------------------------|--------|
| `engine.tick()` | `controller.advance_tick()` → calls `engine.tick()` | ✅ OK |
| `engine.get_game_state()` | `controller.get_state()` → `_tick()` polls every 100ms | ✅ OK |
| `engine.get_entity_info(id)` | `controller.get_entity_info(id)` → `EntityInfoPanel.show_entity()` | ✅ OK |
| `engine.get_chat_messages()` | `controller.get_chat_messages()` → `ChatlogWidget.append_messages()` | ✅ OK |
| `execute_action("feed_all")` | ActionPanel button "Alle Tiere füttern" (feed all animals) | ✅ OK |
| `execute_action("feed_one", animal_id)` | ActionPanel button "Ausgewähltes füttern" (feed selected) | ✅ OK |
| `execute_action("heal", animal_id)` | ActionPanel button "Tier heilen" (heal animal — no medicine gate, as decided in §2.4) | ✅ OK |
| `execute_action("buy_food", type, amount)` | ShopPanel section "Futter kaufen" (buy food) | ✅ OK |
| `execute_action("buy_animal", species)` | ShopPanel section "Tiere kaufen" (buy animals) | ✅ OK |
| `execute_action("clean", enclosure_id)` | ActionPanel button "Gehege reinigen" (clean enclosure) | ✅ OK |

#### ⚠️ Not defined in the backend phase 1 API — the frontend has it anyway

| Frontend feature | Backend status | Risk | Recommendation |
|-----------------|---------------|--------|-----------|
| `start_cremation` button | **Not in the phase 1 API** | Medium — `execute_action("start_cremation")` will fail | Either remove it from the ActionPanel OR ask the backend to implement it |
| `set_ticket_price` button + slider | **Not in the phase 1 API** | Medium — `execute_action("set_ticket_price")` will fail | Ditto |

#### ❌ Explicitly deferred in backend phase 1 → the frontend has NOT implemented it

| Feature | Status |
|---------|--------|
| 4-phase day/night (only `zoo_open: bool`) | ✅ Simple toggle implemented |
| Animal `stage` field | ✅ Hardcoded "Erwachsen" (adult) |
| `get_stats()` charts | ✅ Not implemented |
| Staff auto jobs | ✅ Not implemented |
| Behaviour composition | ✅ Not implemented |
| EnvironmentFactor (weather) | ✅ Not implemented |
| EventScheduler | ✅ Not implemented |
| MEDICINE inventory | ✅ Not implemented |
| UpgradePanel | ✅ Not implemented |
| DecoSprite | ✅ Not implemented |
| Drag & drop | ✅ Not implemented |
| Save/load | ✅ Not implemented |
| Baby animals | ✅ Not implemented |

---

### 📁 Changes outside `frontend/`

| File | Change | Rationale |
|-------|----------|-----------|
| `README.md` | `Eric` → `Erik` (spelling) | Name corrected |
| `=6.5.0` (root) | Created by pip, then deleted | Was an artefact of `pip install PyQt6>=6.5.0` — `>=6.5.0` was interpreted as a file name |
| System packages | `libgl1`, `libegl1` installed via `apt` | Required for PyQt6 in the headless container |

**No changes to `backend/` or `db/`.**

---

## 2026-08-06 — Tier 1 Visual Upgrade

### Changes

| # | Feature | File(s) | Description |
|---|---------|-----------|-------------|
| 1 | **Gradient theme** | `constants.py`, `main.py` | 6 new colour constants (`C_BG_MID`, `C_BG_PANEL2`, `C_BG_CARD2`, `C_ACCENT_GLOW`, `C_RED_GLOW`, `C_GOLD_GLOW`). QSS with `qlineargradient` for MainWindow, toolbar, buttons, group boxes, inputs. No more flat design — depth through colour gradients. |
| 2 | **Shadow system** | `main_window.py` | `_drop_shadow()` helper function + `QGraphicsDropShadowEffect` on the tab widget, EntityInfoPanel, ChatlogWidget. 16px blur, 4px offset. Creates card depth ("floating" panels). |
| 3 | **Button glow** | `main.py` QSS | Accent buttons: light green glow border (`C_ACCENT_GLOW`). Danger buttons: light red glow border (`C_RED_GLOW`). Hover: border switches to white. Pressed: darker colour. All buttons with `qlineargradient` instead of a flat colour. |
| 4 | **Progress bar enhancement** | `main.py` QSS, `entity_info_panel.py` | Height raised from 16px to 18px. Border radius 4px. `QProgressBar::chunk` border radius 3px. |
| 5 | **Enclosure beautification** | `enclosure_item.py`, `constants.py` | Biome-specific gradients (`BIOME_COLORS_LIGHT` + `QLinearGradient`). Enclosure rectangles now have a lighter top edge that darkens towards the bottom — this creates spatial depth. No more flat blob of colour. |

### Impact
- **Before:** Flat GitHub dark theme, no depth, no shadows, buttons invisible
- **After:** Gradient-based surface with soft drop shadows, glowing buttons, atmospheric enclosures — "game-like"

### No changes to backend/DB — purely a visual upgrade

---

## 2026-08-06 — Tier 2 Game Feel Upgrade

### Changes

| # | Feature | File(s) | Description |
|---|---------|-----------|-------------|
| 6 | **Hover Highlight** | `animal_sprite.py` | Sprites grow from 18→21px on hover with a white glow ring (2px pen). Snaps back on leave. No animation framework needed — instant, game-like pop effect. Dead animals are excluded (no hover feedback). |
| 7 | **Score Popups** | `main_window.py` | Floating text overlay on successful God-mode actions. Red "-" prefix for purchases (buy_food, buy_animal), green "✓" for care actions (feed, heal). Fades out over 2 seconds via `QPropertyAnimation` on opacity. Auto-hides after animation. |
| 8 | **Toolbar Enhancement** | `main_window.py` | Emoji icons on every toolbar label: 📅 Tag, 💰 Budget, ⭐ Reputation, 😊 Happiness, 🔓/🔒 Open/Closed, 🏃 Speed. Tab labels: 🎮 Aktionen, 🛒 Shop. Statusbar: 🐾 Tiere, 👥 Besucher, 🏠 Gehege, 🟢 Bereit. |

### Impact
- **Before:** Static sprites without hover feedback, no visual confirmation of actions, toolbar with plain text labels
- **After:** Sprites "pop" on hover with a white glow ring, actions show animated fade-ins, the toolbar is emoji-rich and immediately readable — **game feel**

### No changes to backend/DB — purely a visual upgrade

---

## 2026-08-06 — Tier 3 Atmosphere Upgrade

### Changes

| # | Feature | File(s) | Description |
|---|---------|-----------|-------------|
| 9 | **Dot-Grid Map Background** | `zoo_scene.py` | 40px dot-grid pattern via `QImage`/`QPainter` brush. One dot per 40×40px grid cell in `C_BG_MID`. Creates a game-map aesthetic (like a tactical map). No external assets needed. |
| 10 | **Ambient Particles** | `zoo_scene.py` (new `_Particle` class) | 30 small floating dots that slowly drift upwards and reappear at the bottom once they reach the top edge. Below visitors, above animals in the Z order. Provides a lively atmosphere ("dust in sunlight"). |
| 11 | **Smooth Day/Night Transition** | `zoo_scene.py` | Instead of an instant toggle: `QVariantAnimation` (800ms, InOutCubic) fades the overlay between transparent (day) and dark (night). `_on_lighting_step()` updates `QGraphicsRectItem.setOpacity()`. `QGraphicsItem` is not a QObject → `QVariantAnimation` instead of `QPropertyAnimation`. |

### Bug fix (tier 3)
- **QVariantAnimation instead of QPropertyAnimation:** `QGraphicsRectItem` is not a QObject — `QPropertyAnimation(self._lighting_overlay, b"opacity")` failed with a `TypeError`. Fix: `QVariantAnimation` with a manual `valueChanged` → `setOpacity()` handler. Same effect, Qt6-compatible.
- **QPen(Qt.PenStyle.NoPen):** `setPen(Qt.PenStyle.NoPen)` does not accept a `PenStyle` enum directly in Qt6. Fix: `QPen(Qt.PenStyle.NoPen)` wrapper.

### Impact
- **Before:** Flat black background, no sense of depth, instant lighting change
- **After:** Dotted map background, gently floating particles, soft 800ms day/night transition — **atmosphere**

### No changes to backend/DB — purely a visual upgrade

---

*Changelog created on 2026-08-06. Updated continuously.*

---

## 2026-08-06 — Phase 1 Bug Fixes & Backend API Alignment

### 🐛 Bugs found & fixed

#### Bug 7: `set_ticket_price` not in the backend phase 1 API (CRITICAL)
**Symptom:** Runtime error when clicking "Übernehmen" (apply) in the ShopPanel — the backend `ActionHandler` does not support `set_ticket_price`.
**Fix:** Ticket section removed from `shop_panel.py` entirely (QSlider, QLabel, button, signal `set_ticket_price`, `_on_set_ticket()` method). The corresponding signal wiring in `main_window.py` was removed.
**Affected files:** `ui/shop_panel.py`, `core/main_window.py`

#### Bug 8: `buy_food` kwarg mismatch (CRITICAL)
**Symptom:** Whichever food type was selected in the ShopPanel, MEAT was always bought.
**Cause:** `main_window.py` dispatched `buy_food` with `food_type=ft`, but the backend action handler expects the parameter as `type=`. The wrong keyword was silently ignored and `type` fell back to the default `MEAT`.
**Fix:** `lambda ft, amt: self._dispatch("buy_food", food_type=ft, ...)` → `lambda ft, amt: self._dispatch("buy_food", type=ft, ...)`.
**Affected file:** `core/main_window.py`

#### Cleanup: Unused imports
- `ui/shop_panel.py`: `QSlider`, `Qt`, `QFont`, `C_GOLD` removed
- `core/main_window.py`: `QGraphicsOpacityEffect` removed, `QToolBar`, `QStatusBar` removed (replaced by custom bars)

### Scope audit — backend API alignment check
| Backend action | Frontend | Status |
|---|---|---|
| `feed_all` | ActionPanel button | ✅ |
| `feed_one` | ActionPanel button | ✅ |
| `heal` | ActionPanel button | ✅ |
| `buy_food(type, amount)` | ShopPanel food section | ✅ (kwarg fixed) |
| `buy_animal(species)` | ShopPanel animal section | ✅ |
| `clean(enclosure_id)` | ActionPanel button | ✅ |
| ~~`set_ticket_price`~~ | ~~ShopPanel ticket section~~ | ❌ Removed (not in the API) |

### No changes to backend/DB

---

## 2026-08-06 — Tier 4: Custom Top & Bottom Bars (Visual Upgrade)

### Changes

| # | Feature | File | Description |
|---|---------|-------|-------------|
| 12 | **Custom top bar** | `main_window.py` | Native `QToolBar` replaced by a `QFrame`-based top bar with 6 glass-morphism stat chips + pause button. Gradient background (`C_BG_PANEL2`→`C_BG_PANEL`), 1px bottom border (`C_BORDER`), 8px border radius. |
| 13 | **Custom bottom bar** | `main_window.py` | Native `QStatusBar` replaced by a `QFrame`-based bottom bar with a status label + 4 stat chips + action feedback chip. Same gradient style, 1px top border. |
| 14 | **`_make_chip()` utility** | `main_window.py` | Factory function for a glass-morphism pill badge: `QFrame` with `qlineargradient` (`C_BG_CARD2`→`C_BG_CARD`), 1px `C_BORDER`, 6px radius, 11px font. Contains an icon QLabel + value QLabel in a `QHBoxLayout`. Stores `_val_lbl` and `_accent` as dynamic attributes for updates. |
| 15 | **`_update_chip()` utility** | `main_window.py` | Updates the value text and optionally the accent colour of a chip at runtime (called every tick). |
| 16 | **Dynamic colour coding** | `main_window.py` | All stat chips change colour based on value ranges: budget (green≥10k/gold≥2k/red<2k), happiness (green≥70/gold≥30/red<30), zoo status (green OFFEN/red GESCHL. — open/closed), animals (green all alive/gold dead ones present/red none alive), action feedback (✅ green/❌ red). |
| 17 | **Pause button restyle** | `main_window.py` | The pause button swaps its entire styling on toggle: green gradient + "⏸ Pause" → red gradient + "▶ Start". |
| 18 | **QScrollArea wrapper** | `main_window.py` | Action and shop panels wrapped in a `QScrollArea` with `widgetResizable=True` and a transparent background. Prevents clipping and a white background. QTabWidget with `setSizePolicy(Preferred, Expanding)` + `stretch=2` for correct vertical distribution. |
| 19 | **Layout restructuring** | `main_window.py` | From `QGridLayout` to `QVBoxLayout` (root) → `QHBoxLayout` (body: map + right column) → `QVBoxLayout` (right: tabs + info + chat + banner). Fixed 1400×900 window, clean stretch distribution. |

### Iterative refinements (user feedback)

| Iteration | Change | Before | After |
|-----------|----------|--------|-------|
| 1 | Bar height | 46px | 36px |
| 2 | Border thickness | 2px | 1px |
| 3 | Chip border radius | 10px | 8px |
| 4 | Chip font | 12px | 11px |
| 5 | Chip padding vertical | 5px | 3px |
| 6 | Chip padding horizontal | 12px | 10px |
| 7 | Pause button height | 32px | 28px |
| 8 | Pause button radius | 8px | 6px |
| 9 | Layout margins | 12,4,12,4 | 10,2,10,2 |
| 10 | Bar height (2nd iteration) | 36px | **30px** |
| 11 | Chip border radius (2nd) | 8px | **6px** |
| 12 | Chip padding vertical (2nd) | 3px | **2px** |
| 13 | Chip padding horizontal (2nd) | 10px | **8px** |
| 14 | QScrollArea background | white | **transparent** |
| 14a | QScrollArea viewport | `setAutoFillBackground(True)` (default) | **`setAutoFillBackground(False)`** + `"background: transparent"` via `_transparent_scroll()` |

### Impact
- **Before:** Native QToolBar with plain QLabels, native QStatusBar with `showMessage()`. Shop and action panels partly clipped.
- **After:** Fully custom QFrame bars with glass-morphism chips, colour-coded values, action feedback, seamless scroll areas. All panels formatted correctly. No more natively styled widgets — everything dark-forest themed.

### No changes to backend/DB — purely a visual upgrade

---

*Changelog updated on 2026-08-06 — Tier 4 + bug fixes*

---

## 2026-08-06 — Tier 4 Revisions: QScrollArea Removal & Panel Fixes

### 🐛 QScrollArea / QTabWidget pane conflict (CRITICAL)
**Symptoms (across several iterations):**
1. Shop/action panels showed a white background in the QScrollArea viewport
2. QGroupBox borders invisible (no contrast against the transparent background)
3. QComboBox dropdown menus white (stylesheet cascade broken by `viewport.setStyleSheet()`)

**Root cause:** `QScrollArea` has an internal `QWidget` viewport that owns its own paint pipeline and collides with the `QTabWidget::pane` QSS background. Every attempted fix (transparent stylesheet, `setPalette()`) produced new side effects.

**Final fix:** QScrollArea wrapper removed entirely — ActionPanel and ShopPanel are placed directly into the QTabWidget tabs. The tab pane background (`C_BG_PANEL`) from the global QSS now passes through cleanly.

**Additional changes:**
- `action_panel.py` + `shop_panel.py`: `setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)` + `from PyQt6.QtCore import Qt` added
- `main_window.py`: `_transparent_scroll()` / `_themed_scroll()` functions removed, `QScrollArea` import removed
- QTabWidget: `stretch=2` removed, `setSizePolicy(Fixed)` instead of `Expanding` → panels render at their natural size, the chatlog fills the remaining space

**Affected files:** `core/main_window.py`, `ui/action_panel.py`, `ui/shop_panel.py`

### No changes to backend/DB

---

## 2026-08-06 — ASCII Sprite System: All 3 Species

### Changes

| # | Feature | File(s) | Description |
|---|---------|-----------|-------------|
| 20 | **Old ASCII Lion Replaced** | `assets/ascii_lion.py` | New 44-line ASCII art replaces the old 40-line version. |
| 21 | **Old Files Deleted** | `assets/ascii_lion copy.py`, `assets/ascii_lion_small.py` | Copy file deleted (was temporary). `ascii_lion_small.py` deleted (was imported nowhere — dead code). |
| 22 | **Lion Detail Bump** | `ui/lion_sprite.py` | Render font: 5pt → **6pt**, target width: 80px → **100px**. Result: 100×59px pixmap (previously 80×53). More glyph detail + a larger sprite on the map. |
| 23 | **ASCII Penguin Sprite** | `assets/ascii_penguin.py`, `ui/penguin_sprite.py` | 74-line ASCII penguin, `AsciiPenguinSprite(QGraphicsPixmapItem)` class. Render: 5pt → 120px target → 120×108px. Colour: slate-blue `#7986cb`. Pixmap cache (2 entries: live + dead red). Hover callbacks, death state. |
| 24 | **ASCII Giraffe Sprite** | `assets/ascii_giraffe.py`, `ui/giraffe_sprite.py` | 90-line ASCII giraffe, `AsciiGiraffeSprite(QGraphicsPixmapItem)` class. Render: 5pt → 100px target → 100×113px. Colour: warm sand `#d4a44a`. Pixmap cache (2 entries: live + dead red). Hover callbacks, death state. |
| 25 | **Scene Sprite Routing** | `ui/zoo_scene.py` | New `elif` branches in `update_entities()`: `species == "lion"` → `AsciiLionSprite`, `species == "penguin"` → `AsciiPenguinSprite`, `species == "giraffe"` → `AsciiGiraffeSprite`. Type hints extended to cover all three classes. |

### Sprite Summary

| Species | Asset File | Sprite Class | Pixmap Size | Live Color | Target Width |
|---------|-----------|-------------|-------------|------------|-------------|
| Lion | `ascii_lion.py` | `AsciiLionSprite` | 100×59 | golden `#e8a838` | 100px (6pt) |
| Penguin | `ascii_penguin.py` | `AsciiPenguinSprite` | 120×108 | slate-blue `#7986cb` | 120px (5pt) |
| Giraffe | `ascii_giraffe.py` | `AsciiGiraffeSprite` | 100×113 | warm sand `#d4a44a` | 100px (5pt) |
| *Other* | — | `AnimalSprite` | 18×18 | species color | N/A (circle) |

### No changes to backend/DB

---

## 2026-08-06 — VS Code Launch Configuration

### Changes
- `.vscode/launch.json` created with 2 debug configurations:
  - **🦁 vivizoo — Frontend**: Starts `frontend.main` with an auto-created demo engine (lion, penguin, giraffe)
  - **🦁 vivizoo — Frontend (no engine)**: Starts with the `--no-engine` flag (empty UI for isolated testing)
- Both use `debugpy`, `justMyCode: true`, `cwd: ${workspaceFolder}`

---

*Changelog updated on 2026-08-06 — Tier 4 revisions + ASCII sprites + launch config*

---

## 2026-08-09 — Backend reconciliation: real data instead of placeholders

In several places the interface showed values the backend does not supply at
all, and conversely ignored data that was available. This pass brings the two
into line.

### 🐛 Defects found

#### Bug 9: Wrong prices throughout the shop (CRITICAL)
**Symptom:** Food and animals cost a multiple of their real price in the UI;
after a purchase the budget shrank quite differently from what was shown.
**Cause:** `constants.FOOD_PRICES` and `ANIMAL_PRICES` were simply made up
(50/30/40 € and 8 000/5 000/3 000 €). In reality they are
`Inventory.FOOD_PRICES` = 8/5/6/25 € and the `BUY_PRICE` class attributes
= 900/700/400 €. A discrepancy of up to a factor of 10.
**Fix:** Both dicts set to the backend values, each with a source reference
in the comment.

#### Bug 10: Chatlog without timestamps (MEDIUM)
**Symptom:** Every message showed `[--:--]`.
**Cause:** `chat_view.py` read `msg["time"]` — a field that never existed.
`MessageLogger.to_dict()` supplies `tick_count`.
**Fix:** Timestamp derived from `tick_count` (480 ticks = 24 h → three
simulated minutes per tick) in the format `[T3 07:30]`.

#### Bug 11: All messages on day 1, 00:00 (MEDIUM, knock-on defect)
**Symptom:** After the bug 10 fix, all entries still carried the same
stamp.
**Cause:** The backend calls `logger.log()` in all seven places **without**
`tick_count`; the default 0 is what reaches the frontend.
**Fix:** `append_messages(messages, current_tick)` — if the tick is missing,
the one from the receiving frame is used. The feed is drained every frame
anyway, so the point in time is correct.

#### Bug 12: Reputation and happiness permanently 0 (MEDIUM)
**Symptom:** The chips "⭐" and "😊" always showed 0.
**Cause:** `finances.to_dict()` only supplies `money`, `revenue`,
`expenses`, `ticket_price` — the two fields do not exist in the live
snapshot.
**Fix:** Chips removed and replaced with real values (revenue, expenses,
ticket price). Reputation and average well-being now appear in the new
statistics tab, where `get_stats()` genuinely supplies them per completed day.

#### Bug 13: Enclosures permanently "0/5" (MEDIUM)
**Symptom:** All enclosures reported zero animals.
**Cause:** `_update_enclosures` counted via `animal["enclosure_id"]` —
a field that `animals_on_map` does not contain.
**Fix:** Occupancy via `get_entity_info(enclosure_id)["free_slots"]`.
In addition, the `cleanliness` that is also supplied is displayed and colours
the enclosure frame.

#### Bug 14: All animals were named after their species (MINOR)
**Symptom:** Tooltips showed "Löwe · Löwe" (lion · lion) instead of "Simba · Löwe".
**Cause:** `animals_on_map` contains no `name`; the scene used its own
placeholder.
**Fix:** `FrontendController` resolves the name once per animal via
`get_entity_info()` and caches it; animals that disappear drop out of the
cache.

#### Bug 15: `buy_animal` always fails — **backend defect**
**Symptom:** Every animal purchase ended with "Fehler bei Aktion 'buy_animal'"
(error during action 'buy_animal').
**Cause:** `backend/core/action_handler.py::_action_buy_animal` calls
`create_animal(species, animal_id="tmp", name="tmp")` without `x`/`y`, which
`Animal.__init__` strictly requires → `TypeError`.
**Status:** Not fixable in the frontend (the backend belongs to Benjamin). The
shop section stays, because it matches the documented API.
As a frontend fix, the controller passes the **original error message**
through instead of hiding it behind "Fehler bei Aktion" — which is how the
defect became visible in the first place. Documented as request R5.

#### Bug 16: Score popup never faded out (MINOR)
**Symptom:** The success message above the map vanished abruptly instead of
fading.
**Cause:** `QPropertyAnimation` on `windowOpacity` — that property only
takes effect on real windows, not on child widgets.
**Fix:** `QGraphicsOpacityEffect` with the animation on its `opacity`.

#### Bug 17: Capping the chatlog destroyed the formatting (MINOR)
**Symptom:** From 500 messages onwards the feed lost all colours.
**Cause:** `_trim_to_max()` read back `toPlainText()` and wrote it as
plain text.
**Fix:** The rendered HTML lines are buffered; when capping, the content is
rebuilt from the buffer.

### ✨ Backend data newly put to use

| Feature | File(s) | Source in the backend |
|---|---|---|
| **Four real times of day** with an 800 ms colour cross-fade instead of a two-state toggle | `constants.py`, `zoo_scene.py` | `system.time_of_day` |
| **Daily statistics tab** — visitors, profit, average animal well-being, reputation, deaths per day | `ui/stats_panel.py` (new) | `engine.get_stats()` |
| **Optional persistence** attached so that the statistics get any data at all | `main._create_persistence()` | `DbGateway` + `ZooDatabase(":memory:")` |
| **Enclosure info on click** — biome, occupancy, cleanliness | `entity_info_panel.py` | `get_entity_info(enclosure_id)` |
| **Life status in the info panel** instead of a hardwired "Erwachsen" (adult) | `entity_info_panel.py` | `is_dead` |
| **Medicine in the inventory** (display only, no sale) | `shop_panel.py` | `inventory["MEDICINE"]` |
| **Revenue, expenses, ticket price** as chips | `main_window.py` | `finances` |
| **Animal purchase with name and target enclosure** instead of just `species` | `shop_panel.py` | `buy_animal(species, name, enclosure_id)` |
| **Working speed selector** 1×/2×/5×/0.5× | `frontend_controller.py` | multiple `tick()` calls per frame |
| **Budget gating** — purchase buttons disable themselves before the backend rejects | `shop_panel.py` | `finances.money` |
| **Explanatory tooltips** on disabled actions | `action_panel.py` | inventory, `is_dead`, selection |

### 🧭 Deliberate omissions

* `engine.start()` / `pause()` / `set_speed()` remain unused — they
  control the internal backend thread, which would tick twice alongside the
  Qt loop. Rationale in `IMPLEMENTATION_PLAN` §2.7.
* Buying medicine: technically possible (`buy_food(type="MEDICINE")`), but
  without effect as long as `heal` consumes nothing in god mode.
* Ticket price slider: no matching action in the API.

### No changes to `backend/` or `db/`.

---

## 2026-08-09 — Refactoring: sprite inheritance and assessment criteria

### ♻️ Sprite hierarchy

**Starting point:** `lion_sprite.py`, `penguin_sprite.py` and
`giraffe_sprite.py` were about 197 lines each and roughly 95 % identical — they
differed in four values (ASCII art, colour, target width,
font size). The same death logic, the same hover handling and the same
pixmap cache existed three times in the code.

**New:**

```
EntitySprite ................ contract: update_position(), entity_id
└── AnimalSpriteBase ........ template method update_state(), hover, death
    ├── AnimalSprite ........ ellipse + initial
    └── AsciiAnimalSprite ... pixmap rendering + cache
        ├── AsciiLionSprite ...... 5 class attributes (39 lines)
        ├── AsciiGiraffeSprite ... 5 class attributes (39 lines)
        └── AsciiPenguinSprite ... 5 class attributes (39 lines)
└── VisitorSprite
```

`update_state()` now exists exactly once and calls the hooks
`render_alive()` / `render_dead()` — a classic template method. Around 470
lines of duplication are gone; the rendered pixmaps are unchanged
(100×59, 100×113, 120×108 px).

**Detail:** Qt graphics objects are sip types with their own metaclass, hence
no `abc.ABC` — the abstract methods raise `NotImplementedError` and
are documented as abstract. The base classes come **before** the Qt class in
the base list so that their methods win in the MRO.

### 📏 Assessment criteria

| Criterion | Measure |
|---|---|
| "Eine Aufgabe, eine Datei" (one task, one file) | `StatusChip` extracted from `main_window.py` and `AmbientParticle` from `zoo_scene.py` → 21 classes in 21 files |
| "Wer was macht muss im Code ersichtlich sein" (who did what must be visible in the code — deduction-relevant) | `Module owner: Erik (frontend).` in the docstring of **every** one of the 31 Python files; the four `__init__.py` now have real package docstrings |
| "Für jede Funktion mindestens zwei Tests beschrieben" (at least two tests described for every function) | 36 missing `Tests:` blocks added, mostly on private helper methods → **154 functions, 332 test descriptions, no gaps** |
| Design-Visualisierung (design visualisation) | Class diagram updated to 21 classes, hierarchy diagram and **four sequence diagrams** added |
| Testbeschreibung & Teststrategie (test description & test strategy) | `docs/test_plan.md` new — fixtures, PyQt preconditions, 14 edge cases, manual acceptance test |
| Evidence trail | `docs/criteria_audit.md` new — every criterion with its location and a verification command |

### 📄 Documentation

* `frontend/README.md` rewritten: correct file list (the old one named
  four files that never existed), start-up instructions including `libgl1`/`libegl1`,
  operating overview, interface contract, section "bewusst nicht
  dargestellt" (deliberately not shown).
* `FRONTEND_ARCHITECTURE.md` rewritten — it now describes the
  actual structure instead of the original draft.
* `IMPLEMENTATION_PLAN.md` §2 revised: §2.2 (four phases instead of a toggle),
  §2.3 (real life status instead of "Erwachsen"), §2.5 (`free_slots` instead of
  point-in-rectangle) corrected; §2.7–2.9 new; data contract §3 verified against
  the code; request R5 (backend bug) added.

### No changes to `backend/` or `db/`.

---

## 2026-08-09 — Review pass: 31 confirmed findings

A final review pass over the entire frontend code **and** all
Markdown files, carried out as a multi-agent review across nine
dimensions (controller/entry point, main window, sprites, panels,
scene/view/constants, MD↔MD, MD↔code, assessment criteria,
removal candidates) followed by an adversarial cross-check of every
finding. Result: **31 confirmed, 15 refuted**.

The cross-check was not cosmetic — among other things it exposed three
initial findings as false alarms (particle Z collision with no real
drawing path, a supposedly unreachable over-capacity frame, a supposedly
expensive enclosure update) that would otherwise have led to changes with no
benefit.

### 🐛 Defects fixed

#### Bug 18: Three of four action buttons had no effect (CRITICAL)
**Symptom:** "Ausgewähltes füttern" (feed selected), "Tier heilen" (heal animal) and "Gehege reinigen" (clean enclosure)
always reported `❌ No animal with id None.` or
`❌ No enclosure with id None.` — even though the selection and button state were
correct.
**Cause:** `ActionPanel.action_triggered` is declared as
`pyqtSignal(str, dict)` and was connected directly to
`_dispatch(self, action: str, **kwargs)`. PyQt passes a slot only as many
arguments as it accepts **positionally** — which here is
exactly one. The payload dictionary with `animal_id` or `enclosure_id`
was silently discarded, with no error on the Qt side.
**Fix:** Connection via an unpacking adapter, analogous to the shop signals
that were already wired that way:
`connect(lambda action, params: self._dispatch(action, **(params or {})))`.
**Affected file:** `core/main_window.py`
**Why it went undetected for so long:** All previous tests called
`controller.execute_action(...)` directly and thereby bypassed exactly the
broken signal path. Only a test that really clicks the button exposes
the defect — added to the test plan as an edge case.

#### Bug 19: Info panel frozen (MAJOR)
**Symptom:** HP, hunger and well-being bars permanently showed the
values from the moment of selection. After 200 ticks the backend reported hunger 24,
the panel still 0.
**Cause:** `_refresh_info_panel()` was only called on hover and
click events, not in the render loop.
**Fix:** `_tick()` now calls it every frame; in addition, the new
`_reconcile_selection()` discards a selection whose animal the backend has removed
— otherwise the panel kept showing an animal that had already died.

#### Bug 20: Chatlog stopped auto-scrolling from message 500 (MAJOR)
**Cause:** The capping branch rebuilds the document with `setHtml()`, which
resets the text cursor to position 0; the subsequent
`ensureCursorVisible()` therefore pinned the feed to the **beginning**.
**Fix:** Move the cursor to the end of the document after `setHtml()`.

#### Bug 21: Clock contradicted the time of day (MINOR)
**Symptom:** The chip showed "Mittag 06:00" (noon), "Abend 12:00" (evening), "Nacht 18:00" (night).
**Cause:** The clock anchored tick 0 at 00:00, but the backend starts its
day with the phase `MORNING`.
**Fix:** The new `ZooMainWindow.clock_minutes()` shifts the clock by a
quarter day — MORNING 06:00–11:59, NOON 12:00–17:59, EVENING 18:00–23:59,
NIGHT 00:00–05:59. `ChatlogWidget.format_timestamp()` uses the same anchor.

#### Bug 22: "Alle Tiere füttern" (feed all animals) active with unsuitable food (MINOR)
**Cause:** The button only checked whether *any* food was in stock.
But the backend feeds each animal exclusively from its
`PREFERRED_FOOD` — a full fish store feeds no lion, and the action
reported "Fed 0 animal(s)".
**Fix:** The button is only active if suitable food is in stock for at least one
living animal; a dedicated tooltip explains the case
"stock available but matching no animal".

#### Bug 23: Zoom exceeded its limit (MINOR)
**Cause:** The value **before** scaling was checked, not the
result. The last accepted step landed at 3.059 instead of 3.0.
**Fix:** Clamp the target value and derive the factor from it. Measured: 50
steps in end exactly at 3.0000, 100 out at 0.3000.

#### Bug 24: Black hairline at the map edge (MINOR)
**Cause:** The lighting overlay kept Qt's black default pen —
visible as a 1 px line along the top and left edges, even with completely
transparent midday light.
**Fix:** `setPen(QPen(Qt.PenStyle.NoPen))`.

#### Bug 25: Sprite stayed enlarged after dying while hovered (MINOR)
**Cause:** `hoverLeaveEvent` set `_hovered = False` inside the
`if not self._is_dead` branch. If the animal dies while the mouse is over it,
the flag stays set forever.
**Fix:** Reset the state unconditionally, gate only the visual hook.

#### Bug 26: Letter of the circle sprite at the map origin (MINOR)
**Cause:** `AnimalSprite._centre_label()` computed only with the
diameter and ignored the position of the circle, because the child label sits
relative to the item origin while the ellipse rectangle lies around `(_cx,_cy)`.
**Fix:** Take the circle's origin into account. (Affects only the fallback sprite
for species the backend does not know.)

#### Bug 27: Status line frozen forever (MINOR)
**Cause:** `_last_action_msg` was set but never reset —
after the first action the bottom bar permanently showed the same
message instead of the live summary.
**Fix:** `QTimer.singleShot(5000, …)` releases the line again.

#### Bug 28: Animations piled up (MINOR)
**Cause:** Every successful action created a new
`QPropertyAnimation` as a child of the window; the old one stayed alive.
**Fix:** A single reused animation.

#### Bug 29: Occupancy display in the shop ignored `free_slots` (MINOR)
**Fix:** `_refresh_enclosure_info()` derives the occupancy from
`capacity − free_slots` if necessary, so that a raw `get_entity_info` payload
is rendered correctly as well.

#### Bug 30: Pixmap offset not reset after a colour change (MINOR)
**Fix:** `render_alive()`/`render_dead()` call `_recentre_offset()`. The
two variants are the same size, but the documented promise of
centring now holds regardless.

#### Bug 31: Dead attribute check in the click detection (MINOR)
**Cause:** `ZooGraphicsView.mousePressEvent` checked
`hasattr(item, "enclosure_clicked")` — that attribute has not existed since the
switch to callbacks, and besides, `itemAt()` always returns the overlay anyway
because of the screen-filling overlay. Consequence:
`map_clicked` fired on **every** click, including on an enclosure.
**Fix:** The complete item stack under the cursor is checked via
`isinstance(item, EnclosureItem)`. Re-measured: a click inside an enclosure
no longer triggers `map_clicked`, a click on empty space still does.

### 📄 Documentation corrected

| Finding | Correction |
|---|---|
| Four documents said "9 StatusChips", the code creates 11 | set to 11 everywhere, including the multiplicity in the class diagram |
| README claimed "all eight" engine methods, listed six and excluded three | corrected to "all six methods the interface needs" |
| Root README referred to `backend/requirements.txt` — that file does not exist | line removed, replaced with a rationale (the backend is pure standard library) |
| Root README promised "Tastenkürzel" (keyboard shortcuts), there are none | corrected to "Maussteuerung" (mouse control) |
| The assessment header of IMPLEMENTATION_PLAN still described the old sprite structure (`BaseEntitySprite`) | updated to the actual chain |
| The same header marked Python 3.14 and "eine Klasse pro Datei" (one class per file) as open | set to done, date updated |
| Cross-references to §8 and §10 — neither section exists | redirected to §4 and §7 respectively, also in `constants.py` and `shop_panel.py` |
| `criteria_audit` referred to the "Legende in §7" (legend in §7) of the class diagram, which was only numbered up to §6 | legend numbered as §7 and the OOP section as §8 |
| "25 Python files" | 31 |
| "147 functions / 314 test descriptions" | 150 / 324, table in `test_plan.md` recalculated row by row |
| The test tree left four modules without a test file even though its own table counts them | `test_main.py`, `test_event_banner.py`, `test_particle.py`, `test_styled_widgets.py` added |
| Edge case table | four new cases from this pass added |

### 🤖 AI details made precise

`KI_REFLEXION.md` §1 now names the models actually used instead of
just the tool: **DeepSeek v4 Pro** via the **Cline extension** in
VS Code for planning, initial generation and the first version of the documentation —
**Claude Opus 5** via Claude Code as the final
reviewer/controller/corrector. Extended with the rationale for why the generator
and the reviewer are deliberately two different models.

### No changes to `backend/` or `db/`.

---

## 2026-08-09 (addendum) — Full review evaluation: 71 + 9 findings

The previous entry reported 31 confirmed findings. That was an
**interim evaluation**: at the time of reading, only 15 of the 19
agents had delivered a result. The full evaluation yields
**91 examined findings — 71 confirmed, 20 refuted**, plus **9 findings from a
final completeness critic** that independently looked for what
the nine dimensions had missed.

The critic was worth it: it found the second critical defect.

### 🐛 Second critical defect

#### Bug 32: The animal selection did not survive the trip to the button (CRITICAL)
**Symptom:** "Ausgewähltes füttern" (feed selected) and "Tier heilen" (heal animal) could in practice
never be triggered — the buttons disabled themselves before the click arrived.
**Cause:** An animal counted as selected only **while the mouse was over
it**. `_on_unhover()` set `_selected_animal_id = None`. The path from the
sprite on the map to the button in the right-hand column inevitably triggers
`hoverLeaveEvent`; 100 ms later at the latest, `_tick()` had disabled both
buttons.
**Why bug 18 did not cover this:** Its fix repaired the
signal path, and the evidence for it set the selection programmatically via
`win._on_hover(...)`. That way no `hoverLeaveEvent` ever fired — the second
defect stayed hidden behind exactly the same testing gap as the first.
**Fix:** Separation of preview and selection.
`AnimalSpriteBase` gained `set_click_callback()` and a
`mousePressEvent`; hover now only sets `_hovered_animal_id` (preview in the
info panel), a **click** fixes `_selected_animal_id`. The info panel
shows preview before fixed selection before enclosure before placeholder.

#### Bug 33: The click fell through the entire item stack (CRITICAL, knock-on defect)
**Symptom:** After bug 32, the click set the selection — and cleared it again in
the same event.
**Cause:** Qt's default `mousePressEvent` **ignores** the click. Since all
four animals sit on top of each other at the same starting coordinate, the
scene passed the event on from sprite to sprite down to the `EnclosureItem`
underneath — and its handler sets `_selected_animal_id = None`.
**Fix:** `AnimalSpriteBase.mousePressEvent` and
`EnclosureItem.mousePressEvent` call `event.accept()` instead of passing it on
to the base class.

### 🐛 Further defects fixed

#### Bug 34: Shop tab cut off at the bottom edge (MAJOR)
`setFixedSize(1400, 900)` was 50 px below the minimum of its own
layout (1222 × 950). Qt squeezed the `QTabWidget` below its minimum, and the
lower part of the shop was unreachable. **Fix:** Minimum heights of the
statistics table (200 → 140 px) and the chatlog (150 → 110 px) reduced —
layout minimum now 896 px, the window stays at the documented
1400 × 900.

#### Bug 35: Chat messages were lost from speed 2× upwards (MINOR)
`advance_tick()` computed several ticks per frame and drained the
message queue only afterwards. If the simulation crosses a day boundary in
the process, `DbGateway._build_events()` drains the **same** logger for the
database — everything accumulated before that was gone. **Fix:** The controller
buffers after each individual tick.

#### Bug 36: Wrong error diagnosis in the controller (MINOR)
The `except AttributeError` branch reported "Unbekannte Aktion" (unknown action) — but a
genuinely unknown action name arrives as a `ValueError`. So the branch
could only fire on an internal backend error and then claimed
the wrong thing. **Fix:** A `hasattr` check up front, branch removed.

#### Bug 37: Silent failure at start-up (MINOR)
If building the demo engine failed, `_create_demo_engine()` returned
`None` without comment and the window started empty, with no hint.
**Fix:** Error message with the cause and an installation hint on stderr.

#### Bug 38: Non-cancellable status line timers (MINOR)
The fix from bug 27 armed a new `QTimer.singleShot(5000, …)` per action.
Two actions in quick succession → the timer of the first deleted the
message of the second. **Fix:** a single owned
`QTimer` with `setSingleShot(True)` that is restarted.

#### Bug 39: Dead sprite stayed enlarged (MINOR, residual defect from bug 25)
The first fix reset `_hovered` but still left `highlight_off()`
behind `if not self._is_dead`. **Fix:** run both unconditionally;
`AnimalSprite.highlight_off()` keeps the red frame if the
animal is dead.

#### Bug 40: The dead counter in the animal chip could never be non-zero (MAJOR)
`Zoo.update_animals()` removes an animal from the enclosure in the same tick in
which it dies — `is_dead=True` never reaches the map. Measured over 1500 ticks:
zero occurrences, even though the daily statistics report four deaths.
**Fix:** The chip now shows the population against total capacity ("4 / 12"), and the
dead count only appears if a dead animal really is in the snapshot.

#### Bug 41: Dead signals in `ZooGraphicsView` (MINOR)
`entity_hovered` and `entity_unhovered` were declared and documented,
but never emitted or connected — hover runs via callbacks.
**Fix:** removed, the module docstring now explains why.

### 📄 Further documentation corrections

| Claim | Reality |
|---|---|
| "Mittlere Maustaste: Karte verschieben" (middle mouse button: pan the map) | `ScrollHandDrag` pans with the mouse button held down, and only at zoom > 1 |
| "Widgets enthalten keine eigenen Farbwerte" (widgets contain no colour values of their own) | `StatusChip`, the bars in the `EntityInfoPanel` and `styled_widgets` set inline QSS — now named instead of denied |
| "Fünfstufige Vererbungskette" (five-level inheritance chain) | four classes, three inheritance steps |
| Verification command `grep "import backend\|from db"` | did not match the actual `from backend.x import y` form; replaced by a `grep -rnE` that finds it |
| "Klassendiagramm aller 21 Klassen mit Attributen und Methoden" (class diagram of all 21 classes with attributes and methods) | shows the load-bearing members, not every getter — the claim was reworded accordingly |
| The QSS docstring listed `QToolBar`, `QStatusBar`, `QSlider`, `QCheckBox` | replaced by the widgets the frontend actually creates |
| `CHAT_COLORS` "Typen, die MessageLogger sendet" (types that MessageLogger sends) | the backend never sends `EVENT` — marked as provision for the future |
| Test descriptions in the chatlog said "T2 00:00" | after the clock shift it is "T2 06:00" |
| Counts | 154 functions, 332 test descriptions (table in `test_plan.md` recalculated row by row) |

### 📌 Newly documented backend limitation

`Zoo.add_animal()` places every animal at the fixed starting coordinate
(300, 200) and accepts no position; `animals_on_map` contains no
`enclosure_id`. All animals therefore start visibly inside the rectangle
"Savanne 1" (savannah 1) and roam freely across the map from there — the drawn
position contradicts the (correct, `free_slots`-derived)
occupancy display. Not resolvable from the frontend; recorded in
`frontend/README.md` under "Bekannte Backend-Einschränkungen" (known backend limitations).

### 🧭 Methodological lesson

Both critical defects survived all previous tests, because those
established the state programmatically instead of producing it the way a user
would. Only `QTest.mouseClick` / `QTest.mouseMove` on the real
viewport exposed them. For selection-bound actions, the test plan now
explicitly requires going through real mouse events.

### No changes to `backend/` or `db/`.

---

## 2026-08-09 (round 3) — Clean-up, visibility, tests actually executed

> **Brief:** implement the removal recommendations that had previously only been
> *reported*, strengthen the frontend for assessment without changing the backend, and
> document the deliberately open points as such.
> **Tools:** Claude Opus 5 (Claude Code) as implementer and reviewer.
> **Result:** 34 files · 24 classes · 182 functions ·
> 403 test descriptions · **187 executed tests, all green**.

### 🗑️ Removed (previously reported as a recommendation, now carried out)

| Removed | Extent | Reason |
|---|---|---|
| `Z_DECORATIONS`, `Z_DRAG`, `C_SHADOW`, `GLOW_BLUR`, `GLOW_OFFSET` | 5 constants | zero uses, verified via AST. The gaps in the Z order remain — now with a comment explaining why |
| `styled_button(danger=…)` together with `_DANGER_CSS` | 17 lines | no destructive action exists. How the variant would be retrofitted is described in `IMPLEMENTATION_PLAN.md` §5 F6 |
| `styled_label(large=, color=, size=)` | 3 parameters | no caller; `dim` and `bold` remain, both are used |
| QSS for `QToolBar`, `QStatusBar`, `QSlider`, `QCheckBox` | 4 blocks | none of these widgets is ever created |
| QSS `QPushButton[accent="true"]`, `[danger="true"]` | 4 selectors | `setProperty("accent", …)` is never called anywhere — the rules could never take effect |
| `CHAT_COLORS["EVENT"]` | 1 entry | the backend does not send this type; unknown types fall back to `C_TEXT` anyway |
| `ZooScene.clear_all()`, `.enclosure_item()`, `.phase` | 3 accessors | without a caller. `animals` and `animal_sprite()` remain — both are used |
| `EnclosureItem.capacity` | 1 property | the value is already in the snapshot |
| `ZooMainWindow._paused` | 1 field | second copy of a state that lives in the controller; the window now reads `controller.paused` |
| **`EventBanner`** | 98 lines | permanently invisible widget with no data source — replaced, see below |

**Guiding principle:** whatever has no caller and is not needed for any planned
extension is removed. Whatever is meant to come later is listed with effort and
blocker in [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md) §5 — not as dead code in the repository.

### ✨ New — four classes, all built from existing backend data

#### `AnimalListPanel` (tab "🐾 Tiere" — animals)

The most important addition, and for a concrete reason: the backend
places every animal at the fixed coordinate (300, 200), so freshly
started animals stand **exactly on top of each other**. Clicking an individual
sprite was a matter of luck — and so were the two
selection-bound actions.

The population list gives every animal a unique, always hittable row
with HP, hunger and well-being. A click on it leads to the **same**
slot as a click on the sprite, so that the map and the list can never
disagree. The data source is the new
controller method `get_animal_details()`, which combines the map entry with the
backend's hover payload — not a single new field.

#### `AlertBanner` (replaces `EventBanner`)

The same idea, but with a real data source: `WARNING` and `ERROR` entries
from `get_chat_messages()` appear as a coloured strip above the map.
At 5× speed the message feed scrolls faster than one can
read; a warning was gone after a second.

The strip counts in **render frames**, not milliseconds — at 5× it
therefore lives exactly as long as the situation it describes. And it
sits as a child of the map view above the scene rather than in the right-hand
column: the window was fixed at 1400×900, the column already demands
894 px, and an occasional message must not permanently occupy 36 px
(that is exactly what the first attempt at integration foundered on — a measured 930 px).

#### `TrendChart` (in the statistics tab)

Profit per completed day as bars above and below a zero line,
drawn in a custom `paintEvent()`. The same `get_stats()` rows
as the table — the table answers "what happened on day 7?", the
chart "is it getting better?".

#### `HelpDialog` + nine keyboard shortcuts

`Leertaste` (space bar), `S`, `F`, `E`, `H`, `R`, `Esc`, `1`–`4`, `F1`. The
simulation keeps running while you operate it; aiming for a button
costs you the moment.

The bindings and the help text come from the **same** tuple list
(`help_dialog.SHORTCUTS`): a key therefore cannot exist undocumented
and a documented key cannot be missing. The dangerous case has been checked too
— typing "Sheffe Rex" into the shop's name field triggers
neither pause nor a speed change nor a tab change, because Qt gives the
focused input field precedence via `ShortcutOverride`.

### 🔧 Further improvements

| Change | Effect |
|---|---|
| **Selection marker on the map** | `AnimalSpriteBase.set_selected()` applies a green `QGraphicsDropShadowEffect` — **one** implementation for ellipse *and* pixmap, because a graphics effect works around arbitrary drawings. Without it, after a selection made from the list it would be invisible which animal is meant |
| Self-healing marker | If a sprite is recreated (the animal was briefly out of the snapshot), `_wire_sprite_callbacks()` restores the marker |
| **Chat filter, counter, "Leeren"** (clear) | "Alle / Nur Warnungen / Nur Erfolge" (all / warnings only / successes only). What is filtered is the view, not the buffer — going back to "Alle" shows the whole history again |
| Tab labels count along | "🐾 Tiere (4)", "📊 Statistik (2)" |
| The status line knows about the pause | Previously the next frame immediately overwrote "⏸ Pausiert" (paused) with the live summary again |
| Shortcuts without a selection explain themselves | `H` without a selected animal sends **nothing** to the backend and writes "Erst ein Tier auswählen" (select an animal first) into the status line |
| `ZooScene._animals` typed polymorphically | A named type alias instead of the repeated species list at every occurrence |
| `mousePressEvent(event: QGraphicsSceneMouseEvent \| None)` | Instead of `object` + a `hasattr` check — the real Qt type, so that the analysis tools can follow along |
| QSS extended by `QTableWidget::item:selected` and `QDialog` | The new table and the help dialog needed a selection colour and a background |

### 🧪 New: 187 executed tests

Until now tests were exclusively *described* — as the assignment
requires. Now the automatable part of them is also
**executed**, on the basis of the standard library `unittest`, without a
single new dependency:

```bash
QT_QPA_PLATFORM=offscreen python -m unittest discover -s frontend/tests -t .
# Ran 187 tests in 0.9s ... OK
```

| File | Checks |
|---|---|
| `test_constants.py` | Colour formats, enclosure geometry, species tables, times of day, thresholds |
| `test_layering.py` | **Architecture:** no `backend`/`db` imports outside `main.py`, at most one class per file, module owner everywhere, ≥ 2 test descriptions on every function |
| `test_frontend_controller.py` | Enrichment, name cache including expiry, speed budget, chat buffer, error paths |
| `test_widgets.py` | Chatlog, AlertBanner, animal list, chart, all panels, sprites, enclosures, scene, view |
| `test_main_window.py` | Clock, render loop, dispatch payload, **selection via real mouse clicks**, keyboard shortcuts, alert path |

The three critical defects of earlier rounds are recorded as regression tests
— and specifically via the route that made them visible in the first
place: `QTest` mouse and keyboard events on the real viewport instead of
direct method calls.

`test_layering.py` deserves a mention of its own: four of the
assessment criteria are structural ("eine Klasse je Datei" — one class per file,
"Modulverantwortlicher in jeder Datei" — module owner in every file, "sichtbare Schichtentrennung" — visible layer separation,
"zwei Testbeschreibungen je Funktion" — two test descriptions per function). Until now they stood as a claim
in `criteria_audit.md`. Now the test run fails as soon as one of them
breaks.

#### Bug 42: Built in and found by ourselves — the QApplication disappeared

The first version of `tests/support.py` returned the `QApplication`
without keeping a reference. CPython collected it immediately, and the
next test aborted with "Must construct a QApplication before a QWidget"
— *after* the first green test, which obscured the cause. **Fix:**
module global `_APP`. Recorded as a pitfall in `test_plan.md` §4.

#### Bug 43: Leftover windows swallowed all keyboard tests

`QShortcut` applies in the window context and only fires in the **active** window.
Because every test opened a new window without closing the previous one,
all seven keyboard shortcut tests came to nothing — green when run individually,
red in the suite. **Fix:** `_window()` first closes all previous
windows. Also documented in `test_plan.md` §4.

> Both defects were in the test code, not in the production code. They are
> recorded nonetheless: a test that is green or red for the wrong reason
> is just as dangerous as a bug — it only shifts when you
> notice it.

### 📄 New: `docs/IMPLEMENTATION_PLAN.md` §5

The counterpart to the implementation plan: **what was deliberately not built,
why, and what it would concretely take.** Every entry with an effort estimate
and blocker.

* **§1 Frontend alone** — eight points, all feasible without a backend change
  (sortable list, second chart row, CSV export, resizable
  window, `QSettings`, `danger` variant, decoration layer, new species)
* **§2 Needs the backend first** — eight points with the field missing in each
  case, among them `enclosure_id`, the broken `buy_animal`, weather, staff
* **§3 Tested vs. only described** — what is automated and what
  deliberately is not
* **§4 Deliberately not planned** — where the boundary lies and why

### 📝 Documentation synchronised

`README.md` (keyboard shortcuts, animal list, alert strip, test instructions),
`FRONTEND_ARCHITECTURE.md` (layout tree, four new design decisions),
`IMPLEMENTATION_PLAN.md` (§0 structure, §1 scope instead of phase promises,
§2.6 rationale for the removal, §2.6a the three new displays, §4/§5
figures), `criteria_audit.md`, `test_plan.md` (coverage table,
implemented tests, 11 new edge cases, 13-step acceptance test),
`frontend_class_diagram.md` (three new classes, **fifth
sequence diagram** for list selection), `KI_REFLEXION.md`.

All figures recalculated, not carried forward: **34 files, 24 classes
in 24 files, 182 functions, 403 test descriptions.**

### ✅ Final check

```
python -m frontend.main            → starts, no Qt warning over 1600 ticks
unittest discover frontend/tests   → 187 tests, all green
Layout minimum                     → 894 px ≤ 900 px (no clipping)
Alert strip visible                → layout minimum unchanged at 894 px
Layering test                      → backend/db only in main.py
```

### No changes to `backend/` or `db/`.

---

## 2026-08-09 (round 4) — Resizable, sortable, accessible, automatically checked

> **Brief:** seven concrete improvements that are possible without a backend
> change — dissolve the fixed window size, throttle the population list,
> error dialog, CI, accessibility, sortable list, second
> chart row.
> **Result:** 35 files · 25 classes · 201 functions ·
> 460 test descriptions · **224 executed tests, all green**.

### 🖥️ The fixed window size was a risk for the submission

`setFixedSize(1400, 900)` means on a notebook with 1366 × 768: the
window does **not fit on the screen**, and a window that is too large cannot
be pulled back. Over WSLg the usable area is additionally
smaller than the monitor. Anyone opening the submission on a normal laptop
never sees the footer bar.

The laborious part was not the splitter but the layout minimum. The right-hand
column demanded 894 px, of which 490 px went to the shop tab alone — and a
`QTabWidget` is as tall as its tallest tab.

| Change | Effect |
|---|---|
| `setMinimumSize(1000, 640)` + `resize(1400, 900)` | opens as before, but can be dragged smaller |
| `QSplitter` between the map and the right-hand column | the user decides the division; `setChildrenCollapsible(False)` so that neither half disappears without trace |
| Every tab in a transparent `QScrollArea` | the shop tab scrolls instead of stretching the whole window. Layout minimum: **894 px → 531 px** |
| `ZooGraphicsView` without a fixed size, scrollbars "as needed" | it was nailed to 802 × 602 and thereby nailed the window down |
| `setElideMode(ElideRight)` on the tab bar | at a column width of 340 px, labels are truncated instead of whole tabs being hidden behind arrows |

**New signal `ZooGraphicsView.resized`.** The alert strip and the
action popup are pixel-positioned children of the map, not
layout elements — without this signal they kept the width from
program start for ever. `QGraphicsItem` cannot have signals, but the *view* can:
it is a `QObject`.

Measured: at 1000 × 640 the map is 636 × 529 with scrollbars, the
strip 616 px wide; at 1600 × 1000 it is 1236 and 1216 px.

### 🐾 Population list: sortable, filterable, without relying on colour

* **Numeric sorting.** A click on "Hunger" orders by
  urgency. `QTableWidgetItem` compares text — "100" would come before "9".
  The new class `ui/numeric_table_item.py` overrides `__lt__` and sorts
  by the stored numeric value; the marker in the text does not interfere.
* **Filter "Braucht Aufmerksamkeit"** (needs attention). Hides animals without a warning. The
  criterion is the same marker the user sees — display and
  filter cannot drift apart.
* **Markers instead of colour alone.** Every critical value carries `!!`, every
  notable one `!`. Red against green is no distinction for roughly every twelfth man.
* **Ids travel with the row.** After sorting, row 0 is a different
  animal. The animal id is now in `Qt.ItemDataRole.UserRole` of the
  name cell, not in an index list.
* **Dagger after the name.** As a prefix, `✝` would have sorted all dead animals to
  one end of the alphabet.

### 📊 Four metrics instead of one

Above the chart, a combo box selects between **profit, visitors,
average well-being and reputation** — all four are in the same
`get_stats()` row, so no additional backend call is needed. The
day rows are cached in the panel, and a switch only redraws.
A new metric = one entry in `constants.TREND_METRICS`.

### ⚡ One inefficiency, built in and fixed by ourselves

The population list costs **one `get_entity_info()` call per animal**, and
it ran ten times per second. With 30 animals that is 300 calls per
second for a table nobody reads that fast.

It now updates every five frames — but a **changed animal population**
comes through immediately, because that comparison is free: the ids are
already in the snapshot. A selection also bypasses the throttle, so that
table and map never contradict each other.

### 💬 Error dialog instead of stderr

`_create_demo_engine()` now returns `(engine, reason)` instead of just
`engine`. If the start fails, a `QMessageBox` explains what is missing and
which `pip install` helps. Anyone who does not start the application from the terminal
previously saw an empty window with no explanation at all.

### ♿ Accessibility

| Measure | Why |
|---|---|
| `accessibleName` on all eleven chips | Their label is an emoji — a screen reader reads "Pile of Poo" or skips them |
| `accessibleDescription` follows the value | The name says *what* it is, the description *what is in it* |
| Buttons state their keyboard shortcut | "Tier heilen. Tastenkürzel H." (heal animal. Shortcut H.) |
| Disabled buttons explain themselves accessibly | The reason was only in the tooltip — invisible to everyone who does not hover over it with the mouse |
| Defined tab order | Controls → panels → info → messages → map, i.e. the order in which one works |
| Map and tables named | Otherwise they are announced as "view" and "table" |
| Markers in addition to colour | see population list |

### 🤖 CI: `.github/workflows/frontend-tests.yml`

Runs the 224 tests on every push and every pull request that
touches `frontend/**` — on Python 3.12 **and** 3.14, headless via
`QT_QPA_PLATFORM=offscreen`. A second step starts the application without an
engine and ticks 20 frames. That way a break in the
frontend interface shows up in the PR instead of three days later at start-up.

The file lies outside `frontend/` — it is deliberately scoped so
that it only checks the frontend and touches neither the backend nor the database.

#### Bug 44: A property that paralyses Qt (MAJOR)

`TrendChart` was given a property `metric` in order to read out the metric being
drawn. After that **every paint** aborted:

```
TypeError: 'str' object is not callable
Aborted (exit 134)
```

Cause: `QWidget` inherits from `QPaintDevice`, and that defines the virtual
method **`metric()`** — Qt calls it during the paint pass to
query DPI and dimensions. The property shadowed it, Qt received a string where it
expected a method, and `qFatal()` terminated the process.

Particularly unpleasant: the message appears **without a traceback** and
**twelve times during construction**, long before the test checks anything —
the test output broke off mid-run without reporting a single failure.
Only found through a direct `render()` into a `QPixmap` outside
the test runner.

**Fix:** renamed to `metric_key`, with the rationale in the docstring. A test
now checks that `chart.metric` is still callable — i.e. that it is not
shadowed again.

#### Bug 45: Sorting moved the rows out from under the click (MAJOR, avoided)

When building in the sorting, `_row_ids[row]` would have selected the wrong
animal as soon as the user sorted a column. Switched over to the id in
`UserRole` before the first test run; the test
`test_click_after_sorting_reports_the_right_animal` pins it down.

### 🧪 Tests: 187 → 224

Newly covered: window size and scaling, splitter, overlay tracking,
numeric sorting, click after sorting, markers, filter,
throttling, metric switching, accessibility, engine factory including its
error path, QSS without dead selectors.

Two further pitfalls in the test code documented (`test_plan.md` §4):
a widget inside a layout cannot be checked via `resize()` — change the
window size and call `processEvents()`. And the open
SQLite handle of the demo engine is now closed by the test that
opened it, instead of leaving a `ResourceWarning` behind in every run.

### 📝 Documentation

`README.md` (operation, keyboard shortcuts, file tree), `FRONTEND_ARCHITECTURE.md`
(layout tree, splitter, scroll areas), `IMPLEMENTATION_PLAN.md`,
`criteria_audit.md` (four new pieces of evidence), `test_plan.md`
(coverage table, 11 new edge cases, 3 new acceptance steps),
`frontend_class_diagram.md` (`NumericTableItem`, changed signatures),
`IMPLEMENTATION_PLAN.md` §5 (F1, F2, F4 and the CI run ticked off; F9 newly added),
`KI_REFLEXION.md`, root `README.md`.

### ✅ Final check

```
unittest discover frontend/tests   → 224 tests, all green
1600 frames / 2399 ticks           → no Qt warning
Layout minimum                     → 531 px (previously 894), window from 1000×640
Overlay at 1000 px / 1600 px       → 616 px / 1216 px wide, tracks cleanly
Layering test                      → backend/db still only in main.py
```

### No changes to `backend/` or `db/`.

---

## 2026-08-09 (evening) — Static analysis: pylint from 8.12 to 10.00

A `pylint frontend/` run reported **293 findings**. The task was to
work through them without simply switching them off. The full
list — every remaining exception with its rationale — is in
[`test_plan.md`](test_plan.md) §8; here only what was changed in the code.

### 🔎 First insight: 47 of the 293 messages did not concern the code at all

`pylint` sits in the devcontainer under `/usr/local/py-utils/` in its own
interpreter whose shebang contains `-E` — i.e. without `PYTHONPATH`. PyQt6
lives in `/opt/venv`. The linter could never see Qt and reported
`E0401: Unable to import 'PyQt6.QtWidgets'` in every file, plus four
`E1101 no-member` as a consequence of unknown base classes.

Demonstrated with the same linter and `PYTHONPATH` set: 293 → 246
findings, 8.12 → 9.06. The 47 were a property of the environment.

`.pylintrc` therefore got **one** line — `ignored-modules=PyQt6` — and the
CI workflow a second job that installs PyQt6 and lifts the exception again with
`--ignored-modules=`. Both variants stand at
10.00/10 today; the code does not depend on the exception.

### 🔧 Rebuilt instead of switched off (44 genuine findings)

| Finding | Change |
|---|---|
| `duplicate-code` between `action_panel` and `stats_panel` | New function `styled_widgets.panel_layout()`. The four lines that every panel begins with now exist once; all four panels use them. |
| `ShopPanel.__init__` with 51 statements | Split into `_build_food_section()` and `_build_animal_section()` |
| `_update_labels` with 53 statements and 18 local variables | Split into `_update_clock_chips`, `_update_finance_chips`, `_update_population_chips` — the three groups the eleven chips fall into anyway |
| `TrendChart._paint_bars` with 16 local variables | Scale calculation extracted into `_scale()` |
| 40 × `attribute-defined-outside-init` | `ZooMainWindow` and `AnimalSpriteBase` now declare their state at class level. In the window this has turned into a complete widget inventory — 27 lines that say for the first time, in one place, what the window consists of. |
| 4 × `disallowed-name "bar"` | `menu_bar`, `top`, `bottom`, `progress` |
| `wrong-import-position` + `global-statement` in `support.py` | `QT_QPA_PLATFORM` is now set in `tests/__init__.py`: Python runs the package `__init__` before every test module, i.e. **before** the first PyQt6 import. That puts the import back at the top. The `global _APP` has given way to a module list that keeps the `QApplication` alive just as reliably. |
| `too-many-lines` + `too-many-public-methods` in `test_widgets.py` | Split into `test_widgets.py` (panels) and **`test_map.py`** (sprites, enclosures, scene, zoom). Not only because of the size: the two halves break for different reasons — geometry here, values there. The roster tests were separated into presentation and operation. |
| 9 × `import-outside-toplevel` in the tests | Moved to the module header |
| 6 × missing docstrings | Added |
| `too-few-public-methods` on `AmbientParticle` | `drift_speed` property added. It was overdue anyway: the docstring had always promised a test over that value, which existed only as `_drift_speed`. |
| 2 × `too-many-positional-arguments` | `AnimalSprite` and `EnclosureItem` now take their arguments keyword-only. It costs nothing — every caller already named them — and it prevents swapped `w`/`h`. |

### ⚠️ Pitfall: `_RosterCase` as a `unittest.TestCase`

When splitting the roster tests, the shared fixture was itself a
`TestCase` at first. `unittest` collects TestCase classes via inheritance, not
via the name — the leading underscore is no protection. The base class would
therefore have run too, and every inherited test would have been executed **three
times**. Now `_RosterFixture` is a plain mixin class without `TestCase`, and both
concrete classes inherit `(_RosterFixture, unittest.TestCase)`.

### ⚠️ Pitfall: explanation behind the pragma

`# pylint: disable-next=no-member  (mixin: Qt-Basis fehlt statisch)` produces
four new messages instead of none: pylint reads everything after the equals
sign as comma-separated message names and complains about
`unknown-option-value` for "mixin", "Qt-Basis", "fehlt" and "statisch". The
rationale belongs on a separate comment line above it.

### 🧪 Five new tests (229 instead of 224)

Two for `panel_layout()`, three for `AmbientParticle` (speed within the
configured range, movement by exactly that value, wrap-around at the
top edge). The first attempt at the layout test failed with
`RuntimeError: wrapped C/C++ object of type QVBoxLayout has been deleted` —
the temporary `QWidget()` was collected and took its layout with it. A
named widget is enough.

### 📝 Documentation

New: [`test_plan.md`](test_plan.md) §8 — starting point, each of the 25 remaining
exceptions justified individually, and the evidence for which of them would be
superfluous in an environment with PyQt6 installed (exactly four).
Updated: `test_plan.md` (module list, new fixture description),
`README.md` (file tree, test count, pylint section), `criteria_audit.md`,
`IMPLEMENTATION_PLAN.md`, `IMPLEMENTATION_PLAN.md` §5, root `README.md`, CI workflow.

### ✅ Final check

```
pylint frontend/                          → 10.00/10  (global linter)
pylint --ignored-modules= frontend/       → 10.00/10  (with PyQt6, strict)
unittest discover frontend/tests          → 229 tests, all green
Layering test                             → backend/db still only in main.py
```

### 🔍 Addendum: cross-checking our own documentation

An independent check against the assessment criteria found **eight verifiable
false statements in our own documentation** — each of them a figure a
reviewer can recalculate:

| Where | said | correct |
|---|---|---|
| `frontend/README.md` | 403 test descriptions | **482** (understated its own achievement by 79) |
| `frontend/README.md` (2×) | 4 sequence diagrams | **5** |
| `frontend/README.md` | "vier Meldungen stillgelegt" (four messages silenced) | **25** |
| `docs/test_plan.md` §1 | 187 runnable tests | **229** — and the same file already showed "Ran 229 tests" in §3 |
| `docs/criteria_audit.md` | 23 edge cases | **39** |
| `docs/criteria_audit.md` | 13 acceptance steps | **16** |
| `docs/KI_REFLEXION.md` | 182/201 functions documented | **209/209** |
| `docs/test_plan.md` §5 | "minimumSizeHint darf 900 px nicht überschreiten" (minimumSizeHint must not exceed 900 px) | measured 922 × 531 against the configured minimum of 1000 × 640 — the edge case contradicted the test two lines further down |

Plus three substantive errors:

* **The hover sequence diagram showed the opposite of the code.** It set
  `_selected_animal_id`; in fact `_on_hover` only sets
  `_hovered_animal_id`, because hovering is deliberately only a preview — exactly the
  distinction that fixed one of the three critical defects. Corrected
  together with a note and the fallback to a clicked animal on leaving.
* **Two rows of the design decision table** in
  `FRONTEND_ARCHITECTURE.md` described the state before the last round
  ("Kein `QScrollArea` um die Panels" — no QScrollArea around the panels, "das Fenster ist auf 1400×900
  festgelegt" — the window is fixed at 1400×900). Both have been wrong since the splitter rebuild.
* **`docs/test_plan.md` referred to seven test files that never existed**
  (`test_zoo_scene.py`, `test_action_panel.py`, `test_chat_view.py`, …).
  All references now point to modules that really exist.

And one finding of our own from this round: 11 test descriptions collided
**within the same class** — two methods of the same class promised
the same test name, which could not both be implemented in a single
`TestCase`. All renamed, and a script checks it.

The pylint section itself was likewise imprecise: §2 was titled "Die einzige Anpassung an
`.pylintrc`" (the only adjustment to .pylintrc), but kept quiet about the project-wide
suppressions `no-name-in-module` and `invalid-name` that were already there. Both are now
listed there, with a counter-check: `invalid-name` hides 10 messages, of which 8 are
Qt overrides, one a type alias and `setUp` — no domain logic. Likewise
corrected: the 10.00/10 of the strict variant is measured locally, not from
a CI run, which has not yet happened on GitHub.

### 📐 Class diagram extended and straightened out

The cross-check had measured a member coverage of roughly
55 % for the class diagram and found two places that claim something false.

**Two errors:**

* `HelpDialog` listed `SHORTCUTS` as a class member. It is a
  **module constant** in `help_dialog.py` — and that is precisely the point: both
  `_register_shortcuts()` and the help text read the same table. It now
  appears as its own module box, with both arrows pointing at it.
* The three species classes showed running text (`ASCII_LION, gold, 100 px, 6 pt`)
  instead of class attributes — and the colour was invented. It comes from
  `SPECIES_COLORS`, not from a hex literal.

**Coverage 55 % → 100 %.** All 350 attributes and methods from the code
are now in the diagram. The thinnest were `ShopPanel` (36 %),
`EntityInfoPanel` (45 %), `ActionPanel` (50 %) and `ZooMainWindow` (52 %,
among other things the eleven status chips, the header bar buttons and the new
methods `_update_clock_chips` / `_update_finance_chips` /
`_update_population_chips` were missing). Newly added as a box: the `assets` package.

**Two new diagram types** — until now there were only class and
sequence diagrams:

* **§8 State diagram of the selection** (`stateDiagram-v2`). Four states:
  empty, preview, animal, enclosure. It makes the difference between
  `_hovered_animal_id` (transient) and `_selected_animal_id` (fixed) visible —
  the distinction on which three of the defects that actually occurred hinged.
  Plus a table of which action button is active in which state.
* **§9 Component diagram of the layers** (`flowchart`). It shows that
  `main.py` is the only place with a `backend`/`db` import and that
  all communication runs through six methods on the `FrontendController` —
  the same rule that `tests/test_layering.py` enforces via AST.

That makes **9 Mermaid diagrams in four types** instead of seven in two.

**Verification script** (counts diagram members against `ast.parse()` of every
production file):

```python
import ast, pathlib, re
doc = pathlib.Path("frontend/docs/frontend_class_diagram.md").read_text()
block = doc.split("```mermaid", 1)[1].split("```", 1)[0]
dia, cur = {}, None
for line in block.splitlines():
    m = re.match(r"\s*class (\w+) \{", line)
    if m:
        cur = m.group(1); dia[cur] = set(); continue
    if cur and line.strip() == "}":
        cur = None; continue
    if cur:
        for part in re.split(r",\s*", line.strip().lstrip("+-#$*")):
            name = re.split(r"[ (:=]", part.strip().lstrip("+-#"))[0]
            if name:
                dia[cur].add(name)

hit = total = 0
for path in pathlib.Path("frontend").rglob("*.py"):
    if "tests" in path.parts or "__pycache__" in path.parts:
        continue
    for node in ast.parse(path.read_text()).body:
        if not isinstance(node, ast.ClassDef):
            continue
        # Members = methods and class attributes defined in the class
        # body plus the distinct self.X attributes. Important: read the
        # class attributes only from node.body, NOT from ast.walk --
        # otherwise every local variable of a method is counted too.
        members = {c.name for c in node.body if isinstance(c, ast.FunctionDef)}
        for c in node.body:
            if isinstance(c, (ast.Assign, ast.AnnAssign)):
                targets = c.targets if isinstance(c, ast.Assign) else [c.target]
                for t in targets:
                    if isinstance(t, ast.Name):
                        members.add(t.id)
        for sub in ast.walk(node):
            if isinstance(sub, (ast.Assign, ast.AnnAssign)):
                targets = sub.targets if isinstance(sub, ast.Assign) else [sub.target]
                for t in targets:
                    if isinstance(t, ast.Attribute) and getattr(t.value, "id", "") == "self":
                        members.add(t.attr)
        members -= {"__init__"}
        total += len(members)
        hit += len(members & dia.get(node.name, set()))
print(f"{hit}/{total} members in the diagram")   # 350/350
```

### 🚨 Document audit: one repository finding, eleven false claims

Every Markdown file was checked by its own reviewer against the real code.
The most important finding was not in a document at all.

**24 files were not in git.** The last commit (`a341652`) predates two days
of work. Unpacking the committed state shows 14 UI modules instead of 25, no
`frontend/tests/` at all, no population list, no alert banner, no statistics
panel — and no `.github/`. A zip of the working directory contains
everything; a clone does not. Reported, not fixed: committing is the module
owner's call.

**Eleven verifiable false claims**, all confirmed against the code and
corrected:

| Where | said | actually |
|---|---|---|
| both READMEs, headless check | `FrontendController(_create_demo_engine())` | the function returns a **tuple**, so no engine ever arrived — and the snippet still printed "starts and ticks cleanly". It was verifying an empty window. Now unpacks the tuple and prints the animal count: **4** |
| this changelog, verification script | printed `354/580` right next to the claim "350/350" — `ast.walk` was counting every local variable | prints `350/350` |
| `test_plan.md` coverage table | total 201/460, five rows wrong | regenerated from the code: **209/482** |
| `KI_REFLEXION.md` | "all colours come from `C_*` constants" | 59 hex literals — now named as an exception |
| `KI_REFLEXION.md` | "`test_layering.py` checks the top four points" | it checks three; import cycles and encapsulation are not among them |
| `FRONTEND_ARCHITECTURE.md` | "`ScrollHandDrag`, only effective above zoom 1" | set unconditionally in the constructor |
| `README.md` | "three tests with real `QTest` events" | **twelve** — the README understated itself by a factor of four |
| `criteria_audit.md` and the class diagram | "every property has a caller" | five are read only by the tests |
| class diagram, component view | "21 widget and sprite classes" | 23 |
| class diagram, three signatures | `_update_feed_one(animals: list)`, `_text_cell(…) void`, `_section(title, lines)` | `animal: dict\|None`, `→ QTableWidgetItem`, `_section(title)` |
| the pylint section, "in full" | `class Mute` was missing from the list | added, count corrected |

Plus one wording change across four documents: the CI workflow does not
"run on every push" — it is set up and green locally, but has never run on
GitHub, because `.github/` is not committed either. And `criteria_audit.md`
listed the AI reflection as delivered although §3 still consisted of four
placeholders; it now flags that section as open.

**What this round is really about:** every one of these is a number or a
command a reviewer can check in under a minute. None of them was a bug in
the code — all eleven were in the documentation *about* the code, and four
of them understated what the module actually does.

### 📚 Documentation merged: ten files down to eight

A review of all Markdown files (one reviewer per file, against the code)
found 4746 lines with considerable overlap. Two files have been
absorbed instead of continuing to tell the same story from the side:

| was | is now | why |
|---|---|---|
| `ROADMAP.md` | `IMPLEMENTATION_PLAN.md` **§5 Ausblick** (outlook) | Both are planning: the plan says what was decided, the outlook what deliberately stayed open. With §6 and §7 the plan had two sections that repeated the roadmap anyway — they are gone without replacement. |
| `pylint.md` | `test_plan.md` **§8 Statische Analyse** (static analysis) | A test says whether the code *does* the right thing; the linter, whether it does so comprehensibly. Both are quality assurance. |

Deleted without replacement, because it is covered more completely elsewhere:

* `IMPLEMENTATION_PLAN.md` § "GRADING REQUIREMENTS" (84 lines) — recited
  the root README back; `criteria_audit.md` has the same mapping with
  location and verification command.
* `IMPLEMENTATION_PLAN.md` §5 checklist (45 lines) — self-certification
  without evidence, and it contradicted `criteria_audit.md` on the state of the
  AI reflection.
* `FRONTEND_ARCHITECTURE.md` §3 ASCII inheritance tree — a hand copy of the
  Mermaid diagram, already drifted apart.
* `README.md` documentation table at the end of the file — third mention of the same files.
* `CHANGELOG.md` minute-by-minute log of phase 0 — boiled down to a single paragraph.

All **19 incoming references** were redirected, including two from
production code (`core/constants.py`, `ui/styled_widgets.py`). Counter-check:
no dead `.md` link anywhere in the repository, no mention of the two
deleted files any more.

### ✂️ AI reflection shortened: 184 → 126 lines

The reflection was accurate but overlong for what it has to prove. Cut to its
load-bearing parts: the tool table from four rows to two, the defect list
from eleven rows to the six instructive ones (the full list lives here in
this changelog anyway), the three failure patterns from three paragraphs to
one dense one.

What Erik still has to write himself is now impossible to miss — three
markers instead of a single sentence in a note box: a box at the top of the
file, a second one above the section, and a literal `**[TO BE WRITTEN]**` in
each of the four subsections.

The learning reflection moved from §3 to §4 in the process: the critique of
the AI output now comes first, because it supplies the material the
reflection draws on. `criteria_audit.md` follows the new numbering.

### 🌍 All documentation switched to English

The code and its docstrings were already English; the documents were not.
Seven Markdown files were translated (one translator per file against a
shared glossary, followed by a proofreader).

**Deliberately left in German**, because they are literals in the code and a
reader has to be able to find them there: the UI labels ("Alle Tiere
füttern", "Braucht Aufmerksamkeit", "OFFEN", the tab names, the enclosure
names), each with an English gloss in brackets. Likewise the official
assessment criteria ("Testbeschreibung & Teststrategie", "Reflexion &
KI-Einsatz"), which are quoted verbatim from the assignment.

The 49 German inline comments in the Python code went with them. They were
not part of the request, but after the switch they would have been the only
German left in an otherwise English module — comments only, no behaviour.

### ⚠️ Two defects the translation introduced

**The whole table of contents in `FRONTEND_ARCHITECTURE.md` was dead.** All
eleven anchors still pointed at the German slugs
(`#2-schichten-und-verantwortlichkeiten`) while the headings had been
translated. The translator reported it: the instruction "never change a link
target" had been followed to the letter, which was exactly wrong for
in-document anchors. Rebuilt from the actual headings.

**Section numbering in `test_plan.md` §8 read `8.8.1` instead of `8.1`.**
Our own fault, from the merge script one step earlier: two regular
expressions applied to the same string in sequence, and the second one
matched what the first had just produced. Four cross-references pointed
nowhere as a result.

Three smaller ones: German identifiers and output strings in the
verification snippets (`grund`/`tiere` → `reason`/`animals`), a paragraph in
this changelog that lost its opening word in translation, and a reference to
a README section under its old German name.

### ✅ Final check

```
8 Markdown files, all English          229 tests, all green
dead links or anchors:  none           pylint frontend/  10.00/10
code fences:  all paired               Mermaid blocks:  9, intact
```

### No changes to `backend/` or `db/`.
