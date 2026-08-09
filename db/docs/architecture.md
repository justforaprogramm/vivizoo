# Database Architecture

> **Authorship.** Drafted with AI assistance and completed under a
> human-in-the-loop process: reviewed, executed and reconciled with
> [`planning/db_planning/db_requirements.md`](../../planning/db_planning/db_requirements.md) before being
> committed. The process record — including the ten defects that review
> caught — is in [`ai_usage.md`](ai_usage.md).

Design decisions of the persistence layer, and the reasoning behind them.

---

## 1. Layering

```
┌──────────────────────────────────────────────┐
│  Caller                                      │
│  holds live state in memory                  │
└───────────────────┬──────────────────────────┘
                    │ AbstractPersistence + models
┌───────────────────▼──────────────────────────┐
│  Interface  (db/interface/)                  │
│  the contract — no implementation            │
└───────────────────┬──────────────────────────┘
                    │
┌───────────────────▼──────────────────────────┐
│  Models  (db/models/)                        │
│  one class per table, the shared language    │
└───────────────────┬──────────────────────────┘
                    │
┌───────────────────▼──────────────────────────┐
│  Persistence  (db/persistence/)              │
│  sessions, queries, transactions             │
└───────────────────┬──────────────────────────┘
                    │
              data/zoo.sqlite
```

**The rule that holds it together:** the module imports nothing from the code
that uses it, and callers import nothing from `db.persistence`. What crosses
the boundary is `AbstractPersistence`, the model objects and the enums — plus
the single `ZooDatabase` construction at the application's entry point.

This is not a convention to remember, it is checkable — this must print
nothing:

```bash
grep -rnE "^[[:space:]]*(from|import) db\.persistence" \
     --include="*.py" . --exclude-dir=.venv --exclude-dir=db
```

The pattern is anchored to real import statements and restricted to `*.py`,
so prose that merely mentions a module does not trigger a false positive.

The diagram shows the dependency *direction*, not a strict chain: the
persistence layer imports `db.interface` as well as `db.models`, because it has
to implement the contract. What holds without exception is the direction —
nothing in `db.interface` or `db.models` imports `db.persistence`.

---

## 2. Why SQLite

| Option | Verdict |
|---|---|
| **SQLite** | Ships with Python. No server, no installation, no configuration. The database is a file inside the project. |
| PostgreSQL / MySQL | Would require the reviewer to install, start and configure a server before the application runs at all. |
| MongoDB | The data is strongly relational (days own events, zoos own enclosures own animals). A document store would fight that. |
| A REST API in front of the database | The application is a single-user desktop program. An HTTP hop between two objects in the same process adds latency and failure modes and solves nothing. |

The actual data volume settles it: roughly 5,000 rows after a hundred
simulated days. SQLite becomes interesting somewhere around a few million.

The choice is also cheap to revisit. Because SQLAlchemy sits in between, the
database is a **configuration value**, not an architectural commitment:

```python
ZooDatabase("sqlite:///data/zoo.sqlite")
ZooDatabase("postgresql://user@host/vivizoo")   # same code
```

**One caveat, stated rather than glossed over.** The ORM-mapped tables port
unchanged, and the SQLite pragmas are already dialect-guarded. The two SQL
views in `persistence/views.py` are not: they are registered with
`execute_if(dialect="sqlite")`, so a `postgresql://` URL creates the tables but
no views — verified by emitting the schema against a mock engine (2 `CREATE
VIEW` on SQLite, 0 on PostgreSQL). `get_weekly_summary()` reads
`v_weekly_summary` directly, so it is the single method that would need
porting. Everything else is genuinely a one-string change.

---

## 3. Why an ORM, and how object orientation survives it

An ORM ("Object-Relational Mapper") translates between Python objects and
table rows. Without one, the layer would need hand-written mappers, a CRUD
base class, a transaction wrapper and a schema manager — a lot of plumbing
that demonstrates effort rather than design.

With SQLAlchemy the object-oriented work moves to where it belongs, the
**domain model**:

| Principle | Where it lives |
|---|---|
| **Abstraction** | `AbstractPersistence` — an abstract base class naming the eleven storage operations without implementing any (only the shared `with`-block support is concrete). |
| **Inheritance** | `Animal` → `Lion` / `Giraffe` / `Penguin`; `TimestampMixin` contributes a column to several tables via multiple inheritance. |
| **Polymorphism** | The `species` column is a discriminator: reading animals returns the correct subclass, so `PREFERRED_FOOD` resolves per species without a single type check. |
| **Encapsulation** | `@validates` hooks reject invalid values on assignment; the same rules exist a second time as `CHECK` constraints in the schema. |
| **Composition** | `cascade="all, delete-orphan"`: deleting a zoo deletes its enclosures, their animals and those animals' status effects. |
| **Modularity** | A new species is three lines. A new storage implementation is one class. Neither touches anything else. |

### Two layers of validation, on purpose

```python
@validates("hp", "hunger", "welfare")            # 1. in Python
def _check_percentage(self, field, value): ...

CheckConstraint("hp BETWEEN 0 AND 100")          # 2. in the schema
```

They are not redundant, they guard different things. The validator protects
against bugs in our own code and produces a readable error at the moment of
assignment. The constraint protects the **file** — it still holds if someone
opens the database in a SQLite browser and edits a row by hand.

---

## 4. When is data written

This is the decision the whole performance story rests on.

| Moment | What happens | Cost |
|---|---|---|
| Every tick (up to 20/s) | **nothing.** The disk is not touched. | 0 ms |
| End of a simulation day | one `daily_stats` row plus that day's messages, batched | ~3 ms |
| A savegame is written | the complete zoo graph | ~18 ms for 50 animals, once |

At 20 ticks per second a tick has 50 ms. The database uses none of it,
because live state stays in the caller's memory and only summaries are
persisted. A day transition costs about 3 ms — around one thousandth of the
wall-clock time between two of them.

Writing full state per tick was considered and rejected. The numbers:

```
20 ticks/s x ~170 rows  =  3,400 rows per second
                        =  12 million rows per hour of play
```

for a zoo with 50 animals. Beyond the volume, `session.merge()` costs roughly
0.1–0.5 ms **per object**, so 170 objects would consume 20–80 ms — more than
the entire tick budget, and a synchronous write would stall the UI thread
while it happened.

If per-tick persistence ever becomes a requirement (a replay feature, say),
the order of attack is: batch inserts instead of per-object merges, write only
changed rows, and move writing to a background thread with its own
connection.

### Why `get_stats()` does not load messages

Charts need figures, not chat lines. Eagerly loading every message of every
day made the query about thirty times slower:

| | measured |
|---|---|
| `get_stats(30)` with messages eagerly loaded | 15.6 ms |
| `get_stats(30)` without | 0.5 ms |

So `get_stats()` explicitly suppresses that load. Reading `.events` on one of
its results raises a clear error instead of silently returning an empty list;
`get_events()` is the way to read messages.

---

## 5. SQLite settings that are not optional

Applied to every connection in `persistence/engine_factory.py`:

```python
PRAGMA foreign_keys=ON      # SQLite ignores foreign keys unless asked
PRAGMA journal_mode=WAL     # readers no longer block writers
PRAGMA synchronous=NORMAL   # one fewer fsync per commit; safe under WAL
```

The first one matters most. **SQLite does not enforce foreign keys by
default**, and it must be switched on per connection, every time. Without it
the `ON DELETE CASCADE` rules in the models would be decorative and deleting
a savegame would leave orphaned animals behind.

WAL mode creates `zoo.sqlite-wal` and `zoo.sqlite-shm` next to the database.
They belong to it and are not separate data — keep them out of git.

---

## 6. Design decisions worth defending

### The implementation is called `ZooDatabase`, not after its library

An earlier name was `SqlAlchemyPersistence`. It was replaced, because a class
name should say what the thing *is*, not which library happens to build it:

* SQLAlchemy is an implementation detail — precisely the thing the interface
  exists to hide. Naming the class after it reopened that hole at the one
  place callers touch the module.
* It was already inconsistent: the class said SQLAlchemy, its own docstring
  said SQLite. Two answers to "what is this".
* It named the part most likely to change. Swap the ORM and the database
  stays the same — but the name would be wrong.

`ZooDatabase` combines the domain (whose data) with the medium (where it
lives) and survives a change of either library underneath.

### `profit_loss` is a generated column

The requirements list it as a column of `daily_stats`, so it is one — but
declared as `GENERATED ALWAYS AS (revenue - expenses)`. The database computes
it, so it can never contradict the two values it derives from.

The trade-off: on a freshly built object the attribute is `None`, and it is
only populated on objects read back from the database. That is documented on
the class and is the price of making an inconsistent value structurally
impossible.

### Column defaults apply at construction time

SQLAlchemy normally fills `default=` values while writing a row, so a fresh
`Lion(animal_id="a_01")` would carry `hp = None` until it had been through
the database — and `is_critical()` would crash on it.

An `init` event listener in `models/base.py` closes that gap: defaults are
applied when the object is constructed. Explicitly passed values always win.

### Single-table inheritance for animals

All species share the `animals` table, distinguished by the `species` column.
The alternative — one table per species — would add joins and migrations for
no gain, because the species differ in *behaviour* (`PREFERRED_FOOD`), not in
*stored fields*.

### Enums as `VARCHAR` plus `CHECK`

`native_enum=False` stores enum values as readable text with a `CHECK`
constraint, instead of as opaque integers. The database stays readable in any
SQLite browser, and adding a value is a one-line change.

### `save_game()` deletes before inserting — and then merges

Replacing a slot deletes the old graph first and inserts the new one, inside
one transaction. Merging into the existing rows instead would leave animals
behind that the player had sold or that had died — the save would slowly
accumulate ghosts.

The insert half then uses `merge()` rather than `add()`, which looks redundant
after a delete and is not. The graph handed in has usually just come back from
`load_game()`, because load–play–save is *the* normal cycle. Such a graph still
carries its database identity, so `add()` treats it as an existing row and
emits `UPDATE` statements against rows the same transaction has just deleted —
a `StaleDataError` on the one code path that matters most. `expunge_all()`
followed by `merge()` handles a freshly built graph and a loaded one
identically.

### A day is written once

`save_day()` refuses a `day_id` that already holds figures instead of replacing
it. Overwriting is destructive in two ways at once: the earlier day's numbers
disappear *and* both days' messages end up merged under one id, with nothing
afterwards revealing that a day went missing. The realistic cause is a day
counter that failed to advance, which is a bug worth surfacing rather than
absorbing. `overwrite=True` exists for the deliberate case.

Messages behave the opposite way — they append — because `append_events()` must
be able to flush the queue mid-day without the day-end call wiping the result.
`replace_events=True` inverts that. The two flags are independent.

### Registering the views is idempotent

`register_views()` is called from every `ZooDatabase.__init__`, and
SQLAlchemy's `event.listen` appends rather than replaces. Without a guard, a
second instance would attach the two DDL statements a second time and every
`create_all()` would re-issue all of them — growing without bound in a test
suite that builds one in-memory database per case. The guard makes repeated
registration free rather than merely harmless.

---

## 7. Known limitations

**One save slot.** `enclosure_id` is the primary key of `enclosures`, so two
slots cannot both contain an enclosure `"e_01"`. The MVP uses slot 1 and
`save_game()` replaces it wholesale, so this never surfaces. Supporting
several slots means making the key composite (`zoo_id` + `enclosure_id`) and
extending the animal foreign key accordingly.

**Schema changes require a fresh database.** There is no migration tool
(Alembic would be disproportionate here). After changing a model, delete
`data/zoo.sqlite` or call `reset()`. Worth stating explicitly because an
enum extension counts as a schema change: the `CHECK` constraint is baked
into the table.

**One connection per thread.** SQLite connections are not thread-safe. With
one write per simulation day this never comes up, but a background writer
would need its own connection.

**A real all-zero day has no overwrite protection.** `_assert_day_is_free()`
treats a `daily_stats` row whose every figure is zero as free to fill in,
because that is exactly what `append_events()` leaves behind when messages
arrive before a day is closed. A genuine day on which nothing happened — no
visitors, no revenue, no expenses, no deaths — is indistinguishable from that
placeholder and can therefore be overwritten silently.

Telling the two apart needs a marker column on `daily_stats`, and the schema is
agreed in `planning/db_planning/db_requirements.md`; changing it unilaterally
would break the thing the planning document is for. The alternative — treating
every existing row as occupied — would break the flush-then-close-the-day flow,
which is a real feature rather than a hypothetical day. So the narrower gap was
accepted knowingly. It is recorded as case X-11 in `test_plan.md` so it stays
visible.

---

## 8. File map

| File | Responsibility |
|---|---|
| `interface/persistence_port.py` | The contract. No storage implementation — the eleven abstract operations plus shared `with`-block support. |
| `interface/enums.py` | Shared value sets. |
| `models/base.py` | Declarative base, timestamp mixin, serialisation, default handling. |
| `models/*.py` | One table each. |
| `persistence/engine_factory.py` | Engine creation, database path, SQLite pragmas. |
| `persistence/views.py` | SQL views for aggregated reads. |
| `persistence/zoo_database.py` | `ZooDatabase` — the only place sessions are opened and SQL is issued. |
| `demo.py` | Runnable end-to-end example. |

One responsibility per file, as required.

### The documents

| File | Answers |
|---|---|
| `README.md` | What is this and how do I run it? |
| `docs/usage.md` | How do I call it? |
| `docs/architecture.md` | Why does it look like this? (this file) |
| `docs/uml_class_diagram.md` | What are the classes and how do they relate? |
| `docs/uml_db_schema.md` | What does the schema look like — types, keys, constraints, DDL? |
| `docs/uml_er_diagram.md` | How do the tables relate, and what do the views and indexes do? |
| `docs/uml_sequence_diagrams.md` | What happens, step by step, on each call? |
| `docs/test_plan.md` | What would be tested, and why those cases? |
| `docs/criteria_audit.md` | Where is the evidence for each assessment criterion? |
| `docs/ai_usage.md` | How was AI used, and what did the review catch? |
| `docs/reflexion.md` | What did I take away from it? (my own words, no AI) |
