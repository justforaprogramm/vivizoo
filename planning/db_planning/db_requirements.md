# Database Requirements

> **Authorship.** Drafted with AI assistance and completed under a
> human-in-the-loop process: this plan was agreed first and the code in
> `db/` was written against it, then checked back against it field by
> field. The process record is in [`ai_usage.md`](../../db/docs/ai_usage.md).

**Focus area: Database**

The database is built in two steps:

1. **Basic operation (step 1)**: stores only end-of-day summaries for the
   charts, plus the message log.
2. **Full savegame (step 2)**: stores the complete state of the zoo, so a
   game can be quit and resumed later.

---

## 1. Basic operation: charts and history (step 1)

These tables store a summary at the end of every simulation day, so values
such as revenue or visitor numbers can be plotted.

### Table: `daily_stats` (end-of-day summary)
*Stores the key figures at the end of each simulation day.*

| Column | Data type | Meaning |
| :--- | :--- | :--- |
| `day_id` | Number | Number of the simulation day (day 1, day 2, ...) |
| `created_at` | Date/time | When this row was created in the real world |
| `total_visitors` | Number | How many visitors were in the zoo that day |
| `revenue` | Money | Total income of the day (e.g. from tickets) |
| `expenses` | Money | Total spending of the day (food, staff, ...) |
| `profit_loss` | Money | Revenue minus expenses |
| `avg_animal_welfare` | Percent (0–100) | How well all living animals fared on average |
| `avg_happiness` | Percent (0–100) | How satisfied the visitors were on average |
| `reputation_end_of_day` | Number | Reputation of the zoo at the end of the day |
| `animals_died` | Number | How many animals died that day |

> `profit_loss` is a generated column: the database computes it as
> `revenue - expenses`, so it can never contradict the two values it is
> derived from.

---

### Table: `events` (messages and log)
*Stores all chat and system messages permanently.*

| Column | Data type | Meaning |
| :--- | :--- | :--- |
| `id` | Number | Unique number of the message |
| `day_id` | Number | Reference to the simulation day it happened on |
| `tick_count` | Number | The exact tick the message was produced at |
| `type` | Text | Kind of message (`INFO`, `WARNING`, `ERROR`, `SUCCESS`) |
| `text` | Text | The message body itself |
| `entity_id` | Text (optional) | Identifier of the affected object (e.g. which animal) |
| `details` | JSON (optional) | Structured extra payload, e.g. `{"cause": "starvation"}` |

---

## 2. Saving a game (step 2)

These tables are needed to store a game completely and resume it later at the
same point.

### Table: `zoo_state` (global state)
| Column | Data type | Meaning |
| :--- | :--- | :--- |
| `id` | Number | Unique number of the save slot |
| `tick_count` | Number | Current tick of the simulation |
| `game_day` | Number | Current simulation day |
| `time_of_day` | Text | Phase of the day (`MORNING`, `NOON`, `EVENING`, `NIGHT`) |
| `zoo_open` | Yes/No | Whether the zoo is currently open |
| `money` | Money | Current account balance |
| `reputation` | Number | Current reputation of the zoo |
| `ticket_price` | Money | Current admission price |
| `created_at` | Date/time | When the save was made |

---

### Table: `inventory` (stock levels)
| Column | Data type | Meaning |
| :--- | :--- | :--- |
| `zoo_id` | Number | Which save slot this stock belongs to |
| `food_type` | Text | Kind of resource (`MEAT`, `PLANTS`, `FISH`, `MEDICINE`) |
| `amount` | Number | How many units are in stock |

---

### Table: `enclosures`
| Column | Data type | Meaning |
| :--- | :--- | :--- |
| `enclosure_id` | Text | Identifier of the enclosure (e.g. `e_01`) |
| `zoo_id` | Number | Which save slot this enclosure belongs to |
| `name` | Text | Name of the enclosure |
| `biome` | Text | Landscape type (e.g. `savanna`, `arctic`) |
| `capacity` | Number | Maximum number of animals that fit in |
| `cleanliness` | Percent (0–100) | How clean the enclosure currently is |

---

### Table: `animals`
| Column | Data type | Meaning |
| :--- | :--- | :--- |
| `animal_id` | Text | Identifier of the animal (e.g. `a_01`) |
| `enclosure_id` | Text | Which enclosure the animal lives in |
| `name` | Text | Name of the animal |
| `species` | Text | Species (e.g. `lion`, `penguin`, `giraffe`) |
| `age_days` | Number | Age in simulation days |
| `hp` | Percent (0–100) | Current health |
| `hunger` | Percent (0–100) | Current hunger level |
| `welfare` | Percent (0–100) | How well the animal feels |
| `is_dead` | Yes/No | Whether the animal is alive or has died |
| `pos_x` | Number | Position on the map (X) |
| `pos_y` | Number | Position on the map (Y) |

> `species` is a **discriminator**: it decides which class an animal becomes
> when loaded (`Lion`, `Giraffe`, `Penguin`). Adding a species therefore
> needs no schema change.

---

### Table: `animal_status_effects`
| Column | Data type | Meaning |
| :--- | :--- | :--- |
| `id` | Number | Unique number of the entry |
| `animal_id` | Text | Which animal is affected |
| `effect_name` | Text | Which state applies (e.g. `Hungry`, `Poisoned`, `Stressed`) |
| `remaining_ticks` | Number | How much longer the effect lasts |

---

## 3. How it works behind the scenes

### In the first version (step 1)

1. **While playing**: the simulation holds all data about animals, enclosures
   and food in memory. The database is not touched per tick.
2. **When night falls**:
   * The day's figures are calculated and written into `daily_stats`.
   * The day's messages are written into `events`, in one batch.
   * Both happen inside a single transaction, so a crash can never leave a
     day without its messages.
3. **Displaying charts**: this data is read through `get_stats()` to show
   trends across several days.

### Write frequency

| Moment | What happens | Cost |
| :--- | :--- | :--- |
| Every tick (up to 20/s) | nothing — the disk is not touched | 0 ms |
| End of a simulation day | one `daily_stats` row plus that day's messages | ~3 ms |
| Player saves or quits | the complete zoo graph | ~18 ms for 50 animals, once |

---

## 4. Relationships between the tables

```
daily_stats  1 ──< events                  (a day owns its messages)

zoo_state    1 ──< inventory               (a save owns its stock)
zoo_state    1 ──< enclosures              (a save owns its enclosures)
enclosures   1 ──< animals                 (an enclosure houses animals)
animals      1 ──< animal_status_effects   (an animal owns its effects)
```

All foreign keys use `ON DELETE CASCADE`: deleting a save removes its
enclosures, their animals and those animals' status effects automatically.

---

## 4a. Values the database itself enforces

Most rules below exist **twice**: once in Python, so a mistake in our own code
raises a readable error at the moment of assignment, and once in the schema, so
the file stays valid even when someone edits it in a SQLite browser.

Four rows are marked *(schema only)*. They carry the `CHECK` constraint but no
Python validator, so a bad value is accepted in memory and rejected as an
`IntegrityError` when the row is written. That is a deliberate line, not an
oversight: the doubled rules guard values the *simulation* computes and can get
wrong (percentages, stock levels), while the schema-only ones are counters the
simulation only ever increments.

| Column | Enforced range or value set |
| :--- | :--- |
| `daily_stats.avg_animal_welfare`, `avg_happiness` | 0–100 |
| `daily_stats.total_visitors`, `animals_died` | not negative *(schema only)* |
| `animals.hp`, `hunger`, `welfare` | 0–100 |
| `animals.age_days` | not negative *(schema only)* |
| `enclosures.cleanliness` | 0–100 |
| `enclosures.capacity` | not negative *(schema only)* |
| `zoo_state.tick_count`, `game_day`, `ticket_price` | not negative *(schema only)* |
| `inventory.amount` | not negative |
| `animal_status_effects.remaining_ticks` | not negative |
| `events.type` | `INFO`, `WARNING`, `ERROR`, `SUCCESS` |
| `zoo_state.time_of_day` | `MORNING`, `NOON`, `EVENING`, `NIGHT` |
| `inventory.food_type` | `MEAT`, `PLANTS`, `FISH`, `MEDICINE` |

Eighteen `CHECK` constraints in total. The three value sets are stored as
readable text rather than opaque integers, so a row means something without a
lookup table.

`animals.species` is deliberately **not** in this list: it is a discriminator,
and constraining it would mean a schema change for every new species.

---

## 5. Interface for callers

Callers never see SQL. They receive one object implementing
`AbstractPersistence` and call methods on it:

| Method | Input | Output |
| :--- | :--- | :--- |
| `save_day(stats, events=(), replace_events=False, overwrite=False)` | `DailyStats`, iterable of `Event`, `bool`, `bool` | `None` |
| `append_events(events)` | iterable of `Event` | `None` |
| `get_stats(days_back=30)` | `int` | `list[DailyStats]`, oldest first |
| `get_events(day_id=None, limit=100)` | `int \| None`, `int` | `list[Event]`, oldest first |
| `get_weekly_summary()` | – | `list[dict]`, oldest first |
| `save_game(zoo_state)` | `ZooState` | `int` (slot number) |
| `load_game(save_id=1)` | `int` | `ZooState \| None` |
| `list_saves()` | – | `list[dict]`, newest first |
| `delete_save(save_id)` | `int` | `bool` |
| `reset()` | – | `None` |
| `close()` | – | `None` |

`AbstractPersistence` is an abstract base class: it names the operations and
implements none of them. Callers are typed against it and therefore never
learn which storage they received — which is what makes the layer replaceable
and lets tests run against an in-memory database. The shipped implementation
is `ZooDatabase`, backed by SQLite.

### Write rules for `save_day()`

The two flags are independent switches, because figures and messages have
different lifecycles: figures are written once at the end of a day, messages
arrive in several batches during it.

| Flag | Default | Effect |
| :--- | :--- | :--- |
| `replace_events` | `False` | `False` appends the messages; `True` makes the day's log become exactly the set handed in |
| `overwrite` | `False` | `False` **refuses** a `day_id` that already holds figures; `True` replaces them |

Refusing a repeated `day_id` is deliberate. Overwriting would delete the
earlier day's numbers *and* merge both days' messages under one id, with
nothing afterwards revealing that a day went missing — and the realistic cause
is a day counter that failed to advance.

A day that exists only as a placeholder — created by `append_events()` when
messages arrive before the day is closed — counts as free and is filled in
normally.

### Identifiers the caller assigns

`animal_id` and `enclosure_id` are chosen by the caller, not the database,
because the simulation needs them before anything is stored: a message can
carry `entity_id="a_01"` on the first tick. Two helpers on `ZooState` hand out
free ones:

| Method | Output |
| :--- | :--- |
| `next_animal_id(prefix="a_")` | e.g. `"a_03"`, counting from the highest identifier present |
| `next_enclosure_id(prefix="e_")` | e.g. `"e_03"` |

They count from the highest existing identifier rather than from the number of
objects, so they keep working after a savegame has been loaded. A counter that
restarts at `1` would hand out duplicates, and a duplicate is destructive —
`save_game()` therefore refuses a graph containing one.

### Aggregated reads

Two read-only SQL views ship with the schema and are created alongside the
tables:

| View | Purpose |
| :--- | :--- |
| `v_weekly_summary` | groups `daily_stats` into weeks of seven days; read through `get_weekly_summary()` |
| `v_event_summary` | counts messages per day and type, so "3 warnings, 1 error" needs no message loading |

---

## 6. Implementation status

Implemented in `db/`, and checked back against this document field by field.
See:

* `db/README.md` — quick start and devcontainer notes
* `db/docs/usage.md` — every call with a copy-paste example
* `db/docs/architecture.md` — design decisions and known limitations
* `db/docs/uml_db_schema.md` — the schema as a UML diagram, plus the generated DDL
* `db/docs/uml_class_diagram.md`, `uml_er_diagram.md`, `uml_sequence_diagrams.md`
* `db/docs/test_plan.md` — test strategy and all described test cases
* `db/docs/ai_usage.md` — AI use and the human-in-the-loop review
* `db/docs/reflexion.md` — personal reflection, written by hand without AI
* `db/docs/criteria_audit.md` — every assessment criterion mapped to evidence

### Where this document was corrected to match the code

Kept visible rather than quietly edited, because the point of the exercise is
that plan and implementation agree — and how they were made to agree is part of
the answer.

| Item | Change |
| :--- | :--- |
| `save_day()` signature | The implementation grew an `overwrite` flag that this document did not mention. Documented here, in section 5 |
| Write rules for `save_day()` | The append-vs-replace and refuse-vs-overwrite rules were only in the code. Written down |
| Identifier helpers | `next_animal_id()` / `next_enclosure_id()` existed but were unplanned. Added, with the reason they count from the highest id |
| Views | `v_weekly_summary` and `v_event_summary` were implied by `get_weekly_summary()` only. Named explicitly |
| Enforced value ranges | Section 4a is new — the `CHECK` constraints existed in the schema but nowhere in the plan |

One correction ran the other way, from plan to code: this document had always
described enum columns as a restricted value set, but the schema was generating
a bare `VARCHAR` — SQLAlchemy 2.0 does not create the constraint unless asked.
The code was fixed, not the plan.
