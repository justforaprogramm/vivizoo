# 🎨 Frontend Architecture — vivizoo

> **Module:** Frontend · **Module owner:** Erik
> **As of:** 9 August 2026 · **Framework:** PyQt6
> **Map:** QGraphicsScene/QGraphicsView · **Window:** 1400×900, resizable from 1000×640
> **Theme:** Premium Dark Forest

This document describes the **structure and the design decisions** of the
frontend. What exactly is to be built, and why particular conflicts were
resolved the way they were, is in [`docs/IMPLEMENTATION_PLAN.md`](docs/IMPLEMENTATION_PLAN.md);
the diagrams are in [`docs/frontend_class_diagram.md`](docs/frontend_class_diagram.md).

---

## Contents

1. [Architecture overview](#1-architecture-overview)
2. [Layers and responsibilities](#2-layers-and-responsibilities)
3. [The sprite hierarchy](#3-the-sprite-hierarchy)
4. [The controller as an enrichment layer](#4-the-controller-as-an-enrichment-layer)
5. [Render loop and timing](#5-render-loop-and-timing)
6. [Map: scene, view, lighting](#6-map-scene-view-lighting)
7. [Panels of the right column](#7-panels-of-the-right-column)
8. [Header and footer bar](#8-header-and-footer-bar)
9. [Constants and theme](#9-constants-and-theme)
10. [Data flow](#10-data-flow)
11. [Design decisions in retrospect](#11-design-decisions-in-retrospect)

---

## 1. Architecture overview

```
QApplication  (QSS dark theme from main._get_qss())
└── ZooMainWindow (QMainWindow, opens at 1400×900, minimum 1000×640)
    ├── QMenuBar ........................ Datei → Beenden  (File → Quit)
    ├── Top bar (QFrame, 30 px)
    │     📅 Tag · 🕐 Phase+Uhrzeit · ⏸ Pause · 🏃 Speed
    │     ····· 💰 Budget · 💵 Einnahmen · 💸 Ausgaben · 🎫 Ticket · 🔓 Status
    ├── Body (QSplitter, horizontal, not collapsible)
    │   ├── ZooGraphicsView (resizable, min 420×320) ── ZooScene (800×600)
    │   │        ├── EnclosureItem[]      biome rectangles with occupancy/cleanliness
    │   │        ├── AmbientParticle[30]  floating dust motes
    │   │        ├── AsciiLionSprite[]    ┐
    │   │        ├── AsciiGiraffeSprite[] ├ ASCII pixmaps
    │   │        ├── AsciiPenguinSprite[] ┘
    │   │        ├── AnimalSprite[]       circle fallback for new species
    │   │        ├── VisitorSprite[]      5 px dots
    │   │        └── Lighting overlay     day-phase tint
    │   │   Overlays above the map (no layout space):
    │   │        ├── AlertBanner          WARNING/ERROR, visible for 60 frames
    │   │        └── Score popup          action confirmation, 2 s fade-out
    │   └── Right column (340–460 px)
    │       ├── QTabWidget: 🎮 Aktionen | 🐾 Tiere | 🛒 Shop | 📊 Statistik
    │       │        (each tab in a transparent QScrollArea)
    │       │        └── Statistik: metric selector + TrendChart + table
    │       ├── EntityInfoPanel   animal OR enclosure form
    │       └── ChatlogWidget     colour-coded message feed, filterable
    ├── Bottom bar (QFrame, 30 px)
    │     Statuszeile ····· 🐾 Tiere · 👥 Besucher · 🏠 Gehege · 📋 letzte Aktion
    └── QTimer(100 ms) → _tick() → advance_tick() → get_state() → render
```

---

## 2. Layers and responsibilities

| Layer | Package | Rule |
|---|---|---|
| **Entry point** | `main.py` | The only place that imports `backend` and `db` — and even then locally, inside the engine factory. Builds QApplication, theme, engine, controller, window. |
| **Core** | `core/` | Window, controller, constants. Not a single widget. |
| **UI** | `ui/` | Widgets and graphics items, exactly one class per file. Knows only `constants` and the snapshot — never the backend. |
| **Assets** | `assets/` | Pure data modules (ASCII art). No logic, no Qt imports — which also makes them usable from a console frontend. |

The dependency direction is strictly one-way:

```
main.py  →  core/  →  ui/  →  assets/
   ↓
backend.SimulationEngine   (imported only here)
```

---

## 3. The sprite hierarchy

The critical design decision of this module. Previously there were three
almost identical ASCII sprite classes (~197 lines each, ~95 % duplicated code).
Today:

The hierarchy as a diagram, including the methods, is in
[`docs/frontend_class_diagram.md`](docs/frontend_class_diagram.md) §2.

**Template method.** `update_state(x, y, is_dead)` exists exactly once — in
`AnimalSpriteBase`. It moves the sprite and detects the transition
alive ↔ dead; *what* the state looks like is decided by the hooks
`render_alive()` and `render_dead()` of the subclass. A new species therefore
brings no new state logic with it, only a new appearance.

**Why no `abc.ABC`?** Qt graphics items are sip types with their own
metaclass; combining them with `ABCMeta` breaks with a
metaclass conflict. The abstract methods therefore raise
`NotImplementedError` and are documented as abstract.

**Why callbacks instead of signals?** `QGraphicsItem` is **not** a
`QObject` in Qt6. `pyqtSignal` cannot be defined on it (error:
*"EnclosureItem cannot be converted to PyQt6.QtCore.QObject"*). Sprites
therefore report hover and clicks through registered callbacks.

**Why a pixmap instead of `QGraphicsTextItem`?** ASCII art has to fit into
100 px of width, which corresponds to roughly 3 pt type — at that size Qt
renders without anti-aliasing and the outline falls apart. Instead it is
drawn into a `QImage` at 5–6 pt and scaled down with `SmoothTransformation`.
The result is cached per (class, colour): two render passes per species
(alive, dead) for the entire runtime.

---

## 4. The controller as an enrichment layer

`FrontendController` is more than a pass-through. The backend snapshot
is deliberately lean; so that no widget has to invent data, the
controller adds exactly two things:

| Addition | Why | How |
|---|---|---|
| `name` per animal | `animals_on_map` contains no name — otherwise every lion would be called "Löwe" (lion) | one `get_entity_info(id)` per animal, result in the `_name_cache`; animals that disappear drop out of the cache |
| `enclosures_on_map` | The backend supplies no enclosure list, but does know `cleanliness` and `free_slots` per enclosure id | map geometry from `ENCLOSURE_DEFS` + live values, `occupied = capacity − free_slots` |

In addition it encapsulates error handling: `execute_action()` catches
`ValueError` (unknown action) and any other exception and returns a
result dict — including the **original error text**, so that
integration errors stay visible instead of failing silently.

---

## 5. Render loop and timing

```python
def _tick(self):
    self._controller.advance_tick()      # 1. advance the simulation
    state = self._controller.get_state() # 2. enriched snapshot
    if not state: return                 #    (no backend → render nothing)
    self._state = state
    self._update_sprites(state)          # 3. map
    self._update_labels(state)           # 4. chips + statistics on day change
    self._update_panels(state)           # 5. actions + shop
    msgs = self._controller.get_chat_messages()
    if msgs: self._chatlog.append_messages(msgs, tick)   # 6. messages
```

**What drives the simulation?** The backend brings its own
background thread with it (`engine.start()`). The frontend does
**not** use it: running in parallel with the Qt loop, it would tick twice and
rendering and simulation would drift apart. Instead the
controller calls `tick()` itself — deterministically and in step with the
window.

**Speed** is therefore a frontend gate: `advance_tick()` carries
a fractional budget and computes `speed` ticks per frame (at 0.5×,
one every second frame). **Pause** sets the same gate to zero.

**Statistics only on a day change.** `get_stats()` requires a
database access; the Statistik tab is therefore only rebuilt when
the day number changes — not ten times a second.

---

## 6. Map: scene, view, lighting

**`ZooScene`** holds three dictionaries (`_animals`, `_visitors`,
`_enclosures`), each keyed by backend id. `update_entities()` is a
three-phase batching: update existing sprites, create missing ones,
remove orphaned ones. A frame therefore costs only as much as has really
changed.

**The background** is a 40 px dot grid, generated as a tiled `QBrush` from a
`QImage` — map aesthetics without external assets.

**Lighting.** The backend supplies `system.time_of_day` with four real
phases (`MORNING`, `NOON`, `EVENING`, `NIGHT`). Each phase has its own
RGBA tint in `constants.PHASE_LIGHTING`:

| Phase | Tint | Effect |
|---|---|---|
| `MORNING` | `(255, 190, 120, 28)` | warm, low-angle light |
| `NOON` | `(0, 0, 0, 0)` | full daylight, no tint |
| `EVENING` | `(255, 120, 60, 45)` | orange evening |
| `NIGHT` | `(10, 20, 60, 130)` | deep blue |

The transition runs as an 800 ms `QVariantAnimation` **over the QColor itself** —
Qt interpolates the alpha channel along with it, so that colour and strength
cross-fade at the same time. (`QPropertyAnimation` is ruled out: a
`QGraphicsRectItem` is not a `QObject` and has no animatable
properties.)

**`ZooGraphicsView`** adds mouse-wheel zoom (15 % per step, clamped to
0.3×–3.0×), panning by dragging (`ScrollHandDrag`, set in the constructor — effective as soon as the scene is larger than the visible viewport) and the
click on empty space (`map_clicked`), which clears the selection.

---

## 7. Panels of the right column

### ActionPanel
Four buttons — exactly the four free backend actions `feed_all`,
`feed_one`, `heal`, `clean`. The enabled state follows the snapshot:
food in stock, animal selected and alive, enclosure selected. Every
disabled button explains itself via a tooltip; a hint line names the
selected enclosure.

### ShopPanel
Two sections with the **real** backend prices (meat 8 €, plants
5 €, fish 6 €; lion 900 €, giraffe 700 €, penguin 400 €). When buying an animal
all three kwargs are sent (`species`, `name`, `enclosure_id`), otherwise
every animal ends up in the first enclosure and is called "New lion". Buy buttons
disable themselves as soon as the budget is insufficient — the rejection happens
in the UI before the backend has to report it. The stock display shows all four
resources including medicine (display only, no sale).

### StatsPanel
Table of the completed game days from `get_stats()`: Tag, Besucher,
Gewinn (green/red), Ø Tierwohl, Reputation, Todesfälle (day, visitors,
profit, average welfare, reputation, deaths); above it a
summary of the last day with income, expenses and average
satisfaction. Reputation and satisfaction appear **only here** — the
live snapshot does not have them. Without a persistence layer, a hint text is
shown instead of an empty table.

### EntityInfoPanel
Two mutually exclusive forms plus a placeholder:

* **Tier** (animal) — Name · Art, Alter, Status (lebt/verstorben), HP, Hunger,
  Wohlbefinden, Statuseffekte (name · species, age, status, HP, hunger, welfare, status effects).
* **Gehege** (enclosure) — Name, Biom, Belegung, Sauberkeit (name, biome, occupancy, cleanliness).

The hunger bar follows the backend semantics **0 = full, 100 =
starving**: the colour scale is inverted, a full bar is red.

### ChatlogWidget
Colour-coded feed, capped at 500 entries. The rendered HTML lines
are buffered so that the capping does not destroy the formatting.
Timestamps: 480 ticks = one day = 24 h, so three simulated minutes per
tick → `[T3 07:30]`. Since the backend issues its logger calls **without**
`tick_count`, the widget stamps with the tick of the frame in which
the message arrived — the feed is drained every frame anyway.

---

## 8. Header and footer bar

Instead of `QToolBar`/`QStatusBar`, two custom `QFrame`s with `StatusChip`s —
pills in a glass-morphism style whose value and accent colour are updated
every frame. Colour coding: budget green from 5 000 €, gold from 1 000 €,
otherwise red; animals gold as soon as one animal is dead, red when none is
alive any more; zoo status green/red with a changing lock symbol.

Every chip shows a value that the backend really supplies. The former
chips "⭐ Reputation" and "😊 Happiness" were removed: the corresponding
fields do not exist in the live snapshot and were permanently at 0.

---

## 9. Constants and theme

`core/constants.py` is the single source for colours, dimensions, prices,
enclosure geometry and day phases. Every value that mirrors a backend fact
names its source in a comment (`TICKS_PER_DAY` mirrors
`backend.core.engine.TICKS_PER_DAY`, `FOOD_PRICES` mirrors
`Inventory.FOOD_PRICES`, …) — mirrored rather than imported, so that the
layer separation holds.

Colour palette (GitHub-Dark-inspired, no pure black):

```python
C_BG_DEEP  = "#0d1117"   C_ACCENT   = "#3fb950"   C_TEXT     = "#e6edf3"
C_BG_PANEL = "#161b22"   C_ACCENT2  = "#2ea043"   C_TEXT_DIM = "#8b949e"
C_BG_CARD  = "#1c2333"   C_GOLD     = "#d2991d"   C_BORDER   = "#30363d"
                         C_RED      = "#f85149"
```

The QSS in `main._get_qss()` covers all widget types in use
(buttons, inputs, progress bars, tabs, tables, menus, tooltips).
Widgets largely carry no colour values of their own. There are exceptions where
the global cascade does not take hold reliably — `StatusChip`, the
progress bars in `EntityInfoPanel` and above all `styled_button()`
set complete inline QSS. The reason is a concrete bug — property
selectors such as `QPushButton[accent="true"]` only take effect after
`style().unpolish()/polish()`; without that, hover, pressed and
disabled states had no effect. Self-contained inline styles avoid the
problem reliably.

Besides the two factories, `styled_widgets` also contains `panel_layout()`:
the four lines with which every panel of the right column begins
(`WA_StyledBackground`, vertical layout, spacing, margin). Without that
attribute Qt ignores the background from the stylesheet — a detail that
would have to be right individually in four files and now lives in one place.

---

## 10. Data flow

```
┌──────────────────────── FRONTEND (PyQt6) ────────────────────────┐
│  QTimer(100 ms)                                                  │
│      ▼                                                           │
│  ZooMainWindow._tick()                                           │
│      ├─ controller.advance_tick() ──► engine.tick() × speed      │
│      ├─ controller.get_state()    ──► engine.get_game_state()    │
│      │      └─ enrichment: names (get_entity_info per animal)    │
│      │                    enclosures (get_entity_info per encl.) │
│      ├─ _update_sprites()  → ZooScene.update_entities()          │
│      │                       ZooScene.apply_lighting(phase)      │
│      ├─ _update_labels()   → 11 StatusChips                      │
│      │                       on day change: get_stats()          │
│      ├─ _update_panels()   → ActionPanel / ShopPanel             │
│      └─ get_chat_messages()→ ChatlogWidget                       │
│                                                                  │
│  User interaction                                                │
│      ├─ button  → panel signal → _dispatch(action, **kwargs)     │
│      │                            └─► engine.execute_action()    │
│      ├─ hover   → sprite callback → get_entity_info(animal_id)   │
│      │                               └─► EntityInfoPanel         │
│      └─ click   → EnclosureItem callback or map_clicked          │
└──────────────────────────────────────────────────────────────────┘
```

---

## 11. Design decisions in retrospect

| Decision | Alternative | Why this way |
|---|---|---|
| Modular file structure (25 classes, 25 files) | one large `main_window.py` | SRP, parallel work, assessment criterion "eine Aufgabe, eine Datei" (one task, one file) |
| Template method in `AnimalSpriteBase` | `if species == …` in the scene | new species without new logic; the dead behaviour exists exactly once |
| Callbacks instead of signals for sprites | `pyqtSignal` | `QGraphicsItem` is not a `QObject` in Qt6 |
| Pixmap rendering with a cache | `QGraphicsTextItem` | legible edges at 100 px width; only 2 render passes per species |
| Enrichment in the controller | every widget asks for itself | one backend contact surface, one cache, no repeated queries |
| The frontend drives `tick()` | `engine.start()` thread | no double ticking, deterministic frames, pause/speed controllable |
| Only show metrics where data exists | show a placeholder "0" | an interface that shows 0 although nobody knows the value is worse than one that shows the value where it comes into being |
| Pass the backend error text through | a generic message | "Fehler bei Aktion" (action failed) is not diagnosable; the `TypeError` in `buy_animal` only became visible this way |
| Custom header/footer bar | `QToolBar`/`QStatusBar` | native widgets break out of the dark theme |
| Alert banner as an overlay above the map | a row in the right column | the column already demanded 894 px of height — a banner that only appears occasionally must not permanently take up 36 px of it. As a child of the map it has pixel geometry and follows every resize via `ZooGraphicsView.resized` |
| Inventory list as its own tab | only clicking the sprite | the backend puts all animals on the same coordinate; hitting an individual sprite is a matter of luck, hitting a table row never is |
| Keyboard shortcuts from the same table as the help text | two separate lists | a key cannot exist undocumented, and a documented key cannot be missing |
| Dead code removed rather than kept | "might come in handy later" | an unused variant gets dragged along in every refactoring and thought through on every read; what is meant to come later is in `docs/IMPLEMENTATION_PLAN.md` §5 |
| Every tab in a **transparent, frameless** `QScrollArea` | panels without a scroll area | without it the tallest tab (Shop, 490 px) sets the minimum height of the entire window. A standard `QScrollArea` paints a white box over the `QTabWidget::pane` background; `NoFrame` + a transparent stylesheet + `setAutoFillBackground(False)` solve that — see CHANGELOG |
