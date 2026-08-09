# 🗺️ Frontend — Planning, Decisions and Outlook

> **Module:** Frontend · **Module owner:** Erik
> **Status as of:** 2026-08-09

The planning part of the frontend. It answers three questions:

1. **What was decided and why** (§0–§2) — in particular where Erik's UI
   design and the backend plan contradicted each other. Every resolution
   names the original assumption, the rejection and the reason.
2. **What the frontend talks to the backend with** (§3–§4).
3. **What was deliberately left open** (§5) — with effort and blocker.

The sources that converge here: `FRONTEND_ARCHITECTURE.md` (UI design),
`planning/db_planning/backend_core_plan.md` (backend commitment) and the real
code in `backend/`. Where they contradicted each other, the decision below applies.

---

## Assessment criteria

The official criteria are in the root [`README.md`](../../README.md)
from "## requirements" onwards. Which piece of evidence serves which criterion
is documented in [`criteria_audit.md`](criteria_audit.md) — there with location
and verification command. This document answers the other question: **what was
decided, and why.**

---

## 0. Architectural decision: modular file structure

`FRONTEND_ARCHITECTURE.md` describes all components, but suggests a
single `main_window.py`. For maintainability, parallel work and the
assessment criterion "one task, one file", the following applies instead:

```
frontend/
├── main.py                      entry point: QApplication, QSS, engine factory
├── core/
│   ├── constants.py             all global constants
│   ├── frontend_controller.py   bridge to the SimulationEngine + enrichment
│   └── main_window.py           ZooMainWindow: layout, routing, render loop
├── ui/                          one class per file
│   ├── entity_sprite.py         EntitySprite       (abstract)
│   ├── animal_sprite_base.py    AnimalSpriteBase   (abstract, template method)
│   ├── ascii_animal_sprite.py   AsciiAnimalSprite  (pixmap base)
│   ├── lion_sprite.py           AsciiLionSprite
│   ├── giraffe_sprite.py        AsciiGiraffeSprite
│   ├── penguin_sprite.py        AsciiPenguinSprite
│   ├── animal_sprite.py         AnimalSprite       (circle fallback)
│   ├── visitor_sprite.py        VisitorSprite
│   ├── enclosure_item.py        EnclosureItem
│   ├── particle.py              AmbientParticle
│   ├── zoo_scene.py             ZooScene
│   ├── zoo_view.py              ZooGraphicsView
│   ├── action_panel.py          ActionPanel
│   ├── animal_list_panel.py     AnimalListPanel
│   ├── shop_panel.py            ShopPanel
│   ├── stats_panel.py           StatsPanel
│   ├── trend_chart.py           TrendChart         (own paintEvent)
│   ├── numeric_table_item.py    NumericTableItem   (numeric sorting)
│   ├── entity_info_panel.py     EntityInfoPanel
│   ├── chat_view.py             ChatlogWidget
│   ├── status_chip.py           StatusChip
│   ├── alert_banner.py          AlertBanner
│   ├── help_dialog.py           HelpDialog
│   └── styled_widgets.py        styled_button(), styled_label()
├── assets/                      ascii_lion.py, ascii_giraffe.py, ascii_penguin.py
├── tests/                       runnable unit tests (stdlib unittest)
└── docs/                        diagrams, test plan, criteria evidence, roadmap, changelog
```

**Current state: 25 classes in 25 files.** `StatusChip`, `AmbientParticle` and
`TrendChart` were moved out of `main_window.py`, `zoo_scene.py` and
`stats_panel.py` respectively, because otherwise two classes would have sat in
one file. `tests/test_layering.py` pins the rule down.

---

## 1. Scope

The **core prototype** is implemented and complete with respect to today's
backend interface: all six engine methods the interface needs are used, and
every number displayed comes from an engine response.

| Area | Scope |
|---|---|
| Map | sprites, visitors, enclosures, four day phases, zoom & pan |
| Controls | four god-mode actions, shop, pause, four speeds, nine keyboard shortcuts |
| Display | 11 metric chips, info panel, sortable and filterable roster list, message feed, alert banner, daily statistics with switchable trend chart |
| Window | resizable from 1000 × 640 upwards, splitter between map and panels, named controls for screen readers |

What was **deliberately left open** — with reasoning, effort estimate and the
respective missing backend detail — is in §5.
The boundary in short: no simulation state of its own in the frontend, no
database access, no display without a data source (§2.9).

---

## 2. Conflict resolutions (binding decisions)

### 2.1 Food types: 3 in the shop, 4 in the display ✅
The backend knows four `FoodType` values (`MEAT`, `PLANTS`, `FISH`,
`MEDICINE`) and returns all four in the inventory. Only the first three are
sold: `heal` works in god mode in phase 1 and consumes no medicine, so a
purchase would have no effect. Medicine therefore appears in the stock
display, but not in the purchase dropdown.

### 2.2 Day/night: four real phases ✅ **(corrected 2026-08-09)**
The original decision ("simple two-state toggle via
`zoo_open`") rested on an outdated assumption. The backend does in fact deliver
`system.time_of_day` with four values (`MORNING`, `NOON`,
`EVENING`, `NIGHT`, computed in `SimulationEngine._phase_of`). What is
implemented is therefore the full four-phase lighting from `PHASE_LIGHTING`, with
an 800 ms cross-fade over the `QColor` itself. `zoo_open` now only serves as a
fallback for unknown phase values.

### 2.3 Age stage: replaced by real life status ✅ **(corrected)**
Originally the info panel was to show "Alter · Stadium" (age · stage) with a
hard-wired "Erwachsen" (adult). But a hard-wired value is exactly the kind of
phantom display that is to be avoided. The panel now shows two
real fields: **Alter** (age) from `age_days` and **Status** from `is_dead`
("lebt" / "verstorben" — alive / deceased). A stage will come back as soon as
the backend supplies one.

### 2.4 Healing: god mode without a medicine gate ✅
`execute_action("heal", animal_id)` calls the vet logic directly, without
staff and without cost. The button is enabled as soon as a **living** animal is
selected. No medicine check.

### 2.5 Enclosures: geometry local, state from the backend ✅ **(corrected)**
The snapshot contains no list of enclosures, and the point-in-rectangle test
originally envisaged would have been wrong: animals all start at (300,
200) and roam freely across the map, they do not stay inside their rectangle.
Instead, `get_entity_info("e_01")` supplies `name`, `biome`,
`cleanliness` and `free_slots` per enclosure. The controller combines these
live values with the map geometry from `ENCLOSURE_DEFS` into
`enclosures_on_map` and computes `occupied = capacity − free_slots`. The
capacities in `ENCLOSURE_DEFS` match those created by
`main._create_demo_engine()`.

### 2.6 Deferred features ✅ **(revised)**
UpgradePanel, DecoSprite, drag & drop, staff panel, save/load and
`styled_card()` remain unbuilt — the backend offers no interface for them.
Full list with effort and blocker: §5.

The `EventBanner` originally prepared was **removed**: it was 98
lines of widget that stayed permanently invisible, because running events
cannot be queried. `AlertBanner` took its place — the same idea,
but with a real data source: `WARNING` and `ERROR` entries from
`get_chat_messages()`. A prepared widget without data is dead code,
not extensibility.

### 2.6a Visibility rather than completeness ✅ **(new)**
Three displays go beyond the plain snapshot rendering without inventing a
new data source:

* **Roster list** (`AnimalListPanel`) — the same data as the
  info panel, but for all animals at once. Necessary because the backend
  puts all animals on the same coordinate, which makes individual sprites
  barely clickable (§ Known limitations).
* **Alert banner** (`AlertBanner`) — at 5× speed, warnings scroll past
  faster than you can read them.
* **Profit trend** (`TrendChart`) — the same `get_stats()` rows as the
  table, but as a trend instead of a snapshot.

All three read existing backend fields exclusively.

### 2.7 Who drives the simulation? ✅ **(new)**
The engine brings its own thread (`start()`), in addition to
`pause()` and `set_speed()`. The frontend uses none of these three methods:
if the thread ran alongside the Qt loop, ticking would happen twice, and
`set_speed()` only affects the sleep duration of that thread anyway.
Instead, `FrontendController.advance_tick()` calls `tick()` itself — with
a fractional budget for the speed steps 1×/2×/5×/0.5× and
a pause gate. That keeps simulation and rendering in step.

### 2.8 Prices: the backend is authoritative ✅ **(new)**
The original frontend constants (meat 50 €, plants 30 €, fish
40 €; lion 8 000 €, giraffe 5 000 €, penguin 3 000 €) were invented out of
thin air and deviated from the real values by a factor of 6 to 10.
Authoritative are:

| Resource | Price | Backend source |
|---|---:|---|
| Meat | 8 € | `Inventory.FOOD_PRICES[MEAT]` |
| Plants | 5 € | `Inventory.FOOD_PRICES[PLANTS]` |
| Fish | 6 € | `Inventory.FOOD_PRICES[FISH]` |
| Medicine | 25 € | `Inventory.FOOD_PRICES[MEDICINE]` |
| Lion | 900 € | `Lion.BUY_PRICE` |
| Giraffe | 700 € | `Giraffe.BUY_PRICE` |
| Penguin | 400 € | `Penguin.BUY_PRICE` |

### 2.9 No placeholder metrics ✅ **(new)**
The header and footer bars show only fields that really occur in the
snapshot. The chips "⭐ Reputation" and "😊 Happiness" were removed:
`finances` contains neither `reputation` nor `zoo_happiness`, both sat
permanently at 0. The backend supplies both values per completed day via
`get_stats()` — that is where they now appear, in the statistics tab.

---

## 3. Data contract with the backend

Verified against `backend/core/zoo.py`, `animal.py`, `finances.py`,
`inventory.py` and `message_logger.py` (as of 2026-08-09).

### 3.1 `engine.get_game_state()`

```python
{
    "system": {
        "tick_count": int,     # 480 ticks = 1 game day
        "time_of_day": str,    # "MORNING" | "NOON" | "EVENING" | "NIGHT"
        "zoo_open": bool,      # False exactly during NIGHT
    },
    "finances": {
        "money": float,
        "revenue": float,       # income today
        "expenses": float,      # expenditure today
        "ticket_price": float,
        # NO reputation, NO zoo_happiness
    },
    "inventory": {"MEAT": int, "PLANTS": int, "FISH": int, "MEDICINE": int},
    "animals_on_map": [
        {"id": str, "species": str, "x": int, "y": int, "is_dead": bool}
        # NO name, NO enclosure_id
    ],
    "visitors_on_map": [{"id": str, "x": int, "y": int}],
}
```

From that, the controller adds:

```python
    "animals_on_map": [{..., "name": str}],          # via get_entity_info
    "enclosures_on_map": [                            # via get_entity_info
        {"id", "name", "biome", "x", "y", "w", "h",
         "capacity", "cleanliness", "free_slots", "occupied"}
    ],
```

### 3.2 `engine.get_entity_info(entity_id)`

For an **animal**:

```python
{"id": str, "name": str, "species": str, "age_days": int,
 "hp": float, "hunger": float,   # 0 = full, 100 = starving
 "welfare": float, "is_dead": bool, "status_effects": list[str]}
```

For an **enclosure**:

```python
{"id": str, "name": str, "biome": str,
 "cleanliness": float, "free_slots": int}
```

Unknown id → `{}`.

### 3.3 `engine.get_chat_messages()`

```python
[{"tick_count": int, "type": str, "text": str,
  "entity_id": str | None, "details": dict | None}]
```

`type` ∈ `INFO | WARNING | ERROR | SUCCESS`. **Careful:** the backend calls
its logger without `tick_count`, so all entries arrive with `0`. The
frontend therefore stamps them with the tick of the receiving frame.

### 3.4 `engine.execute_action(action, **kwargs)`

```python
{"success": bool, "message": str, "chat_entries": list[dict]}
```

| Action | Kwargs |
|---|---|
| `feed_all` | — |
| `feed_one` | `animal_id` |
| `heal` | `animal_id` |
| `clean` | `enclosure_id` |
| `buy_food` | `type` (**not** `food_type`), `amount` |
| `buy_animal` | `species`, `name`, `enclosure_id` |

Unknown actions raise `ValueError`; the controller catches it.

### 3.5 `engine.get_stats(days_back)`

```python
[{"day_id": int, "total_visitors": int, "revenue": float,
  "expenses": float, "profit_loss": float, "avg_animal_welfare": float,
  "avg_happiness": float, "reputation_end_of_day": int,
  "animals_died": int}]
```

Empty as long as no `DbGateway` is attached to the engine.

---

## 4. Test descriptions

The test cases originally collected here have moved to the code: every
function carries its `Tests:` block in the docstring. Strategy, fixtures,
PyQt preconditions and edge cases are in
[`test_plan.md`](test_plan.md).

**Current state:** 209 functions, 482 test descriptions, no function without a
docstring.

**Executed on top of that:** 229 runnable tests under
`frontend/tests/`, based on the standard library — no additional
dependency:

```bash
QT_QPA_PLATFORM=offscreen python -m unittest discover -s frontend/tests -t .
```

---

---

## 5. Outlook — what was deliberately left open

The opposite direction to §2: **what was deliberately not built, why, and what
it would concretely take.** The prototype runs and is complete with respect to
today's backend interface
([`backend/docs/api.md`](../../backend/docs/api.md)) — it is not a finished
game, and that is a decision, not a gap.

Every entry names **effort** (S = hours, M = one day, L = several days)
and **blocker**. Everything under "frontend only" can be implemented without a
single line in `backend/` or `db/`.

### 5.1 Frontend only — feasible immediately

#### Done (as of 2026-08-09)

| # | Item | Implemented as |
|---|---|---|
| ✅ F1 | Animal list sortable & filterable | The column header sorts numerically via `ui/numeric_table_item.py`; the "Braucht Aufmerksamkeit" (needs attention) filter hides inconspicuous animals |
| ✅ F2 | Second chart series | Metric selector above the chart: Gewinn, Besucher, Ø Wohlbefinden, Reputation (profit, visitors, avg. welfare, reputation) — all from the same `get_stats()` row |
| ✅ F4 | Release the window size | `QSplitter` between map and panels, every tab in a transparent `QScrollArea`; window resizable from 1000 × 640 upwards |
| ✅ — | Accessibility | `accessibleName`/`accessibleDescription` on all chips, buttons and tables, defined tab order, warning values additionally as `!`/`!!` instead of colour alone |
| ✅ — | Error dialog instead of stderr | If the engine fails, a `QMessageBox` explains the reason instead of showing an empty window |
| ✅ — | Roster throttling | The roster list is refreshed every five frames instead of ten times per second; a changed animal population still comes through immediately |
| ✅ — | CI workflow | `.github/workflows/frontend-tests.yml` is set up: 229 tests on Python 3.12 and 3.14 plus pylint, triggered on every push and PR touching `frontend/**`. Both steps pass locally; on GitHub the workflow has not run yet |

#### Open

| # | Item | What it gains | Effort |
|---|---|---|---|
| F3 | **CSV export of the daily statistics** | One button, `QFileDialog.getSaveFileName`, `csv.DictWriter` over the list from `get_stats()`. Makes the simulation analysable without touching the DB. | S |
| F5 | **Remember settings** (`QSettings`) | Speed, active tab, chat filter, window size and splitter position survive a restart. Purely client-side. | S |
| F6 | **Destructive actions (`danger` variant)** | `styled_widgets` has three variants today. As soon as an action takes something away (sell an animal, demolish an enclosure), it needs a red one: a `_DANGER_CSS` template analogous to `_ACCENT_CSS` and a branch in `styled_button()`. Deliberately not there yet — a variant without a caller is dead code. | S |
| F7 | **Decoration layer** | The z-order deliberately leaves room between enclosures (1) and animals (4). Hook in trees, paths and benches as their own `QGraphicsItem` class — purely visual, no backend needed. | M |
| F8 | **Add more species** | A new species is a 39-line sprite subclass with five class attributes plus four entries in `constants.py`. Only worthwhile once `backend.core.animal.known_species()` knows it — otherwise the shop offers something the backend rejects. | S |
| F9 | **Fit the map to the window** | The scene stays 800 × 600; in a wide window it sits centred with a margin. An "Einpassen" (fit) button (`fitInView`) or an automatic zoom on resize would be one line — the question is whether it may override the manual zoom. | S |

---

### 5.2 Needs a backend change first (Benjamin)

These points are **not** frontend omissions. The interface would follow
within hours in each case; it simply lacks the data item.

| # | Item | Missing backend detail | Frontend effort afterwards |
|---|---|---|---|
| B1 | **Draw animals in the correct enclosure** | `Zoo.add_animal()` puts every animal on the fixed coordinate (300, 200), and `animals_on_map` names no `enclosure_id`. The map therefore contradicts the (correct) occupancy display. Needed: `enclosure_id` in the snapshot **or** a start position inside the enclosure. | S |
| B2 | **Buy an animal** | `execute_action("buy_animal", …)` currently raises `TypeError: Animal.__init__() missing 2 required positional arguments: 'x' and 'y'` in `backend/core/action_handler.py::_action_buy_animal`. The shop section deliberately stays in place and shows the original error message. | 0 — works without a change |
| B3 | **Show the running event** | `EventScheduler` generates events, but the engine offers no query ("which event is running, and for how long?"). The `AlertBanner` therefore shows `WARNING`/`ERROR` from the message stream instead of real event bands. Needed: `get_active_event()` or a field in `system`. | S |
| B4 | **Weather & environment** | `zoo.environment` exists in the backend, but does not appear in `to_game_state()`. With a `system.weather` field, a weather chip and matching lighting would be an hour's work. | S |
| B5 | **Actually sell medicine** | The `MEDICINE` stock is displayed, but not sold: `heal` is god mode and consumes nothing. As soon as healing costs medicine, the display becomes a fourth shop row. | S |
| B6 | **Make staff visible** | `Zoo.update_staff()` runs every round, but staff appear in no snapshot field. With `staff_on_map` analogous to `visitors_on_map` it is one sprite class and one chip. | M |
| B7 | **Death counter** | The backend removes an animal in the same tick in which it dies — `is_dead=True` practically never reaches the interface. The animal chip therefore shows the population instead of deaths. With a grace period of a few ticks, the death rendering (grey sprite, red frame) that has long existed in the code would become visible. | 0 — already implemented |
| B8 | **Reset the simulation** | There is no way to restart the zoo without terminating the process. Needed: `engine.reset()` or a second zoo instance. Only then is a "Neues Spiel" (new game) action, including scene clean-up, worthwhile. | S |

---

### 5.3 Checked automatically

`frontend/tests/` contains **229 runnable tests** using the stdlib
`unittest` — without an additional dependency:

```bash
python -m unittest discover -s frontend/tests -t .
```

Covered are constant invariants, the architecture rules (layering,
one class per file, module owner, docstrings), the controller, the
window including real mouse and keyboard events, and most
widgets. **Not** automated, still only described:

* **Pixel-exact appearance.** Screenshot comparisons test Qt, not our
  code — what is checked instead is that the correct colour constant ends up
  in the stylesheet.
* **Animation curves.** The lighting fade (800 ms) and the score popup (2000 ms)
  are checked for start and target value, not for the curve in between.
* **The wiring in `main.py`.** `launch_frontend()` starts an
  event loop; what is tested instead is the engine factory via its
  return value.
* **`assets/ascii_*.py`.** Pure data modules without logic.

Since 9 August 2026 the suite is additionally **automatable**:
`.github/workflows/frontend-tests.yml` starts it on every push and every
pull request that touches `frontend/**` — on Python 3.12 and 3.14, with
`QT_QPA_PLATFORM=offscreen`. After that the workflow checks that the application
starts and ticks without an engine, and runs pylint strictly over `frontend/`.
Both steps pass locally; on GitHub the workflow has not run
yet.

---

### 5.4 Deliberately *not* planned

So that it is clear where the boundary lies:

* **No simulation state of its own in the frontend.** Everything displayed
  comes from an engine response. A metric that the interface computes itself
  would be a second truth — see §2.9.
* **No access to the database.** The frontend talks exclusively to
  `SimulationEngine`; `backend`/`db` are imported exclusively in `main.py`,
  and a test pins that down
  (`tests/test_layering.py`).
* **No drag & drop of animals.** Without `enclosure_id` (B1) there would be no
  target to drop onto.
* **No multi-language support.** The interface is German throughout, the
  backend messages are English. A translation layer would honestly only make
  sense if both sides joined in.
