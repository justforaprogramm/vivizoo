"""The database-backed implementation of :class:`AbstractPersistence`.

:class:`ZooDatabase` is what the application uses in normal operation. It is
the only place in the project that opens sessions and issues queries; every
other module talks to it through the abstract interface.

The name says what it *is* -- the zoo's database -- rather than which
library gets it there. SQLAlchemy and SQLite are implementation details that
stop at this file's edge; nothing outside :mod:`db.persistence` names either
of them.

Session handling
    A :class:`~sqlalchemy.orm.Session` is SQLAlchemy's unit of work: objects
    are collected in it and written together on ``commit``. If anything
    raises, everything is rolled back. Two forms appear below::

        with self._session_factory.begin() as session:   # writing
            ...                                          # commit / rollback automatic

        with self._session_factory() as session:         # reading
            ...                                          # no transaction needed

Why results stay usable after the session closes
    The factory is created with ``expire_on_commit=False``, and every
    relationship in the models uses ``lazy="selectin"``. Objects therefore
    carry their data with them; callers never have to think about sessions.

A note on the ``# pylint: disable`` comments below
    Five of them appear in this file and they are all the same false
    positive. SQLAlchemy builds ``sessionmaker.begin`` and the ``func.*``
    namespace at runtime, so a static analyser cannot see members that exist
    perfectly well when the code runs. The suppressions are per line rather
    than per module, so a *genuine* attribute error in this file is still
    reported.

Part of the vivizoo project. Module owner: Jannes (database).

Authorship:
    Drafted with AI assistance and completed under a human-in-the-loop
    process: every declaration in this file was read, executed and reconciled
    with ``planning/db_planning/db_requirements.md`` before it was committed.
    ``db/docs/ai_usage.md`` records what that review covered and the ten
    defects it caught.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Any

from sqlalchemy import delete, func, select, text
from sqlalchemy.orm import Session, raiseload, sessionmaker

from db.interface.persistence_port import AbstractPersistence
from db.models import Base, DailyStats, Event, ZooState
from db.persistence.engine_factory import create_db_engine
from db.persistence.views import register_views

__all__ = ["ZooDatabase"]


class ZooDatabase(AbstractPersistence):
    """The zoo's database: stores every piece of game data that outlives a tick.

    Two kinds of data live here, matching the two steps of the requirements:
    the end-of-day summaries plus the message log (for charts and history),
    and complete savegames (so a zoo can be resumed later).

    Args:
        database (str | Path | None): Path or URL of the database file.
            ``None`` uses ``<repository root>/data/zoo.sqlite``. Pass
            ``":memory:"`` for a throwaway database that never touches disk.
        echo (bool): Print every generated SQL statement. Useful for
            learning and debugging, off by default.

    Attributes:
        DEFAULT_SLOT (int): Save slot used when none is specified.

    Example:
        >>> with ZooDatabase(":memory:") as storage:
        ...     storage.save_day(DailyStats(day_id=1, revenue=840.0))
        ...     storage.get_stats(7)[0].profit_loss
        840.0
    """

    DEFAULT_SLOT = 1

    def __init__(self, database: str | Path | None = None, echo: bool = False) -> None:
        """Open the database and create the schema if it does not exist yet.

        Tables and views are created on construction, so a fresh checkout
        works immediately -- there is no separate setup command to forget.

        Args:
            database (str | Path | None): Path or URL of the database.
                ``None`` selects the default location.
            echo (bool): Whether to print generated SQL statements.

        Returns:
            None (constructor).

        Tests:
            1. ``ZooDatabase(":memory:")`` creates an object whose
               ``get_stats(30)`` immediately returns ``[]`` -- the schema
               exists and is empty.
            2. Constructing twice against the *same* file path succeeds
               without a "table already exists" error, proving schema
               creation is idempotent.
        """
        self._engine = create_db_engine(database, echo=echo)
        register_views(Base.metadata)
        Base.metadata.create_all(self._engine)
        self._session_factory = sessionmaker(
            self._engine,
            expire_on_commit=False,
            class_=Session,
        )
        self._closed = False

    # ------------------------------------------------------------------
    # Step 1 -- analytics
    # ------------------------------------------------------------------

    def save_day(
        self,
        stats: DailyStats,
        events: Iterable[Event] = (),
        replace_events: bool = False,
        overwrite: bool = False,
    ) -> None:
        """Persist one finished simulation day together with its messages.

        Day row and events share one transaction, so a failed call writes
        nothing and can safely be retried.

        Messages are appended by default, so mid-day flushes through
        :meth:`append_events` survive. Set ``replace_events`` to make the
        day's log become exactly what is handed in.

        A ``day_id`` that already holds recorded figures is **refused**
        rather than overwritten -- see :meth:`_assert_day_is_free`.

        Args:
            stats (DailyStats): Key figures of the finished day; its
                ``day_id`` identifies the row.
            events (Iterable[Event]): Messages of that day. Events without a
                ``day_id`` inherit the one from ``stats``.
            replace_events (bool): Delete this day's stored messages before
                writing the new ones. Defaults to ``False``.
            overwrite (bool): Allow replacing a day that already holds
                figures. Defaults to ``False``, which turns an accidental
                repeat into an error instead of silent data loss.

        Returns:
            None.

        Raises:
            ValueError: If ``stats`` holds out-of-range values (from the
                model validators), or if the day already holds figures and
                ``overwrite`` is ``False``.

        Tests:
            1. After saving day 1 with ``revenue=840.0, expenses=300.0``,
               ``get_stats(1)[0].profit_loss`` equals ``540.0``.
            2. Saving day 1 a second time raises ``ValueError``; repeating it
               with ``overwrite=True`` succeeds and leaves one row holding the
               newer figures.
        """
        event_list = list(events)
        with self._session_factory.begin() as session:  # pylint: disable=no-member
            if not overwrite:
                self._assert_day_is_free(session, stats.day_id)
            merged = session.merge(stats)
            session.flush()
            if replace_events:
                session.execute(delete(Event).where(Event.day_id == merged.day_id))
                session.flush()
            for entry in event_list:
                if entry.day_id is None:
                    entry.day_id = merged.day_id
                session.add(entry)

    def append_events(self, events: Iterable[Event]) -> None:
        """Append messages to the log without closing a day.

        Creates a placeholder ``daily_stats`` row for any day that does not
        exist yet, because ``events.day_id`` is a foreign key. The later
        :meth:`save_day` call overwrites that placeholder with the real
        figures.

        Args:
            events (Iterable[Event]): Messages to append; each needs a
                ``day_id``. An empty iterable does nothing and opens no
                transaction.

        Returns:
            None.

        Raises:
            ValueError: If any event has no ``day_id``. Unlike
                :meth:`save_day` there is no ``DailyStats`` to take one from,
                so the message cannot be filed anywhere.

        Tests:
            1. ``append_events([Event(day_id=7, type="INFO", text="hi")])`` on
               an empty database succeeds, and ``get_events(day_id=7)``
               returns that event afterwards.
            2. ``append_events([])`` leaves the database completely
               unchanged and issues no SQL at all; an event whose ``day_id``
               is ``None`` raises ``ValueError`` before any transaction opens.
        """
        event_list = list(events)
        if not event_list:
            return

        # Checked up front rather than left to the database. A missing day_id
        # would otherwise surface as a FlushError about a "NULL identity key"
        # halfway through the write -- a message that names neither the event
        # nor the field that is actually missing.
        if any(entry.day_id is None for entry in event_list):
            raise ValueError(
                "append_events() requires a day_id on every event; "
                f"{sum(entry.day_id is None for entry in event_list)} of "
                f"{len(event_list)} have none. Unlike save_day() there is no "
                f"DailyStats here to inherit it from -- set Event.day_id, or "
                f"pass the messages to save_day() instead."
            )

        with self._session_factory.begin() as session:  # pylint: disable=no-member
            for day_id in {entry.day_id for entry in event_list}:
                self._ensure_day_exists(session, day_id)
            session.flush()
            session.add_all(event_list)

    @staticmethod
    def _assert_day_is_free(session: Session, day_id: int) -> None:
        """Refuse to overwrite a day that already holds recorded figures.

        Overwriting is silently destructive: the previous day's numbers
        disappear and its messages end up merged with the new day's. The
        usual cause is a day counter that failed to advance, and nothing in
        the data afterwards reveals that a day went missing.

        A row is treated as free when it does not exist, or when every figure
        is still at zero. The zero case matters because
        :meth:`append_events` creates exactly such a placeholder when
        messages arrive before the day is closed -- that one *must* stay
        overwritable.

        Retrying a failed :meth:`save_day` is unaffected: a failed call rolls
        back, so nothing was written and the day is still free.

        Args:
            session (Session): The open session to look in. Not committed
                here -- the caller owns the transaction.
            day_id (int): The day about to be written.

        Returns:
            None.

        Raises:
            ValueError: If the day already holds figures. The message repeats
                the stored values and names the ``overwrite`` escape hatch.

        Tests:
            1. Saving day 2 with real figures and then saving day 2 again
               raises ``ValueError`` whose message contains ``"2"``; the
               stored row keeps its original figures.
            2. A day created as a placeholder by ``append_events`` (all
               figures zero) is accepted without complaint, so the normal
               flush-then-close-the-day flow keeps working.
        """
        existing = session.get(DailyStats, day_id)
        if existing is None:
            return

        recorded = (
            existing.total_visitors,
            existing.revenue,
            existing.expenses,
            existing.avg_animal_welfare,
            existing.avg_happiness,
            existing.reputation_end_of_day,
            existing.animals_died,
        )
        if not any(recorded):
            return  # placeholder from append_events -- fine to fill in

        raise ValueError(
            f"Day {day_id} already holds recorded figures "
            f"({existing.total_visitors} visitors, revenue {existing.revenue}). "
            f"Refusing to overwrite them silently -- a repeated day_id is "
            f"usually a day counter that did not advance. Pass "
            f"overwrite=True if replacing the day is really intended."
        )

    @staticmethod
    def _ensure_day_exists(session: Session, day_id: int) -> None:
        """Create a placeholder day row if it does not exist yet.

        Internal helper for :meth:`append_events`. Needed because
        ``events.day_id`` references ``daily_stats.day_id``; inserting an
        event for a day that has not been closed yet would otherwise violate
        the foreign key.

        Args:
            session (Session): The open session to work in. Not committed
                here -- the caller owns the transaction.
            day_id (int): Day number to make sure exists.

        Returns:
            None.

        Tests:
            1. Called for a ``day_id`` that does not exist, a row with that
               id and all figures at ``0`` appears afterwards.
            2. Called for an existing day that already holds
               ``revenue=500.0``, the row is left untouched -- the real
               figures are not overwritten with zeros.
        """
        if session.get(DailyStats, day_id) is None:
            session.add(DailyStats(day_id=day_id))

    def get_stats(self, days_back: int = 30) -> list[DailyStats]:
        """Read the most recent daily summaries for charts.

        Fetches the newest ``days_back`` rows and reverses them, so the
        result is chronological and can be plotted directly.

        The ``events`` collection of the returned objects is deliberately
        **not** loaded: charts need figures, not messages, and pulling in
        every message of every day makes this query roughly thirty times
        slower. Use :meth:`get_events` for the chat log. Touching
        ``day.events`` on a result of this method raises a clear SQLAlchemy
        error rather than silently returning an empty list.

        Args:
            days_back (int): How many days to read, counting back from the
                newest. ``0`` or less returns an empty list.

        Returns:
            list[DailyStats]: Up to ``days_back`` rows, oldest first, with
            figures populated and ``events`` intentionally unloaded. Empty
            list if nothing has been saved yet.

        Tests:
            1. With days 1--5 saved, ``get_stats(3)`` returns ``day_id``
               values ``[3, 4, 5]`` in that order.
            2. ``get_stats(0)`` returns ``[]``, and so does ``get_stats(10)``
               on an empty database.
        """
        if days_back <= 0:
            return []
        with self._session_factory() as session:
            rows = session.scalars(
                select(DailyStats)
                .options(raiseload(DailyStats.events))
                .order_by(DailyStats.day_id.desc())
                .limit(days_back)
            ).all()
        return list(reversed(rows))

    def get_events(self, day_id: int | None = None, limit: int = 100) -> list[Event]:
        """Read log messages, optionally restricted to a single day.

        Args:
            day_id (int | None): Restrict to this day; ``None`` reads across
                all days.
            limit (int): Maximum number of messages, counting back from the
                newest. ``0`` or less returns an empty list.

        Returns:
            list[Event]: Up to ``limit`` messages, oldest first. Empty if the
            day does not exist or holds no messages.

        Tests:
            1. With 5 events on day 1 and 3 on day 2, ``get_events(day_id=2)``
               returns exactly the 3 events of day 2.
            2. ``get_events(limit=10)`` with 200 events stored returns the
               newest 10 in oldest-first order; ``get_events(day_id=999)``
               returns ``[]``.
        """
        if limit <= 0:
            return []
        query = select(Event).order_by(Event.id.desc()).limit(limit)
        if day_id is not None:
            query = query.where(Event.day_id == day_id)
        with self._session_factory() as session:
            rows = session.scalars(query).all()
        return list(reversed(rows))

    def get_weekly_summary(self) -> list[dict[str, Any]]:
        """Aggregate the daily summaries into calendar weeks.

        Reads the ``v_weekly_summary`` view, so the aggregation runs inside
        SQLite rather than in Python. See :mod:`db.persistence.views`.

        Args:
            None (instance method, only ``self``).

        Returns:
            list[dict[str, Any]]: One dictionary per week, oldest first, with
            the keys described in
            :meth:`~db.interface.persistence_port.AbstractPersistence.get_weekly_summary`.
            Empty list if no day has been saved.

        Tests:
            1. With days 1--7 saved at ``revenue=100.0`` each, the result has
               one entry with ``week == 1`` and ``revenue == 700.0``.
            2. With days 1--8 saved, the result has two entries and the
               second reports ``days_recorded == 1`` (partial week).
        """
        statement = text(
            "SELECT week, days_recorded, total_visitors, revenue, expenses, "
            "profit_loss, avg_animal_welfare, avg_happiness, animals_died "
            "FROM v_weekly_summary ORDER BY week"
        )
        with self._session_factory() as session:
            return [dict(row) for row in session.execute(statement).mappings()]

    # ------------------------------------------------------------------
    # Step 2 -- savegames
    # ------------------------------------------------------------------

    def save_game(self, zoo_state: ZooState) -> int:
        """Persist a complete savegame, replacing whatever occupied the slot.

        The old slot is wiped first, so animals that were sold or died really
        disappear instead of lingering as ghosts. Delete and insert share one
        transaction, so an interrupted save cannot destroy the previous one.

        The graph may come from anywhere: freshly built objects, a graph
        returned by :meth:`load_game`, or a mixture. That matters, because
        load-play-save is the normal cycle -- see the note below.

        Args:
            zoo_state (ZooState): Root of the object graph. If its ``id`` is
                ``None``, :attr:`DEFAULT_SLOT` is used and written back onto
                the object.

        Returns:
            int: The slot number that was written.

        Note:
            The old rows are removed with a bulk ``DELETE`` that relies on the
            database's ``ON DELETE CASCADE``, and the new graph is written
            with ``merge()`` rather than ``add()``. Both details are
            deliberate: a graph that came from :meth:`load_game` still carries
            its database identity, and ``add()`` would treat it as an existing
            row and emit ``UPDATE`` statements against rows that were just
            deleted.

        Tests:
            1. Saving a zoo with one enclosure and two animals, then calling
               ``load_game()``, yields a zoo whose ``total_animals()`` is
               ``2``.
            2. Loading a savegame, removing one animal from its enclosure and
               saving the same graph again leaves exactly one animal and no
               orphaned status effects.
        """
        slot = zoo_state.id if zoo_state.id is not None else self.DEFAULT_SLOT
        zoo_state.id = slot
        self._assert_unique_ids(zoo_state)

        with self._session_factory.begin() as session:  # pylint: disable=no-member
            session.execute(delete(ZooState).where(ZooState.id == slot))
            session.flush()
            session.expunge_all()
            session.merge(zoo_state)
        return slot

    @staticmethod
    def _assert_unique_ids(zoo_state: ZooState) -> None:
        """Reject a savegame that reuses an identifier.

        Without this check a duplicate is **silently destructive**: the graph
        is written with ``merge()``, so a second animal carrying an existing
        ``animal_id`` overwrites the first one instead of being added. The
        zoo would come back one animal short, with no error anywhere.

        The realistic way to hit this is an identifier counter that restarts
        at one after a savegame was loaded. Use
        :meth:`~db.models.zoo_state.ZooState.next_animal_id` to avoid it, and
        rely on this check to catch it if it happens anyway.

        Args:
            zoo_state (ZooState): The graph about to be written.

        Returns:
            None.

        Raises:
            ValueError: If two enclosures share an ``enclosure_id`` or two
                animals share an ``animal_id``. The message names the
                offending identifier.

        Tests:
            1. A zoo whose two animals both carry ``"a_01"`` raises
               ``ValueError`` mentioning ``"a_01"``, and the database is left
               untouched.
            2. A zoo with unique identifiers passes silently, and one with
               two animals of the same *name* but different ids is accepted --
               only identifiers have to be unique.
        """
        enclosure_ids: set[str] = set()
        animal_ids: set[str] = set()

        for enclosure in zoo_state.enclosures:
            if enclosure.enclosure_id in enclosure_ids:
                raise ValueError(
                    f"Duplicate enclosure_id {enclosure.enclosure_id!r} in the "
                    f"savegame. Every enclosure needs a unique identifier; use "
                    f"ZooState.next_enclosure_id() to obtain one."
                )
            enclosure_ids.add(enclosure.enclosure_id)

            for animal in enclosure.animals:
                if animal.animal_id in animal_ids:
                    raise ValueError(
                        f"Duplicate animal_id {animal.animal_id!r} in the "
                        f"savegame. Every animal needs a unique identifier; use "
                        f"ZooState.next_animal_id() to obtain one."
                    )
                animal_ids.add(animal.animal_id)

    def load_game(self, save_id: int = 1) -> ZooState | None:
        """Load a complete savegame including all nested objects.

        The returned graph can be walked in **both** directions once the call
        returns: downwards (``state.enclosures[0].animals[0]``) and upwards
        (``animal.enclosure.name``).

        Args:
            save_id (int): Slot to load; defaults to :attr:`DEFAULT_SLOT`.

        Returns:
            ZooState | None: The fully populated object graph, or ``None`` if
            the slot is empty.

        Tests:
            1. After a save, ``load_game(1).enclosures[0].animals[0]`` is an
               instance of the correct species subclass (e.g. ``Lion``), and
               reading ``.enclosure.name`` on it works after the call.
            2. ``load_game(99)`` on a database without that slot returns
               ``None`` instead of raising.
        """
        with self._session_factory() as session:
            state = session.get(ZooState, save_id)
            if state is None:
                return None
            self._resolve_parent_links(state)
            return state

    @staticmethod
    def _resolve_parent_links(state: ZooState) -> None:
        """Populate the upward links of a loaded savegame.

        The downward relationships (``enclosures``, ``animals``,
        ``status_effects``, ``inventory``) use ``lazy="selectin"`` and are
        therefore loaded automatically. The upward ones -- ``animal.enclosure``,
        ``enclosure.zoo`` and friends -- are not: they form a cycle with the
        collections above, and SQLAlchemy stops eager-loading when it detects
        one. Reading such an attribute after the session closed would raise
        ``DetachedInstanceError``.

        Touching them here, while the session is still open, fixes that. It
        costs **no extra queries**: every parent row is already in the
        session's identity map, so each lookup resolves in memory.

        Args:
            state (ZooState): The freshly loaded savegame root. Modified in
                place.

        Returns:
            None.

        Tests:
            1. After ``load_game()``, reading ``animal.enclosure.name`` and
               ``enclosure.zoo.game_day`` works without raising, even though
               the session has closed.
            2. Loading a savegame with 1 enclosure, 1 animal and 1 status
               effect issues no more SQL statements than the same load
               without this call (identity-map hits only).
        """
        for item in state.inventory:
            _ = item.zoo
        for enclosure in state.enclosures:
            _ = enclosure.zoo
            for animal in enclosure.animals:
                _ = animal.enclosure
                for effect in animal.status_effects:
                    _ = effect.animal

    def list_saves(self) -> list[dict[str, Any]]:
        """List all existing savegames for a "load game" menu.

        Args:
            None (instance method, only ``self``).

        Returns:
            list[dict[str, Any]]: One entry per slot, newest first, with the
            keys ``id``, ``game_day``, ``money``, ``reputation`` and
            ``created_at``. Empty list if no save exists.

        Tests:
            1. After saving slot 1, the result has length ``1`` and its entry
               carries ``id == 1`` plus a non-empty ``created_at``.
            2. On an untouched database the result is ``[]``.
        """
        query = select(
            ZooState.id,
            ZooState.game_day,
            ZooState.money,
            ZooState.reputation,
            ZooState.created_at,
        ).order_by(ZooState.created_at.desc())
        with self._session_factory() as session:
            return [
                {
                    "id": row.id,
                    "game_day": row.game_day,
                    "money": row.money,
                    "reputation": row.reputation,
                    "created_at": row.created_at.isoformat(),
                }
                for row in session.execute(query)
            ]

    def delete_save(self, save_id: int) -> bool:
        """Delete a savegame together with everything belonging to it.

        Loads the row first rather than issuing a bulk ``DELETE``, so
        SQLAlchemy's ORM cascades run and the children are removed reliably.

        Args:
            save_id (int): Slot to delete.

        Returns:
            bool: ``True`` if a slot was deleted, ``False`` if it did not
            exist.

        Tests:
            1. ``delete_save(1)`` on an existing slot returns ``True``, a
               following ``load_game(1)`` returns ``None``, and the
               ``animals`` table no longer holds that slot's animals.
            2. ``delete_save(99)`` on a missing slot returns ``False`` and
               leaves all other slots untouched.
        """
        with self._session_factory.begin() as session:  # pylint: disable=no-member
            existing = session.get(ZooState, save_id)
            if existing is None:
                return False
            session.delete(existing)
        return True

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Delete all stored data and recreate an empty schema.

        Drops every table and creates it again. Intended for tests and for a
        "new game" action -- never for normal gameplay.

        Args:
            None (instance method, only ``self``).

        Returns:
            None.

        Tests:
            1. After saving several days, ``reset()`` followed by
               ``get_stats(30)`` returns ``[]``.
            2. Calling ``reset()`` twice in a row succeeds and the object is
               still usable for saving afterwards.
        """
        Base.metadata.drop_all(self._engine)
        Base.metadata.create_all(self._engine)

    def close(self) -> None:
        """Close all database connections held by the engine.

        Safe to call more than once; further calls do nothing.

        Args:
            None (instance method, only ``self``).

        Returns:
            None.

        Tests:
            1. After ``close()`` the SQLite file is no longer held open and
               can be deleted on any platform.
            2. Calling ``close()`` twice does not raise.
        """
        if not self._closed:
            self._engine.dispose()
            self._closed = True

    def count_rows(self, model: type[Base]) -> int:
        """Count the rows of one table -- a small helper for tests and demos.

        Not part of :class:`AbstractPersistence`, because it exposes the
        table structure and is therefore a diagnostic tool rather than part
        of the contract.

        Args:
            model (type[Base]): A model class, e.g. ``DailyStats``.

        Returns:
            int: Number of rows currently stored in that table; ``0`` for an
            empty table.

        Tests:
            1. After saving three days, ``count_rows(DailyStats)`` returns
               ``3``.
            2. On an empty database ``count_rows(Event)`` returns ``0``.
        """
        with self._session_factory() as session:
            count = select(func.count()).select_from(model)  # pylint: disable=not-callable
            return int(session.scalar(count) or 0)
