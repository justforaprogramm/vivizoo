"""Model for the ``animal_status_effects`` table -- temporary animal states.

One row equals one active effect on one animal, e.g. "animal a_01 is
poisoned for another 40 ticks". Effects are deleted automatically when their
animal is deleted (composition).

The effect name is a free-text column rather than an enum, because phase 2
of the application plan keeps adding new effects (``Hungry``, ``Poisoned``,
``Malnourished``, ``Stressed``, ...). Keeping it open means new effects never
require a schema change.

Part of the vivizoo project. Module owner: Jannes (database).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from db.models.base import Base

if TYPE_CHECKING:  # imported for type checkers only, not at runtime
    from db.models.animal import Animal

__all__ = ["AnimalStatusEffect"]


class AnimalStatusEffect(Base):
    """A temporary effect currently applied to an animal.

    Attributes:
        id (int): Auto-incrementing primary key. Never set this manually.
        animal_id (str): Affected animal (foreign key to
            ``animals.animal_id``).
        effect_name (str): Name of the effect, e.g. ``"Poisoned"`` or
            ``"Stressed"``.
        remaining_ticks (int): How many more ticks the effect lasts. ``0``
            means it expires with the current tick.
        animal (Animal): The affected animal (relationship).

    Example:
        >>> AnimalStatusEffect(
        ...     animal_id="a_01", effect_name="Poisoned", remaining_ticks=40
        ... )
    """

    __tablename__ = "animal_status_effects"
    __table_args__ = (
        CheckConstraint("remaining_ticks >= 0", name="ck_effect_remaining"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    animal_id: Mapped[str] = mapped_column(
        ForeignKey("animals.animal_id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    effect_name: Mapped[str] = mapped_column(String(60), nullable=False)
    remaining_ticks: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    animal: Mapped["Animal"] = relationship(back_populates="status_effects")

    @validates("remaining_ticks")
    def _check_remaining(self, field: str, value: int) -> int:
        """Reject a negative remaining duration.

        A negative duration has no meaning: an expired effect is removed from
        the list rather than counted down past zero.

        Args:
            field (str): Name of the attribute being set -- always
                ``"remaining_ticks"`` here. Supplied by SQLAlchemy.
            value (int): The duration about to be assigned.

        Returns:
            int: The unchanged value if it is zero or positive.

        Raises:
            ValueError: If ``value`` is negative.

        Tests:
            1. ``AnimalStatusEffect(animal_id="a_01", effect_name="Stressed",
               remaining_ticks=0)`` is accepted -- zero is valid and means the
               effect expires now (boundary case).
            2. Assigning ``remaining_ticks = -1`` raises ``ValueError``.
        """
        if value < 0:
            raise ValueError(f"{field} must not be negative, got {value}.")
        return value

    def is_expired(self) -> bool:
        """Report whether the effect has run out.

        Args:
            None (instance method, only ``self``).

        Returns:
            bool: ``True`` if :attr:`remaining_ticks` has reached ``0``,
            otherwise ``False``.

        Tests:
            1. An effect with ``remaining_ticks=0`` returns ``True``.
            2. An effect with ``remaining_ticks=1`` returns ``False``
               (boundary directly above the threshold).
        """
        return self.remaining_ticks == 0
