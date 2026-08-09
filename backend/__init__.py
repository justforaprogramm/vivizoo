"""vivizoo backend package.

This package implements the **core simulation logic** ("the heartbeat").
It sits between the database module (``db/``) and the frontend (PyQt):

* ``.core`` holds the object-oriented domain model and the tick engine.
* ``.persistence`` maps the domain state to the database contract
  (:class:`db.interface.AbstractPersistence`).

The backend does **not** generate database tables and does **not** render
a frontend. It exposes a small, stable API that the frontend can call --
see ``docs/api.md``.

Typical wiring from an entry point::

    from backend.core.zoo import Zoo
    from backend.persistence.db_gateway import DbGateway
    from backend.core.engine import SimulationEngine
    from backend.core.message_logger import MessageLogger

    engine = SimulationEngine(
        Zoo(name="My Zoo", logger=MessageLogger.instance()),
        persistence=DbGateway(persistence),
    )
    engine.start()

Part of the vivizoo project. Module owner: Benjamin (backend).
"""

from __future__ import annotations

from backend.core.animal import Animal, Giraffe, Lion, Penguin, create_animal
from backend.core.engine import SimulationEngine
from backend.core.zoo import Zoo

__all__ = [
    "Animal",
    "Lion",
    "Giraffe",
    "Penguin",
    "create_animal",
    "Zoo",
    "SimulationEngine",
]

__version__ = "1.0.0"
