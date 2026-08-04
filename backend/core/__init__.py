"""Core simulation domain of the vivizoo backend.

One responsibility per module:

* ``animal.py``          -- the ``Animal`` hierarchy (Lion, Giraffe, Penguin).
* ``behaviour.py``       -- the ``Behaviour`` strategy hierarchy.
* ``status_effect.py``   -- temporary modifiers applied to animals.
* ``enclosure.py``       -- container that aggregates animals.
* ``visitor.py``         -- the visitor entity.
* ``finances.py``        -- budget / revenue / expense management.
* ``inventory.py``       -- food stock and the ``Food`` item.
* ``employee.py``        -- the staff hierarchy (Keeper, Veterinarian, AdminStaff).
* ``environment.py``     -- weather / temperature factor.
* ``event_scheduler.py`` -- timed and random events.
* ``message_logger.py``  -- singleton chat feed.
* ``zoo.py``             -- the aggregate root that owns all the above.
* ``engine.py``          -- the ``SimulationEngine`` tick loop.
* ``action_handler.py``  -- the player-facing ``execute_action`` God mode.

These modules depend on each other only in one direction: the small helpers
(``behaviour``, ``status_effect``, ``finances``, ``inventory``,
``message_logger``) know nothing about the engine; the aggregates
(``zoo``, ``engine``) compose them. See ``docs/class_diagram.md``.
"""

from __future__ import annotations

__all__: list[str] = []
