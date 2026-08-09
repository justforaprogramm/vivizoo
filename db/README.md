# Database Module

> **Authorship.** Drafted with AI assistance and completed under a
> human-in-the-loop process: reviewed, executed and reconciled with
> [`planning/db_planning/db_requirements.md`](../planning/db_planning/db_requirements.md) before being
> committed. The process record — including the ten defects that review
> caught — is in [`ai_usage.md`](docs/ai_usage.md).

Persistence layer of the vivizoo zoo simulation.

This module stores two things:

- **End-of-day summaries and the message log**, so figures can be plotted
  across many days and the history can be reviewed.
- **Complete savegames**, so a zoo can be quit and resumed later.

Callers never write SQL. They create objects and call methods.

---

## Quick start

```bash
pip install -r db/requirements.txt
```

```bash
python -m db.demo
```

The demo writes three simulation days, reads them back, saves a complete zoo
and loads it again. If that runs, everything works.

---

## In 60 seconds

```python
from db import ZooDatabase, DailyStats, Event, EventType

storage = ZooDatabase()                       # -> data/zoo.sqlite

storage.save_day(
    DailyStats(
        day_id=3,
        total_visitors=180,
        revenue=1260.0,
        expenses=420.0,
        avg_animal_welfare=94.0,
        avg_happiness=96.5,
        reputation_end_of_day=92,
        animals_died=0,
    ),
    [Event(tick_count=2200, type=EventType.SUCCESS, text="Record attendance!")],
)

days = storage.get_stats(30)                  # oldest first, ready to plot
storage.close()
```

The database file and all tables are created on first use. Full details:
[`docs/usage.md`](docs/usage.md).

---

## Layout

```
db/
├── interface/                  THE CONTRACT — callers import only this
│   ├── persistence_port.py     AbstractPersistence: every available operation
│   └── enums.py                EventType, TimeOfDay, FoodType
│
├── models/                     ONE CLASS PER TABLE
│   ├── base.py                 Base + TimestampMixin + serialisation
│   ├── daily_stats.py          DailyStats         -> table daily_stats
│   ├── event.py                Event              -> table events
│   ├── zoo_state.py            ZooState           -> table zoo_state
│   ├── inventory.py            InventoryItem      -> table inventory
│   ├── enclosure.py            Enclosure          -> table enclosures
│   ├── animal.py               Animal + Lion/Giraffe/Penguin -> table animals
│   └── animal_status_effect.py AnimalStatusEffect -> table animal_status_effects
│
├── persistence/                THE IMPLEMENTATION
│   ├── engine_factory.py       engine creation + SQLite settings
│   ├── views.py                SQL views for aggregated reads
│   └── zoo_database.py         ZooDatabase — all queries and transactions
│
├── docs/                       usage, architecture, UML, test plan
├── demo.py                     runnable end-to-end example
└── requirements.txt
```

**The dependency rule:**

```
caller       ->  db.interface + db.models      never db.persistence
entry point  ->  db.persistence                creates the storage object
```

It is machine-checkable — this must print nothing:

```bash
grep -rnE "^[[:space:]]*(from|import) db\.persistence" \
     --include="*.py" . --exclude-dir=.venv --exclude-dir=db
```

---

## The seven tables

| Table | Purpose | Written |
|---|---|---|
| `daily_stats` | Key figures of one finished day | once per day |
| `events` | Log and chat messages | once per day, batched |
| `zoo_state` | Savegame root (money, day, …) | on save |
| `inventory` | Stock level per resource | on save |
| `enclosures` | The enclosures | on save |
| `animals` | The animals, including species | on save |
| `animal_status_effects` | Temporary effects on animals | on save |

Column-by-column detail: [`docs/uml_er_diagram.md`](docs/uml_er_diagram.md).

---

## The contract

Callers do not receive a `ZooDatabase`. They receive an
`AbstractPersistence` — an abstract base class listing the eleven operations
storage supports, none of which it implements. (It does implement `__enter__`
and `__exit__` once, so every storage class gains `with`-block support for
free.)

That buys three concrete things:

- **The storage layer can be rewritten** without any caller noticing, as long
  as the method signatures hold.
- **Tests need no database file.** Same class, different argument:

  ```python
  storage = ZooDatabase()             # normal -> data/zoo.sqlite
  storage = ZooDatabase(":memory:")   # tests  -> nothing on disk
  ```

- **Python enforces the contract.** A storage class that forgets a method
  cannot be instantiated at all — the mismatch surfaces at start-up, not
  halfway through a run.

Because SQLAlchemy sits underneath, the database engine itself is largely a
configuration value rather than an architectural commitment:
`"sqlite:///data/zoo.sqlite"` becomes `"postgresql://…"` and every ORM-mapped
table ports unchanged. The one exception is the two SQL views, which are
registered SQLite-only, so `get_weekly_summary()` would need porting. SQLite is
the deliberate choice here — see
[`docs/architecture.md`](docs/architecture.md), sections "Why SQLite" and the
portability caveat that follows it.

---

## Devcontainer / DevPod

The project runs in a devcontainer
(`mcr.microsoft.com/devcontainers/python:3.14`, workspace
`/workspaces/vivizoo`, user `vscode`).

**The short version: it already works.** `.devcontainer/Dockerfile` installs
SQLAlchemy into the container venv `/opt/venv`, and `devcontainer.json` puts
that venv on `PATH` and makes it the default interpreter. So in a fresh
container:

```bash
cd /workspaces/vivizoo
python -m db.demo
```

Two things worth knowing:

**1. A workspace-local `.venv` is optional, and you have to create it.** The
container does not create `/workspaces/vivizoo/.venv`, and it is gitignored, so
it is absent from a fresh clone. If you want one separate from `/opt/venv`:

```bash
cd /workspaces/vivizoo
python -m venv --system-site-packages .venv
source .venv/bin/activate
pip install -r db/requirements.txt
python -m db.demo
```

That venv is container-internal: the paths inside point into the container, so
it does not work on the host. Never ship it in a submission archive.

**2. There is no `postCreateCommand`,** but nothing needs one — the image
already carries the dependency. Only a self-made `.venv` needs the
`pip install` step above. To change the preinstalled set, edit the
`pip install` line in `.devcontainer/Dockerfile`.

**Database location.** The default path is resolved from the module location,
not the working directory:

```
/workspaces/vivizoo/data/zoo.sqlite
```

`data/` lives inside the workspace mount, so the database survives container
rebuilds and is reachable from the host. The directory is created
automatically on first use.

**Files to keep out of version control:**

```
data/*.sqlite
data/*.sqlite-wal
data/*.sqlite-shm
```

The `-wal` and `-shm` files appear because the database runs in
Write-Ahead-Logging mode; they belong to the database file and are not
separate data.

---

## Performance

Median of seven runs on Python 3.14.6 with SQLite 3.53.3, in-process, warm
cache. Absolute values depend on the machine; the ratios are the point.

| Operation | Cost |
|---|---|
| `save_day()` — one day plus 50 messages | ~3.4 ms |
| `get_stats(30)` — chart data | ~0.4 ms |
| `get_events(100)` — message feed | ~0.7 ms |
| `get_weekly_summary()` — aggregated by an SQL view | ~0.15 ms |

The module is written to once per simulation day, not per tick. In a
simulation running at 20 ticks per second — a 50 ms budget per tick — a day
transition costs about 3 ms, once every few thousand ticks. The reasoning is
in [`docs/architecture.md`](docs/architecture.md), section "When is data
written".

---

## Documentation

| Document | Contents |
|---|---|
| [`docs/usage.md`](docs/usage.md) | **Start here.** Every call with a copy-paste example. |
| [`docs/architecture.md`](docs/architecture.md) | Design decisions, layering, write timing, known limitations. |
| [`docs/uml_class_diagram.md`](docs/uml_class_diagram.md) | Class diagrams: inheritance, composition, aggregation, association. |
| [`docs/uml_db_schema.md`](docs/uml_db_schema.md) | Schema diagram: tables, column types, keys, constraints — plus the real DDL. |
| [`docs/uml_er_diagram.md`](docs/uml_er_diagram.md) | ER diagram, views, indexes and cascade behaviour. |
| [`docs/uml_sequence_diagrams.md`](docs/uml_sequence_diagrams.md) | What happens on each call, step by step. |
| [`docs/test_plan.md`](docs/test_plan.md) | Test strategy and at least two described cases per function. |
| [`docs/criteria_audit.md`](docs/criteria_audit.md) | Mapping of every assessment criterion to the evidence. |
| [`docs/ai_usage.md`](docs/ai_usage.md) | AI use, the human-in-the-loop review, and the defects it caught. |
| [`docs/reflexion.md`](docs/reflexion.md) | Personal reflection — written by hand, without AI. |

Three diagram documents rather than one, because they answer different
questions: `uml_class_diagram.md` describes the **Python objects**,
`uml_db_schema.md` the **physical tables**, and `uml_er_diagram.md` the
**relationships** between them.

Every function additionally carries a docstring with `Args`, `Returns`, a
`Raises` section where the function can actually raise, and a `Tests:` section,
so a test description always sits next to the code it covers.
