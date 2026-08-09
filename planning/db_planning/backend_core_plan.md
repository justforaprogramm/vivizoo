# 🔧 Backend Core Plan – Zoo Digital Twin

> **Authorship.** Drafted with AI assistance and completed under a
> human-in-the-loop process: this plan was agreed first and the code in
> `db/` was written against it, then checked back against it field by
> field. The process record is in [`ai_usage.md`](../../db/docs/ai_usage.md).

> **Only the absolute MVP core mechanics.**
> Everything else (upgrades, achievements, graveyard, crafting, seasons) builds ON TOP of this.

---

## 1. The Core Loop (Tick Engine)

```
┌──────────────────────────────────────────┐
│  SimulationEngine.tick()                 │
│                                          │
│  1. Update all Animals (hunger ↓, age ↑) │
│  2. Visitors spawn & pay tickets         │
│  3. Staff do jobs (feed, heal, clean)    │
│  4. Check deaths & cleanup               │
│  5. Night? → Day-end DB-save             │
│  6. Return data dict → Frontend          │
└──────────────────────────────────────────┘
```

---

## 2. Core Classes (Only the Must-Haves)

```
┌─────────────────┐      ┌──────────────────┐
│      Zoo        │──────│ SimulationEngine │
│  (Aggregation)  │      │  (Orchestration) │
└───────┬─────────┘      └──────────────────┘
        │ contains
  ┌─────┴──────────────┬──────────────┬──────────────┐
  ▼                    ▼              ▼              ▼
Enclosure[]        Employee[]     Finances      Visitor[]
  │ contains        │               │
  ▼                 ▼               ▼
Animal[]     Keeper / Veterinarian / Inventory
             AdminStaff
```

| Class | Type | Why it's core |
|-------|------|---------------|
| `Animal` (abstract) | **Base for all animals** | Hunger/HP/welfare tick down → death |
| `Lion`, `Giraffe`, `Penguin` | **Inherit Animal** | Different `digestion_rate`, `food_type` |
| `Enclosure` | **Container for animals** | Capacity, biome check |
| `Visitor` | **Visitor entity** | X/Y coordinates, `remaining_ticks` (lifetime), pays ticket on spawn |
| `Zoo` | **Root aggregate** | Holds all: enclosures[], staff[], finances, inventory, visitors[] |
| `Finances` | **Budget manager** | `budget +=` from tickets, `budget -=` from purchases |
| `Inventory` | **Resource storage** | Dict of `{food_type: amount}`; tracks expiry per stack → `StatusEffect.Poisoned` |
| `Food` / `Item` | **Base for consumables** | Fields: `type`, `amount`, `purchase_tick` (age), `is_spoiled()` check |
| `StatusEffect` | **State modifier** | Fields: `name`, `tick_interval`, `hp_drain`, `remaining_ticks`; applied to Animal |
| `Employee` (abstract) | **Staff base** | `work(zoo)` |
| `Keeper` | **Feeds & cleans** | Checks hunger → deducts from inventory |
| `Veterinarian` | **Heals animals** | Restores HP, removes status effects |
| `AdminStaff` | **Manages budget** | Adjusts ticket price, oversees finances |
| `Behaviour` (abstract) | **Behaviour strategy** | Composable behaviour for Animal (Strategy Pattern) |
| `FeedingBehaviour` | **Eating behaviour** | What & how much the animal eats; implements `Behaviour` |
| `RestingBehaviour` | **Sleep behaviour** | Day/night sleep patterns; implements `Behaviour` |
| `EnvironmentFactor` | **Environmental influence** | Fields: `weather` (rain/sun), `temperature`; modifies `welfare` & `Visitor` spawn rate |
| `EventScheduler` | **Random & timed events** | Checks each tick: small chance for staff accident, animal illness, weather change |
| `SimulationEngine` | **The heartbeat** | `tick()` loop, `start()`, `pause()`, `set_speed()` |
| `MessageLogger` | **Chatlog feed** | Singleton, collects events → flushed to frontend |

---

## 3. Core Resource Cycle (THE Game Loop)

```
     ┌─────────┐
     │  BUDGET  │◄──────────────────────┐
     └────┬─────┘                       │
          │ buys                        │
          ▼                             │
     ┌─────────┐    feeds   ┌────────┐  │
     │  FOOD    │──────────►│ ANIMAL │  │
     │(Inventory)│           └───┬────┘  │
     └─────────┘                │       │
                                │ happy │
                                ▼       │
     ┌─────────────┐    ┌──────────┐   │
     │  VISITORS   │◄───│ WELFARE  │   │
     │ (pay ticket)│    │ (health) │───┘
     └─────────────┘    └──────────┘
```

**Translation:**
1. Money buys food
2. Food keeps animals alive & happy
3. Happy animals attract visitors
4. Visitors pay tickets → money returns

---

## 4. Minimal API (What Frontend Needs)

> **Critical:** `tick()` only computes logic. The frontend uses **separate polling** via `get_game_state()` to render. This decouples the physics loop from the PyQt render loop.

### Engine Control (all Phase 1)

| Method | Input | Output | Purpose |
|--------|-------|--------|---------|
| `engine.start()` | – | – | Begins internal tick timer |
| `engine.pause()` | – | – | Freezes tick counter |
| `engine.tick()` | – | – | **Computes one logic step only** (no return value) |
| `engine.set_speed(multiplier: float)` | `float` | – | 1.0 = normal, 2.0 = double speed |
| `get_game_state()` | – | `dict` | **Returns full current snapshot** for UI rendering (see payload below) |
| `get_entity_info(entity_id: str)` | `str` | `dict` | Returns `animal_hover_data` or `enclosure_hover_data` for tooltip popups |
| `get_chat_messages()` | – | `list[dict]` | Returns new chat entries since last call (flush) |

### Player Actions (God Mode)

```python
# Signature: execute_action(action_name: str, **kwargs) -> ActionResult
```

| Action | Call | kwargs | Effect |
|--------|------|--------|--------|
| **Feed all** | `execute_action("feed_all")` | – | Iterates all animals, deducts from inventory, returns report |
| **Feed one** | `execute_action("feed_one")` | `animal_id="a_01"` | Feeds a single animal |
| **Heal** | `execute_action("heal")` | `animal_id="a_01"` | Veterinarian restores HP, removes one status effect |
| **Buy food** | `execute_action("buy_food")` | `type="MEAT", amount=10` | Deducts budget, adds to inventory |
| **Buy animal** | `execute_action("buy_animal")` | `species="penguin"` | Deducts budget, spawns Animal in default Enclosure |
| **Clean** | `execute_action("clean")` | `enclosure_id="e_03"` | Resets enclosure cleanliness |

### Analytics (Phase 2+)

| Method | Input | Output | Purpose |
|--------|-------|--------|---------|
| `get_stats(days_back: int)` | `int` | `list[dict]` | Aggregated numbers for calendar graphs |

### Action Result Format (returned by every `execute_action`)

```python
{
    "success": True,
    "message": "All animals in enclosure 'Savanna 1' fed. Food used: 5x meat.",
    "chat_entries": [
        {"type": "INFO", "text": "5x meat removed from inventory."}
    ]
}
```

### game_state_data Payload (must include inventory)

```python
game_state_data = {
    "system": {
        "tick_count": 4500,
        "time_of_day": "MORNING",
        "zoo_open": True
    },
    "finances": {
        "money": 15400.50,
        "reputation": 85,
        "zoo_happiness": 92
    },
    "inventory": {                # ← FRONTEND NEEDS THIS to gray out buttons!
        "MEAT": 15,
        "PLANTS": 0,
        "FISH": 3
        # "MEDICINE" added in Phase 2 when heal() exists
    },
    "animals_on_map": [
        {"id": "a_01", "species": "lion", "x": 150, "y": 300, "is_dead": False},
        {"id": "a_02", "species": "penguin", "x": 400, "y": 120, "is_dead": True}
    ],
    "visitors_on_map": [
        {"id": "v_99", "x": 50, "y": 80}
    ]
}
```

### Hover-Info Payload (on request per entity)

```python
animal_hover_data = {
    "name": "Hungry Harry",
    "species": "Lion",
    "age_days": 14,
    # "stage" field added in Phase 3 (baby/growth); all animals are adults in Phase 1-2
    "hp": 85,
    "hunger": 20,
    "welfare": 90,
    "status_effects": ["Slightly hungry", "Stressed"]
}
```

### Chatlog Payload (flushed each tick)

```python
chatlog_data = [
    {"time": "08:15", "type": "INFO", "text": "Zoo has opened."},
    {"time": "09:30", "type": "WARNING", "text": "Hungry Harry is starving!"}
]
```

---

## 5. Database Tables

> **Owned by the database module.** The authoritative specification
> is `planning/db_planning/db_requirements.md`; the implementation lives in
> `db/`. The tables below are the ones the backend actually touches.

The backend does **not** write SQL. It builds model objects and passes them
to an object implementing `AbstractPersistence`:

```python
from db.interface import AbstractPersistence
from db.models import DailyStats, Event

class SimulationEngine:
    def __init__(self, zoo: Zoo, persistence: AbstractPersistence) -> None:
        self._persistence = persistence

    def _on_day_end(self) -> None:
        """Called once per simulation day, at the end of the night phase."""
        self._persistence.save_day(
            DailyStats(
                day_id=self._zoo.current_day,
                total_visitors=self._visitors_today,
                revenue=self._revenue_today,
                expenses=self._expenses_today,
                avg_animal_welfare=self._zoo.average_welfare(),
                avg_happiness=self._zoo.average_happiness(),
                reputation_end_of_day=self._zoo.reputation,
                animals_died=self._deaths_today,
            ),
            self._message_logger.drain(),
        )
```

### Table: `daily_stats`
| Column | Type |
|--------|------|
| day_id | INT PK |
| total_visitors | INT |
| revenue | FLOAT |
| expenses | FLOAT |
| profit_loss | FLOAT (generated: revenue - expenses) |
| avg_animal_welfare | FLOAT |
| avg_happiness | FLOAT |
| reputation_end_of_day | INT |
| animals_died | INT |
| created_at | DATETIME |

### Table: `events`
| Column | Type |
|--------|------|
| id | INT PK |
| day_id | INT FK |
| tick_count | INT |
| type | STRING (INFO / WARNING / ERROR / SUCCESS) |
| text | STRING |
| entity_id | STRING (optional) |
| details | JSON (optional) |

### Savegame tables (Phase 3)

`zoo_state`, `inventory`, `enclosures`, `animals`, `animal_status_effects`.
Written through a single `save_game(zoo_state)` call; the backend builds the
object graph, the database persists it in one transaction. Full column lists
in `db_requirements.md`.

---

## 6. Phased Implementation Plan

### Phase 1 – Prototype MVP (NOW)

**Goal:** The hunger→feed→death loop works end-to-end. Backend returns `get_game_state()` dict. Frontend renders one animal, one button, one budget counter.

**What to build FIRST:**

| Priority | Feature | Why |
|----------|---------|-----|
| 🔴 | `Animal` (+3 species), `Enclosure`, `Zoo`, `Finances`, `Inventory` | Core data model |
| 🔴 | `SimulationEngine.tick()` with throttled hunger/HP updates | The heartbeat |
| 🔴 | `get_game_state()` + `get_entity_info()` + `get_chat_messages()` | Frontend can render |
| 🔴 | `execute_action("feed_one")`, `execute_action("buy_food")` | Player can interact |
| 🔴 | `Visitor` spawn/despawn + ticket payment | Money comes in |
| 🔴 | `MessageLogger` (in-memory list) | Chatlog works |
| 🔴 | **`persistence.save_day()` wired into the day-end** | Otherwise the database module is invisible in the submission |
| 🟡 | `Food` class with `is_spoiled()` stub (always False) | Prepares for Phase 2 |
| 🟡 | `zoo_open: bool` (NO multi-phase day/night system yet) | Simple open/closed toggle |

**What to SKIP in Phase 1 (stub or hardcode):**

| Feature | Phase 1 approach |
|---------|-----------------|
| 4-Phase `time_of_day` (morning/noon/evening/night) | `zoo_open = True` always |
| Aggregate metrics (`welfare`, `reputation`, `zoo_happiness`) | Stub → return `0.0` or `100.0` |
| Visitor random walk / pathfinding | Spawn, set `remaining_ticks`, despawn only |
| Staff auto-jobs (Keeper/Veterinarian) | Player uses God Mode via `execute_action` |
| `Behaviour` composition (FeedingBehaviour etc.) | Hardcode eating into `Animal.feed()` |
| `EnvironmentFactor` weather | Stub → always "sun", no effect |
| `EventScheduler` random events | Stub → `check_events()` always returns `[]` |
| `stage: "adult"` in hover | Remove field entirely; all animals are adults by default |
| `MEDICINE` in inventory | Remove; no healing mechanic yet |

> **Changed from the original plan:** `save_day()` and `append_events()` are
> **not** stubbed. They are one call each, cost about 3 ms per simulation
> day, and without them the database contributes nothing observable to the
> running application. `get_stats()` may stay stubbed until the frontend has
> charts.

---

### Phase 2 – Biological Depth (build NEXT)

Once the prototype loop is stable:

| Feature | What to add |
|---------|-------------|
| `StatusEffect` class with tick updates | `Hungry`, `Poisoned`, `Malnourished`, `Stressed` |
| `Food.is_spoiled()` real logic | Tracks `purchase_tick`; triggers `Poisoned` on feed |
| `Behaviour` abstract + `FeedingBehaviour` / `RestingBehaviour` | Strategy Pattern; composable per species |
| `EnvironmentFactor` (weather/temperature) | Affects `welfare` and visitor spawn rate |
| `EventScheduler` real implementation | 1% chance/tick: staff accident, animal illness, weather change |
| `Veterinarian` subclass working | `execute_action("heal", id)` removes effects, restores HP |
| `AdminStaff` subclass | Adjusts ticket price, affects reputation |
| `MEDICINE` in inventory | Required for `heal` action |
| 4-phase `time_of_day` cycle | Night = no visitors, different animal behaviour |
| `get_stats()` wired to the database | Frontend charts go live |

---

### Phase 3 – Tycoon Depth (build LAST)

All the features that depend on Phase 1+2 being rock-solid:

| Feature | Description |
|---------|-------------|
| Baby animals / growth stages | `stage: "baby"` → timer → `"adult"` |
| Upgrade system (enclosure level) | Level 1→2 increases capacity |
| Ticket price elasticity | Higher price = fewer visitors (demand formula) |
| Graveyard / cremation / urns | Death cleanup workflow |
| Drag & drop God Mode | Move animals between enclosures |
| Decoration placement | Fixed-node system (fountain_centre etc.) |
| Restaurant / crafting | Special food buffs |
| Season events / festivals | Timed buffs (festival of lights) |
| Achievements & titles | Milestone tracking + badges |
| Lighting upgrades | Extended opening hours |
| Savegame persistence | `save_game(zoo_state)` / `load_game(slot)` — already implemented in `db/` |

**All of the above are features that depend on the core running first.**

---

## 7. Milestone 1 – Absolute Minimum Test

```
1 Animal (Lion)  → hunger ticks down
1 Button         → "Feed"
1 Budget check   → enough money?
1 Death trigger  → hunger = 0 for 3 days → dead
1 UI readout     → hunger, HP, budget numbers
```

**If this loop works end-to-end, the architecture is correct.**

---

## 8. Tick Update Frequency – What to Compute When

> Not every attribute of every entity needs recalculation **each tick**. Throttle to save CPU and keep the loop lean.

### Update Matrix

| Entity / Attribute | Frequency | Trigger / Threshold | Why |
|-------------------|-----------|---------------------|-----|
| **Animal.x, Animal.y** (movement) | **Every Tick** | Always | Smooth animation; frontend polls each frame |
| **Visitor.x, Visitor.y** | **Every Tick** (if open) | `zoo.is_open == True` | Random walk step for each active visitor |
| **Day phase** | **Every Tick** | Check `tick_counter % ticks_per_phase` | Transitions: Morning→Noon→Evening→Night |
| **Animal.hunger** | **Every N Ticks** | Every `~10 ticks` (configurable per species via `digestion_rate`) | Hunger changes slowly; a lion eating every 3 days needs 1 tick |
| **Animal.hp** | **Every N Ticks** | Only when `days_starved > 0` OR active status effect | Drains slowly; no need to compute when fully healthy |
| **Animal.welfare** | **Daily** | Tick counter hits `ticks_per_day` | Aggregate metric; changes slowly with hunger/biome |
| **Animal.age_days** | **Daily** | Tick counter hits `ticks_per_day` | Age in days, not ticks |
| **Death Check** (`is_dead`) | **Every N Ticks** | After HP update OR `days_starved` changes | Only check after relevant value changed |
| **Status Effects Tick** | **Every N Ticks** | Each active effect has its own `tick_interval` | Poison drains HP fast → check often; "wrong_climate" → check rarely |
| **Visitor Spawn** | **Per Phase / Hourly** | `tick_counter % ticks_per_spawn_window` | Batch-spawn per time window, not every tick |
| **Visitor Despawn** | **Per Tick** (sparse) | Each visitor has `remaining_ticks`; decrement & remove if 0 | Lightweight int decrement; no complex logic |
| **Staff Job Execution** | **Every N Ticks** | Every `~20 ticks` | Keeper checks hunger / cleans; not needed per tick |
| **Global Happiness Score** | **Daily** | Tick counter hits `ticks_per_day` | Aggregated from all factors; only matters for next day's visitors |
| **DB Save (day end)** | **Daily** | End of Night phase → one `save_day()` call | Single write (~3 ms), not per tick |
| **Chatlog Flush** | **Every Tick** (empty most ticks) | Always (but only sends if `message_queue` non-empty) | Frontend needs near-real-time messages; cost is near-zero when queue is empty |

### Implementation Pattern (Example)

```python
class Animal:
    TICKS_PER_HUNGER_UPDATE = 10  # override per species

    def tick_update(self, tick_counter: int) -> None:
        """Advance this animal by one tick, if it is due for an update."""
        # Guard: skip if not due for update
        if tick_counter % self.TICKS_PER_HUNGER_UPDATE != 0:
            return  # nothing to do this tick

        # Actual update logic only runs when threshold met
        self.hunger = max(0, self.hunger - self.digestion_rate)

        if self.hunger <= 0:
            self.days_starved += 1
```

### Performance Tip: Random Offset for Staggered Updates

When 500 animals all pass `tick_counter % 10 == 0` at the same tick, you get a massive CPU spike → UI lags.

**Solution:** Give each entity a random `update_offset` at spawn time:

```python
class Animal:
    TICKS_PER_HUNGER_UPDATE = 10

    def __init__(self, ...):
        self._update_offset = random.randint(0, self.TICKS_PER_HUNGER_UPDATE - 1)

    def tick_update(self, tick_counter: int) -> None:
        if (tick_counter + self._update_offset) % self.TICKS_PER_HUNGER_UPDATE != 0:
            return
        # ... update logic ...
```

This spreads the workload evenly: animal 1 updates at tick 10, 20, 30. Animal 2 at tick 11, 21, 31. Animal 3 at tick 12, 22, 32. No single tick carries all animals.

### Rule of Thumb

```
If a value changes at "day" granularity      → update once per day.
If a value changes at "hour" granularity     → update every N ticks.
If a value changes continuously AND the
frontend renders it                          → update each tick.
```
