# Sequence Diagrams — Database Module

Five interactions, from the first call down to the database file. Together
they cover every path through the module.

`Caller` stands for whatever code uses this module.

1. [End of day — writing](#1-end-of-day)
2. [Reading day summaries](#2-reading-day-summaries)
3. [Saving a game](#3-saving-a-game)
4. [Loading a game](#4-loading-a-game)
5. [Start-up](#5-start-up)

---

## 1. End of day

The most frequent write. Happens once per simulation day, never per tick.

```mermaid
sequenceDiagram
    autonumber
    participant APP as Caller
    participant Q as Message queue<br/>(caller side)
    participant PER as ZooDatabase
    participant SES as Session<br/>(unit of work)
    participant DB as zoo.sqlite

    Note over APP: the simulation day has ended

    APP->>APP: calculate day figures
    APP->>Q: collect messages
    Q-->>APP: list[Event] (the day's messages)

    APP->>APP: DailyStats(day_id=3, revenue=..., ...)
    Note right of APP: @validates runs immediately.<br/>An out-of-range percentage<br/>raises here, not later.

    APP->>PER: save_day(stats, events)
    activate PER

    PER->>SES: begin()
    activate SES
    Note right of SES: BEGIN TRANSACTION

    PER->>SES: merge(stats)
    Note right of SES: INSERT OR UPDATE —<br/>saving the same day twice<br/>overwrites instead of failing
    PER->>SES: flush()
    SES->>DB: INSERT INTO daily_stats ...

    loop for each event
        PER->>SES: add(event) with day_id filled in
    end

    SES->>DB: INSERT INTO events ... (batched)
    Note right of DB: profit_loss is computed<br/>by the database itself

    SES->>SES: COMMIT
    deactivate SES
    Note right of SES: On any exception:<br/>ROLLBACK — nothing is written

    PER-->>APP: None
    deactivate PER

    Note over APP,DB: total cost ~3 ms for one day plus 50 messages
```

**Key point:** day row and messages share one transaction. A crash mid-write
can never leave a day without its events, or events pointing at a day that
does not exist.

---

## 2. Reading day summaries

```mermaid
sequenceDiagram
    autonumber
    participant APP as Caller
    participant PER as ZooDatabase
    participant SES as Session
    participant DB as zoo.sqlite

    APP->>APP: get_stats(30)
    APP->>PER: get_stats(30)
    activate PER

    PER->>SES: open session (read-only)
    activate SES
    PER->>SES: select(DailyStats)<br/>.options(raiseload(events))<br/>.order_by(day_id DESC).limit(30)
    Note right of PER: raiseload suppresses loading<br/>the messages — charts need<br/>figures. 15.6 ms -> 0.5 ms

    SES->>DB: SELECT * FROM daily_stats<br/>ORDER BY day_id DESC LIMIT 30
    DB-->>SES: 30 rows
    SES-->>PER: 30 DailyStats objects
    deactivate SES

    PER->>PER: reversed(rows)
    Note right of PER: chronological order —<br/>plots straight onto an x-axis

    PER-->>APP: list[DailyStats]
    deactivate PER

    APP->>ENG: [day.as_dict() for day in days]
    APP-->>UI: list[dict] (JSON-friendly)

    APP->>APP: plot the figures
```

**Key point:** the objects stay usable after the session closes
(`expire_on_commit=False`). Callers never have to think about sessions.

---

## 3. Saving a game

One call writes a four-level object tree.

```mermaid
sequenceDiagram
    autonumber
    participant APP as Caller
    participant PER as ZooDatabase
    participant SES as Session
    participant DB as zoo.sqlite

    APP->>APP: player clicks "Save"
    APP->>ENG: build ZooState graph<br/>(inventory, enclosures, animals, effects)
    Note right of APP: create_animal("lion", ...)<br/>picks the right subclass

    APP->>PER: save_game(zoo_state)
    activate PER

    PER->>SES: begin()
    activate SES

    PER->>SES: get(ZooState, slot)
    SES->>DB: SELECT * FROM zoo_state WHERE id = 1
    DB-->>SES: the old save (or nothing)

    alt slot already occupied
        PER->>SES: delete(old)
        SES->>DB: DELETE FROM zoo_state WHERE id = 1
        Note right of DB: CASCADE removes inventory,<br/>enclosures, animals and<br/>status effects
        PER->>SES: flush()
    end

    PER->>SES: add(zoo_state)
    SES->>DB: INSERT INTO zoo_state ...
    SES->>DB: INSERT INTO inventory ...
    SES->>DB: INSERT INTO enclosures ...
    SES->>DB: INSERT INTO animals ...
    SES->>DB: INSERT INTO animal_status_effects ...
    Note right of SES: cascades write the whole tree;<br/>foreign keys are filled automatically

    SES->>SES: COMMIT
    deactivate SES

    PER-->>APP: slot number (int)
    deactivate PER
    APP-->>UI: "Game saved"
```

**Why delete before insert:** merging instead would leave behind animals the
player had sold or that had died. The save would slowly accumulate ghosts.
Delete and insert share one transaction, so an interrupted save cannot
destroy the old one.

---

## 4. Loading a game

```mermaid
sequenceDiagram
    autonumber
    participant APP as Caller
    participant PER as ZooDatabase
    participant SES as Session
    participant DB as zoo.sqlite

    APP->>APP: player picks slot 1
    APP->>PER: load_game(1)
    activate PER

    PER->>SES: get(ZooState, 1)
    activate SES
    SES->>DB: SELECT * FROM zoo_state WHERE id = 1

    alt slot empty
        DB-->>SES: no row
        SES-->>PER: None
        PER-->>APP: None
        Note over APP: start a new game instead
    else slot occupied
        DB-->>SES: 1 row
        Note right of SES: lazy="selectin" now loads<br/>the rest, one query per level
        SES->>DB: SELECT * FROM inventory WHERE zoo_id = 1
        SES->>DB: SELECT * FROM enclosures WHERE zoo_id = 1
        SES->>DB: SELECT * FROM animals WHERE enclosure_id IN (...)
        SES->>DB: SELECT * FROM animal_status_effects WHERE animal_id IN (...)

        Note right of SES: reads the species column and<br/>builds Lion / Giraffe / Penguin
        SES-->>PER: fully populated ZooState
        deactivate SES

        PER-->>APP: ZooState
        deactivate PER

        APP->>ENG: rebuild simulation objects from the graph
        APP-->>UI: zoo restored
    end
```

**Key point:** the whole tree is loaded before the session closes, so a
caller can walk it freely. And `type(animal).__name__` really is `"Lion"` —
the database resolved the inheritance itself.

---

## 5. Start-up

The one moment storage is created. Everything after it is independent of
which implementation was chosen.

```mermaid
sequenceDiagram
    autonumber
    participant APP as Caller
    participant FAC as engine_factory
    participant PER as ZooDatabase
    participant DB as zoo.sqlite
    participant APP as Caller

    APP->>PER: ZooDatabase()
    activate PER

    PER->>FAC: create_db_engine(None)
    FAC->>FAC: default_database_path()
    Note right of FAC: resolved from the module location,<br/>not the working directory:<br/>/workspaces/vivizoo/data/zoo.sqlite
    FAC->>FAC: register "connect" listener
    FAC-->>PER: Engine

    PER->>PER: register_views(Base.metadata)
    PER->>DB: CREATE TABLE IF NOT EXISTS ... (x7)
    PER->>DB: CREATE VIEW IF NOT EXISTS ... (x2)
    Note right of DB: On first connect the listener runs:<br/>PRAGMA foreign_keys=ON<br/>PRAGMA journal_mode=WAL<br/>PRAGMA synchronous=NORMAL

    PER-->>APP: storage
    deactivate PER

    APP->>APP: pass storage into the application
    Note right of APP: typed as AbstractPersistence —<br/>the engine never learns<br/>which implementation it got

    APP-->>MAIN: engine
    APP->>APP: start
```

**Choosing the storage** is exactly one line, at the application's entry point:

```python
storage = ZooDatabase()             # normal operation -> data/zoo.sqlite
storage = ZooDatabase(":memory:")   # tests -> nothing on disk
```

Every arrow after that point in the diagram stays identical, because
everything after it is typed against `AbstractPersistence`.
