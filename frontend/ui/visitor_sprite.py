"""
VisitorSprite — visual representation of a zoo visitor on the map.

Rendered as a small 5×5 px coloured ellipse. Visitors are NOT
interactive — no hover or click events. Colour is randomly assigned
at construction and remains stable for the visitor's lifetime.

Tests:
    - test_sprite_is_correct_size: Create sprite; verify bounding rect
      is 5×5 px.
    - test_sprite_updates_position: Call update_state(100, 200); verify
      pos() ≈ (98, 198) (centred: x-2, y-2).
"""

from typing import Optional
import random

from PyQt6.QtWidgets import QGraphicsEllipseItem, QGraphicsItem
from PyQt6.QtGui import QBrush, QColor

from frontend.core.constants import Z_VISITORS

# ── Visitor pastel palette ────────────────────────────────────────────────
_VISITOR_COLORS = [
    "#f4a460",  # sandy brown
    "#87ceeb",  # sky blue
    "#90ee90",  # light green
    "#dda0dd",  # plum
    "#f0e68c",  # khaki
]

SPRITE_SIZE = 5


class VisitorSprite(QGraphicsEllipseItem):
    """Small coloured dot representing a zoo visitor.

    Visitors are non-interactive — no hover or click events.
    Colour is randomly assigned at construction and remains stable.

    Tests:
        - test_sprite_is_correct_size: Create sprite; verify bounding rect
          is 5×5 px.
        - test_sprite_updates_position: Call update_state(100, 200); verify
          pos() ≈ (98, 198) (centred at x-2, y-2).
    """
    def __init__(
        self,
        visitor_id: str,
        x: float,
        y: float,
        parent: Optional[QGraphicsItem] = None,
    ) -> None:
        """Create a visitor dot at the given position.

        Args:
            visitor_id: Unique backend id (e.g. "v_99").
            x: Centre X pixel coordinate on the map.
            y: Centre Y pixel coordinate on the map.
            parent: Optional parent QGraphicsItem.
        """
        half = SPRITE_SIZE / 2
        super().__init__(
            x - half, y - half, SPRITE_SIZE, SPRITE_SIZE, parent,
        )
        self._visitor_id = visitor_id
        self._color = random.choice(_VISITOR_COLORS)
        self.setBrush(QBrush(QColor(self._color)))
        self.setPen(QColor(0, 0, 0, 0))  # no outline
        self.setZValue(Z_VISITORS)

    # ── Public interface ──────────────────────────────────────────────────

    def update_state(self, x: float, y: float) -> None:
        """Move the visitor dot to a new position.

        Args:
            x: New centre X pixel coordinate on the map.
            y: New centre Y pixel coordinate on the map.

        Tests:
            - test_update_state_moves_dot: Call with (300, 400); verify
              the ellipse centre is approximately at (300, 400).
        """
        half = SPRITE_SIZE / 2
        self.setRect(x - half, y - half, SPRITE_SIZE, SPRITE_SIZE)

    @property
    def visitor_id(self) -> str:
        """Return the backend visitor identifier.

        Tests:
            - test_returns_constructor_id: Create with id "v_99"; verify
              visitor_id property returns "v_99".
        """
        return self._visitor_id
