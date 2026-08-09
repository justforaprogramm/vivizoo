# UML Class Diagrams — Database Module

> **Authorship.** Drafted with AI assistance and completed under a
> human-in-the-loop process: reviewed, executed and reconciled with
> [`planning/db_planning/db_requirements.md`](../../planning/db_planning/db_requirements.md) before being
> committed. The process record — including the ten defects that review
> caught — is in [`ai_usage.md`](ai_usage.md).

All diagrams are Mermaid and render directly on GitHub and in VS Code
(extension *Markdown Preview Mermaid Support*).

Five diagrams, each answering one question:

1. [The complete picture](#1-overview) — how everything fits together
2. [The interface](#2-interface-and-implementations) — abstraction and polymorphism
3. [The models](#3-domain-model) — inheritance, composition, aggregation
4. [The animal hierarchy](#4-animal-hierarchy) — polymorphism in detail
5. [The enumerations](#5-enumerations) — the shared value sets

These describe the **object model**: Python classes, their methods and how they
relate. For the same seven tables seen as a *database* — column types, keys,
constraints, indexes and the generated DDL — see
[`uml_db_schema.md`](uml_db_schema.md) and [`uml_er_diagram.md`](uml_er_diagram.md).

---

## 1. Overview

The layering, and the direction dependencies are allowed to run.

```mermaid
classDiagram
    direction TB

    namespace CallingCode {
        class Caller {
            <<outside this module>>
            -AbstractPersistence _storage
        }
    }

    namespace Interface {
        class AbstractPersistence {
            <<abstract>>
            +save_day(stats, events, replace_events, overwrite) None*
            +append_events(events) None*
            +get_stats(days_back) list~DailyStats~*
            +get_events(day_id, limit) list~Event~*
            +get_weekly_summary() list~dict~*
            +save_game(zoo_state) int*
            +load_game(save_id) ZooState|None*
            +list_saves() list~dict~*
            +delete_save(save_id) bool*
            +reset() None*
            +close() None*
            +__enter__() AbstractPersistence
            +__exit__(type, value, tb) bool
        }
    }

    namespace Persistence {
        class ZooDatabase {
            -Engine _engine
            -sessionmaker _session_factory
            -bool _closed
            +DEFAULT_SLOT int$
            +count_rows(model) int
            -_assert_day_is_free(session, day_id)$ None
            -_ensure_day_exists(session, day_id)$ None
            -_assert_unique_ids(zoo_state)$ None
            -_resolve_parent_links(state)$ None
        }
        class EngineFactory {
            <<module>>
            +default_database_path() Path
            +build_sqlite_url(database) str
            +create_db_engine(database, echo) Engine
            +connection_is_healthy(connection) bool
            -_apply_sqlite_pragmas(conn, record) None
        }
    }

    namespace Models {
        class Base {
            <<abstract>>
            +as_dict() dict
            +from_dict(data) Base$
            +__repr__() str
        }
    }

    Caller ..> AbstractPersistence : depends on (injected)
    AbstractPersistence <|.. ZooDatabase : realises
    ZooDatabase ..> EngineFactory : uses
    ZooDatabase ..> Base : reads and writes
    AbstractPersistence ..> Base : contract type
```

**What to read out of it:** the calling code has a dashed arrow to
`AbstractPersistence` — a dependency, not ownership. It receives the storage
object rather than constructing one, and it is typed against the abstract
class, so it never learns which implementation it got. Everything inside the
solid boxes belongs to this module.

---

## 2. Interface and implementations

Zoomed in on the abstraction. Every operation of the contract is abstract
(`*`). There is exactly one implementation, `ZooDatabase`, and it adds exactly
one public method the interface does not declare — `count_rows`, a diagnostic
helper for tests and demos rather than part of the contract.

```mermaid
classDiagram
    direction LR

    class AbstractPersistence {
        <<abstract>>
        +save_day(stats: DailyStats, events: Iterable~Event~, replace_events: bool, overwrite: bool) None*
        +append_events(events: Iterable~Event~) None*
        +get_stats(days_back: int) list~DailyStats~*
        +get_events(day_id: int, limit: int) list~Event~*
        +get_weekly_summary() list~dict~*
        +save_game(zoo_state: ZooState) int*
        +load_game(save_id: int) ZooState|None*
        +list_saves() list~dict~*
        +delete_save(save_id: int) bool*
        +reset() None*
        +close() None*
        +__enter__() AbstractPersistence
        +__exit__(exc_type, exc_value, traceback) bool
    }

    class ZooDatabase {
        +DEFAULT_SLOT: int = 1$
        -_engine: Engine
        -_session_factory: sessionmaker
        -_closed: bool
        +__init__(database, echo)
        +count_rows(model: type) int
        -_assert_day_is_free(session, day_id)$ None
        -_ensure_day_exists(session, day_id)$ None
        -_assert_unique_ids(zoo_state)$ None
        -_resolve_parent_links(state)$ None
    }

    AbstractPersistence <|.. ZooDatabase

    note for AbstractPersistence "Abstraction: 11 abstract methods,\nno implementation. Python refuses to\ninstantiate a subclass that misses one.\nThe two concrete methods (__enter__/__exit__)\nare inherited by every implementation."
    note for ZooDatabase "Stores in SQLite.\nUses Session as unit of work.\nThe only place sessions are opened\nand queries are issued.\nThe four private static methods are\nguards and helpers — not contract."
```

**Why the split matters:** callers are typed against the left-hand box and
never mention the right-hand one. Swapping the storage layer, or handing a
test an in-memory database, changes one line and nothing else.

---

## 3. Domain model

The seven tables and how they relate. Note the two kinds of diamond:

- **filled (`*--`) = composition** — the child cannot exist without the
  parent and dies with it (`cascade="all, delete-orphan"`)
- **hollow (`o--`) = aggregation** — a looser has-a relationship

```mermaid
classDiagram
    direction TB

    class Base {
        <<abstract>>
        +as_dict() dict
        +from_dict(data) Base$
        +__repr__() str
    }

    class TimestampMixin {
        <<mixin>>
        +created_at: datetime
    }

    class DailyStats {
        +day_id: int «PK»
        +total_visitors: int
        +revenue: float
        +expenses: float
        +profit_loss: float «computed»
        +avg_animal_welfare: float
        +avg_happiness: float
        +reputation_end_of_day: int
        +animals_died: int
        +is_profitable() bool
        -_check_percentage(field, value) float
        -_reject_profit_loss(field, value) float
    }

    class Event {
        +id: int «PK»
        +day_id: int «FK»
        +tick_count: int
        +type: EventType
        +text: str
        +entity_id: str
        +details: dict «JSON»
        +is_problem() bool
        -_coerce_type(field, value) EventType
    }

    class ZooState {
        +id: int «PK»
        +tick_count: int
        +game_day: int
        +time_of_day: TimeOfDay
        +zoo_open: bool
        +money: float
        +reputation: int
        +ticket_price: float
        +total_animals() int
        +next_animal_id(prefix) str
        +next_enclosure_id(prefix) str
        -_coerce_time_of_day(field, value) TimeOfDay
    }

    class InventoryItem {
        +zoo_id: int «PK, FK»
        +food_type: FoodType «PK»
        +amount: int
        -_coerce_food_type(field, value) FoodType
        -_check_amount(field, value) int
    }

    class Enclosure {
        +enclosure_id: str «PK»
        +zoo_id: int «FK»
        +name: str
        +biome: str
        +capacity: int
        +cleanliness: float
        +free_slots() int
        +is_full() bool
        -_check_cleanliness(field, value) float
    }

    class Animal {
        <<polymorphic base>>
        +PREFERRED_FOOD: FoodType$
        +animal_id: str «PK»
        +enclosure_id: str «FK»
        +name: str
        +species: str «discriminator»
        +age_days: int
        +hp: float
        +hunger: float
        +welfare: float
        +is_dead: bool
        +pos_x: int
        +pos_y: int
        +is_critical() bool
        -_check_percentage(field, value) float
    }

    class AnimalStatusEffect {
        +id: int «PK»
        +animal_id: str «FK»
        +effect_name: str
        +remaining_ticks: int
        +is_expired() bool
        -_check_remaining(field, value) int
    }

    Base <|-- DailyStats
    Base <|-- Event
    Base <|-- ZooState
    Base <|-- InventoryItem
    Base <|-- Enclosure
    Base <|-- Animal
    Base <|-- AnimalStatusEffect

    TimestampMixin <|-- DailyStats
    TimestampMixin <|-- ZooState

    DailyStats "1" *-- "0..*" Event : owns
    ZooState "1" *-- "0..*" InventoryItem : owns
    ZooState "1" *-- "0..*" Enclosure : owns
    Enclosure "1" o-- "0..*" Animal : houses
    Animal "1" *-- "0..*" AnimalStatusEffect : owns

    note for TimestampMixin "Mixin, not a table.\nContributes one column\nto several tables via\nmultiple inheritance."
    note for DailyStats "profit_loss is GENERATED\nALWAYS AS (revenue - expenses).\nComputed by the database."
```

**Composition vs aggregation, concretely:** deleting a `ZooState` deletes its
enclosures, and deleting an `Enclosure` deletes its animals — but an animal
is *housed in* an enclosure rather than being a body part of it, which is why
that edge is drawn as aggregation. In the schema both are `ON DELETE
CASCADE`; the distinction is one of meaning.

---

## 4. Animal hierarchy

The polymorphic part. All species live in one table; the `species` column
tells SQLAlchemy which class to build.

```mermaid
classDiagram
    direction TB

    class Animal {
        <<polymorphic base>>
        +PREFERRED_FOOD: FoodType = MEAT$
        +animal_id: str
        +name: str
        +species: str «discriminator»
        +hp: float
        +hunger: float
        +welfare: float
        +is_dead: bool
        +is_critical() bool
    }

    class Lion {
        +PREFERRED_FOOD = FoodType.MEAT$
        polymorphic_identity = "lion"
    }

    class Giraffe {
        +PREFERRED_FOOD = FoodType.PLANTS$
        polymorphic_identity = "giraffe"
    }

    class Penguin {
        +PREFERRED_FOOD = FoodType.FISH$
        polymorphic_identity = "penguin"
    }

    class AnimalFactory {
        <<module functions>>
        +known_species() dict~str, type~
        +create_animal(species, **fields) Animal
    }

    class FoodType {
        <<enumeration>>
        MEAT
        PLANTS
        FISH
        MEDICINE
    }

    Animal <|-- Lion
    Animal <|-- Giraffe
    Animal <|-- Penguin
    AnimalFactory ..> Animal : creates
    Animal ..> FoodType : uses

    note for Animal "Single-table inheritance:\nall species share the table 'animals'.\npolymorphic_on = species"
    note for AnimalFactory "create_animal('lion', ...) picks\nthe right class from a string.\nknown_species() reads the registry\nat runtime — a new subclass\nappears automatically."
```

**Why it matters in practice:**

```python
animals = session.scalars(select(Animal)).all()
# -> [Lion, Giraffe, Penguin, ...] — not [Animal, Animal, Animal]

for animal in animals:
    print(animal.PREFERRED_FOOD)   # MEAT / PLANTS / FISH
```

No `if species == "lion"` chain anywhere. Adding a species is three lines and
changes nothing else.

---

## 5. Enumerations

```mermaid
classDiagram
    direction LR

    class EventType {
        <<enumeration>>
        INFO
        WARNING
        ERROR
        SUCCESS
    }

    class TimeOfDay {
        <<enumeration>>
        MORNING
        NOON
        EVENING
        NIGHT
    }

    class FoodType {
        <<enumeration>>
        MEAT
        PLANTS
        FISH
        MEDICINE
    }

    Event ..> EventType : type
    ZooState ..> TimeOfDay : time_of_day
    InventoryItem ..> FoodType : food_type
    Animal ..> FoodType : PREFERRED_FOOD

    note for EventType "All inherit from str,\nso EventType.INFO == 'INFO'.\nStored as VARCHAR + CHECK."
```
