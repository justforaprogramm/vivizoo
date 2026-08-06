"""Adapter that maps backend domain state onto the database contract.

:class:`DbGateway` wraps an :class:`db.interface.AbstractPersistence` and
offers the backend a small, focused API. It translates domain facts (a zoo's
daily snapshot, the pending chat messages) into the model objects the
database module already knows -- :class:`db.models.DailyStats` and
:class:`db.models.Event` -- and calls the persistence methods.

This is the *only* place in the backend that imports from ``db``. It performs
**no schema work**; tables are owned entirely by the database module.

Module owner: Benjamin (backend).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Iterable

from db.interface import AbstractPersistence
from db.interface.enums import EventType
from db.models import DailyStats, Event

if TYPE_CHECKING:  # type checkers only, avoids a runtime cycle
    from backend.core.zoo import Zoo


class DbGateway:
    """The backend's only doorway to persistent storage.

    Args:
        persistence (AbstractPersistence): The storage implementation to
            write through, e.g. ``ZooDatabase()``.
    """

    def __init__(self, persistence: AbstractPersistence) -> None:
        """Hold the storage implementation.

        Args:
            persistence (AbstractPersistence): Any concrete storage object.

        Returns:
            None (constructor).

        Tests:
            1. A gateway keeps its storage for later use.
        """
        self._persistence = persistence

    def save_daily_summary(self, zoo: "Zoo") -> None:
        """Persist a finished day and its messages in one transaction.

        Args:
            zoo (Zoo): The zoo whose ``daily_snapshot()`` and drained chat
                log are written to storage.

        Returns:
            None.

        Tests:
            1. A day is written without raising for an empty zoo.
            2. The chat messages share the day's ``day_id``.
        """
        snapshot = zoo.daily_snapshot()
        stats = DailyStats(
            day_id=snapshot["day_id"],
            total_visitors=snapshot["total_visitors"],
            revenue=snapshot["revenue"],
            expenses=snapshot["expenses"],
            avg_animal_welfare=snapshot["avg_animal_welfare"],
            avg_happiness=snapshot["avg_happiness"],
            reputation_end_of_day=snapshot["reputation_end_of_day"],
            animals_died=snapshot["animals_died"],
        )
        events = self._build_events(zoo, snapshot["day_id"])
        self._persistence.save_day(stats, events)

    def _build_events(self, zoo: "Zoo", day_id: int) -> list[Event]:
        """Convert the drained chat log into database ``Event`` objects.

        Args:
            zoo (Zoo): The zoo whose logger is drained.
            day_id (int): The day the messages belong to.

        Returns:
            list[Event]: Persistable events, oldest first.

        Tests:
            1. A ``WARNING`` log entry becomes an ``Event`` with the matching
               type and text.
        """
        entries = zoo.logger.drain()
        events: list[Event] = []
        for entry in entries:
            message_type = EventType(entry.message_type)
            events.append(
                Event(
                    day_id=day_id,
                    tick_count=entry.tick_count,
                    type=message_type,
                    text=entry.text,
                    entity_id=entry.entity_id,
                    details=entry.details,
                )
            )
        return events

    def fetch_stats(self, days_back: int = 30) -> Iterable[dict]:
        """Read recent daily summaries as plain dictionaries for charts.

        Args:
            days_back (int): How many days to read.

        Returns:
            Iterable[dict]: Each day as a dict (see ``docs/api.md``).

        Tests:
            1. After a day was saved, at least one dict is returned.
        """
        rows = self._persistence.get_stats(days_back)
        return [
            {
                "day_id": row.day_id,
                "total_visitors": row.total_visitors,
                "revenue": row.revenue,
                "expenses": row.expenses,
                "profit_loss": row.profit_loss,
                "avg_animal_welfare": row.avg_animal_welfare,
                "avg_happiness": row.avg_happiness,
                "reputation_end_of_day": row.reputation_end_of_day,
                "animals_died": row.animals_died,
            }
            for row in rows
        ]
