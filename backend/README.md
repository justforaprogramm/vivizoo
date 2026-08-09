# vivizoo — Backend (`backend/`)

The **backend** is the core logic ("the heartbeat") of the zoo simulation. It sits in the middle of the three-tier architecture:

```
┌─────────────┐   API calls    ┌─────────────┐   domain→models   ┌─────────────┐
│   Frontend  │ ─────────────▶ │   Backend   │ ───────────────▶ │  Database   │
│   (PyQt)    │ ◀───────────── │   (this)    │ ◀─────────────── │   (db/)     │
└─────────────┘   snapshots    └─────────────┘   models          └─────────────┘
```

It owns the **object-oriented simulation logic**: the tick loop, the animal hierarchy, behaviours, visitors, finances, inventory, staff, environmental factors and the player's "God mode". It neither renders the UI nor writes SQL — those are the frontend's and database module's jobs.

Module owner: **Benjamin (backend)**.

---

## Scope and responsibilities

| Concern | Where it lives |
| --- | --- |
| Tick engine, game state, entity info, actions | `backend/core/engine.py` |
| `execute_action` God mode (feed, heal, buy, clean, …) | `backend/core/action_handler.py` |
| Animal hierarchy + behaviour (chapter 2) | `backend/core/animal.py`, `behaviour.py` |
| Zoo aggregate root (composition) | `backend/core/zoo.py` |
| Staff roles (chapter 1) | `backend/core/employee.py` |
| Visitors / budget / stock / weather / effects / chat | `backend/core/visitor.py`, `finances.py`, `inventory.py`, `environment.py`, `status_effect.py`, `message_logger.py` |
| Persistence *adapter* to the database contract | `backend/persistence/db_gateway.py` |
| Architecture and API documentation | `backend/docs/` |

The backend follows a strict dependency rule:

```
backend.core  ->  backend.persistence  ->  db.interface + db.models   (imports)
```

Only `backend/persistence/db_gateway.py` may import from `db`. The core domain stays database-ignorant, which keeps the simulation testable in isolation.

---

## Installation & running

The backend is standard library, but it imports the database module, which needs SQLAlchemy. From the repository root (inside the devcontainer):

```bash
pip install -r db/requirements.txt   # SQLAlchemy (the backend builds on the db module)
```

Run the self-contained demonstration of the core logic:

```bash
python -m backend.demo                  # in-memory only
python -m backend.demo --with-db        # also writes a day to the database
```

> **Note:** the backend provides **no separate** `requirements.txt`. It imports `db`, so install the database module's `db/requirements.txt` (= `SQLAlchemy>=2.0,<3.0`), which covers the backend as well.

---

## How to plug the frontend in

The frontend talks to exactly one object: a `SimulationEngine`. The public methods are (details in `docs/api.md`):

```python
engine = SimulationEngine(zoo, persistence=gateway, logger=MessageLogger.instance())

engine.start()                       # begin ticking in a background thread
engine.pause() / engine.set_speed(2.0)

state  = engine.get_game_state()     # snapshot each render frame
info   = engine.get_entity_info("a_01")   # tooltip data
msgs   = engine.get_chat_messages()  # chat feed (drained)
result = engine.execute_action("feed_all")   # God mode
rows   = engine.get_stats(7)         # chart data (optional gateway)
```

The `persistence` argument is optional: without it the backend runs purely in memory (handy for demos), with it, day summaries and chat messages are stored through `db.interface.AbstractPersistence`.

---

## Code quality (Pylint)

The Pylint configuration lives at the **project root** (`.pylintrc`) so that Pylint finds it automatically when invoked from there. It relaxes precisely the checks that the OOP design deliberately calls for (encapsulation, slim strategy/handler classes, the `db` import in the demo as a third "party") — without switching off the overloaded-methods or snake_case guards in principle. Because it only relaxes, the file never has a lowering effect for other modules (e.g. `db/`).

```bash
cd /workspaces/vivizoo            # project root
pylint backend/                   # => 10.00/10
```

---

## AI use & Reflection
> **Note:** `deepseek flash` at plattform.deepseek.com and `gemini flash` at gemini.google.com were used

This backend was developed with the support of an AI assistant. The AI was deliberately used for the following purposes:

* **Writing code:** functions and classes were generated individually by the AI (for example the tick logic, the `Behaviour` strategies or the `ActionHandler` dispatcher), instead of producing whole modules at once.
* **Ideation:** the AI served as a sparring partner for design questions (e.g. how the day/phase logic should be throttled, how visitor probability should reasonably depend on the weather, or how persistence should be cleanly hidden behind an adapter).
* **Targeted refactoring:** hard-to-read or "not good" code was deliberately refactored — based on concrete AI suggestions the structure was rebuilt without changing the existing behaviour.
* **Pylint cleanup:** the AI helped to fix Pylint warnings and adjust the configuration (`.pylintrc`) so that it supports the patterns the OOP design intends (encapsulation, slim strategy classes, the `db` import of the demo as a third party) without switching off the general quality rules.

**Own responsibility / quality assurance:** the AI was used exclusively as a tool. Every single generated function was **logically checked myself** (the `Tests:` blocks in the docstrings are a result of this manual verification), so the AI-generated building blocks were only adopted after human review.

---

## Tests

This module provides no finished tests, but the framework. The expectations for every public method are already stored as short `Tests:` blocks in the docstrings — they are the basis for unit tests.

### Structure of the test folder

The folder `backend/tests/` is sensibly built **mirroring the production code** — one test file per production module, with a shared fixture module for the recurring setup logic:

```
backend/tests/
├── __init__.py           # makes the folder a package (imports from backend.*)
├── conftest.py           # shared pytest fixtures (e.g. a fresh Zoo instance)
├── test_animal.py        # tests for backend/core/animal.py (chapter 2: animal simulation)
├── test_employee.py      # tests for backend/core/employee.py (chapter 1: staff)
├── test_enclosure.py     # tests for backend/core/enclosure.py
├── test_zoo.py           # tests for the aggregate backend/core/zoo.py
├── test_engine.py        # tests for the tick loop and the ActionHandler
├── test_finances.py      # tests for backend/core/finances.py (budgets)
├── test_inventory.py     # tests for backend/core/inventory.py (stock)
├── test_environment.py   # tests for backend/core/environment.py (weather)
├── test_status_effect.py # tests for backend/core/status_effect.py
└── test_persistence.py   # tests for backend/persistence/db_gateway.py (database connection)
```

Guidelines for the structure:

* **One production module, one test file** — so the mapping stays unambiguous and it is immediately visible which reality a test covers.
* **`conftest.py`** keeps the setup code (build a zoo, reset the logger, create the engine) as fixtures instead of duplicating it in every test file. Examples are shown further down.
* **Test names speak the *behaviour*, not the implementation:** `test_feed_reduces_hunger` instead of `test_feed`.
* Every test file starts with a short docstring that names the chapter/area (e.g. "Chapter 2: animal simulation").

### What is tested

The backend covers the three OOP pillars of the assignment — the tests are oriented along them:

| Area | Example case |
| --- | --- |
| **Encapsulation** | statistics can never fall outside 0–100; `spend()` must not make the budget negative; `finances._balance` is private. |
| **Polymorphism** | `Lion`/`Giraffe`/`Penguin` inherit from `Animal` but differ in `PREFERRED_FOOD`, `DIGESTION_RATE`, `move()`; `create_animal("penguin", …)` returns the correct subclass. |
| **Composition** | `Zoo` contains enclosures/finances/inventory; `Enclosure` holds animals; a "zoo management" test checks adding/removing and capacity. |

Concretely per module:

* **animal.py** — species discriminator, `feed`/`rest`/`age_one_day`/`move`, hunger increase over ticks, death after 3 starved days, value clamping.
* **employee.py** — each role fulfils its core task in the zoo (Keeper feeds/cleans, Veterinarian heals, Admin sets the ticket price).
* **enclosure.py** — `free_slots`, `is_full`, `clean`, `average_welfare`, cleanliness decay.
* **zoo.py** — create and find enclosures/animals/staff, daily snapshot, `to_game_state` shape, visitors pay a ticket.
* **engine.py** — tick counts up; `execute_action` mutates the zoo; an unknown action raises `ValueError`; `get_entity_info` returns `{}` for an unknown id.
* **persistence.py** — through an in-memory `ZooDatabase(":memory:")`: after one finished day exactly one `DailyStats` entry is readable; the events share the `day_id`.

### Important boundary conditions for individual tests

* **Isolate the logger.** `MessageLogger` is a singleton. Before a test that expects chat entries, it must be reset to fresh, otherwise tests drag in messages from earlier tests:
  ```python
  MessageLogger.reset_to_fresh()
  zoo = Zoo(name="T", logger=MessageLogger.instance())
  ```
* **Determinism of randomness.** Movement, weather and visitor spawns are random. Tests for them must **not check fixed values** on coordinates, only invariants ("within a range", "a valid weather"). Where possible use `random.seed(...)` or deliberately set the random component (e.g. `_update_offset`) to `0` so the throttled update fires immediately.
* **Tick boundaries.** Many flows are throttled (hunger every N ticks, Veterinarian from ~20, the day closes at `tick % 480 == 0`). A test of the day close must let the engine run exactly **one full round** (`for _ in range(TICKS_PER_DAY): engine.tick()`), otherwise no day is ever closed and persistence returns 0 rows.
* **Hunger semantics.** Hunger is `0 = full` / `100 = starving`. A "feed" test therefore starts an animal hungry (e.g. `_hunger = 70.0`), otherwise it is not fed because `hunger < threshold` holds.
* **No side effects on real data.** Budget, inventory and random tests build their objects freshly. The persistence tests use `ZooDatabase(":memory:")` and close it at the end (`storage.close()`).
* **Respect encapsulation.** Where possible do not write private attributes (`_hp` etc.) in tests; where this is unavoidable (e.g. when pre-setting hunger), mark it in a comment.
* **Each test checks one thing.** A failure should have a single cause; hence one assertion or one coherent scenario per test.

### Helpful fixture templates (for `conftest.py`)

```python
import pytest
from backend.core.message_logger import MessageLogger
from backend.core.zoo import Zoo

@pytest.fixture
def zoo():
    MessageLogger.reset_to_fresh()
    z = Zoo(name="Test Zoo", logger=MessageLogger.instance())
    savanna = z.add_enclosure("Savanna 1", "savanna", capacity=8)
    return z, savanna

@pytest.fixture
def hungry_lion(zoo):
    z, savanna = zoo
    lion = z.add_animal("lion", "Simba", savanna)
    lion._hunger = 80.0  # hungry -> will be fed by feed_all
    return z, lion
```

---

## Database relationship ("nothing added to the database")

This module **adds no tables and no schema**. It consumes the database module's public contract exactly as the planning requires:

* It holds a reference to an `AbstractPersistence` (e.g. `ZooDatabase`).
* At the end of each day it builds the `DailyStats` and `Event` model objects the database module already knows and calls `persistence.save_day(...)`.
* The mapping happens in `backend/persistence/db_gateway.py`.

Field names (species keys `"lion"`/`"giraffe"`/`"penguin"`, `FoodType` resources, `enclosure_id`, …) intentionally mirror the database module, so the adapter needs no transformation logic.

---

## Documentation

* `docs/class_diagram.md` — Mermaid UML class diagram of the domain.
* `docs/sequence_diagrams.md` — Mermaid sequence diagrams (tick loop, action, persistence).
* `docs/api.md` — the frontend-facing API contract and data shapes.
* `docs/test_plan.md` — distributed test expectations (each method's `Tests:` docstring) and how to turn them into unit tests (see the **Tests** section above for the concrete structure and boundary conditions).
