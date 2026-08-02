"""Model for the ``daily_stats`` table -- the end-of-day summary.

One row equals one finished simulation day. This table is the basis for
every chart in a UI (revenue, visitor and welfare trends across
multiple days).

It is written **exactly once per simulation day**, at the end of the night
phase -- never per tick. See ``db/docs/architecture.md``, section
"When is data written".

Part of the vivizoo project. Module owner: Jannes (database).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Computed, Float, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from db.models.base import Base, TimestampMixin

if TYPE_CHECKING:  # imported for type checkers only, not at runtime
    from db.models.event import Event

__all__ = ["DailyStats"]


class DailyStats(TimestampMixin, Base):
    """Key figures of one finished simulation day.

    Attributes:
        day_id (int): Number of the simulation day (1, 2, 3 ...). Primary key
            -- exactly one row exists per day. Assigned by the application, *not*
            auto-incremented.
        total_visitors (int): Number of visitors on that day.
        revenue (float): Sum of all income (ticket sales).
        expenses (float): Sum of all spending (food, salaries).
        profit_loss (float | None): ``revenue - expenses``. **Computed
            column** -- see the note below.
        avg_animal_welfare (float): Average welfare of all living animals in
            percent (0--100).
        avg_happiness (float): Average visitor satisfaction in percent
            (0--100).
        reputation_end_of_day (int): Zoo reputation at the end of the day.
        animals_died (int): Number of animals that died on that day.
        created_at (datetime): Real-world timestamp, inherited from
            :class:`~db.models.base.TimestampMixin`.
        events (list[Event]): All messages belonging to this day. A
            relationship, not a column -- deleting a day takes its events
            with it (composition).

    Note on ``profit_loss``:
        The column is declared as ``GENERATED ALWAYS AS (revenue - expenses)``.
        The **database** computes the value, so it can never drift away from
        ``revenue`` and ``expenses``. Two consequences for the application:

        * The value must **not** be passed to the constructor.
        * On a freshly created object it is ``None``. It is only populated on
          objects **read back** from the database, i.e. on everything
          returned by ``get_stats()``.

    Example:
        >>> day = DailyStats(
        ...     day_id=1, total_visitors=120,
        ...     revenue=840.0, expenses=300.0,
        ...     avg_animal_welfare=88.5, avg_happiness=91.0,
        ...     reputation_end_of_day=85, animals_died=0,
        ... )
        >>> day.profit_loss is None    # not in the database yet
        True
    """

    __tablename__ = "daily_stats"
    __table_args__ = (
        CheckConstraint(
            "avg_animal_welfare BETWEEN 0 AND 100", name="ck_daily_stats_welfare"
        ),
        CheckConstraint(
            "avg_happiness BETWEEN 0 AND 100", name="ck_daily_stats_happiness"
        ),
        CheckConstraint("total_visitors >= 0", name="ck_daily_stats_visitors"),
        CheckConstraint("animals_died >= 0", name="ck_daily_stats_deaths"),
    )

    day_id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=False,
        doc="Simulation day number; assigned by the caller.",
    )
    total_visitors: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    revenue: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    expenses: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    profit_loss: Mapped[float | None] = mapped_column(
        Float,
        Computed("revenue - expenses"),
        nullable=True,
        doc="Computed by the database -- do not set manually.",
    )
    avg_animal_welfare: Mapped[float] = mapped_column(
        Float, default=0.0, nullable=False
    )
    avg_happiness: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    reputation_end_of_day: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    animals_died: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    events: Mapped[list["Event"]] = relationship(
        back_populates="day",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="Event.id",
    )

    @validates("avg_animal_welfare", "avg_happiness")
    def _check_percentage(self, field: str, value: float) -> float:
        """Guarantee that percentage values stay within 0--100.

        SQLAlchemy calls this hook **automatically** whenever one of the
        listed attributes is assigned -- including inside the constructor. An
        invalid value therefore never even reaches the database
        (encapsulation / data integrity).

        Args:
            field (str): Name of the attribute being set, e.g.
                ``"avg_animal_welfare"``. Supplied by SQLAlchemy, not by the
                caller.
            value (float): The value about to be assigned.

        Returns:
            float: The unchanged value if it is valid. Only this return value
            is actually stored.

        Raises:
            ValueError: If ``value`` is below 0 or above 100.

        Tests:
            1. ``DailyStats(day_id=1, avg_animal_welfare=50.0)`` is created
               successfully and ``obj.avg_animal_welfare`` equals ``50.0``
               (happy path, value untouched).
            2. ``DailyStats(day_id=1, avg_animal_welfare=101.0)`` raises
               ``ValueError``, and so does ``-1.0`` (both just outside the
               boundary), while ``0.0`` and ``100.0`` are accepted.
        """
        if not 0 <= value <= 100:
            raise ValueError(f"{field} must be between 0 and 100, got {value}.")
        return value

    @validates("profit_loss")
    def _reject_profit_loss(self, field: str, value: float) -> float:
        """Refuse any attempt to set the computed column by hand.

        ``profit_loss`` is calculated by the database as
        ``revenue - expenses``. Without this hook, passing it to the
        constructor would succeed silently and only fail much later, on
        insert, with a cryptic SQLite message ("cannot INSERT into generated
        column"). Failing here instead points straight at the line that
        caused it.

        Args:
            field (str): Name of the attribute being set -- always
                ``"profit_loss"`` here. Supplied by SQLAlchemy.
            value (float): The value the caller tried to assign.

        Returns:
            float: Never returns -- the method always raises. The return type
            is declared only because SQLAlchemy validators are expected to
            return the value they accept.

        Raises:
            ValueError: Always, explaining that the column is computed and
                naming the two fields to set instead.

        Tests:
            1. ``DailyStats(day_id=1, profit_loss=500.0)`` raises
               ``ValueError`` at construction, and the message mentions both
               ``revenue`` and ``expenses``.
            2. ``DailyStats(day_id=1, revenue=100.0, expenses=40.0)`` is
               created without error and its ``profit_loss`` is ``None``
               until the row has been read back from the database.
        """
        raise ValueError(
            f"{field} is computed by the database as 'revenue - expenses' and "
            f"must not be set manually (got {value!r}). Set revenue and "
            f"expenses instead; the value appears on objects read back via "
            f"get_stats()."
        )

    def is_profitable(self) -> bool:
        """Report whether the day closed with a surplus.

        Deliberately derived from ``revenue`` and ``expenses`` instead of
        :attr:`profit_loss`, so the method also works on freshly created
        objects that have not been through the database yet.

        Args:
            None (instance method, only ``self``).

        Returns:
            bool: ``True`` if ``revenue > expenses``, otherwise ``False``.
            An exactly break-even day returns ``False``.

        Tests:
            1. ``DailyStats(day_id=1, revenue=840.0, expenses=300.0).is_profitable()``
               returns ``True``.
            2. With ``revenue == expenses`` (e.g. both ``100.0``) the method
               returns ``False``; with ``revenue=0.0, expenses=50.0`` it also
               returns ``False``.
        """
        return self.revenue > self.expenses
