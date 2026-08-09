"""The contract between the application and the database.

This module defines :class:`AbstractPersistence` -- the complete list of
operations the application may perform on stored data. It contains **no**
implementation: it names the operations, their inputs and their outputs, and
nothing else.

Why an abstract base class?
    Calling code accepts an ``AbstractPersistence`` and never imports
    SQLAlchemy. That has three practical consequences:

    * The storage layer can be rewritten freely; as long as these method
      signatures hold, the application does not notice.
    * Tests run against an in-memory database by passing a different object
      in -- no file, no leftovers, no mocking framework.
    * Python enforces the contract: a subclass that forgets a method cannot
      be instantiated, so the mismatch surfaces at start-up rather than in
      the middle of a play session.

The shipped implementation is
:class:`~db.persistence.zoo_database.ZooDatabase`, backed
by SQLite.

The model classes are part of this contract as well: they are the language
the two sides speak. Calling code therefore imports :mod:`db.models` and :mod:`db.interface`,
but never :mod:`db.persistence`.

Part of the vivizoo project. Module owner: Jannes (database).

Authorship:
    Drafted with AI assistance and completed under a human-in-the-loop
    process: every declaration in this file was read, executed and reconciled
    with ``planning/db_planning/db_requirements.md`` before it was committed.
    ``db/docs/ai_usage.md`` records what that review covered and the ten
    defects it caught.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable
from typing import Any

from db.models import DailyStats, Event, ZooState

__all__ = ["AbstractPersistence"]


class AbstractPersistence(ABC):
    """Every operation this module offers.

    Implementations must honour these guarantees:

    * **Atomicity** -- a call either completes fully or changes nothing.
    * **Detached results** -- returned objects stay usable after the call
      returns; the caller never has to worry about sessions.
    * **Chronological order** -- the time-series reads (:meth:`get_stats`,
      :meth:`get_events`, :meth:`get_weekly_summary`) return oldest first,
      which is the order charts and chat logs need. :meth:`list_saves` is the
      deliberate exception and returns newest first, because a load menu wants
      the most recent save at the top.
    """

    # ------------------------------------------------------------------
    # Step 1 -- analytics: daily summaries and the message log
    # ------------------------------------------------------------------

    @abstractmethod
    def save_day(
        self,
        stats: DailyStats,
        events: Iterable[Event] = (),
        replace_events: bool = False,
        overwrite: bool = False,
    ) -> None:
        """Persist one finished simulation day, together with its messages.

        Called once per simulation day, at the end of the night phase. Both
        arguments are written in a single transaction, so a crash can never
        leave a day row without its events or vice versa. A failed call
        writes nothing at all, which makes a retry after an error safe.

        **A day is written once.** If the ``day_id`` already holds recorded
        figures, the call raises instead of replacing them. Reusing a
        ``day_id`` is nearly always a day counter that failed to advance, and
        overwriting would delete the earlier day's numbers and merge the two
        days' messages -- with nothing afterwards revealing that a day went
        missing. Pass ``overwrite=True`` to replace a day on purpose.

        A day that exists only as a placeholder -- created by
        :meth:`append_events` when messages arrive before the day is closed --
        counts as free and is filled in normally.

        **Messages behave differently from figures, on purpose.** They are
        *appended*, which is what lets :meth:`append_events` flush during the
        day and this call add the remainder at the end without losing the
        earlier ones. Pass ``replace_events=True`` when the day's log should
        become exactly what you hand in.

        Args:
            stats (DailyStats): Key figures of the finished day. Its
                ``day_id`` identifies the row. Must not have ``profit_loss``
                set -- that column is computed by the database.
            events (Iterable[Event]): Messages produced during that day.
                Defaults to an empty tuple. Any event whose ``day_id`` is
                ``None`` is automatically assigned the ``day_id`` of
                ``stats``.
            replace_events (bool): If ``True``, every message already stored
                for this day is deleted before the new ones are written, so
                the day ends up holding exactly ``events``. Defaults to
                ``False`` (append).
            overwrite (bool): If ``True``, a day that already holds figures
                is replaced instead of rejected. Defaults to ``False``.

        Returns:
            None. Errors are raised as exceptions rather than returned.

        Raises:
            ValueError: If ``stats`` contains values outside their valid
                range (propagated from the model validators), or if the day
                already holds figures and ``overwrite`` is ``False``.

        Tests:
            1. After ``save_day(DailyStats(day_id=1, revenue=840.0,
               expenses=300.0))``, a following ``get_stats(1)`` returns
               exactly one row whose ``profit_loss`` is ``540.0`` -- proving
               the computed column works.
            2. Saving day 1 a second time raises ``ValueError`` and leaves
               the stored figures untouched; repeating it with
               ``overwrite=True`` succeeds and the row holds the newer
               values.
        """

    @abstractmethod
    def append_events(self, events: Iterable[Event]) -> None:
        """Append messages to the log without closing a day.

        Useful for flushing the message queue mid-day so a crash does not
        lose the chat history. If no day row exists yet for an event's
        ``day_id``, a placeholder row is created; the later
        :meth:`save_day` call fills in the real figures.

        Args:
            events (Iterable[Event]): Messages to append. Each one must have
                a ``day_id`` set. An empty iterable is valid and does
                nothing at all -- no transaction is opened.

        Returns:
            None.

        Tests:
            1. ``append_events([Event(day_id=7, type="INFO", text="hi")])``
               on an empty database succeeds, and ``get_events(day_id=7)``
               afterwards returns that one event.
            2. ``append_events([])`` returns without error and leaves the
               database completely unchanged (empty-input edge case).
        """

    @abstractmethod
    def get_stats(self, days_back: int = 30) -> list[DailyStats]:
        """Read the most recent daily summaries for charts.

        Args:
            days_back (int): How many days to read, counting back from the
                most recent one. Defaults to ``30``. Values of ``0`` or less
                return an empty list.

        Returns:
            list[DailyStats]: Up to ``days_back`` rows in **chronological
            order** (oldest first), so the list can be plotted directly along
            an x-axis. Fewer rows are returned if fewer days exist; an empty
            list if nothing has been saved yet.

            Only the figures are populated -- the ``events`` collection of
            the returned objects is not filled, because charts do not need
            messages and loading them makes the query far slower. Use
            :meth:`get_events` for the chat log.

        Tests:
            1. With days 1--5 saved, ``get_stats(3)`` returns three rows whose
               ``day_id`` values are ``[3, 4, 5]`` in that order -- confirming
               both the limit and the chronological ordering.
            2. ``get_stats(10)`` on an empty database returns ``[]``, and
               ``get_stats(0)`` also returns ``[]`` (zero and empty-database
               edge cases).
        """

    @abstractmethod
    def get_events(
        self, day_id: int | None = None, limit: int = 100
    ) -> list[Event]:
        """Read log messages, optionally restricted to one day.

        Args:
            day_id (int | None): Restrict to this simulation day. ``None``
                (the default) reads across all days.
            limit (int): Maximum number of messages to return, counting back
                from the newest. Defaults to ``100``.

        Returns:
            list[Event]: Up to ``limit`` messages in **chronological order**
            (oldest first), ready to be rendered as a chat feed. Empty list
            if the day does not exist or holds no messages.

        Tests:
            1. With 5 events on day 1 and 3 on day 2, ``get_events(day_id=2)``
               returns exactly the 3 events of day 2.
            2. With 200 events stored, ``get_events(limit=10)`` returns 10
               rows, and they are the *newest* ten but ordered oldest-first;
               ``get_events(day_id=999)`` returns ``[]`` for a day that does
               not exist.
        """

    @abstractmethod
    def get_weekly_summary(self) -> list[dict[str, Any]]:
        """Aggregate the daily summaries into calendar weeks.

        Feeds a UI's long-range charts, where plotting 200 individual
        days would be unreadable. Week ``1`` covers days 1--7, week ``2``
        days 8--14, and so on.

        Args:
            None (instance method, only ``self``).

        Returns:
            list[dict[str, Any]]: One dictionary per week, oldest first, with
            the keys ``week``, ``days_recorded``, ``total_visitors``,
            ``revenue``, ``expenses``, ``profit_loss``,
            ``avg_animal_welfare``, ``avg_happiness`` and ``animals_died``.
            Sums are totals across the week; averages are means over the days
            actually recorded. Empty list if no day has been saved.

        Tests:
            1. With days 1--7 saved at 100.0 revenue each, the result holds
               one entry with ``week == 1`` and ``revenue == 700.0``.
            2. With days 1--8 saved, the result holds two entries; the second
               has ``week == 2`` and ``days_recorded == 1`` -- confirming a
               partial week is reported rather than dropped.
        """

    # ------------------------------------------------------------------
    # Step 2 -- savegames
    # ------------------------------------------------------------------

    @abstractmethod
    def save_game(self, zoo_state: ZooState) -> int:
        """Persist a complete savegame, replacing whatever occupied the slot.

        The whole object graph is written in one transaction: the zoo state,
        its inventory, its enclosures, their animals and their status
        effects. An interrupted save can therefore never leave half a zoo
        behind.

        Args:
            zoo_state (ZooState): Root of the object graph to save. If its
                ``id`` is ``None``, the default slot ``1`` is used and
                assigned back onto the object.

        Returns:
            int: The slot number actually written, suitable for a later
            :meth:`load_game` call.

        Tests:
            1. Saving a ``ZooState`` holding one enclosure with two animals
               and then calling ``load_game()`` returns a zoo whose
               ``total_animals()`` is ``2``.
            2. Saving twice into the same slot -- first with three animals,
               then with one -- leaves exactly one animal in the database,
               proving the old graph was removed rather than merged.
        """

    @abstractmethod
    def load_game(self, save_id: int = 1) -> ZooState | None:
        """Load a complete savegame including all nested objects.

        Args:
            save_id (int): Slot to load. Defaults to ``1``, the slot used by
                :meth:`save_game` when none is given.

        Returns:
            ZooState | None: The fully populated object graph -- enclosures,
            animals and status effects are already loaded and remain usable
            after the call. ``None`` if the slot is empty.

        Tests:
            1. After a successful :meth:`save_game`, ``load_game(1)`` returns
               a ``ZooState`` whose ``enclosures[0].animals[0]`` is an
               instance of the correct species subclass (e.g. ``Lion``) --
               proving polymorphic loading works.
            2. ``load_game(99)`` on a database without that slot returns
               ``None`` rather than raising.
        """

    @abstractmethod
    def list_saves(self) -> list[dict[str, Any]]:
        """List all existing savegames for a "load game" menu.

        Deliberately returns plain dictionaries rather than ``ZooState``
        objects, so the menu can be rendered without loading every zoo in
        full.

        Args:
            None (instance method, only ``self``).

        Returns:
            list[dict[str, Any]]: One entry per slot, newest first, with the
            keys ``id``, ``game_day``, ``money``, ``reputation`` and
            ``created_at`` (an ISO-8601 string). Empty list if no save
            exists.

        Tests:
            1. After saving slot 1, the result has length ``1`` and its entry
               carries ``id == 1`` plus a non-empty ``created_at`` string.
            2. On an untouched database the result is ``[]``.
        """

    @abstractmethod
    def delete_save(self, save_id: int) -> bool:
        """Delete a savegame together with everything belonging to it.

        Args:
            save_id (int): Slot to delete.

        Returns:
            bool: ``True`` if a slot was deleted, ``False`` if it did not
            exist. Deleting a missing slot is not an error.

        Tests:
            1. After ``delete_save(1)`` on an existing slot the method returns
               ``True`` and a following ``load_game(1)`` returns ``None``;
               the enclosures and animals of that slot are gone as well.
            2. ``delete_save(99)`` on a non-existent slot returns ``False``
               and leaves every other slot untouched.
        """

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    @abstractmethod
    def reset(self) -> None:
        """Delete all stored data and recreate an empty structure.

        Intended for tests and for a "new game" action. Never call this from
        normal gameplay code.

        Args:
            None (instance method, only ``self``).

        Returns:
            None.

        Tests:
            1. After saving several days, ``reset()`` followed by
               ``get_stats(30)`` returns ``[]``.
            2. Calling ``reset()`` twice in a row succeeds, and the object is
               still usable for saving afterwards (idempotence).
        """

    @abstractmethod
    def close(self) -> None:
        """Release all resources, e.g. open database connections.

        After this call the object must not be used again. Prefer the context
        manager form, which calls this automatically::

            with ZooDatabase() as storage:
                storage.save_day(stats)

        Args:
            None (instance method, only ``self``).

        Returns:
            None.

        Tests:
            1. After ``close()`` the underlying SQLite file is no longer held
               open and can be deleted on any platform.
            2. Calling ``close()`` twice does not raise (idempotence).
        """

    # ------------------------------------------------------------------
    # Context manager support -- implemented once for every subclass
    # ------------------------------------------------------------------

    def __enter__(self) -> "AbstractPersistence":
        """Enter a ``with`` block and return the storage object itself.

        Implemented here in the abstract class, so every implementation gains
        context manager support automatically.

        Args:
            None (instance method, only ``self``).

        Returns:
            AbstractPersistence: ``self``, so it can be bound with ``as``.

        Tests:
            1. ``with ZooDatabase() as storage:`` binds ``storage``
               to the same object the constructor produced.
            2. Inside the ``with`` block, ``save_day`` works normally --
               entering does not change any state.
        """
        return self

    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> bool:
        """Leave the ``with`` block and close the storage.

        Args:
            exc_type (Any): Exception class if the block was left through an
                exception, otherwise ``None``.
            exc_value (Any): The exception instance, or ``None``.
            traceback (Any): The traceback object, or ``None``.

        Returns:
            bool: Always ``False``, so an exception raised inside the block
            keeps propagating and is never silently swallowed.

        Tests:
            1. Leaving the block normally calls :meth:`close` exactly once.
            2. Raising a ``ValueError`` inside the block still calls
               :meth:`close`, and the ``ValueError`` reaches the caller
               (return value ``False``).
        """
        self.close()
        return False
