"""Model for the ``inventory`` table -- stock levels of a savegame.

One row equals one resource type of one save slot, e.g. "save 1 holds 15
units of meat". The primary key is composite (``zoo_id`` + ``food_type``),
which makes it structurally impossible to store the same resource twice for
the same save.

Part of the vivizoo project. Module owner: Jannes (database).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Enum as SAEnum, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from db.interface.enums import FoodType
from db.models.base import Base

if TYPE_CHECKING:  # imported for type checkers only, not at runtime
    from db.models.zoo_state import ZooState

__all__ = ["InventoryItem"]


class InventoryItem(Base):
    """Amount of one resource type held in a save slot.

    Attributes:
        zoo_id (int): Save slot this stock belongs to. Part of the composite
            primary key and a foreign key to ``zoo_state.id``.
        food_type (FoodType): Which resource. Second half of the composite
            primary key -- a slot can hold each type at most once. Accepts an
            enum member or the equivalent plain string.
        amount (int): How many units are in stock. Never negative, enforced
            both in Python and by a ``CHECK`` constraint.
        zoo (ZooState): The save slot this row belongs to (relationship).

    Example:
        >>> InventoryItem(zoo_id=1, food_type=FoodType.MEAT, amount=15)
    """

    __tablename__ = "inventory"
    __table_args__ = (CheckConstraint("amount >= 0", name="ck_inventory_amount"),)

    zoo_id: Mapped[int] = mapped_column(
        ForeignKey("zoo_state.id", ondelete="CASCADE"),
        primary_key=True,
    )
    food_type: Mapped[FoodType] = mapped_column(
        SAEnum(FoodType, native_enum=False, length=16),
        primary_key=True,
    )
    amount: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    zoo: Mapped["ZooState"] = relationship(back_populates="inventory")

    @validates("food_type")
    def _coerce_food_type(self, field: str, value: FoodType | str) -> FoodType:
        """Accept both enum members and plain strings for ``food_type``.

        Args:
            field (str): Name of the attribute being set -- always
                ``"food_type"`` here. Supplied by SQLAlchemy.
            value (FoodType | str): A ``FoodType`` member or a string matching
                one of its values (e.g. ``"MEAT"``).

        Returns:
            FoodType: The matching enum member, which is what gets stored.

        Raises:
            ValueError: If ``value`` is a string that matches no member.

        Tests:
            1. ``InventoryItem(zoo_id=1, food_type="FISH").food_type`` equals
               ``FoodType.FISH``.
            2. ``InventoryItem(zoo_id=1, food_type="HAY")`` raises
               ``ValueError``; passing ``FoodType.PLANTS`` returns it
               unchanged.
        """
        if isinstance(value, FoodType):
            return value
        try:
            return FoodType(value)
        except ValueError as error:
            allowed = ", ".join(member.value for member in FoodType)
            raise ValueError(
                f"{field}={value!r} is not a valid FoodType. Valid values: {allowed}."
            ) from error

    @validates("amount")
    def _check_amount(self, field: str, value: int) -> int:
        """Reject negative stock levels before they reach the database.

        The ``CHECK`` constraint on the table catches this as well, but the
        validator fails earlier and with a far more readable message.

        Args:
            field (str): Name of the attribute being set -- always
                ``"amount"`` here. Supplied by SQLAlchemy.
            value (int): The amount about to be assigned.

        Returns:
            int: The unchanged value if it is zero or positive.

        Raises:
            ValueError: If ``value`` is negative.

        Tests:
            1. ``InventoryItem(zoo_id=1, food_type=FoodType.MEAT, amount=0)``
               is accepted -- zero is a valid stock level (boundary case).
            2. Assigning ``amount = -1`` raises ``ValueError`` and the object
               keeps its previous value.
        """
        if value < 0:
            raise ValueError(f"{field} must not be negative, got {value}.")
        return value
