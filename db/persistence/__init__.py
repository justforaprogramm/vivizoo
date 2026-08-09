"""The concrete storage implementation.

Everything in this package implements
:class:`~db.interface.persistence_port.AbstractPersistence`. Application code
does **not** import from here -- it receives a ready-made storage object
through its constructor. Only the entry point (or a test) picks an
implementation.

Contents:
    * :class:`~db.persistence.zoo_database.ZooDatabase`
      -- SQLite via SQLAlchemy.
    * :mod:`db.persistence.engine_factory` -- engine creation, database
      location and the SQLite settings that have to be applied per
      connection.
    * :mod:`db.persistence.views` -- SQL views for aggregated reads.

Part of the vivizoo project. Module owner: Jannes (database).

Authorship:
    Drafted with AI assistance and completed under a human-in-the-loop
    process: every declaration in this file was read, executed and reconciled
    with ``planning/db_planning/db_requirements.md`` before it was committed.
    ``db/docs/ai_usage.md`` records what that review covered and the ten
    defects it caught.
"""

from __future__ import annotations

from db.persistence.engine_factory import (
    build_sqlite_url,
    create_db_engine,
    default_database_path,
)
from db.persistence.zoo_database import ZooDatabase

__all__ = [
    "ZooDatabase",
    "create_db_engine",
    "build_sqlite_url",
    "default_database_path",
]
