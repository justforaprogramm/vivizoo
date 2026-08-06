# Usage Guide

How to use the database module. No SQL knowledge required — you create
objects and call methods.

---

## Install

```bash
pip install -r db/requirements.txt
```

One dependency: SQLAlchemy. SQLite ships with Python.

---

## Quick start

```python
from db import ZooDatabase, DailyStats, Event, EventType

storage = ZooDatabase()                       # -> data/zoo.sqlite

storage.save_day(
    DailyStats(day_id=1, total_visitors=120, revenue=840.0, expenses=300.0),
    [Event(type=EventType.INFO, text="Zoo has opened.")],
)

for day in storage.get_stats(30):
    print(day.day_id, day.revenue, day.profit_loss)

storage.close()
```

The database file and all tables are created on first use. There is no setup
step.

---

## The two things you work with

**One storage object.** Created once at start-up, passed around, closed at
the end.

```python
storage = ZooDatabase()             # normal operation -> data/zoo.sqlite
storage = ZooDatabase(":memory:")   # tests -> nothing written to disk
storage = ZooDatabase("path/to/other.sqlite")
```

Type your own code against `AbstractPersistence`, not against `ZooDatabase`:

```python
from db.interface import AbstractPersistence

def __init__(self, storage: AbstractPersistence) -> None:
    self._storage = storage
```

`AbstractPersistence` is the abstract base class listing every operation
below and implementing none of them. Depending on it rather than on the
concrete class means the storage layer can be swapped — including for an
in-memory one in tests — without your code changing.

**Model objects.** Plain Python objects describing what is stored. You fill
them in and hand them over; you get them back the same way.

| Class | Represents |
|---|---|
| `DailyStats` | The key figures of one finished simulation day |
| `Event` | One log or chat message |
| `ZooState` | The root of a savegame |
| `Enclosure` | One enclosure inside a savegame |
| `Animal` (`Lion`, `Giraffe`, `Penguin`) | One animal inside an enclosure |
| `AnimalStatusEffect` | A temporary effect on an animal |
| `InventoryItem` | Stock level of one resource |

---

## The methods

| Method | What it does |
|---|---|
| `save_day(stats, events=(), replace_events=False, overwrite=False)` | Store one finished day plus its messages |
| `append_events(events)` | Store messages without closing a day |
| `get_stats(days_back=30)` | Read day summaries, oldest first |
| `get_events(day_id=None, limit=100)` | Read messages, oldest first |
| `get_weekly_summary()` | The same figures grouped into weeks |
| `save_game(zoo_state)` | Store a complete savegame → slot number |
| `load_game(save_id=1)` | Read a savegame → `ZooState` or `None` |
| `list_saves()` | List slots for a load menu |
| `delete_save(save_id)` | Delete a slot → `True` / `False` |
| `reset()` | Delete everything and recreate empty tables |
| `close()` | Release the database |

---

## What goes where

Two independent stores, written at different moments. Mixing them up is the
easiest mistake to make:

| Call | Stores | When |
|---|---|---|
| `save_day(stats, events)` | Figures and messages. **No animals.** | Once per simulation day |
| `save_game(zoo_state)` | The zoo itself: enclosures, animals, stock | Whenever a savegame should be written |

They are unrelated: a zoo with no savegame still has a full history of
figures, and a savegame does not need any day to have been recorded.

If a run should survive being closed, call **both** at the end of the day:

```python
storage.save_day(stats, messages)     # ~3 ms
storage.save_game(zoo_state)          # ~26 ms for 50 animals
```

---

## Storing a finished day

Call once per simulation day. Both arguments are written in one transaction:
either everything lands or nothing does.

```python
storage.save_day(
    DailyStats(
        day_id=3,
        total_visitors=180,
        revenue=1260.0,
        expenses=420.0,
        avg_animal_welfare=94.0,      # 0-100
        avg_happiness=96.5,           # 0-100
        reputation_end_of_day=92,
        animals_died=0,
    ),
    [
        Event(tick_count=100, type=EventType.INFO, text="Zoo has opened."),
        Event(tick_count=2200, type=EventType.SUCCESS, text="Record attendance!"),
    ],
)
```

### `DailyStats` fields

Only `day_id` is required. Everything else defaults to `0`.

| Field | Type | Notes |
|---|---|---|
| `day_id` | int | **Required.** Which simulation day. |
| `total_visitors` | int | |
| `revenue` | float | |
| `expenses` | float | |
| `avg_animal_welfare` | float | **0–100**, otherwise `ValueError` |
| `avg_happiness` | float | **0–100**, otherwise `ValueError` |
| `reputation_end_of_day` | int | |
| `animals_died` | int | |
| `profit_loss` | — | **Do not set.** Computed by the database. |
| `created_at` | — | Set automatically. |

### `Event` fields

Only `type` and `text` are required.

| Field | Type | Notes |
|---|---|---|
| `type` | `EventType` | **Required.** `INFO`, `WARNING`, `ERROR`, `SUCCESS`. A plain string works too. |
| `text` | str | **Required.** The message body. |
| `tick_count` | int | Defaults to `0`. Orders messages within a day. |
| `entity_id` | str | Optional, e.g. `"a_01"` — points at the object concerned. |
| `details` | dict | Optional, stored as JSON. New kinds of event need no schema change. |
| `day_id` | — | Filled in by `save_day()`. Required only for `append_events()`. |
| `id` | — | Assigned by the database. |

```python
Event(
    tick_count=1480,
    type=EventType.ERROR,
    text="Giraffe 'Long Neck' has died.",
    entity_id="a_02",
    details={"cause": "starvation", "days_without_food": 3},
)
```

---

## Storing messages during the day

To keep the log safe before a day ends:

```python
storage.append_events([
    Event(day_id=3, tick_count=900, type="WARNING", text="Lion is hungry."),
])
```

Each message needs a `day_id` here, since there is no `DailyStats` to take it
from. If that day has no row yet, a placeholder is created and later
overwritten by `save_day()` — the order of the two calls does not matter.

Passing an empty list is free: it does nothing and touches no file.

### A day is written once

Reusing a `day_id` that already holds figures is refused:

```python
storage.save_day(DailyStats(day_id=2, total_visitors=200, revenue=900.0))
storage.save_day(DailyStats(day_id=2, total_visitors=300, revenue=1400.0))
# ValueError: Day 2 already holds recorded figures (200 visitors, revenue 900.0).
#             Refusing to overwrite them silently -- a repeated day_id is usually
#             a day counter that did not advance. Pass overwrite=True if
#             replacing the day is really intended.
```

That is worth the friction: overwriting would delete the first day's numbers
**and** merge both days' messages into one, and nothing afterwards would show
that a day went missing.

To replace a day on purpose:

```python
storage.save_day(stats, events, overwrite=True)
```

Two cases deliberately stay unaffected:

- **Retrying a failed call.** A failed `save_day()` rolls back completely, so
  the day is still free and the retry just works.
- **Closing a day that already has messages.** `append_events()` creates a
  placeholder row with all figures at zero; that counts as free and gets
  filled in normally.

### Append or replace

`save_day()` treats figures and messages differently, on purpose:

- **`stats` is replaced.** Calling it again for the same `day_id` overwrites
  the row instead of failing.
- **`events` are appended.** That is what lets `append_events()` store
  messages during the day without the day-end call wiping them.

So calling `save_day()` twice with the same events stores them twice. When
the day's log should become exactly what you hand in:

```python
storage.save_day(stats, events, replace_events=True)
```

A *failed* call writes nothing at all, so retrying after an error is always
safe.

---

## Reading day summaries

```python
for day in storage.get_stats(30):
    print(day.day_id, day.revenue, day.profit_loss, day.is_profitable())
```

```
1 840.0  540.0 True
2 665.0 -145.0 False
3 1260.0 840.0 True
```

Three things to know:

- **Oldest first**, so the list plots straight onto an x-axis.
- `get_stats(3)` means *the newest three entries*, not "days 1–3". If days
  are missing from the history, you get the last three **stored** days.
- The returned objects carry **figures only**. Their `events` collection is
  not loaded, because charts do not need messages and loading them makes the
  query about thirty times slower. Use `get_events()` for messages.

Need plain dictionaries?

```python
day.as_dict()
# {'day_id': 3, 'revenue': 1260.0, 'profit_loss': 840.0, ...}
```

Every model object has `as_dict()`. Enums become strings and timestamps
become ISO strings, so the result survives `json.dumps`.

---

## Reading messages

```python
for message in storage.get_events(day_id=2, limit=100):
    marker = "!" if message.is_problem() else " "
    print(marker, message.tick_count, message.type.value, message.text)
```

| Argument | Effect |
|---|---|
| `day_id=None` | across all days (default) |
| `day_id=2` | only day 2 |
| `limit=100` | the newest 100 messages, returned oldest first |

`is_problem()` is `True` for `WARNING` and `ERROR` — useful for a
"problems only" filter.

`limit` defaults to **100**. If a day produces more messages than that and
you want all of them, raise it; otherwise you silently get only the newest
hundred.

---

## Reading weekly figures

Plotting two hundred individual days is unreadable. This groups them into
weeks of seven, aggregated inside the database:

```python
for week in storage.get_weekly_summary():
    print(week["week"], week["revenue"], week["profit_loss"])
```

Keys: `week`, `days_recorded`, `total_visitors`, `revenue`, `expenses`,
`profit_loss`, `avg_animal_welfare`, `avg_happiness`, `animals_died`.

A partial week is reported rather than dropped — `days_recorded` says how
many days it actually covers.

---

## Identifiers: who assigns them

`Event.id` and `ZooState.id` are assigned by the database. `animal_id` and
`enclosure_id` are **not** — you choose them. Two reasons:

- They are text (`"a_01"`, `"e_01"`), not numbers, so there is nothing to
  auto-increment.
- More importantly, the simulation needs an identifier **before** anything is
  stored. A message can carry `entity_id="a_01"` on the first tick, hours
  before the first save. If the database handed out identifiers, a live
  animal would have none until it was written.

To get a free one, ask the savegame:

```python
animal = create_animal("penguin", animal_id=state.next_animal_id(), name="Pingu")
enclosure = Enclosure(enclosure_id=state.next_enclosure_id(), ...)
```

Both count from the **highest identifier already present**, so they keep
working after a savegame has been loaded.

> **Do not use a plain counter that restarts at one.** After loading a
> savegame it would hand out `a_01` again, and a duplicate identifier is
> destructive: the new animal would overwrite the old one instead of being
> added. `save_game()` refuses a graph containing duplicates, but
> `next_animal_id()` avoids the situation entirely.

---

## Creating the savegame objects

Five classes make up a savegame. Each one is a plain Python object: fill in
what you know, leave the rest at its default.

### Animals — `create_animal(species, **fields)`

Always use the factory rather than the classes directly. It picks the right
subclass from the species string, which is what makes an animal come back as
a `Lion` rather than a generic `Animal`.

```python
lion = create_animal(
    "lion",
    animal_id=zoo.next_animal_id(),   # required
    name="Harry",                     # required
    age_days=14,
    hp=85.0,
    hunger=20.0,
    welfare=90.0,
    is_dead=False,
    pos_x=150,
    pos_y=300,
)
```

| Field | Type | Default | Notes |
|---|---|---|---|
| `animal_id` | str | **required** | Primary key, e.g. `"a_01"` |
| `name` | str | **required** | The animal's given name |
| `age_days` | int | `0` | Age in simulation days, never negative |
| `hp` | float | `100.0` | **0–100** |
| `hunger` | float | `0.0` | **0–100**, 100 = starving |
| `welfare` | float | `100.0` | **0–100** |
| `is_dead` | bool | `False` | |
| `pos_x`, `pos_y` | int | `0` | Position on the map |
| `species` | — | from the factory | Never set it by hand |
| `enclosure_id` | — | filled automatically | Set by appending to `enclosure.animals` |

Species available out of the box: `"lion"`, `"giraffe"`, `"penguin"`. The
call is case-insensitive; an unknown species raises `ValueError`.

To ask which species exist rather than hard-coding the list:

```python
from db import known_species

known_species()          # {'lion': Lion, 'giraffe': Giraffe, 'penguin': Penguin}
sorted(known_species())  # ['giraffe', 'lion', 'penguin']
```

It reads the registry at runtime, so a species added later shows up
automatically — useful for populating a "buy animal" dropdown.

Every animal also offers:

```python
animal.PREFERRED_FOOD     # FoodType.MEAT / PLANTS / FISH — differs per species
animal.is_critical()      # True if alive and hp <= 25 or hunger >= 75
```

### Status effects — `AnimalStatusEffect`

```python
animal.status_effects = [
    AnimalStatusEffect(effect_name="Poisoned", remaining_ticks=40),
]
```

| Field | Type | Default | Notes |
|---|---|---|---|
| `effect_name` | str | **required** | Free text, e.g. `"Stressed"` |
| `remaining_ticks` | int | `0` | Never negative. `0` means it expires now |
| `id`, `animal_id` | — | automatic | |

`effect.is_expired()` returns `True` at `0`.

### Enclosures — `Enclosure`

```python
enclosure = Enclosure(
    enclosure_id=zoo.next_enclosure_id(),   # required
    name="Savanna 1",                       # required
    biome="savanna",                        # required
    capacity=8,
    cleanliness=95.0,
)
enclosure.animals = [lion, giraffe]
```

| Field | Type | Default | Notes |
|---|---|---|---|
| `enclosure_id` | str | **required** | Primary key, e.g. `"e_01"` |
| `name` | str | **required** | Display name |
| `biome` | str | **required** | Free text: `"savanna"`, `"arctic"`, … |
| `capacity` | int | `0` | Maximum animals, never negative |
| `cleanliness` | float | `100.0` | **0–100** |
| `zoo_id` | — | filled automatically | Set by appending to `zoo.enclosures` |

```python
enclosure.free_slots()    # capacity minus animals, never below 0
enclosure.is_full()       # True when no room is left
```

### Stock — `InventoryItem`

```python
zoo.inventory = [
    InventoryItem(food_type=FoodType.MEAT, amount=15),
    InventoryItem(food_type=FoodType.FISH, amount=3),
]
```

| Field | Type | Default | Notes |
|---|---|---|---|
| `food_type` | `FoodType` | **required** | `MEAT`, `PLANTS`, `FISH`, `MEDICINE`. A plain string works |
| `amount` | int | `0` | Never negative |
| `zoo_id` | — | filled automatically | |

One row per resource per savegame — a slot cannot hold `MEAT` twice.

### The savegame root — `ZooState`

```python
zoo = ZooState(
    tick_count=4500,
    game_day=3,
    time_of_day=TimeOfDay.NIGHT,
    zoo_open=False,
    money=15400.50,
    reputation=85,
    ticket_price=12.50,
)
zoo.enclosures = [enclosure]
```

| Field | Type | Default | Notes |
|---|---|---|---|
| `id` | int | assigned on save | Save slot; leave it alone unless you use several |
| `tick_count` | int | `0` | Never negative |
| `game_day` | int | `1` | Never negative |
| `time_of_day` | `TimeOfDay` | `MORNING` | `MORNING`, `NOON`, `EVENING`, `NIGHT`. A plain string works |
| `zoo_open` | bool | `True` | |
| `money` | float | `0.0` | |
| `reputation` | int | `0` | |
| `ticket_price` | float | `0.0` | Never negative |
| `created_at` | — | automatic | Real-world timestamp of the save |

```python
zoo.total_animals()       # across all enclosures
zoo.next_animal_id()      # a free identifier
zoo.next_enclosure_id()
```

### How they link together

Assign the lists; the foreign keys follow on their own.

```
ZooState
  ├── inventory   = [InventoryItem, ...]
  └── enclosures  = [Enclosure, ...]
                      └── animals = [Animal, ...]
                                      └── status_effects = [AnimalStatusEffect, ...]
```

You never set `enclosure_id` on an animal, `zoo_id` on an enclosure or
`animal_id` on an effect. Appending to the parent's list is enough.

---

## Saving a complete zoo

You build the object graph, the module stores it — in one transaction, so an
interrupted save cannot leave half a zoo behind.

```python
from db import ZooState, Enclosure, InventoryItem, AnimalStatusEffect
from db import TimeOfDay, FoodType, create_animal

state = ZooState(
    tick_count=4500,
    game_day=3,
    time_of_day=TimeOfDay.NIGHT,     # or the plain string "NIGHT"
    zoo_open=False,
    money=15400.50,
    reputation=85,
    ticket_price=12.50,
)

state.inventory = [
    InventoryItem(food_type=FoodType.MEAT, amount=15),
    InventoryItem(food_type=FoodType.FISH, amount=3),
]

enclosure = Enclosure(
    enclosure_id="e_01",
    name="Savanna 1",
    biome="savanna",
    capacity=8,
    cleanliness=95.0,
)

lion = create_animal(                 # picks the right subclass from the string
    "lion",
    animal_id="a_01",
    name="Hungry Harry",
    age_days=14,
    hp=85.0,
    hunger=20.0,
    welfare=90.0,
    pos_x=150,
    pos_y=300,
)
lion.status_effects = [
    AnimalStatusEffect(effect_name="Stressed", remaining_ticks=40)
]

enclosure.animals = [lion]
state.enclosures = [enclosure]

slot = storage.save_game(state)       # -> 1
```

You never set `enclosure_id` on an animal or `zoo_id` on an enclosure —
appending to the list is enough, the links are filled in automatically.

Saving into an occupied slot **replaces** it completely, so animals that were
sold or died really disappear.

---

## Loading a zoo

```python
state = storage.load_game(1)

if state is None:
    ...                                   # empty slot
else:
    print(state.game_day, state.money, state.total_animals())

    for enclosure in state.enclosures:
        print(enclosure.name, enclosure.free_slots(), "slots free")
        for animal in enclosure.animals:
            print(type(animal).__name__)     # Lion / Giraffe / Penguin
            print(animal.PREFERRED_FOOD)     # MEAT / PLANTS / FISH
            print(animal.is_critical())      # needs attention?
```

Animals come back as their **species subclass**, resolved from the stored
`species` value. No `if species == "lion"` chain is needed anywhere.

The whole graph is loaded before `load_game()` returns, so you can walk it
freely afterwards — in **both** directions:

```python
animal.enclosure.name          # upwards: which enclosure?
animal.enclosure.zoo.game_day  # upwards: which savegame?
enclosure.animals              # downwards
```

---

## Finding one specific animal

There is no `get_animal(id)` — animals are stored as part of a savegame, so
you load the zoo and pick the one you want:

```python
state = storage.load_game(1)

# every animal, across all enclosures
all_animals = [a for e in state.enclosures for a in e.animals]

# by id
harry = next(a for a in all_animals if a.animal_id == "a_01")

# by name
harry = next(a for a in all_animals if a.name == "Harry")

# by condition
needs_help = [a for a in all_animals if a.is_critical()]
hungry_lions = [a for a in all_animals if a.PREFERRED_FOOD == FoodType.MEAT
                and a.hunger > 50]
```

`next(...)` raises `StopIteration` if nothing matches. To get `None` instead:

```python
harry = next((a for a in all_animals if a.animal_id == "a_01"), None)
```

---

## Changing an animal and saving again

Load, change, save — the normal cycle:

```python
state = storage.load_game(1)

harry = next(a for a in state.enclosures[0].animals if a.animal_id == "a_01")
harry.hunger = 95.0
harry.hp = 20.0

storage.save_game(state)          # same graph back in
```

Removing an animal works the same way — take it out of the list and save:

```python
enclosure.animals = [a for a in enclosure.animals if a.animal_id != "a_02"]
storage.save_game(state)          # a_02 and its status effects are gone
```

Saving replaces the slot completely, so removed animals really disappear
rather than lingering in the database.

---

## Managing save slots

```python
storage.list_saves()
# [{'id': 1, 'game_day': 3, 'money': 15400.5, 'reputation': 85,
#   'created_at': '2026-08-02T21:04:28'}]

storage.delete_save(1)      # True if it existed, False otherwise
```

Deleting a slot removes its enclosures, animals and status effects with it.

---

## Lifecycle

```python
with ZooDatabase() as storage:
    storage.save_day(stats)
# closed automatically, even if an exception was raised
```

Or manually:

```python
storage = ZooDatabase()
...
storage.close()
```

`reset()` deletes everything and recreates empty tables — for tests and for a
"new game" action, never during normal operation.

---

## Adding an animal species

Three lines in `db/models/animal.py`:

```python
class Elephant(Animal):
    """Herbivore."""
    PREFERRED_FOOD = FoodType.PLANTS
    __mapper_args__ = {"polymorphic_identity": "elephant"}
```

Then export it in `db/models/__init__.py`. No migration, no new table.
`create_animal("elephant", ...)` works immediately, and loading an elephant
returns an `Elephant`.

---

## Testing against this module

```python
storage = ZooDatabase(":memory:")
```

A real SQLite database that lives in RAM and disappears when the process
ends. Real SQL, real constraints, real cascades — no file, no cleanup, no
leftovers between tests, and no mocking needed.

---

## Errors and what they mean

| Message | Cause | Fix |
|---|---|---|
| `ValueError: avg_animal_welfare must be between 0 and 100` | A percentage out of range | Fix the value at its source |
| `ValueError: type='PANIC' is not a valid EventType` | Unknown message type | Use `INFO`, `WARNING`, `ERROR` or `SUCCESS` |
| `ValueError: profit_loss is computed by the database` | `profit_loss` was passed in | Set `revenue` and `expenses`; the value appears on read |
| `ValueError: Day 2 already holds recorded figures` | The same `day_id` twice | Advance your day counter, or pass `overwrite=True` if intended |
| `ValueError: Duplicate animal_id 'a_01'` | The same identifier twice in one savegame | Use `zoo.next_animal_id()` |
| `ValueError: Unknown species 'dragon'` | No class for that species | Add the class (see above) |
| `InvalidRequestError: 'DailyStats.events' is not available` | Reading `.events` on a `get_stats()` result | Use `get_events()` |
| `IntegrityError: FOREIGN KEY constraint failed` | An event references a day that does not exist | Use `save_day()`, or let `append_events()` create the placeholder |
| `ModuleNotFoundError: No module named 'db'` | Started from the wrong directory | Run from the repository root |

---

## Performance

Measured on Python 3.14 with SQLite 3.53:

| Operation | Cost |
|---|---|
| `save_day()` with 50 messages | ~3 ms |
| `save_day()` with 200 messages | ~9.5 ms |
| `get_stats(30)` | ~0.5 ms |
| `get_events(100)` | ~0.7 ms |
| `get_weekly_summary()` | ~0.4 ms |

The module is designed to be written **once per simulation day**, not per
tick. A simulation running at 20 ticks per second has a 50 ms budget per
tick; a day transition costs about 3 ms of that, once every few thousand
ticks.

Storing full state on every tick was considered and rejected: at 20 ticks/s
and ~170 rows per tick that is 12 million rows per hour of play, and the
writing alone would exceed the tick budget. See
[`architecture.md`](architecture.md), section "When is data written".

---

## Advanced: `Base`

`Base` is the declarative base class every model inherits from. It is
exported for completeness and for type hints — normal use never needs it.

Two things it is good for:

```python
from db import Base, DailyStats

storage.count_rows(DailyStats)      # takes any model class; handy in tests
Base.metadata.tables.keys()         # the seven table names
```

`count_rows()` is a diagnostic helper on `ZooDatabase` and deliberately not
part of `AbstractPersistence`: it exposes the table structure, which the
contract does not promise.

---

## Where to look next

| Document | Contents |
|---|---|
| [`architecture.md`](architecture.md) | Design decisions, layering, limitations |
| [`uml_class_diagram.md`](uml_class_diagram.md) | Class diagrams |
| [`uml_er_diagram.md`](uml_er_diagram.md) | Database schema |
| [`uml_sequence_diagrams.md`](uml_sequence_diagrams.md) | What happens on each call |
| [`test_plan.md`](test_plan.md) | Test strategy and cases |

Every method is documented in full — arguments, return value, exceptions and
test cases — in
[`../interface/persistence_port.py`](../interface/persistence_port.py).
For a working example of everything above, run `python -m db.demo`.
