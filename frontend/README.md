# vivizoo — Frontend (`frontend/`)

Graphical user interface of the zoo simulation, built with **PyQt6**. The
frontend is the topmost layer of the three-layer architecture:

```
┌─────────────┐    API calls    ┌─────────────┐   domain→models   ┌─────────────┐
│  Frontend   │ ──────────────▶ │   Backend   │ ───────────────▶ │  Database   │
│   (PyQt6)   │ ◀────────────── │             │ ◀─────────────── │    (db/)    │
└─────────────┘   Snapshots     └─────────────┘   models          └─────────────┘
```

It renders the zoo state reported by the backend and translates user input
into god-mode actions. It writes no SQL and contains no simulation logic.

**Module owner: Erik (Frontend).**
The note additionally appears in the docstring of **every** Python file of
this module.

---

## Installation & start

Inside the devcontainer, from the project root directory:

```bash
pip install -r frontend/requirements.txt
```

On Linux, PyQt6 needs two system libraries that are not pre-installed in
the container:

```bash
sudo apt-get install -y libgl1 libegl1
```

Start:

```bash
python -m frontend.main              # with a prepared demo zoo
python -m frontend.main --no-engine  # without backend (empty UI, for testing the interface)
```

Check headless (e.g. in CI or over SSH, without a display):

```bash
QT_QPA_PLATFORM=offscreen python -c "
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
from frontend.main import _get_qss, _create_demo_engine
from frontend.core.frontend_controller import FrontendController
from frontend.core.main_window import ZooMainWindow
app = QApplication([]); app.setStyleSheet(_get_qss())
engine, reason = _create_demo_engine()         # tuple: (engine, failure reason)
win = ZooMainWindow(FrontendController(engine)); win.show()
QTimer.singleShot(2000, app.quit); app.exec()
animals = len(win._controller.get_state().get('animals_on_map') or [])
print(f'Frontend runs. Animals in snapshot: {animals}   Backend: {reason or \"ok\"}')
"
```

The demo zoo creates three enclosures (Savanne, Eiswelt, Aquarium) and four
animals (Simba, Melman, Pingu, Kowalski) and attaches — if SQLAlchemy is
available — an in-memory database so that the statistics tab gets data.

> **Tip:** The simulation runs at 10 frames per second. One game day lasts
> 480 ticks, so roughly 48 seconds. With the speed button (🏃) set to 5×,
> days pass in about 10 seconds — handy for watching day/night and the
> daily statistics.

---

## Operation

| Element | Effect |
|---|---|
| **Mouse over an animal** | Preview in the info panel: Name, Art, Alter, HP, Hunger, Wohlbefinden, Statuseffekte (name, species, age, HP, hunger, well-being, status effects) |
| **Click on an animal** | Selects it persistently — "Ausgewähltes füttern" and "Tier heilen" become enabled and stay enabled while the mouse travels to the button |
| **Click on an enclosure** | The info panel shows biome, occupancy and cleanliness; "Gehege reinigen" becomes enabled |
| **Click on empty space** | Clear the selection |
| **Mouse wheel** | Zoom (0.3× to 3.0×) |
| **Drag with the mouse button held** | Pan the map (only visible when zoomed in) |
| **⏸ / ▶** | Pause and resume the simulation |
| **🏃** | Speed 1× → 2× → 5× → 0.5× |
| **Tab "Aktionen"** | Alle füttern, Ausgewähltes füttern, Heilen, Gehege reinigen (feed all, feed the selected one, heal, clean the enclosure) |
| **Tab "Tiere"** | Inventory list with HP, hunger and well-being; clicking a row selects the animal, clicking a column header sorts, filter "Braucht Aufmerksamkeit" (needs attention) |
| **Tab "Shop"** | Futter kaufen, Tier kaufen (buy food, buy an animal — with name and target enclosure) |
| **Tab "Statistik"** | Trend chart (Gewinn, Besucher, Ø Wohlbefinden or Reputation) + a table row per completed game day |
| **Window edge / splitter** | Window freely resizable from 1000 × 640; the splitter between map and panels can be dragged |

Disabled buttons explain themselves via tooltip ("Kein Futter im Lager",
"Das Tier ist verstorben", …).

### Keyboard shortcuts

The simulation keeps running while you operate it — that is why there is a
key for every frequent action. **F1** shows the same list in the program.

| Key | Effect |
|---|---|
| `Space` | Anhalten / fortsetzen (pause / resume) |
| `S` | Nächste Geschwindigkeitsstufe (next speed level) |
| `F` | Alle Tiere füttern (feed all animals) |
| `E` | Ausgewähltes Tier füttern (feed the selected animal) |
| `H` | Ausgewähltes Tier heilen (heal the selected animal) |
| `R` | Ausgewähltes Gehege reinigen (clean the selected enclosure) |
| `Esc` | Auswahl aufheben (clear the selection) |
| `1` – `4` | Tab wechseln (switch tab) |
| `F1` | Hilfe: Tastenkürzel & Legende (help: shortcuts & legend) |

While typing into an input field (the animal name in the shop, for
instance) the single letters do not fire — Qt gives the input field
priority.

### Warnings

`WARNING` and `ERROR` messages additionally appear as a coloured banner
above the map and stay there for 60 frames. The reason: at 5× speed the
message feed scrolls faster than anyone can read. The banner counts in
frames, not in seconds — so it lives exactly as long as the situation it
describes.

---

## Structure

```
frontend/
├── main.py                       Entry point: QApplication, QSS theme, engine factory
├── requirements.txt
├── README.md                     ← this file
├── FRONTEND_ARCHITECTURE.md      Design document (structure, theme, rendering)
│
├── core/                         Infrastructure (not a single widget)
│   ├── constants.py              Colours, dimensions, prices, enclosure geometry, day phases
│   ├── frontend_controller.py    Sole bridge to the SimulationEngine + data enrichment
│   └── main_window.py            ZooMainWindow: layout, signal routing, render loop
│
├── ui/                           Widgets & graphics items — exactly one class per file
│   ├── entity_sprite.py          EntitySprite        (abstract contract of the scene)
│   ├── animal_sprite_base.py     AnimalSpriteBase    (template method, hover, death, selection)
│   ├── ascii_animal_sprite.py    AsciiAnimalSprite   (pixmap rendering + cache)
│   ├── lion_sprite.py            AsciiLionSprite     ┐
│   ├── giraffe_sprite.py         AsciiGiraffeSprite  ├ 5 class attributes each
│   ├── penguin_sprite.py         AsciiPenguinSprite  ┘
│   ├── animal_sprite.py          AnimalSprite        (circle fallback for new species)
│   ├── visitor_sprite.py         VisitorSprite
│   ├── enclosure_item.py         EnclosureItem
│   ├── particle.py               AmbientParticle
│   ├── zoo_scene.py              ZooScene            (sprite batching, lighting)
│   ├── zoo_view.py               ZooGraphicsView     (zoom, pan, click)
│   ├── action_panel.py           ActionPanel
│   ├── animal_list_panel.py      AnimalListPanel     (inventory list, sortable and filterable)
│   ├── shop_panel.py             ShopPanel
│   ├── stats_panel.py            StatsPanel          (metric selection + table)
│   ├── trend_chart.py            TrendChart          (own paintEvent, four metrics)
│   ├── numeric_table_item.py     NumericTableItem    (sorts by number, not by text)
│   ├── entity_info_panel.py      EntityInfoPanel
│   ├── chat_view.py              ChatlogWidget       (filter, counter, clear)
│   ├── status_chip.py            StatusChip
│   ├── alert_banner.py           AlertBanner         (warnings above the map)
│   ├── help_dialog.py            HelpDialog          (keyboard shortcuts + legend)
│   └── styled_widgets.py         styled_button(), styled_label(), panel_layout()
│
├── assets/                       Pure data, no logic
│   ├── ascii_lion.py
│   ├── ascii_giraffe.py
│   └── ascii_penguin.py
│
├── tests/                        Runnable unit tests (stdlib unittest)
│   ├── support.py                QApplication singleton, FakeEngine, snapshot construction kit
│   ├── test_constants.py         Invariants of the configuration
│   ├── test_layering.py          Architecture rules (layering, one class per file)
│   ├── test_frontend_controller.py
│   ├── test_widgets.py           Chat, banner, animal list, chart, panels
│   ├── test_map.py               Sprites, enclosures, scene, zoom, particles
│   └── test_main_window.py       Render loop, dispatch, selection, keyboard shortcuts
│
└── docs/
    ├── frontend_class_diagram.md Class, sequence, state and
    │                             component diagram (9 × Mermaid)
    ├── test_plan.md              Test strategy, edge cases, static analysis
    ├── criteria_audit.md         Evidence for every assessment criterion
    ├── IMPLEMENTATION_PLAN.md    Planning: decisions and outlook
    ├── CHANGELOG.md              Chronology of all changes and bugs
    └── KI_REFLEXION.md           Reflection on the use of AI
```

---

## Interface to the backend

The frontend talks to **exactly one** object: a `SimulationEngine`
(`backend.core.engine`). The contract is written down in `backend/docs/api.md`.
All six methods the interface needs are used:

| Call | What it is for in the UI |
|---|---|
| `tick()` | Render loop (`QTimer`, 100 ms); pause and speed are frontend gates on top of it |
| `get_game_state()` | Map, metric chips, all panels |
| `get_entity_info(id)` | Animal info on hover, enclosure info on click, resolution of the animal names |
| `get_chat_messages()` | Message feed |
| `execute_action(…)` | `feed_all`, `feed_one`, `heal`, `clean`, `buy_food`, `buy_animal` |
| `get_stats(days_back)` | Statistics tab |

Not used are `start()`, `pause()` and `set_speed()` — they drive the
backend's internal background thread, which would tick in addition to the
Qt loop and run the simulation twice.

### What the controller adds

The backend snapshot is deliberately lean. `FrontendController.get_state()`
enriches it so that the widgets do not have to invent anything:

* **Animal names** — `animals_on_map` contains no name; the controller
  resolves it once per animal via `get_entity_info()` and remembers it.
* **`enclosures_on_map`** — the backend supplies no enclosure list. The
  controller combines the map geometry from `constants.ENCLOSURE_DEFS`
  with the live values `cleanliness` and `free_slots`, which the backend
  knows per enclosure id.
* **`get_animal_details()`** — the inventory list needs more per animal
  than the map excerpt provides. The controller joins the map entry
  (position, alive status) with the hover payload (HP, hunger,
  well-being) into a row sorted by name.

### Deliberately not displayed

So that the interface does not invent any numbers:

* **Reputation and average satisfaction** are not in the live snapshot.
  They appear exclusively in the statistics tab, where the backend really
  does supply them per completed day.
* **Ticket price** is displayed but not changed — there is no action for
  it in the API.
* **Medicine** is part of the stock, but cannot be bought: `heal`
  consumes none at this stage, so buying it would be a feature without
  effect.

### Known backend limitations

**Animals do not stand in their enclosure.** `Zoo.add_animal()` places every
animal on the fixed start coordinate (300, 200) and takes no position;
`animals_on_map` also contains no `enclosure_id`. All animals therefore
start in the "Savanne 1" rectangle and roam the map freely from there —
the drawn position contradicts the occupancy display, which comes from
`free_slots` and is correct. The frontend cannot resolve this: it lacks
the information about which animal belongs to which enclosure.

Because freshly started animals therefore sit **exactly on top of each
other**, clicking a single one on the map is a matter of luck. The tab
"Tiere" is the answer to that: it gives every animal a unique, always
hittable row and leads to the same selection as a click on the sprite.

**Buying an animal fails.** `execute_action("buy_animal", …)` fails in the
backend
(`TypeError: Animal.__init__() missing 2 required positional arguments:
'x' and 'y'` in `action_handler._action_buy_animal`). The shop section
stays in place because it matches the documented interface, and it shows
the original error message instead of swallowing it.

---

## Extending

* **New animal species with ASCII art:** put the art file in `assets/` and
  create a subclass of `AsciiAnimalSprite` with five class attributes —
  see `ui/lion_sprite.py`. Then add a branch in
  `ZooScene._make_sprite()`. Without a species of its own, the scene falls
  back to the circle sprite automatically.
* **New panel:** create the widget in `ui/`, register it as a tab in
  `ZooMainWindow._build_body()` and feed it the snapshot in `_update_panels()`.
* **New action:** a button in the `ActionPanel`, wire the signal in
  `_connect_signals()` to `_dispatch(name, **kwargs)` — nothing more is needed.
* **Theme:** primarily touch `core/constants.py` and the QSS in
  `main._get_qss()`. A few widgets additionally set inline QSS where the
  global cascade does not take hold reliably (`styled_widgets`,
  `StatusChip`, the progress bars in the `EntityInfoPanel`).

---

## Tests

**Described (mandatory):** Each of the **209 functions** carries a
`Tests:` block with at least two cases — **482 descriptions** in total,
right next to the code. Strategy, fixtures, PyQt preconditions and edge
cases are in [`docs/test_plan.md`](docs/test_plan.md), the manual
acceptance test in §7 of the same document.

**Statically checked:** `pylint frontend/` gives **10.00/10**. What was
restructured for that and which 25 messages are silenced with a
justification is in [`docs/test_plan.md`](docs/test_plan.md) §8 — short enough
to check them one by one.

**Executed (voluntary):** `frontend/tests/` contains **229 runnable
tests** based on the stdlib `unittest` — no additional dependency
required:

```bash
QT_QPA_PLATFORM=offscreen python -m unittest discover -s frontend/tests -t .
```

Among them twelve tests that take the route which made this project's
critical bugs visible in the first place: real `QTest` mouse and keyboard
events instead of direct method calls. And `tests/test_layering.py` pins
down the architecture rules instead of merely asserting them: no
`backend`/`db` imports outside `main.py`, at most one class per file, a
module owner in every file, two test descriptions on every function.

Recompute the numbers (`frontend/tests/` deliberately does not count — tests
need no test descriptions):

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

## Documentation

| Document | Content |
|---|---|
| [`FRONTEND_ARCHITECTURE.md`](FRONTEND_ARCHITECTURE.md) | Structure, layers, design decisions |
| [`docs/frontend_class_diagram.md`](docs/frontend_class_diagram.md) | 9 Mermaid diagrams: classes, sequences, state, components |
| [`docs/test_plan.md`](docs/test_plan.md) | Test strategy, edge cases, acceptance test, static analysis |
| [`docs/criteria_audit.md`](docs/criteria_audit.md) | Evidence per assessment criterion, with verification command |
| [`docs/IMPLEMENTATION_PLAN.md`](docs/IMPLEMENTATION_PLAN.md) | Planning: decisions, data contract, outlook |
| [`docs/CHANGELOG.md`](docs/CHANGELOG.md) | Chronology and bug catalogue |
| [`docs/KI_REFLEXION.md`](docs/KI_REFLEXION.md) | Reflection on the use of AI |
