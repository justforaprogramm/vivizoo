"""ORM models -- one Python class per database table.

Importing this package is what makes SQLAlchemy aware of every table. The
relationships between models are declared as strings (e.g.
``order_by="Event.id"``) and are only resolved once *all* classes are known,
so importing them in one place avoids ordering problems entirely.

Table overview:

======================== ============================== ====================
Table                    Class                          Purpose
======================== ============================== ====================
``daily_stats``          :class:`DailyStats`            End-of-day summary
``events``               :class:`Event`                 Chat / system log
``zoo_state``            :class:`ZooState`              Savegame root
``inventory``            :class:`InventoryItem`         Stock levels
``enclosures``           :class:`Enclosure`             Animal containers
``animals``              :class:`Animal` (+ subclasses) The animals
``animal_status_effects`` :class:`AnimalStatusEffect`   Temporary states
======================== ============================== ====================

Typical import in application code::

    from db.models import DailyStats, Event

Part of the vivizoo project. Module owner: Jannes (database).

Authorship:
    Drafted with AI assistance and completed under a human-in-the-loop
    process: every declaration in this file was read, executed and reconciled
    with ``planning/db_planning/db_requirements.md`` before it was committed.
    ``db/docs/ai_usage.md`` records what that review covered and the ten
    defects it caught.
"""

from __future__ import annotations

from db.models.base import Base, TimestampMixin
from db.models.daily_stats import DailyStats
from db.models.event import Event
from db.models.zoo_state import ZooState
from db.models.inventory import InventoryItem
from db.models.enclosure import Enclosure
from db.models.animal import (
    Animal,
    Giraffe,
    Lion,
    Penguin,
    create_animal,
    known_species,
)
from db.models.animal_status_effect import AnimalStatusEffect

__all__ = [
    "Base",
    "TimestampMixin",
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
]
