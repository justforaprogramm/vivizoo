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
