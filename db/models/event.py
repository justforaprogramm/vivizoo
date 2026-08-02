"""Model for the ``events`` table -- the persistent chat and system log.

Every message the simulation produces can be archived here
so the player can review what happened on a given day. A UI renders
these rows as the chat feed.

Write pattern:
    Events are collected in memory during the day and flushed **in one batch**
    at the end of the day, together with the :class:`~db.models.daily_stats.DailyStats`
    row. A single ``executemany`` for 50 rows is far cheaper than 50
    individual inserts.

Part of the vivizoo project. Module owner: Jannes (database).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    JSON,
    Enum as SAEnum,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from db.interface.enums import EventType
from db.models.base import Base

if TYPE_CHECKING:  # imported for type checkers only, not at runtime
    from db.models.daily_stats import DailyStats

__all__ = ["Event"]


class Event(Base):
    """A single log message produced by the simulation.

    Attributes:
        id (int): Auto-incrementing primary key. Never set this manually --
            the database assigns it on insert.
        day_id (int): Simulation day the message belongs to. Foreign key to
            ``daily_stats.day_id``; deleting a day deletes its events.
        tick_count (int): Exact simulation tick the message was produced at.
            Lets a UI order messages within a day.
        type (EventType): Severity of the message. Accepts either an
            :class:`~db.interface.enums.EventType` member or the equivalent
            plain string.
        text (str): The message body itself.
        entity_id (str | None): Optional identifier of the affected object,
            e.g. ``"a_01"`` for an animal or ``"e_03"`` for an enclosure.
            Lets a UI jump to the entity when a line is clicked.
        details (dict | None): Optional structured payload, stored as JSON,
            e.g. ``{"cause": "starvation", "days_without_food": 3}``. New
            kinds of event never require a schema change.
        day (DailyStats): The day this event belongs to (relationship).

    Example:
        >>> Event(
        ...     day_id=1, tick_count=4500, type=EventType.WARNING,
        ...     text="Lion 'Hungry Harry' is starving!", entity_id="a_01",
        ... )
    """

    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    day_id: Mapped[int] = mapped_column(
        ForeignKey("daily_stats.day_id", ondelete="CASCADE"),
        index=True,
        nullable=False,
        doc="Simulation day this message belongs to.",
    )
    tick_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    type: Mapped[EventType] = mapped_column(
        SAEnum(EventType, native_enum=False, length=16),
        nullable=False,
        doc="Severity; stored as VARCHAR with a CHECK constraint.",
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    entity_id: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    details: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
        default=None,
        doc="Optional structured payload; avoids schema changes for new event kinds.",
    )

    day: Mapped["DailyStats"] = relationship(back_populates="events")

    @validates("type")
    def _coerce_type(self, field: str, value: EventType | str) -> EventType:
        """Accept both enum members and plain strings for the ``type`` column.

        Makes the application's life easier: ``Event(type="WARNING")`` works just
        as well as ``Event(type=EventType.WARNING)``. Invalid strings are
        rejected immediately instead of failing later at insert time.

        Args:
            field (str): Name of the attribute being set -- always ``"type"``
                here. Supplied by SQLAlchemy.
            value (EventType | str): Either an ``EventType`` member or a
                string matching one of its values (e.g. ``"WARNING"``).

        Returns:
            EventType: The matching enum member. This is what actually gets
            stored.

        Raises:
            ValueError: If ``value`` is a string that does not match any
                ``EventType`` member.

        Tests:
            1. ``Event(day_id=1, type="WARNING", text="x").type`` equals
               ``EventType.WARNING`` -- the string was coerced into an enum
               member.
            2. ``Event(day_id=1, type="PANIC", text="x")`` raises
               ``ValueError``; passing ``EventType.INFO`` directly returns it
               unchanged (pass-through case).
        """
        if isinstance(value, EventType):
            return value
        try:
            return EventType(value)
        except ValueError as error:
            allowed = ", ".join(member.value for member in EventType)
            raise ValueError(
                f"{field}={value!r} is not a valid EventType. Valid values: {allowed}."
            ) from error

    def is_problem(self) -> bool:
        """Report whether this message signals something going wrong.

        Convenience helper for a UI, which highlights problematic
        lines and can offer a "problems only" filter.

        Args:
            None (instance method, only ``self``).

        Returns:
            bool: ``True`` for :attr:`~db.interface.enums.EventType.WARNING`
            and :attr:`~db.interface.enums.EventType.ERROR`, ``False`` for
            ``INFO`` and ``SUCCESS``.

        Tests:
            1. An event with ``type=EventType.ERROR`` returns ``True``; one
               with ``type=EventType.WARNING`` also returns ``True``.
            2. An event with ``type=EventType.SUCCESS`` returns ``False``, and
               so does ``EventType.INFO`` -- confirming success is not treated
               as a problem.
        """
        return self.type in (EventType.WARNING, EventType.ERROR)
