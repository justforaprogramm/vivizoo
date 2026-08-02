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
"""

from __future__ import annotations

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
