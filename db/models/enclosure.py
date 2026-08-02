"""Model for the ``enclosures`` table -- the containers holding animals.

An enclosure belongs to exactly one save slot and aggregates the animals
living in it. Deleting a save deletes its enclosures, and deleting an
enclosure deletes its animals (composition, expressed through
``cascade="all, delete-orphan"``).

Part of the vivizoo project. Module owner: Jannes (database).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from db.models.base import Base

if TYPE_CHECKING:  # imported for type checkers only, not at runtime
    from db.models.animal import Animal
    from db.models.zoo_state import ZooState

__all__ = ["Enclosure"]


class Enclosure(Base):
    """A single enclosure of a saved zoo.

    Attributes:
        enclosure_id (str): Identifier such as ``"e_01"``. Primary key,
            assigned by the caller.
        zoo_id (int): Save slot this enclosure belongs to (foreign key to
            ``zoo_state.id``).
        name (str): Display name, e.g. ``"Savanna 1"``.
        biome (str): Landscape type, e.g. ``"savanna"`` or ``"arctic"``.
            Deliberately a free-text column rather than an enum so new biomes
            need no schema change.
        capacity (int): Maximum number of animals that fit in.
        cleanliness (float): Current cleanliness in percent (0--100).
        zoo (ZooState): The save slot this enclosure belongs to.
        animals (list[Animal]): Animals living in this enclosure.

    Example:
        >>> Enclosure(
        ...     enclosure_id="e_01", zoo_id=1, name="Savanna 1",
        ...     biome="savanna", capacity=8, cleanliness=95.0,
        ... )
    """

    __tablename__ = "enclosures"
    __table_args__ = (
        CheckConstraint("cleanliness BETWEEN 0 AND 100", name="ck_enclosure_clean"),
        CheckConstraint("capacity >= 0", name="ck_enclosure_capacity"),
    )

    enclosure_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    zoo_id: Mapped[int] = mapped_column(
        ForeignKey("zoo_state.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    biome: Mapped[str] = mapped_column(String(40), nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cleanliness: Mapped[float] = mapped_column(Float, default=100.0, nullable=False)

    zoo: Mapped["ZooState"] = relationship(back_populates="enclosures")
    animals: Mapped[list["Animal"]] = relationship(
        back_populates="enclosure",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="Animal.animal_id",
    )

    @validates("cleanliness")
    def _check_cleanliness(self, field: str, value: float) -> float:
        """Keep the cleanliness percentage inside 0--100.

        Args:
            field (str): Name of the attribute being set -- always
                ``"cleanliness"`` here. Supplied by SQLAlchemy.
            value (float): The value about to be assigned.

        Returns:
            float: The unchanged value if it is valid.

        Raises:
            ValueError: If ``value`` is below 0 or above 100.

        Tests:
            1. Assigning ``cleanliness = 0.0`` succeeds -- a filthy enclosure
               is legal (lower boundary).
            2. Assigning ``cleanliness = 100.1`` raises ``ValueError``, and so
               does ``-0.1`` (just outside both boundaries).
        """
        if not 0 <= value <= 100:
            raise ValueError(f"{field} must be between 0 and 100, got {value}.")
        return value

    def free_slots(self) -> int:
        """Return how many more animals fit into this enclosure.

        Dead animals still occupy a slot until the application removes them, so
        the count is based on all attached rows.

        Args:
            None (instance method, only ``self``).

        Returns:
            int: ``capacity - len(animals)``, clamped at ``0`` so an
            over-occupied enclosure never reports a negative number.

        Tests:
            1. An enclosure with ``capacity=8`` holding 3 animals returns
               ``5``.
            2. An enclosure with ``capacity=2`` holding 2 animals returns
               ``0``; one holding 3 animals also returns ``0`` rather than
               ``-1`` (clamping edge case).
        """
        return max(0, self.capacity - len(self.animals))

    def is_full(self) -> bool:
        """Report whether the enclosure has no room left.

        Args:
            None (instance method, only ``self``).

        Returns:
            bool: ``True`` if no further animal fits in, otherwise ``False``.

        Tests:
            1. An enclosure with ``capacity=2`` holding 2 animals returns
               ``True``.
            2. An enclosure with ``capacity=2`` holding 1 animal returns
               ``False``; one with ``capacity=0`` returns ``True`` even
               though it holds no animals at all.
        """
        return self.free_slots() == 0
