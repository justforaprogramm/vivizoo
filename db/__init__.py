"""Database module of the vivizoo project.

Everything a caller needs is re-exported here, so a
single import line is enough::

    from db import ZooDatabase, DailyStats, Event, EventType

Package layout:

``db.interface``
    The contract: :class:`~db.interface.persistence_port.AbstractPersistence`
    and the shared enums. This is the boundary the application talks to.

``db.models``
    One class per table, including the polymorphic ``Animal`` hierarchy.
    These objects are the language callers and storage share.

``db.persistence``
    The implementation. Application code never imports from here directly;
    the entry point creates the storage object and passes it on.

The dependency direction is strictly one-way::

    caller       ->  db.interface + db.models     (never db.persistence)
    entry point  ->  db.persistence                (creates the storage object)

Quick start::

    from db import ZooDatabase, DailyStats

    with ZooDatabase(":memory:") as storage:
        storage.save_day(DailyStats(day_id=1, revenue=840.0, expenses=300.0))
        print(storage.get_stats(7)[0].profit_loss)   # -> 540.0

See ``db/README.md`` for the full guide and ``db/docs/`` for architecture,
UML diagrams and the test plan.

Part of the vivizoo project. Module owner: Jannes (database).

Authorship:
    Drafted with AI assistance and completed under a human-in-the-loop
    process: every declaration in this file was read, executed and reconciled
    with ``planning/db_planning/db_requirements.md`` before it was committed.
    ``db/docs/ai_usage.md`` records what that review covered and the ten
    defects it caught.
"""

from __future__ import annotations

# pylint: disable=duplicate-code
#   This file re-exports what ``db.interface`` and ``db.models`` already
#   export, so its ``__all__`` necessarily repeats theirs. Pylint sees three
#   near-identical name lists and reports duplicate code; here that repetition
#   *is* the feature -- it is what makes ``from db import DailyStats`` work
#   next to ``from db.models import DailyStats``. Deriving the list
#   programmatically would silence the warning at the cost of the one thing an
#   ``__all__`` is for: being readable at a glance.

from db.interface import AbstractPersistence, EventType, FoodType, TimeOfDay
from db.models import (
    Animal,
    AnimalStatusEffect,
    Base,
    DailyStats,
    Enclosure,
    Event,
    Giraffe,
    InventoryItem,
    Lion,
    Penguin,
    ZooState,
    create_animal,
    known_species,
)
from db.persistence import ZooDatabase

__all__ = [
    # Contract
    "AbstractPersistence",
    "EventType",
    "TimeOfDay",
    "FoodType",
    # Models
    "Base",
    "DailyStats",
    "Event",
    "ZooState",
    "InventoryItem",
    "Enclosure",
    "Animal",
    "Lion",
    "Giraffe",
    "Penguin",
    "AnimalStatusEffect",
    "create_animal",
    "known_species",
    # Implementation
    "ZooDatabase",
]

__version__ = "1.0.0"
