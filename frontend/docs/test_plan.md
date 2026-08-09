# 🧪 Frontend — Test Plan, Test Strategy and Static Analysis

> **Module:** Frontend · **Module owner:** Erik
> **Assessment criterion:** Testbeschreibung & Teststrategie (test description & test strategy, 15 points)
> **As of:** 2026-08-09
>
> §1–§7 tests · §8 pylint

The assignment requires that **at least two tests are described, but not
implemented, for every function**. This document describes the strategy, the
structure and the edge cases; the individual test descriptions deliberately
sit **right next to the code** — in every docstring as a `Tests:` block, so
that description and implementation never drift
apart.

Beyond that, part of it has **voluntarily been implemented as well**: 229
runnable tests in `frontend/tests/`, see §3. And because a test only says
whether the code *does* the right thing, §8 holds the second half of
quality assurance: what the linter says about its readability.

---

## 1. Coverage at a glance

| File | Functions | Described tests |
|---|---:|---:|
| `core/frontend_controller.py` | 16 | 40 |
| `core/main_window.py` | 42 | 102 |
| `main.py` | 4 | 10 |
| `ui/action_panel.py` | 8 | 18 |
| `ui/alert_banner.py` | 5 | 11 |
| `ui/animal_list_panel.py` | 13 | 34 |
| `ui/animal_sprite.py` | 9 | 18 |
| `ui/animal_sprite_base.py` | 18 | 38 |
| `ui/ascii_animal_sprite.py` | 7 | 14 |
| `ui/chat_view.py` | 8 | 20 |
| `ui/enclosure_item.py` | 6 | 13 |
| `ui/entity_info_panel.py` | 7 | 16 |
| `ui/entity_sprite.py` | 2 | 4 |
| `ui/help_dialog.py` | 5 | 10 |
| `ui/numeric_table_item.py` | 4 | 8 |
| `ui/particle.py` | 3 | 6 |
| `ui/shop_panel.py` | 9 | 19 |
| `ui/stats_panel.py` | 6 | 14 |
| `ui/status_chip.py` | 4 | 9 |
| `ui/styled_widgets.py` | 3 | 8 |
| `ui/trend_chart.py` | 8 | 21 |
| `ui/visitor_sprite.py` | 4 | 8 |
| `ui/zoo_scene.py` | 13 | 28 |
| `ui/zoo_view.py` | 5 | 13 |
| **Total** | **209** | **482** |

In addition, **every class** carries a `Tests:` block in its class
docstring. The numbers can be recomputed — `frontend/tests/` is left out of
this, because test code needs no test descriptions:

```bash
python - <<'PY'
import ast, pathlib
f = t = 0
for p in pathlib.Path("frontend").rglob("*.py"):
    if "tests" in p.parts:
        continue
    for n in ast.walk(ast.parse(p.read_text())):
        if isinstance(n, ast.FunctionDef):
            f += 1
            t += (ast.get_docstring(n) or "").count("- test")
print(f"{f} Funktionen, {t} Testbeschreibungen")
PY
```

---

## 2. Why the descriptions live in the docstring

A separate test directory would separate the description from the code it
describes; at the next refactoring the two drift apart. In the docstring the
opposite holds: whoever changes the method inevitably reads its test cases too.
The format is the same everywhere:

```python
def update_state(self, x: float, y: float, is_dead: bool) -> None:
    """Move the sprite and switch its rendering when life state changes.

    Args:
        x: New centre X coordinate in map pixels.
        y: New centre Y coordinate in map pixels.
        is_dead: The backend's ``is_dead`` flag for this animal.

    Returns:
        None.

    Tests:
        - test_position_always_updated: Call with (10, 20, False);
          verify the sprite centre moved to (10, 20).
        - test_render_dead_called_once: Call twice with is_dead=True;
          verify render_dead ran only on the first transition.
    """
```

---

## 3. Implemented tests

To run — with no extra dependency, `unittest` is part of the standard
library:

```bash
QT_QPA_PLATFORM=offscreen python -m unittest discover -s frontend/tests -t .
# Ran 229 tests ... OK
```

The same files run unchanged under `pytest frontend/tests` if pytest is
installed: both runners understand `unittest.TestCase`.

```
frontend/tests/
├── __init__.py
├── support.py                   QApplication singleton, FakeEngine, snapshot construction kit
├── test_constants.py            23 tests: colour formats, enclosure geometry, species tables,
│                                day phases, thresholds
├── test_layering.py             architecture: no backend/db imports outside main.py,
│                                one class per file, module owner, docstrings
├── test_frontend_controller.py  25 tests: enrichment, name cache including expiry,
│                                speed budget, chat buffer, error paths
├── test_widgets.py              panels of the right-hand column: chat log, AlertBanner,
│                                AnimalListPanel, NumericTableItem, TrendChart,
│                                ActionPanel, ShopPanel, EntityInfoPanel,
│                                StatsPanel, styled_widgets, HelpDialog
├── test_map.py                  everything on the map: sprites, EnclosureItem,
│                                ZooScene, ZooGraphicsView, AmbientParticle
└── test_main_window.py          clock, render loop, dispatch payload, selection via
                                 real mouse clicks, keyboard shortcuts, alarm path,
                                 window size, roster throttling, accessibility,
                                 engine factory
```

Why not one file per module, as originally sketched? Because one widget test
needs the same `QApplication` and the same helper functions as the next.
Six thematic files stay readable; twenty files with three tests each would be
administration without benefit.

The split between `test_widgets.py` and `test_map.py` was added on 9 August
2026, when the widget file grew past 1000 lines. It is not merely a question
of size: the two halves break for different reasons. A map test fails when
**geometry** changes (a sprite sits on the wrong point, a zoom overshoots its
limit); a panel test fails when a **value** is formatted or enabled wrongly.

**`frontend/tests/` is exempt from the docstring count.** A test describes
its case in the method documentation and in the method name —
a `Tests:` block *above* a test would be one level too many.

---

## 4. Preconditions for PyQt6 tests

**1. Exactly one `QApplication` per test run.** Qt widgets cannot be
instantiated without an application object; two of them lead to a crash.
Implemented in `tests/support.py`:

```python
from PyQt6.QtWidgets import QApplication

_KEEP_ALIVE: list[QApplication] = []   # <- the reference is what matters

def app() -> QApplication:
    existing = QApplication.instance()
    if not isinstance(existing, QApplication):
        existing = QApplication([])
    if existing not in _KEEP_ALIVE:
        _KEEP_ALIVE.append(existing)
    return existing
```

> **A pitfall that hit us:** Without the module-level reference the
> QApplication is collected by the garbage collector immediately after being
> returned, and on the next widget Qt reports "Must construct a
> QApplication before a QWidget". A local variable is not enough.

`QT_QPA_PLATFORM=offscreen` is not set by this module but by
`tests/__init__.py`. Python runs the package `__init__` before every test
module — that is the only place which sets the variable reliably **before**
the first PyQt6 import, without an import having to sit in the middle of
`support.py`.

**2. No real backend.** The controller is wired up via dependency injection;
tests pass a fake engine instead of a real
`SimulationEngine` (in full in `tests/support.py`):

```python
class FakeEngine:
    def tick(self): self.calls.append("tick")
    def get_game_state(self): ...      # deep copy of the snapshot
    def get_entity_info(self, entity_id): ...
    def get_chat_messages(self): ...   # empties the buffer like the original
    def get_stats(self, days_back=30): ...
    def execute_action(self, action, **kw):
        self.calls.append((action, kw))
        return {"success": True, "message": f"ok:{action}", "chat_entries": []}
```

**2a. The snapshot must be a copy.** The controller writes names
*into* the state dict. If the fake engine handed out the same object twice,
the second test would be checking the first test's enrichment.

**2b. Leftover windows swallow keyboard shortcuts.** `QShortcut` applies in
the window context and only fires in the **active** window. If windows from
earlier tests stay open, all keyboard tests are silently lost —
which is why `test_main_window._window()` closes all previous ones first.

**2c. A widget inside a layout cannot be resized directly.**
`view.resize(...)` is overwritten at the next layout pass. Anyone wanting to
check that overlays follow along changes the **window** size and then calls
`processEvents()`.

**2d. No attribute may shadow a Qt method.** `QWidget` inherits from
`QPaintDevice` and thereby `metric()`, `paintEngine()`, `devType()`. A
property of the same name leads to `TypeError: 'str' object is not callable`
**from inside the drawing code** — with no traceback, with `abort()`. A
render test into a `QPixmap` exposes this, a pure attribute test does not.

**3. No checks on randomness.** Visitor colours (`random.choice`) and the
particle drift speed are random. Tests check invariants
("the colour comes from `VISITOR_COLORS`"), not concrete values.

**4. Do not wait for animations.** The lighting fade (800 ms) and the
score popup (2000 ms) run via `QVariantAnimation` /
`QPropertyAnimation`. Tests check the start and target value, not the
progression — otherwise they hang on the event loop.

**5. `isVisibleTo(parent)` instead of `isVisible()`.** As long as the window
is not actually shown, `isVisible()` returns `False` for child widgets.
For form switching in the `EntityInfoPanel`, `isVisibleTo` is the
right predicate.

---

## 5. Edge cases that must be covered

| Edge case | Expected behaviour | Where checked |
|---|---|---|
| **No engine** (`FrontendController(None)`) | `get_state()` → `{}`, `get_stats()` → `[]`, `execute_action()` → `success: False`; the window starts anyway | `test_frontend_controller.py`, `test_main_window.py` |
| **Empty snapshot** (`{}`) | `_tick()` aborts before panels are updated — no `KeyError` | `test_main_window.py` |
| **Unknown entity id** | backend returns `{}` → info panel shows the placeholder | `test_widgets.py` |
| **Animal dies while selected** | sprite turns grey/red, the heal and feed buttons disable themselves | `test_widgets.py`, `test_map.py` |
| **Animal disappears from the snapshot** | sprite is removed from the scene, the name cache entry expires | `test_map.py`, `test_frontend_controller.py` |
| **Empty inventory** | "Alle Tiere füttern" (feed all animals) disabled, tooltip gives the reason | `test_widgets.py` |
| **Budget too small** | both purchase buttons disabled before the backend has to refuse | `test_widgets.py` |
| **Backend raises `TypeError`/`ValueError`** | controller catches it and returns a readable error message instead of a crash | `test_frontend_controller.py` |
| **500+ chat messages** | only the last 500 remain, formatting is preserved | `test_widgets.py` |
| **Message without `tick_count`** | the timestamp of the receiving frame is used | `test_widgets.py` |
| **Persistence missing** | `get_stats()` → `[]`, statistics tab shows a note instead of an empty table | `test_widgets.py` |
| **Maximum zoom level** | zoom clamps at 0.3× and 3.0× | `test_map.py` |
| **Unknown species** | `_make_sprite` falls back to `AnimalSprite` (circle), no crash | `test_map.py` |
| **Unknown day phase** | `apply_lighting` uses the `zoo_open` fallback | `test_map.py` |
| **Action with a selection parameter** | the signal `action_triggered(str, dict)` must arrive unpacked at the backend — `heal` without `animal_id` is a silent failure | `test_main_window.py` |
| **Selected animal dies** | `_reconcile_selection` discards the selection, info panel falls back to the placeholder | `test_main_window.py` |
| **Stock matches no animal** | only FISH in stock, only a lion alive → "Alle füttern" (feed all) stays disabled | `test_widgets.py` |
| **Zoom at the limit** | 50 steps inwards end at exactly 3.0 — not at 3.06 | `test_map.py` |
| **Selection via real mouse events** | `QTest.mouseClick` on a sprite, then `QTest.mouseMove` away from it → the selection must persist. Setting `_selected_animal_id` programmatically does **not** exercise this path | `test_main_window.py` |
| **Stacked sprites** | click on an animal standing inside an enclosure → the animal is selected, not the enclosure | `test_main_window.py` |
| **Layout minimum** | the window's `minimumSizeHint()` stays below the configured minimum of 1000 × 640 — measured 922 × 531; without the scroll areas it would be 894 px in height and the shop tab would be cut off | `test_main_window.py` |
| **Enclosure over capacity** | red, solid 3 px border | `test_map.py` |
| **Smallest screen** | `minimumSizeHint()` must not exceed 1000 × 640, otherwise the window does not fit on a laptop screen | `test_main_window.py` |
| **Enlarging the window** | the alarm banner is a pixel-positioned child of the map and must grow with it | `test_main_window.py` |
| **Numeric sorting** | sorted by HP, 9 comes before 100 — as text it would be the other way round | `test_widgets.py` |
| **Click after sorting** | row 0 is a different animal afterwards; the id travels with the row, not with the index | `test_widgets.py` |
| **Marker instead of colour** | every critical value additionally carries `!!`, every notable one `!` | `test_widgets.py` |
| **Filter "Braucht Aufmerksamkeit"** (needs attention) | healthy animals are hidden, not deleted | `test_widgets.py` |
| **Throttling of the roster list** | 20 frames must not mean 20 rebuilds — but a new animal must mean one immediately | `test_main_window.py` |
| **Metric switch in the chart** | uses the cached day rows without asking the backend again | `test_widgets.py` |
| **Engine not loadable** | the factory returns the reason instead of only writing it to stderr | `test_main_window.py` |
| **Name collision with Qt** | a property named `metric` would shadow `QPaintDevice.metric()` and abort every draw | `test_widgets.py` |
| **Keyboard shortcut in the input field** | typing "Sheffe Rex" into the name field must neither pause, nor change the speed, nor switch the tab | `test_main_window.py` |
| **Shortcut without a selection** | `H` with no animal selected sends **nothing** to the backend and explains in the status bar what is missing | `test_main_window.py` |
| **Warning in the message stream** | `WARNING`/`ERROR` additionally appear in the alarm banner, `INFO` does not | `test_main_window.py`, `test_widgets.py` |
| **Alarm banner and layout** | a shown banner must not raise the layout minimum — it sits above the map, not in the column | `test_main_window.py` |
| **Chat filter** | filtered entries disappear from the view but stay buffered; "Alle" (all) shows them again | `test_widgets.py` |
| **Empty animal list** | note text instead of an empty grid | `test_widgets.py` |
| **Chart without data** | `paintEvent` draws the placeholder without throwing | `test_widgets.py` |

---

## 6. What is deliberately *not* tested

* **Pixel-exact appearance.** QSS gradients and shadows are not compared by
  screenshot — that would be brittle and would check Qt, not our code.
  What is checked instead is that the right colour constant ends up in the
  stylesheet.
* **Animation progressions.** The lighting fade (800 ms) and the score popup
  (2000 ms) are checked via their start and target value. Waiting for the end
  would mean hanging on the event loop.
* **The backend simulation itself.** Hunger curves, visitor numbers and
  animal behaviour belong to the backend test plan (`backend/docs/test_plan.md`).
  The frontend only tests that it displays the reported state correctly.
* **The database.** The frontend talks to the engine and to nothing else.
* **`launch_frontend()`.** The function starts an event loop and only returns
  on shutdown. What is checked instead is the engine factory, via
  its return value.
* **`assets/ascii_*.py`.** Pure data modules without logic.

---

## 7. Manual acceptance test (smoke test)

In addition to the described unit tests — to be carried out in this order
after every larger change:

1. `python -m frontend.main` starts without a traceback, window 1400×900.
2. The four animals are visible and moving, visitor dots appear.
3. Hovering over an animal fills the info panel with name, age, HP, hunger,
   well-being.
4. **Clicking** an animal makes it glow green; the selection persists
   while the mouse travels to the button. "Tier heilen" (heal animal) is enabled.
5. Tab "Tiere" (animals): all animals are in the list. Clicking a row selects
   the same animal — the marker on the map jumps along.
6. Clicking an enclosure shows biome, occupancy and cleanliness; "Gehege
   reinigen" (clean enclosure) becomes enabled and sets cleanliness to 100 %.
7. Shop: buying food lowers the budget and raises the stock; "Alle Tiere
   füttern" becomes enabled as a result.
8. Speed to 5× — the day chip and the phase chip visibly cycle through
   Morgen → Mittag → Abend → Nacht (morning, noon, evening, night), the map darkens towards night.
9. After the first day change the statistics tab fills with one row **and**
   the chart gets a bar.
10. A warning ("… is starving") additionally appears as a golden
    banner above the map and disappears by itself after about six
    seconds.
11. Keyboard: `Leertaste` (space bar) pauses, `S` changes the speed, `F1`
    opens the help, `Esc` clears the selection.
12. Type an animal name in the shop — while doing so **none** of the
    single-letter shortcuts may trigger.
13. Pause freezes the simulation, clicking again resumes it.
14. Shrink the window to 1000 × 640: all four tabs stay reachable,
    the map gets scroll bars, nothing is cut off. The splitter
    between map and panels can be moved.
15. Tab "Tiere": clicking "Hunger" sorts; the filter "Braucht
    Aufmerksamkeit" hides healthy animals.
16. Tab "Statistik" (statistics): switching the metric redraws the same days.

---

## 8. Static analysis — pylint over `frontend/`

> pylint 4.0.6 / astroid 4.0.4 · as of 2026-08-09

```bash
pylint frontend/
# Your code has been rated at 10.00/10
```

Tests say whether the code does the right thing; the linter says whether it
does it understandably. Both are quality assurance, which is why they stand
here in the same document. What follows is the cross-check on the score: **every**
place where a message was silenced instead of fixed is listed below with its
justification. A 10.00 whose origin cannot be looked up is
no statement about the code.

### 8.1 Starting point

The first run reported **293 findings** and 8.12/10. They fell into
three groups:

| Group | Count | What was behind it |
|---|---|---|
| Environment, not code | 47 | pylint could not find PyQt6 (see §8.2) |
| Genuine findings | 44 | methods too long, copied code, forbidden names, missing docstrings, attributes outside `__init__` |
| Deliberate test practice | 202 | access to private fields in the unit tests (see §4) |

Everything in the second group was fixed **by restructuring**, not by
switching checks off. What the restructurings were is in §8.3.

---

### 8.2 The change to `.pylintrc`

`.pylintrc` sits in the root directory because pylint looks for its
configuration in the working directory — so it applies to all three modules,
and all three modules have written into it. **Exactly one line of it comes
from the frontend:**

```ini
ignored-modules=PyQt6
```

Everything else in the file was contributed by the backend module. After
merging `develop` it reads:

```ini
[MESSAGES CONTROL]
disable = too-few-public-methods, protected-access, unused-argument,
          import-outside-toplevel, invalid-name, no-name-in-module

[DESIGN]
max-args = 12 · max-positional-arguments = 12
max-attributes = 25 · max-locals = 20
```

Two of those are unavoidable with PyQt6 in any case: `no-name-in-module`
(the names live in a C extension) and `invalid-name` (Qt's `camelCase`
methods must keep their name when overridden — `paintEvent`,
`hoverEnterEvent`, `mousePressEvent`). The rest are the backend's decisions,
not the frontend's.

> **Consequence for §8.4, measured rather than assumed.** The relaxed limits
> make **11 of the 25 waivers in the frontend redundant** — everything that
> only silenced `protected-access`, an attribute count below 25 or an
> argument count below 12. They are deliberately kept: each one carries the
> *reason* the class has that shape, not just the suppression, and they keep
> the frontend clean if the shared configuration is ever tightened again.
> Reproduce it with:
>
> ```bash
> pylint --enable=useless-suppression frontend/
> ```
>
> Still load-bearing under the merged configuration: `too-many-lines` and
> the 40 attributes of `ZooMainWindow` (above the raised limit of 25), plus
> the four `no-member` lines of the sprite mixin.

**The merge also broke the file once.** Both branches had added an
`ignored-modules` entry, so the merged `[MAIN]` section contained the key
twice — `configparser` refuses that, pylint reported
`F0011: error while parsing the configuration` and fell back to its
defaults. The rating dropped from 10.00 to 9.06, and every `E0401` and
`invalid-name` came back, although nothing about the code had changed.
Worth remembering: a linter config is shared state between modules, and a
merge conflict in it fails loudly in one place and silently everywhere else.

PyQt6 is a C extension and lives in the project environment
(`frontend/requirements.txt`). If pylint is installed as a **global tool** —
in the devcontainer, for instance, under `/usr/local/py-utils/`, with its
own interpreter and `-E` in the shebang line — then it does not see that
environment and reports in every file:

```
frontend/ui/zoo_view.py:36:0: E0401: Unable to import 'PyQt6.QtWidgets'
```

That is 43 messages about a missing import, not about the code, plus
four follow-on errors (`E1101 no-member`, because the Qt base classes stay
unknown). The entry hides exactly this environment difference.

**The exception covers nothing up.** With PyQt6 installed it can be lifted
again, and the result stays the same — measured locally:

```bash
python -m pylint --ignored-modules= --fail-under=10 frontend/
# Your code has been rated at 10.00/10
```

So **both** variants are clean — the convenient one and the strict one. The
code does not depend on the exception; it is only there so that the linter
also runs through outside the project environment.

This is exactly the command the CI job `lint` in
[`.github/workflows/frontend-tests.yml`](../../.github/workflows/frontend-tests.yml)
runs on every push. The workflow was created on 9 August 2026 and has not
yet run on GitHub; the 10.00/10 above comes from the local run
of the same command, not from a green tick.

Of the three old entries, `invalid-name` remains the only one that could
theoretically hide something. Cross-check with the check switched on
(`pylint --disable=all --enable=C0103 frontend/`): **10 messages**, of which
8 are Qt overrides that must not be renamed (`paintEvent`,
`wheelEvent`, `resizeEvent`, 3× `mousePressEvent`, `hoverEnterEvent`,
`hoverLeaveEvent`), one the type alias `AnimalSpriteT` and one
`setUp` from `unittest`. Not a single one concerns domain logic.

---

### 8.3 What was restructured

No switching off, but code changes:

| Message | Where | What was done |
|---|---|---|
| `R0801` copied code | `action_panel`, `stats_panel` | The four identical lines every panel begins with are now `styled_widgets.panel_layout()`. `shop_panel` and `animal_list_panel` use it too. |
| `R0915` too many statements | `ShopPanel.__init__` | Split into `_build_food_section()` and `_build_animal_section()` — the two sections the shop has anyway. |
| `R0914` / `R0915` | `ZooMainWindow._update_labels` | Split into `_update_clock_chips`, `_update_finance_chips` and `_update_population_chips`. The eleven chips fall into exactly these three groups. |
| `R0914` | `TrendChart._paint_bars` | The scale calculation is now `_scale()`. |
| `W0201` attribute outside `__init__` | `main_window` (24×), `animal_sprite_base` (16×) | Both classes now declare their state at class level. In the window this has become a complete widget inventory list; in the sprite, the explanation of why `init_animal()` and not `__init__` sets the values (the sip constructor of the Qt base must run first). |
| `C0104` forbidden name | `main_window` (3×), `entity_info_panel` | `bar` → `menu_bar` / `top` / `bottom` / `progress`. |
| `C0413` / `W0603` | `tests/support.py` | `QT_QPA_PLATFORM` is now set in `tests/__init__.py` — the only place that reliably runs before the first PyQt6 import. That puts the import back at the top, and the `global` has given way to a module-level list that keeps the `QApplication` alive. |
| `C0302` / `R0904` | `tests/test_widgets.py` | Split into `test_widgets.py` (panels) and `test_map.py` (map), the roster tests into presentation and operation. |
| `C0415` import not at the top | tests (9×) | All nine moved to the module head. |
| `C0115` / `C0116` missing docstrings | `test_frontend_controller`, `test_main_window` (6×) | Added. |
| `R0903` too few public methods | `ui/particle.py` | `AmbientParticle` has been given a `drift_speed` property. It was due anyway: the docstring promised a test on the value, which only existed via `_drift_speed`. |
| `R0917` too many positional arguments | `AnimalSprite`, `EnclosureItem` | All arguments are keyword-only. Costs nothing (every caller named them already) and prevents swapped `w`/`h`. |

Plus **five new tests** (229 instead of 224): two for `panel_layout()`, three
for `AmbientParticle`.

---

### 8.4 What was silenced — in full

Every place carries the reason as a comment directly above it. Here they are
listed again for counting.

#### 8.4.1 `protected-access` in the tests — 3 modules, 202 findings

`# pylint: disable=protected-access` at the head of `test_widgets.py`,
`test_map.py` and `test_main_window.py`.

These tests are deliberately white-box. A Qt window has no public
interface beyond "show it and let it tick"; its behaviour sits in
slots, timers and child widgets. That is exactly where the three bugs this
project actually had were sitting (payload lost between signal and slot,
selection only while the pointer rests on the sprite, click falling through the
item stack). The alternative to `window._lbl_status.text()` would be a
pixel comparison — and that checks Qt, not our code
(§4 of this document).

Since the `develop` merge these three lines are redundant: the shared
`.pylintrc` disables `protected-access` project-wide (§8.2). They stay,
because they say *why* these tests reach into private state — a global
switch does not.

#### 8.4.2 `no-member` in `ui/animal_sprite_base.py` — 4 lines

`AnimalSpriteBase` is a mixin class: the Qt base is only mixed in by the
concrete subclass
(`class AnimalSprite(AnimalSpriteBase, QGraphicsEllipseItem)`). `EntitySprite`,
the only statically visible base, is pure Python. `setGraphicsEffect`
and `super().hoverEnterEvent` are guaranteed to exist at runtime, but not
statically — the same four lines have always carried a
`# type: ignore` for the same reason.

#### 8.4.3 `too-many-instance-attributes` — 7 classes

| Class | Fields | Why |
|---|---|---|
| `ZooMainWindow` | 40 | The only place where all the controls come together |
| `EntityInfoPanel` | 14 | Keeps both forms (animal, enclosure) plus the placeholder ready at the same time and switches between them instead of rebuilding |
| `ShopPanel` | 12 | One control each for the two purchase sections plus budget and enclosure list |
| `EnclosureItem` | 12 | Id, name, biome, capacity, occupancy, cleanliness, callback, four geometry values, label |
| `AnimalSpriteBase` | 8 | The three callbacks replace the three `pyqtSignal`s that a `QGraphicsItem` must not have in Qt6 |
| `ActionPanel` | 8 | Four buttons, hint line, shortcut mapping, two selection ids |
| `ZooScene` | 8 | Three sprite registers, particle list, four parts of the lighting |

The default value of 7 is meant for business logic. A Qt widget class
holds one attribute per child widget it still has to address later; that
can only be lowered by putting the widgets into a dict and losing all type checking.

Deliberately **not** raised in `.pylintrc`: a global `max-attributes=15`
would apply to `backend/` and `db/` as well and might swallow genuine
findings there. The exception therefore sits on every single class — visible
to whoever reads it.

#### 8.4.4 `too-many-arguments` — 2 constructors

`AnimalSprite.__init__` (6 instead of 5) and `EnclosureItem.__init__` (9 instead of
5). An enclosure is simply described by eight values. Merging them into a
dict would cost the type annotations; instead they are all
keyword-only.

#### 8.4.5 `too-many-lines` — `core/main_window.py`

1551 lines, of which **555 are code**: the rest is 681 lines of docstrings, 68
lines of comments and 247 blank lines. The submission rule "at least two
test descriptions per function" makes every file roughly twice as long, and
pylint counts documentation like any other line.

Extracting header and footer bar widgets was considered and rejected: it
moves around 310 lines, but leaves the file at ~1232 lines still above
the limit, and costs two classes that do nothing but pass the same widgets
on.

#### 8.4.6 `too-few-public-methods` — 4 widget classes + 2 test classes

For `ShopPanel`, `ActionPanel`, `AnimalListPanel` and `ZooMainWindow` this is
a **follow-on error from §2**: for this check pylint also counts the
inherited methods. If the Qt base cannot be resolved, a widget
with hundreds of inherited methods looks like a class with a single one.

This can be demonstrated:

```bash
# strict, with PyQt6 installed
python -m pylint --ignored-modules= --enable=useless-suppression frontend/
frontend/ui/shop_panel.py:59:0: I0021: Useless suppression of 'too-few-public-methods'
frontend/ui/animal_list_panel.py:85:0: I0021: Useless suppression of ...
frontend/ui/action_panel.py:47:0: I0021: Useless suppression of ...
frontend/core/main_window.py:142:0: I0021: Useless suppression of ...
```

Exactly these four — and **only** these four — were superfluous as soon as
pylint could see Qt, back when the frontend was the only module writing to
`.pylintrc`.

Since the `develop` merge that count is higher: the backend's configuration
disables `too-few-public-methods` project-wide and raises `max-attributes` to
25, which makes **11 of the 25 waivers redundant** (§8.2). The measurement
is in §8.5; the waivers stay for the reason given there.

Two further places are genuinely tiny classes in the tests, not
environment artefacts:

* `_RosterFixture` in `test_widgets.py` — a test fixture whose only
  public method is `setUp`. It needs no more than that.
* `class Mute` in `test_frontend_controller.py:249` — an engine stub with
  exactly one method (`get_game_state`) that checks what happens when the
  backend knows no actions. A second method would have destroyed the test case.

#### 8.4.7 `broad-exception-caught` — 3 places (already there before)

`frontend_controller.py::execute_action`, `main.py::_create_persistence` and
`main.py::_create_demo_engine`. All three are boundaries to the backend: what
comes up there is not predictable (today the shop triggers a
`TypeError` from `Animal.__init__`, see [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md) §5.2 B2).
A narrow `except` would let these errors through and close the
window; instead the original message is displayed. These three
exceptions do not stem from this round, but belong in this list for
completeness.

#### 8.4.8 `import-outside-toplevel` — `main.py`, 2 blocks

The imports of `backend` and `db` sit **inside** the functions
`_create_persistence()` and `_create_demo_engine()` on purpose. The frontend is
meant to start without a backend as well (`--no-engine`), and
[`tests/test_layering.py`](../tests/test_layering.py) records via AST that
`main.py` is the only place that knows these packages at all. An import
at module level would bind every start hard to them — which is exactly what the
layering is meant to prevent.

---

### 8.5 Adding it up

| | |
|---|---|
| `pylint: disable` lines in total | **25** in 15 files |
| of those from this round | 22 (three `broad-exception-caught` already existed, §8.4.7) |
| of those Qt peculiarities: attribute count, mixin, arguments, file length | 12 |
| of those deliberate test practice | 3 modules (§8.4.1) + 2 test classes |
| **redundant since the `develop` merge, kept on purpose** | **11** |
| still load-bearing under the merged configuration | 14 |
| messages that instead disappeared through restructuring | 44 |

Both numbers are measurable, not estimated:

```bash
grep -rn "# pylint: disable" frontend/ --include="*.py" | wc -l   # 25
pylint --enable=useless-suppression frontend/ | grep -c I0021      # 11
```

Why keep something the linter no longer needs? Because a waiver states two
things, and only one of them is the suppression. `ZooScene` holds eight
fields *because* it manages three sprite registries, a particle list and the
four parts of the lighting — that sentence is worth reading whether or not
`max-attributes` currently happens to be 25. And if the shared configuration
is tightened again, the frontend stays at 10.00 without anyone having to
rediscover the reasons.

Each of the 25 lines is explained in §8.4, and each carries its
justification as a comment directly above it in the code.
