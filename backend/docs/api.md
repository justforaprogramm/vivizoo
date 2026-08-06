# Backend API — Frontend Connection Contract

The frontend interacts with the backend through a single object,
`backend.core.engine.SimulationEngine`. This document is the contract: every
method the UI may call, its parameters, and the exact shapes of the returned
data. Keep this file in sync when the backend API changes.

---

## Bootstrap

```python
from backend.core.zoo import Zoo
from backend.core.message_logger import MessageLogger
from backend.core.engine import SimulationEngine
from backend.persistence.db_gateway import DbGateway   # optional
from db import ZooDatabase                              # optional

logger = MessageLogger.instance()          # singleton chat feed
zoo    = Zoo(name="My Zoo", logger=logger)

# optional persistence (day summaries + chat log to SQLite)
gateway = DbGateway(ZooDatabase(":memory:"))

engine  = SimulationEngine(zoo, persistence=gateway, logger=logger)
engine.start()
```

> **Tip:** Give `engine.release_thread()`-free design by letting the engine
> own its background thread; call `engine.pause()` to freeze and
> `engine.set_speed()` to re-tune.

---

## Methods

### `engine.start()`
Begin ticking on a daemon background thread. No-op if already running.

### `engine.pause()`
Freeze the tick counter (e.g. when the app loses focus).

### `engine.set_speed(multiplier: float)`
Change the simulation speed. `1.0` is normal, `2.0` is double. Raises
`ValueError` if not positive.

### `engine.get_game_state() -> dict`
The full snapshot the UI renders each frame.

```jsonc
{
  "system": {
    "tick_count": 480,
    "time_of_day": "NIGHT",           // MORNING | NOON | EVENING | NIGHT
    "zoo_open": false
  },
  "finances": {
    "money": 9421.5,
    "revenue": 620.0,
    "expenses": 88.0,
    "ticket_price": 12.5
  },
  "inventory": {
    "MEAT": 15,
    "PLANTS": 4,
    "FISH": 7,
    "MEDICINE": 0
  },
  "animals_on_map": [
    { "id": "a_01", "species": "lion", "x": 302, "y": 198, "is_dead": false }
  ],
  "visitors_on_map": [
    { "id": "v_001", "x": 51, "y": 49 }
  ]
}
```

### `engine.get_entity_info(entity_id: str) -> dict`
Tooltip / hover payload for one entity.

For an **animal**:

```jsonc
{
  "id": "a_01",
  "name": "Hungry Harry",
  "species": "lion",
  "age_days": 0,
  "hp": 100.0,
  "hunger": 41.0,          // 0 = full, 100 = starving
  "welfare": 62.0,
  "is_dead": false,
  "status_effects": ["Stressed"]
}
```

For an **enclosure**:

```jsonc
{ "id": "e_01", "name": "Savanna 1", "biome": "savanna",
  "cleanliness": 92.4, "free_slots": 3 }
```

Returns `{}` for an unknown id.

### `engine.get_chat_messages() -> list[dict]`
New chat entries since the last poll; the buffer is **drained** so each
message is delivered once.

```jsonc
[
  { "tick_count": 360, "type": "WARNING", "text": "Sam is stressed.",
    "entity_id": "a_02" }
]
```

### `engine.execute_action(action_name: str, **kwargs) -> dict`
Run a player action and return its result.

```jsonc
{ "success": true, "message": "Fed 2 animal(s). Food used: 1x MEAT.",
  "chat_entries": [{ "type": "SUCCESS", "text": "2 animals fed." }] }
```

**Supported actions (phase 1):**

| action | kwargs | effect |
| --- | --- | --- |
| `feed_all` | — | feed every hungry living animal (uses stock) |
| `feed_one` | `animal_id` | feed a single animal |
| `heal` | `animal_id` | heal one animal, clear a status effect |
| `buy_food` | `type` (`"MEAT"`…), `amount` | spend budget to add stock |
| `buy_animal` | `species`, `name`, `enclosure_id` | buy and place a new animal |
| `clean` | `enclosure_id` | reset an enclosure's cleanliness |

Unknown action names raise `ValueError`; failures return `success: false`.

### `engine.get_stats(days_back: int = 30) -> list[dict]`
Recent daily summaries for charts (requires a persistence gateway; otherwise
returns `[]`). Oldest first.

```jsonc
[
  { "day_id": 1, "total_visitors": 54, "revenue": 715.0, "expenses": 88.0,
    "profit_loss": 627.0, "avg_animal_welfare": 70.6, "avg_happiness": 84.0,
    "reputation_end_of_day": 80, "animals_died": 0 }
]
```

---

## Persistence relationship

The backend never runs SQL. `DbGateway` builds `db.models.DailyStats` and
`db.models.Event` from the domain and calls `AbstractPersistence.save_day()`.
This keeps the frontend and backend independent of SQLAlchemy, and satisfies
the planning's requirement that the backend *adapt to* (not extend) the
database module.
