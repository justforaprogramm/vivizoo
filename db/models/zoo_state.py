"""Model for the ``zoo_state`` table -- the root of a savegame.

While :mod:`db.models.daily_stats` and :mod:`db.models.event` cover the
analytics side (step 1), this table starts the savegame side (step 2).

One row equals **one save slot**. Everything else that belongs to a saved
game -- enclosures, animals, status effects, inventory -- hangs off this row
through cascading relationships. Saving therefore means writing a single
object graph, and deleting a slot wipes all of its children automatically.

    ZooState
      +-- InventoryItem[]
      +-- Enclosure[]
            +-- Animal[]
                  +-- AnimalStatusEffect[]

Part of the vivizoo project. Module owner: Jannes (database).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, Enum as SAEnum, Float, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from db.interface.enums import TimeOfDay
from db.models.base import Base, TimestampMixin

if TYPE_CHECKING:  # imported for type checkers only, not at runtime
    from db.models.enclosure import Enclosure
    from db.models.inventory import InventoryItem

__all__ = ["ZooState"]


class ZooState(TimestampMixin, Base):
    """Global state of one saved game.

    Attributes:
        id (int): Save slot number and primary key. The MVP uses a single
            slot (``1``); see ``db/docs/architecture.md``, section "Known
            limitations", for how to support several.
        tick_count (int): Current simulation tick.
        game_day (int): Current simulation day.
        time_of_day (TimeOfDay): Current phase of the day. Accepts an enum
            member or the equivalent plain string.
        zoo_open (bool): Whether the zoo is currently open to visitors.
        money (float): Current account balance.
        reputation (int): Current reputation score.
        ticket_price (float): Current admission price.
        created_at (datetime): Real-world timestamp of the save, inherited
            from :class:`~db.models.base.TimestampMixin`.
        inventory (list[InventoryItem]): Stock levels of this save.
        enclosures (list[Enclosure]): Enclosures of this save, each holding
            its own animals.

    Example:
        >>> state = ZooState(
        ...     id=1, tick_count=4500, game_day=3,
        ...     time_of_day=TimeOfDay.NIGHT, zoo_open=False,
        ...     money=15400.5, reputation=85, ticket_price=12.5,
        ... )
    """

    __tablename__ = "zoo_state"
    __table_args__ = (
        CheckConstraint("tick_count >= 0", name="ck_zoo_state_tick"),
        CheckConstraint("game_day >= 0", name="ck_zoo_state_day"),
        CheckConstraint("ticket_price >= 0", name="ck_zoo_state_price"),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        doc="Save slot number.",
    )
    tick_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    game_day: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    time_of_day: Mapped[TimeOfDay] = mapped_column(
        SAEnum(TimeOfDay, native_enum=False, length=16),
        default=TimeOfDay.MORNING,
        nullable=False,
    )
    zoo_open: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    money: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    reputation: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    ticket_price: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    inventory: Mapped[list["InventoryItem"]] = relationship(
        back_populates="zoo",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    enclosures: Mapped[list["Enclosure"]] = relationship(
        back_populates="zoo",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="Enclosure.enclosure_id",
    )

    @validates("time_of_day")
    def _coerce_time_of_day(self, field: str, value: TimeOfDay | str) -> TimeOfDay:
        """Accept both enum members and plain strings for ``time_of_day``.

        Args:
            field (str): Name of the attribute being set -- always
                ``"time_of_day"`` here. Supplied by SQLAlchemy.
            value (TimeOfDay | str): A ``TimeOfDay`` member or a string
                matching one of its values (e.g. ``"NIGHT"``).

        Returns:
            TimeOfDay: The matching enum member, which is what gets stored.

        Raises:
            ValueError: If ``value`` is a string that matches no member.

        Tests:
            1. ``ZooState(time_of_day="NIGHT").time_of_day`` equals
               ``TimeOfDay.NIGHT`` -- the string was coerced.
            2. ``ZooState(time_of_day="MIDNIGHT")`` raises ``ValueError``,
               while passing ``TimeOfDay.NOON`` returns it unchanged.
        """
        if isinstance(value, TimeOfDay):
            return value
        try:
            return TimeOfDay(value)
        except ValueError as error:
            allowed = ", ".join(member.value for member in TimeOfDay)
            raise ValueError(
                f"{field}={value!r} is not a valid TimeOfDay. Valid values: {allowed}."
            ) from error

    def total_animals(self) -> int:
        """Count all animals across every enclosure of this save.

        Walks the already-loaded object graph; because every relationship in
        this module uses ``lazy="selectin"``, no additional query is issued.

        Args:
            None (instance method, only ``self``).

        Returns:
            int: Total number of animal rows attached to this save,
            including dead ones. ``0`` if the zoo has no enclosures.

        Tests:
            1. A ``ZooState`` with two enclosures holding 3 and 2 animals
               returns ``5``.
            2. A ``ZooState`` with no enclosures returns ``0``, and one with
               an empty enclosure also returns ``0`` (edge case: enclosure
               exists but is unoccupied).
        """
        return sum(len(enclosure.animals) for enclosure in self.enclosures)

    def next_animal_id(self, prefix: str = "a_") -> str:
        """Return an animal identifier that is not in use in this savegame.

        Identifiers are chosen by the caller rather than the database, because
        the simulation needs them **before** anything is stored -- a message
        can reference ``entity_id="a_01"`` on the first tick, long before the
        first save. This helper takes the bookkeeping off your hands and, more
        importantly, keeps working after a savegame has been loaded: it counts
        from the highest identifier already present instead of restarting at
        one.

        Args:
            prefix (str): Text placed before the number. Defaults to ``"a_"``,
                producing ``"a_01"``, ``"a_02"`` and so on.

        Returns:
            str: The next free identifier, numbered with at least two digits.
            ``"a_01"`` for an empty zoo.

        Tests:
            1. On a zoo holding ``a_01`` and ``a_02`` the method returns
               ``"a_03"``; on an empty zoo it returns ``"a_01"``.
            2. On a zoo holding only ``a_07`` it returns ``"a_08"`` -- the
               highest number wins, not the count of animals, so identifiers
               are never reused after one has been removed.
        """
        used = {
            animal.animal_id
            for enclosure in self.enclosures
            for animal in enclosure.animals
        }
        return _next_free_id(used, prefix)

    def next_enclosure_id(self, prefix: str = "e_") -> str:
        """Return an enclosure identifier that is not in use in this savegame.

        Counterpart of :meth:`next_animal_id`; the same reasoning applies.

        Args:
            prefix (str): Text placed before the number. Defaults to ``"e_"``.

        Returns:
            str: The next free identifier, e.g. ``"e_03"``. ``"e_01"`` for a
            zoo without enclosures.

        Tests:
            1. On a zoo holding ``e_01`` and ``e_02`` the method returns
               ``"e_03"``; on an empty zoo it returns ``"e_01"``.
            2. Calling it twice without adding an enclosure in between returns
               the same value both times -- it reports the next free id, it
               does not reserve one.
        """
        used = {enclosure.enclosure_id for enclosure in self.enclosures}
        return _next_free_id(used, prefix)


def _next_free_id(used: set[str], prefix: str) -> str:
    """Build the next identifier after the highest number already used.

    Shared by :meth:`ZooState.next_animal_id` and
    :meth:`ZooState.next_enclosure_id`. Identifiers that do not match
    ``prefix`` followed by digits are ignored, so hand-written ones like
    ``"lion_pen"`` never break the numbering.

    Args:
        used (set[str]): Identifiers already taken.
        prefix (str): The prefix to match and to reuse for the new value.

    Returns:
        str: ``prefix`` followed by the next number, padded to at least two
        digits. Starts at ``01`` when nothing matches.

    Tests:
        1. ``_next_free_id({"a_01", "a_02"}, "a_")`` returns ``"a_03"``, and
           ``_next_free_id(set(), "a_")`` returns ``"a_01"``.
        2. ``_next_free_id({"a_09", "lion_pen"}, "a_")`` returns ``"a_10"`` --
           the non-matching identifier is ignored and the padding grows
           correctly.
    """
    highest = 0
    for identifier in used:
        if not identifier.startswith(prefix):
            continue
        suffix = identifier[len(prefix):]
        if suffix.isdigit():
            highest = max(highest, int(suffix))
    return f"{prefix}{highest + 1:02d}"
