# Sequence Diagrams — Database Module

> **Authorship.** Drafted with AI assistance and completed under a
> human-in-the-loop process: reviewed, executed and reconciled with
> [`planning/db_planning/db_requirements.md`](../../planning/db_planning/db_requirements.md) before being
> committed. The process record — including the ten defects that review
> caught — is in [`ai_usage.md`](ai_usage.md).

Six interactions, from the first call down to the database file. Together they
cover every path through the module.

`Caller` stands for whatever code uses this module — in this project the
backend's `DbGateway`, but the module neither knows nor cares.

Every diagram is traced against the implementation: each step on a
`ZooDatabase` lifeline corresponds to a statement in
`persistence/zoo_database.py`, and steps on any other lifeline belong to the
participant they are drawn on. The table at the end names the exact method and
module each diagram was checked against, so the claim can be verified rather
than taken on trust.

1. [End of day — writing](#1-end-of-day)
2. [A repeated day is refused](#2-a-repeated-day-is-refused)
3. [Reading day summaries](#3-reading-day-summaries)
4. [Saving a game](#4-saving-a-game)
5. [Loading a game](#5-loading-a-game)
6. [Start-up](#6-start-up)

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
    APP->>Q: drain the message queue
    Q-->>APP: list[Event] (the day's messages)

    APP->>APP: DailyStats(day_id=3, revenue=..., ...)
    Note right of APP: @validates runs immediately.<br/>An out-of-range percentage<br/>raises here, not later.

    APP->>PER: save_day(stats, events)
    activate PER

    PER->>SES: begin()
    activate SES
    Note right of SES: BEGIN TRANSACTION

    PER->>PER: _assert_day_is_free(session, day_id)
    Note right of PER: raises if the day already<br/>holds figures — see diagram 2

    PER->>SES: merge(stats)
    PER->>SES: flush()
    SES->>DB: INSERT INTO daily_stats ...

    opt replace_events=True
        PER->>SES: delete(Event).where(day_id == ...)
        PER->>SES: flush()
        Note right of SES: the day's log becomes exactly<br/>what was handed in
    end

    loop for each event
        PER->>SES: add(event), day_id filled in from stats if missing
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
can never leave a day without its events, or events pointing at a day that does
not exist. Because a failed call writes *nothing*, retrying after an error is
safe.

**Messages append by default.** That is what lets `append_events()` flush the
queue during the day without the day-end call wiping those messages. Pass
`replace_events=True` for the opposite behaviour.

---

## 2. A repeated day is refused

Split out because it is the one call that can fail on input that looks
perfectly correct, and because the reason is not obvious from the signature.

```mermaid
sequenceDiagram
    autonumber
    participant APP as Caller
    participant PER as ZooDatabase
    participant SES as Session
    participant DB as zoo.sqlite

    APP->>PER: save_day(DailyStats(day_id=2, ...))
    activate PER
    PER->>SES: begin()
    activate SES

    PER->>SES: get(DailyStats, 2)
    SES->>DB: SELECT * FROM daily_stats WHERE day_id = 2

    alt no row — the day is free
        DB-->>SES: nothing
        PER->>PER: proceed as in diagram 1
    else row exists, every figure still 0
        DB-->>SES: placeholder row
        Note right of PER: created by append_events() when<br/>messages arrived before the day<br/>was closed — fill it in
        PER->>PER: proceed as in diagram 1
    else row exists and holds figures
        DB-->>SES: 200 visitors, revenue 900.0
        PER-->>APP: raise ValueError
        Note right of PER: ROLLBACK — nothing written.<br/>A repeated day_id is nearly always<br/>a day counter that did not advance.
    end

    deactivate SES
    deactivate PER
```

**Why refuse rather than overwrite.** Overwriting is silently destructive in
two ways at once: the earlier day's figures disappear, *and* both days'
messages end up merged under one `day_id`. Nothing afterwards reveals that a
day went missing. `overwrite=True` is there for when replacing a day really is
intended.

Two cases deliberately stay unaffected:

- **Retrying a failed call.** A failed `save_day()` rolls back completely, so
  the day is still free and the retry just works.
- **Closing a day that already has messages.** The placeholder row created by
  `append_events()` counts as free and gets filled in normally.

> **One edge case, stated plainly.** A real day on which every figure happened
> to be zero is indistinguishable from a placeholder, so it carries no
> overwrite protection. Telling the two apart would need a marker column, which
> would change the agreed schema. See [`architecture.md`](architecture.md), §7.

---

## 3. Reading day summaries

```mermaid
sequenceDiagram
    autonumber
    participant APP as Caller
    participant UI as Chart / view
    participant PER as ZooDatabase
    participant SES as Session
    participant DB as zoo.sqlite

    APP->>PER: get_stats(30)
    activate PER

    PER->>SES: open session (read-only)
    activate SES
    PER->>SES: select(DailyStats)<br/>.options(raiseload(events))<br/>.order_by(day_id DESC).limit(30)
    Note right of PER: raiseload suppresses loading<br/>the messages — charts need<br/>figures. 15.6 ms -> 0.5 ms

    SES->>DB: SELECT * FROM daily_stats<br/>ORDER BY day_id DESC LIMIT 30
    DB-->>SES: up to 30 rows
    SES-->>PER: DailyStats objects
    deactivate SES

    PER->>PER: reversed(rows)
    Note right of PER: chronological order —<br/>plots straight onto an x-axis

    PER-->>APP: list[DailyStats]
    deactivate PER

    APP->>APP: [day.as_dict() for day in days]
    APP->>UI: JSON-friendly dicts
    UI->>UI: plot the figures
```

**Key point:** the objects stay usable after the session closes
(`expire_on_commit=False`). Callers never have to think about sessions.

Reading `.events` on one of these results raises a clear SQLAlchemy error
rather than silently returning an empty list — `get_events()` is the way to
read messages.

---

## 4. Saving a game

One call writes a four-level object tree.

```mermaid
sequenceDiagram
    autonumber
    participant APP as Caller
    participant PER as ZooDatabase
    participant SES as Session
    participant DB as zoo.sqlite

    APP->>APP: player clicks "Save"
    APP->>APP: build ZooState graph<br/>(inventory, enclosures, animals, effects)
    Note right of APP: create_animal("lion", ...)<br/>picks the right subclass

    APP->>PER: save_game(zoo_state)
    activate PER

    PER->>PER: slot = zoo_state.id or DEFAULT_SLOT
    PER->>PER: _assert_unique_ids(zoo_state)
    Note right of PER: two animals sharing an id would<br/>silently overwrite one another —<br/>raises ValueError instead

    PER->>SES: begin()
    activate SES

    PER->>SES: delete(ZooState).where(id == slot)
    SES->>DB: DELETE FROM zoo_state WHERE id = 1
    Note right of DB: ON DELETE CASCADE removes<br/>inventory, enclosures, animals<br/>and status effects
    PER->>SES: flush()
    PER->>SES: expunge_all()
    Note right of SES: detach whatever the delete<br/>left in the identity map

    PER->>SES: merge(zoo_state)
    SES->>DB: INSERT INTO zoo_state ...
    SES->>DB: INSERT INTO enclosures ...
    SES->>DB: INSERT INTO inventory ...
    SES->>DB: INSERT INTO animals ...
    SES->>DB: INSERT INTO animal_status_effects ...
    Note right of SES: cascades write the whole tree,<br/>foreign keys are filled automatically

    SES->>SES: COMMIT
    deactivate SES

    PER-->>APP: slot number (int)
    deactivate PER
```

**Why delete before insert:** merging into the existing slot would leave behind
animals the player had sold or that had died. The save would slowly accumulate
ghosts. Delete and insert share one transaction, so an interrupted save cannot
destroy the old one.

**Why `merge()` and not `add()`:** the graph handed in has very often just come
back from `load_game()` — load, play, save is *the* normal cycle. Such a graph
still carries its database identity, so `add()` would treat it as an existing
row and emit `UPDATE` statements against rows this same transaction had just
deleted. `expunge_all()` followed by `merge()` handles a freshly built graph
and a loaded one identically.

---

## 5. Loading a game

```mermaid
sequenceDiagram
    autonumber
    participant APP as Caller
    participant PER as ZooDatabase
    participant SES as Session
    participant DB as zoo.sqlite

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

        PER->>PER: _resolve_parent_links(state)
        Note right of PER: touches animal.enclosure and<br/>enclosure.zoo while the session is<br/>open — identity-map hits only,<br/>no extra queries

        SES-->>PER: fully populated ZooState
        PER-->>APP: ZooState

        APP->>APP: rebuild simulation objects from the graph
    end

    deactivate SES
    deactivate PER
```

**Key point:** the whole tree is loaded before the session closes, so the graph
can be walked freely afterwards — **in both directions**. `animal.enclosure`
works, not just `enclosure.animals`. Without `_resolve_parent_links` the upward
direction would raise `DetachedInstanceError`, because SQLAlchemy stops
eager-loading as soon as relationships form a cycle.

And `type(animal).__name__` really is `"Lion"` — the database resolved the
inheritance itself.

---

## 6. Start-up

The one moment storage is created. Everything after it is independent of which
implementation was chosen.

```mermaid
sequenceDiagram
    autonumber
    participant MAIN as Entry point
    participant FAC as engine_factory
    participant PER as ZooDatabase
    participant DB as zoo.sqlite
    participant APP as Caller

    MAIN->>PER: ZooDatabase()
    activate PER

    PER->>FAC: create_db_engine(None)
    FAC->>FAC: default_database_path()
    Note right of FAC: resolved from the module location,<br/>not the working directory
    FAC->>FAC: register "connect" listener
    FAC-->>PER: Engine

    PER->>PER: register_views(Base.metadata)
    Note right of PER: guarded — attaching twice would<br/>pile up duplicate DDL listeners
    PER->>DB: CREATE TABLE IF NOT EXISTS ... (x7)
    PER->>DB: CREATE VIEW IF NOT EXISTS ... (x2)
    Note right of DB: On first connect the listener runs:<br/>PRAGMA foreign_keys=ON<br/>PRAGMA journal_mode=WAL<br/>PRAGMA synchronous=NORMAL

    PER-->>MAIN: storage
    deactivate PER

    MAIN->>APP: inject storage
    Note right of APP: typed as AbstractPersistence —<br/>the caller never learns<br/>which implementation it got
    APP->>APP: run
```

**Choosing the storage** is exactly one line, at the application's entry point:

```python
storage = ZooDatabase()             # normal operation -> data/zoo.sqlite
storage = ZooDatabase(":memory:")   # tests -> nothing on disk
```

Every arrow after that point stays identical, because everything downstream is
typed against `AbstractPersistence`.

---

## Where each diagram is traced from

| Diagram | Implementation it was checked against |
|---|---|
| 1. End of day | `ZooDatabase.save_day` |
| 2. A repeated day is refused | `ZooDatabase._assert_day_is_free` |
| 3. Reading day summaries | `ZooDatabase.get_stats` |
| 4. Saving a game | `ZooDatabase.save_game`, `_assert_unique_ids` |
| 5. Loading a game | `ZooDatabase.load_game`, `_resolve_parent_links` |
| 6. Start-up | `ZooDatabase.__init__`, `engine_factory`, `views` |

Every participant used in a diagram is declared in it — Mermaid would
otherwise invent one silently, which is how a diagram drifts away from the code
without anyone noticing.
