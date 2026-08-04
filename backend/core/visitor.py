"""The visitor entity.

A :class:`Visitor` is a lightweight, short-lived creature: it spawns at the
gate, wanders a little, and despawns after a fixed lifetime, paying its
ticket on arrival. The map coordinates are updated every tick so the frontend
gets smooth movement; the lifetime countdown and the ticket payment are the
economic part.
"""

from __future__ import annotations

import random


class Visitor:
    """A single guest inside the zoo.

    Args:
        visitor_id (str): Unique identifier, e.g. ``"v_99"``.
        x (int), y (int): Spawn position (the gate).
        remaining_ticks (int): How many ticks the visitor stays.

    Attributes:
        visitor_id (str): Unique identifier.
        x (int), y (int): Current position.
        remaining_ticks (int): Ticks left before despawn.
    """

    def __init__(
        self,
        visitor_id: str,
        x: int,
        y: int,
        remaining_ticks: int,
    ) -> None:
        """Create a visitor at a position with a limited lifetime.

        Args:
            visitor_id (str): Unique identifier.
            x (int), y (int): Spawn position.
            remaining_ticks (int): Persistence in ticks; must be non-negative.

        Returns:
            None (constructor).

        Tests:
            1. A fresh visitor has the given coordinates and lifetime.
            2. ``remaining_ticks=0`` means it despawns on the next tick.
        """
        if remaining_ticks < 0:
            raise ValueError(
                f"remaining_ticks must not be negative, got {remaining_ticks}."
            )
        self.visitor_id = visitor_id
        self.x = x
        self.y = y
        self.remaining_ticks = remaining_ticks

    def move(self) -> None:
        """Take one random-walk step within a small radius.

        Args:
            None.

        Returns:
            None.

        Tests:
            1. Position changes by a small bounded amount.
        """
        self.x += random.randint(-2, 2)
        self.y += random.randint(-2, 2)

    def tick(self) -> None:
        """Advance the visitor by one tick (moving and aging).

        Args:
            None.

        Returns:
            None.

        Tests:
            1. ``remaining_ticks`` drops by one; position changed.
        """
        if self.remaining_ticks > 0:
            self.remaining_ticks -= 1
        self.move()

    def is_leaving(self) -> bool:
        """Report whether the visitor should be removed now.

        Args:
            None.

        Returns:
            bool: ``True`` when ``remaining_ticks`` reached ``0``.

        Tests:
            1. Starting at ``1``, after one :meth:`tick` it returns ``True``.
        """
        return self.remaining_ticks == 0

    def to_dict(self) -> dict:
        """Render the visitor's map data for the frontend.

        Args:
            None.

        Returns:
            dict: With ``id``, ``x`` and ``y``.

        Tests:
            1. The dict exposes the three map keys.
        """
        return {"id": self.visitor_id, "x": self.x, "y": self.y}

    def __repr__(self) -> str:  # pragma: no cover - debugging
        """Return a short readable representation.

        Args:
            None.

        Returns:
            str: Named debug string.
        """
        return f"<Visitor {self.visitor_id} ({self.x},{self.y}) {self.remaining_ticks} ticks>"
