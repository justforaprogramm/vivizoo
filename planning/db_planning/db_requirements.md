# Database Requirements

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
| Player saves or quits | the complete zoo graph | ~50–100 ms, once |

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

## 5. Interface for callers

Callers never see SQL. They receive one object implementing
`AbstractPersistence` and call methods on it:

| Method | Input | Output |
| :--- | :--- | :--- |
| `save_day(stats, events=(), replace_events=False)` | `DailyStats`, iterable of `Event`, `bool` | `None` |
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

---

## 6. Implementation status

Implemented in `db/`. See:

* `db/README.md` — quick start and devcontainer notes
* `db/docs/usage.md` — every call with a copy-paste example
* `db/docs/architecture.md` — design decisions and known limitations
* `db/docs/uml_class_diagram.md`, `uml_er_diagram.md`, `uml_sequence_diagrams.md`
* `db/docs/test_plan.md` — test strategy and all described test cases
