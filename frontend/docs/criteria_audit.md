# ✅ Frontend — evidence for the assessment criteria

> **Module:** Frontend · **Module owner:** Erik
> **As of:** 2026-08-09
> Basis: assessment criteria from the assignment (`README.md` in the
> project root directory).

Every row names the place in the code where the criterion can be verified.

---

## Objektorientierte Programmierung (object-oriented programming) — 40 points

### Klassenstruktur & Modellierung — class structure & modelling (12)

| Evidence | Location |
|---|---|
| 25 classes in 25 files — "one job, one file" | `frontend/core/`, `frontend/ui/` |
| Helper classes deliberately extracted instead of dumped into catch-all files | `ui/status_chip.py` (out of `main_window.py`), `ui/particle.py` (out of `zoo_scene.py`), `ui/trend_chart.py` and `ui/numeric_table_item.py` (out of `stats_panel.py` and `animal_list_panel.py` respectively) |
| Clear layering Core ↔ UI ↔ Assets | `core/` = window/controller/constants, `ui/` = widgets, `assets/` = pure data |
| Only the entry point knows `backend`/`db` — no UI module and not even the controller imports them | only four local imports, all in the engine factory of `main.py` |
| **The rules are tested, not merely asserted** | `tests/test_layering.py` — checks layering, "one class per file", the module owner and docstrings via AST |

Verification command (fails as soon as a rule breaks):

```bash
QT_QPA_PLATFORM=offscreen python -m unittest frontend.tests.test_layering
```

### Vererbung & Polymorphie — inheritance & polymorphism (10)

| Evidence | Location |
|---|---|
| Four-level inheritance chain (three inheritance steps) | `EntitySprite` → `AnimalSpriteBase` → `AsciiAnimalSprite` → `AsciiLionSprite` |
| Abstract contracts | `ui/entity_sprite.py` (`update_position`, `entity_id`), `ui/animal_sprite_base.py` (`render_alive`, `render_dead`) |
| **Template method** `update_state()` — the dead-state logic exists exactly once, the appearance comes from the subclasses | `ui/animal_sprite_base.py` |
| Polymorphic call without a type check | `ZooScene._update_animals()` calls `update_state()` on all sprites in the same collection |
| Two completely different renderings behind one interface | `AnimalSprite` (ellipse + letter) vs. `AsciiAnimalSprite` (pixmap) |
| Hook override instead of a special-case `if` | `highlight_on()`/`highlight_off()` — no-op in the base class, overridden in `AnimalSprite` |
| **One base implementation for both Qt base classes** | `set_selected()` installs a `QGraphicsDropShadowEffect` — works for the ellipse *and* the pixmap without any subclass having to override anything |
| Custom painting instead of composed widgets | `ui/trend_chart.py` overrides `paintEvent()` — a chart made of *n* child widgets would have to be rebuilt on every change of day |
| Overriding a Qt comparison operator | `NumericTableItem.__lt__()` — the same table sorts by number instead of by text, without the table knowing about it |

### Kapselung & Datenintegrität — encapsulation & data integrity (8)

| Evidence | Location |
|---|---|
| Internal state consistently private, with a leading underscore | `_animals`, `_visitors`, `_enclosures`, `_selected_animal_id`, `_name_cache`, `_tick_budget`, `_entries` |
| Read access exclusively through properties, writing only through named methods. Five of the properties are read today only by the tests (`is_dead`, `is_selected`, `entry_count`, `TrendChart.day_count`, `frames_left`) — they belong to the contract of the class, not to the render path | `ZooScene.animals` (callback wiring), `AnimalSpriteBase.is_dead`/`is_selected`, `ChatlogWidget.entry_count` (header line), `StatsPanel.day_count` (tab label), `FrontendController.paused` (status line), `TrendChart.day_count`, `AlertBanner.frames_left` |
| No duplicated state | The window no longer keeps **any** pause copy of its own but reads `controller.paused` — two copies drift apart |
| No direct backend access from widgets — everything goes through the controller | `core/frontend_controller.py` as the only door |
| Faulty backend responses are caught instead of passed on | `FrontendController.execute_action()` catches `ValueError`/`TypeError` and returns a result dict |
| Value ranges are clamped | `EntityInfoPanel._grade()`, `_collect_enclosures()` (`max(0, …)`), `ChatlogWidget.format_timestamp()` |
| No name collides with a Qt base class | `TrendChart.metric_key` instead of `metric` — `QPaintDevice.metric()` is a Qt-internal method; a property of the same name breaks all painting (CHANGELOG Bug 44) |

### Modularität & Erweiterbarkeit — modularity & extensibility (10)

| Evidence | Location |
|---|---|
| **A new animal species = 5 class attributes**, no new logic | `ui/lion_sprite.py` (39 lines including docstrings) |
| A new action = one button + one signal line | `ui/action_panel.py` → `ZooMainWindow._connect_signals()` |
| A new keyboard shortcut = **one line** | `help_dialog.SHORTCUTS` is binding table and help text at once — `_register_shortcuts()` reads the same list of tuples that the dialog displays |
| Theme, prices and geometry configurable in one place | `core/constants.py` |
| Dependency injection instead of hard coupling | `ZooMainWindow(controller)`, `FrontendController(engine)` |
| The frontend also runs without a backend | `python -m frontend.main --no-engine` |
| Persistence can be switched on optionally | `main._create_persistence()` — if it is missing, only the statistics tab stays empty |
| A new metric in the chart = **one tuple entry** | `constants.TREND_METRICS` feeds the selection box and the drawing at the same time |
| The interface adapts to the screen | `QSplitter` + `QScrollArea` per tab; window scalable from 1000 × 640 instead of fixed at 1400 × 900 |
| **No dead code as an "extension point"** | Unused constants, button variants and QSS rules were removed rather than kept; whatever is intended for the future is listed with its effort and its blocker in [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md) §5 |

---

## Funktionalität & Korrektheit (functionality & correctness) — 15 points

### Implementierung der Kernfunktionen — implementation of the core features (8)

| Backend API | Frontend implementation |
|---|---|
| `tick()` | Render loop `QTimer(100 ms)` → `FrontendController.advance_tick()`, with pause and 4 speed levels |
| `get_game_state()` | Map sprites, 11 metric chips, all panels |
| `get_entity_info(id)` | Animal info on hover, enclosure info on click, names and **the complete roster** in the "Tiere" (animals) tab |
| `get_chat_messages()` | `ChatlogWidget` (colour-coded, filterable, with a derived timestamp) **and** `AlertBanner` for `WARNING`/`ERROR` |
| `execute_action("feed_all"/"feed_one"/"heal"/"clean")` | four buttons in the `ActionPanel`, enabled depending on context |
| `execute_action("buy_food")` | Shop section with live price preview and budget gating |
| `execute_action("buy_animal")` | Shop section with name and target enclosure (see the known limitation below) |
| `get_stats(days_back)` | `StatsPanel` — table of the completed days **plus** `TrendChart` as the profit trend |

**Completeness:** All six engine methods the interface needs are actually
used. Not used are `start()`, `pause()` and `set_speed()` — they drive the
internal backend thread, which would tick a second time alongside the
Qt render loop (rationale: `IMPLEMENTATION_PLAN`
§2.7).

### Simulationslogik & Realismus — simulation logic & realism (7)

| Evidence | Location |
|---|---|
| Hunger semantics adopted correctly (0 = full, 100 = starving) | `EntityInfoPanel.show_entity()` inverts the colour scale |
| Dead animals turn grey or red and disable actions | `AnimalSpriteBase.update_state()`, `ActionPanel._update_heal()` |
| Real backend prices instead of made-up values | `constants.FOOD_PRICES` = 8/5/6 €, `ANIMAL_PRICES` = 900/700/400 € |
| Four real phases of the day with a soft colour transition | `constants.PHASE_LIGHTING`, `ZooScene.apply_lighting()` |
| Enclosures show real occupancy and cleanliness | `FrontendController._collect_enclosures()` via `free_slots`/`cleanliness` |
| **No placeholder metrics** — reputation and satisfaction appear only where the backend supplies them (daily statistics) | `ui/stats_panel.py` |
| Warnings are recognisable without colour vision | `AnimalListPanel._grade()` returns a colour **and** the marker `!`/`!!`; the filter logic reads the same marker |
| The cost of the display is kept in view | The roster costs one backend call per animal and is therefore throttled (`ROSTER_REFRESH_FRAMES`), while a changed roster is shown immediately |

---

## Testbeschreibung & Teststrategie (test description & test strategy) — 15 points

| Evidence | Location |
|---|---|
| 209 functions, **482 test descriptions** — every function ≥ 2 | every `Tests:` block in the code |
| Every class additionally carries test cases | class docstrings |
| Strategy, fixtures, PyQt preconditions | `docs/test_plan.md` |
| Edge cases in tabular form (39 entries) | `docs/test_plan.md` §5 |
| Manual acceptance test (16 steps) | `docs/test_plan.md` §7 |
| **Beyond the requirement: 229 executed tests** without an additional dependency | `frontend/tests/` — stdlib `unittest` |
| The project's three critical bugs are pinned down as regression tests — through real `QTest` mouse and keyboard events, not through direct method calls | `tests/test_main_window.py::TestSelection`, `::TestDispatch` |

Run:

```bash
QT_QPA_PLATFORM=offscreen python -m unittest discover -s frontend/tests -t .
# Ran 229 tests ... OK
```

---

## Dokumentation (documentation) — 15 points

| Evidence | Location |
|---|---|
| Every class and every function with a complete docstring (description, `Args`, `Returns`, `Raises` where applicable, `Tests`) | all files |
| Module docstring with the purpose **and the rationale** for the design decision | e.g. `ui/ascii_animal_sprite.py` (why a pixmap instead of a text item), `ui/entity_sprite.py` (why no `abc.ABC`) |
| Module owner noted in **every** file (deduction-relevant) | `Module owner: Erik (frontend).` in all 43 Python files, tests included |
| Inline comments in the places that are not obvious | `constants.py` (backend source per value), `frontend_controller.py` (error propagation), `main_window.py` (why the alert banner is not a layout element) |
| Architecture, change, planning and outlook documents | `FRONTEND_ARCHITECTURE.md`, `docs/IMPLEMENTATION_PLAN.md`, `docs/CHANGELOG.md`, `docs/IMPLEMENTATION_PLAN.md` §5 |
| **Statically checked: `pylint frontend/` → 10.00/10.** Each of the 25 justified exceptions is listed individually and can be verified; the CI job additionally runs a strict check with PyQt6 installed | `docs/test_plan.md` §8, `.pylintrc`, `.github/workflows/frontend-tests.yml` |

Verification command (`frontend/tests/` excluded — test code needs no
test descriptions):

```bash
python - <<'PY'
import ast, pathlib
bad = [f"{p}:{n.name}" for p in pathlib.Path("frontend").rglob("*.py")
       if "tests" not in p.parts
       for n in ast.walk(ast.parse(p.read_text()))
       if isinstance(n, ast.FunctionDef)
       and "Tests:" not in (ast.get_docstring(n) or "")]
print(bad or "every function documented")
PY
```

---

## Design-Visualisierung (Mermaid) — 10 points

| Evidence | Location |
|---|---|
| Class diagram of **all 25 classes** with every kind of relationship — 350 of 350 attributes and methods in the code are shown, counted via AST | `docs/frontend_class_diagram.md` §1 |
| **Four kinds of diagram**, not just one: class, sequence, state and component diagram | `docs/frontend_class_diagram.md` §1, §3–§7, §8, §9 |
| State diagram of the selection — the distinction between preview and binding, on which three of the bugs that actually occurred hinged | `docs/frontend_class_diagram.md` §8 |
| Component diagram of the layers with the single seam to the backend (six methods) | `docs/frontend_class_diagram.md` §9 |
| Inheritance, composition, aggregation, association and dependency distinguished | ibid., §7 legend |
| Additional diagram of the sprite hierarchy | ibid. §2 |
| **Five sequence diagrams** (bonus): render loop, feeding action, hover, end of day, selection via the animal list | ibid. §3–§7 |

---

## Reflexion & KI-Einsatz (reflection & use of AI) — 5 points

| Evidence | Location |
|---|---|
| Tools used, tasks, verification | `docs/KI_REFLEXION.md` §1 |
| Human in the loop: what was checked and what was corrected | ibid. §2 |
| Concrete cases in which the AI output was wrong, plus three error patterns | ibid. §3 |
| ⚠️ **Open:** §4 "What I learned" — four sections that Erik writes in his own words. The bullet points above them are pointers from the project history, not a substitute | ibid. §4 |

---

## Submission requirements (deduction-relevant)

| Requirement | Status |
|---|---|
| `frontend/requirements.txt` present | ✅ `PyQt6>=6.5.0` — the tests need nothing beyond that |
| Module owner visible in the README **and** in the code | ✅ `frontend/README.md` + docstring of every file |
| Automated test run | ✅ `.github/workflows/frontend-tests.yml` set up: tests on Python 3.12 and 3.14 plus a strict pylint run, triggered on push and PR touching `frontend/**`. Both steps green locally; not yet run on GitHub |
| Runs on small screens as well | ✅ window scalable from 1000 × 640; previously fixed at 1400 × 900 |
| Operable without a mouse and without colour vision | ✅ nine keyboard shortcuts, named controls, markers instead of colour coding alone |
| Instructions for testing the application | ✅ `frontend/README.md` §Tests (executable), `docs/test_plan.md` §7 (manual) |
| Visible separation of frontend / backend / interface / database | ✅ separate top-level packages; interface = `core/frontend_controller.py` against `backend/docs/api.md`; secured by a test |
| One class per file | ✅ 25/25, secured by a test |
| Runs on Python 3.14 | ✅ tested in the devcontainer (`python:3.14`) |
| `venv/` not in the submission | ⚠️ remember when zipping — exclude `.venv/` and `__pycache__/` |

---

## Known limitations (not fixable on the frontend side)

Full list with effort estimates: [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md) §5 §2.
The two most visible ones:

### Animals do not stand in their enclosure

`Zoo.add_animal()` places every animal at the fixed coordinate (300, 200) and
`animals_on_map` names no `enclosure_id`. The drawn position therefore
contradicts the occupancy display, which comes from `free_slots` and is
correct. Freshly started animals sit exactly on top of one another and are
barely clickable individually.

**Answer on the frontend side:** the "Tiere" (animals) tab
(`ui/animal_list_panel.py`). It gives every animal an unambiguous row and
leads to the same selection as a click on the sprite — the limitation
remains, its consequence does not.

### Buying an animal fails

`execute_action("buy_animal", …)` currently fails **in the backend**:

```
TypeError: Animal.__init__() missing 2 required positional arguments: 'x' and 'y'
```

The cause is `backend/core/action_handler.py::_action_buy_animal`, which calls
`create_animal(species, animal_id="tmp", name="tmp")` without coordinates.
The shop section deliberately stays — it matches the interface documented in
`backend/docs/api.md` — and shows the backend's original error message
instead of swallowing it. As soon as `x`/`y` are added there, buying works
without any frontend change.
