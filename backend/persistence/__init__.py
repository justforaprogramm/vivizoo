"""Persistence gateway package of the backend.

The backend never writes SQL and never creates database tables. Instead it
holds a reference to an :class:`db.interface.AbstractPersistence` and hands
it fully-formed model objects. The single adapter in this package,
:class:`~backend.persistence.db_gateway.DbGateway`, owns the mapping from
backend domain objects to the database model objects the database contract
expects.

Dependency rule (mirroring ``db/README.md``):

    backend.core  ->  backend.persistence  ->  db.interface + db.models

Only :mod:`backend.persistence` may import from ``db``; the domain in
``backend.core`` stays ignorant of the database.
"""

from __future__ import annotations

__all__ = ["DbGateway"]
