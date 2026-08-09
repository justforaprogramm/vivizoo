"""The public boundary of the database module.

Everything in this package is public API. The application imports from here (and
from :mod:`db.models`) and from nowhere else inside :mod:`db`.

Contents:
    * :class:`~db.interface.persistence_port.AbstractPersistence` -- the list
      of operations storage supports.
    * :mod:`db.interface.enums` -- the value sets used by several columns.

Typical import in application code::

    from db.interface import AbstractPersistence, EventType

Part of the vivizoo project. Module owner: Jannes (database).

Authorship:
    Drafted with AI assistance and completed under a human-in-the-loop
    process: every declaration in this file was read, executed and reconciled
    with ``planning/db_planning/db_requirements.md`` before it was committed.
    ``db/docs/ai_usage.md`` records what that review covered and the ten
    defects it caught.
"""

from __future__ import annotations

from db.interface.enums import EventType, FoodType, TimeOfDay
from db.interface.persistence_port import AbstractPersistence

__all__ = [
    "AbstractPersistence",
    "EventType",
    "TimeOfDay",
    "FoodType",
]
