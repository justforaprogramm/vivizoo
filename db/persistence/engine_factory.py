"""Creation and configuration of the SQLAlchemy engine.

The *engine* is the object that owns the connection pool to the database
file. It is created once at application start-up and shared afterwards.

This module exists as a separate file because engine configuration is a task
of its own: choosing the file location, switching on SQLite features that are
off by default, and doing so in one place instead of scattered across the
persistence code.

Three SQLite settings matter here and are applied to **every** connection:

``PRAGMA foreign_keys=ON``
    SQLite ignores foreign keys unless this is switched on -- per connection,
    every time. Without it the ``ON DELETE CASCADE`` rules in the models
    would be decorative and deleting a save would leave orphaned animals
    behind.

``PRAGMA journal_mode=WAL``
    Write-Ahead Logging. Readers no longer block writers, which matters as
    soon as the UI reads while the simulation writes.

``PRAGMA synchronous=NORMAL``
    Skips one ``fsync`` per commit. Safe under WAL for a desktop game and
    considerably faster than the default.

Part of the vivizoo project. Module owner: Jannes (database).

Authorship:
    Drafted with AI assistance and completed under a human-in-the-loop
    process: every declaration in this file was read, executed and reconciled
    with ``planning/db_planning/db_requirements.md`` before it was committed.
    ``db/docs/ai_usage.md`` records what that review covered and the ten
    defects it caught.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from sqlalchemy import Engine, create_engine, event, text
from sqlalchemy.engine import Connection
from sqlalchemy.exc import SQLAlchemyError

__all__ = [
    "default_database_path",
    "build_sqlite_url",
    "create_db_engine",
    "connection_is_healthy",
]

#: Location of the database file relative to the repository root.
DATA_DIRECTORY = "data"

#: File name of the production database.
DATABASE_FILENAME = "zoo.sqlite"


def default_database_path() -> Path:
    """Return the standard location of the database file.

    Resolved from this module's own location rather than the current working
    directory, so the same file is used no matter where the application was
    started from -- an editor, a terminal or the devcontainer.

    The containing directory is created if it does not exist yet.

    Args:
        None.

    Returns:
        Path: Absolute path to ``<repository root>/data/zoo.sqlite``. The
        file itself is not created; SQLite does that on first connect.

    Tests:
        1. The returned path is absolute and ends with
           ``"data/zoo.sqlite"``.
        2. After the call the parent directory exists, even if it did not
           before (directory is created as a side effect).
    """
    repository_root = Path(__file__).resolve().parents[2]
    directory = repository_root / DATA_DIRECTORY
    directory.mkdir(parents=True, exist_ok=True)
    return directory / DATABASE_FILENAME


def build_sqlite_url(database: str | Path | None = None) -> str:
    """Turn a file path into a SQLAlchemy connection URL.

    Args:
        database (str | Path | None): Where the database lives. ``None`` uses
            :func:`default_database_path`. The literal string
            ``":memory:"`` produces an in-memory database that disappears
            when the process ends -- ideal for tests. A value that already
            looks like a URL (contains ``"://"``) is passed through
            unchanged, which is what makes switching to another database
            engine a one-string change.

    Returns:
        str: A SQLAlchemy URL such as
        ``"sqlite:////workspaces/vivizoo/data/zoo.sqlite"`` or
        ``"sqlite:///:memory:"``.

    Tests:
        1. ``build_sqlite_url(":memory:")`` returns exactly
           ``"sqlite:///:memory:"``.
        2. ``build_sqlite_url("postgresql://user@host/db")`` returns that
           string unchanged (pass-through case), while ``build_sqlite_url(None)``
           returns a URL starting with ``"sqlite:///"`` and containing
           ``"zoo.sqlite"``.
    """
    if database is None:
        database = default_database_path()
    location = str(database)
    if "://" in location:
        return location
    if location == ":memory:":
        return "sqlite:///:memory:"
    return f"sqlite:///{Path(location).resolve()}"


def _apply_sqlite_pragmas(dbapi_connection: Any, _connection_record: Any) -> None:
    """Apply the required SQLite settings to a freshly opened connection.

    Registered as an event listener in :func:`create_db_engine` and called by
    SQLAlchemy for every new connection -- never directly by application
    code. The settings are per-connection in SQLite, which is exactly why
    they cannot simply be executed once at start-up.

    Args:
        dbapi_connection (Any): The raw DB-API connection SQLAlchemy just
            opened. For non-SQLite backends this listener is not registered
            at all.
        _connection_record (Any): SQLAlchemy's pool bookkeeping object.
            Unused; present because the event signature requires it.

    Returns:
        None.

    Tests:
        1. After connecting through an engine built by
           :func:`create_db_engine`, ``PRAGMA foreign_keys`` reports ``1``.
        2. On a file-backed database ``PRAGMA journal_mode`` reports ``wal``,
           and deleting a ``zoo_state`` row really does remove its enclosures
           (proving the foreign key setting took effect).
    """
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
    finally:
        cursor.close()


def create_db_engine(
    database: str | Path | None = None, echo: bool = False
) -> Engine:
    """Create a fully configured SQLAlchemy engine.

    This is the only place in the project that calls
    :func:`sqlalchemy.create_engine`. Everything else receives the finished
    engine.

    Args:
        database (str | Path | None): Path or URL of the database, forwarded
            to :func:`build_sqlite_url`. ``None`` uses the default location.
        echo (bool): If ``True``, every generated SQL statement is printed to
            stdout. Extremely useful while learning or debugging; leave it
            ``False`` in normal operation.

    Returns:
        Engine: A ready-to-use engine with the SQLite pragmas registered.
        No connection has been opened yet -- that happens lazily on first
        use.

    Tests:
        1. ``create_db_engine(":memory:")`` returns an ``Engine`` whose
           ``dialect.name`` is ``"sqlite"``, and a trivial ``SELECT 1``
           through it succeeds.
        2. ``create_db_engine(":memory:", echo=True)`` produces an engine
           with ``engine.echo is True``, confirming the flag is forwarded.
    """
    url = build_sqlite_url(database)
    engine = create_engine(url, echo=echo, future=True)

    if engine.dialect.name == "sqlite":
        event.listen(engine, "connect", _apply_sqlite_pragmas)

    return engine


def connection_is_healthy(connection: Connection) -> bool:
    """Check that a connection can actually execute a statement.

    Intended for a start-up self-check or a smoke test, where a clear early
    error beats a confusing one later on. Not currently called anywhere in the
    module -- ``demo.py`` relies on the operations themselves failing loudly.

    Args:
        connection (Connection): An open SQLAlchemy connection.

    Returns:
        bool: ``True`` if a trivial ``SELECT 1`` succeeds, ``False`` if any
        database error occurs.

    Tests:
        1. On a connection from a working in-memory engine the function
           returns ``True``.
        2. On a connection that has already been closed the function returns
           ``False`` instead of raising.
    """
    try:
        connection.execute(text("SELECT 1"))
    except SQLAlchemyError:
        return False
    return True
