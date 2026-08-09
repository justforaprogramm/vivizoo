"""
VisitorSprite — a single zoo visitor on the map.

A 5 px pastel dot. Visitors are deliberately not interactive: the backend
offers no ``get_entity_info`` payload for them, so hovering one could not
show anything, and 100+ hover-enabled items would cost frame time for
nothing.

Module owner: Erik (frontend).

Tests:
    - test_sprite_is_correct_size: Create a sprite; verify the bounding
      rect is 5×5 px.
    - test_sprite_updates_position: Call update_position(100, 200); verify
      the ellipse centre is (100, 200).
"""

from __future__ import annotations

import random
from typing import Optional

from PyQt6.QtWidgets import QGraphicsEllipseItem, QGraphicsItem
from PyQt6.QtGui import QBrush, QColor

from frontend.core.constants import Z_VISITORS
from frontend.ui.entity_sprite import EntitySprite

VISITOR_COLORS = (
    "#f4a460",  # sandy brown
    "#87ceeb",  # sky blue
    "#90ee90",  # light green
    "#dda0dd",  # plum
    "#f0e68c",  # khaki
)

SPRITE_SIZE = 5


class VisitorSprite(EntitySprite, QGraphicsEllipseItem):
    """Small coloured dot representing one visitor.

    The colour is drawn once at construction and kept for the sprite's
    lifetime, so the crowd looks varied without flickering every frame.

    Tests:
        - test_colour_is_stable: Move a sprite twice; verify its brush
          colour never changes.
        - test_colour_from_palette: Create a sprite; verify its colour is
          one of VISITOR_COLORS.
    """

    def __init__(
        self,
        visitor_id: str,
        x: float,
        y: float,
        parent: Optional[QGraphicsItem] = None,
    ) -> None:
        """Create a visitor dot centred at the given position.

        Args:
            visitor_id: Backend visitor id, e.g. "v_007".
            x: Centre X coordinate in map pixels.
            y: Centre Y coordinate in map pixels.
            parent: Optional parent QGraphicsItem.

        Returns:
            None (constructor).

        Tests:
            - test_no_outline: Verify the pen is fully transparent so the
              dot reads as a soft point.
            - test_z_value_above_animals: Verify zValue() is Z_VISITORS.
        """
        half = SPRITE_SIZE / 2
        super().__init__(x - half, y - half, SPRITE_SIZE, SPRITE_SIZE, parent)
        self._visitor_id = visitor_id
        self._color = random.choice(VISITOR_COLORS)
        self.setBrush(QBrush(QColor(self._color)))
        self.setPen(QColor(0, 0, 0, 0))
        self.setZValue(Z_VISITORS)

    # ── EntitySprite implementation ───────────────────────────────────────

    def update_position(self, x: float, y: float) -> None:
        """Move the dot to a new map position.

        Args:
            x: New centre X coordinate in map pixels.
            y: New centre Y coordinate in map pixels.

        Returns:
            None.

        Tests:
            - test_update_moves_dot: Call with (300, 400); verify the
              ellipse centre is approximately (300, 400).
            - test_size_unchanged: Move a sprite; verify the rect is still
              5×5 px.
        """
        half = SPRITE_SIZE / 2
        self.setRect(x - half, y - half, SPRITE_SIZE, SPRITE_SIZE)

    @property
    def entity_id(self) -> str:
        """Return the backend visitor id (EntitySprite contract).

        Returns:
            str: The id passed to the constructor.

        Tests:
            - test_matches_visitor_id: Verify entity_id equals visitor_id.
            - test_returns_constructor_value: Build with "v_009"; verify
              the property returns "v_009".
        """
        return self._visitor_id

    @property
    def visitor_id(self) -> str:
        """Return the backend visitor identifier.

        Returns:
            str: The id passed to the constructor, e.g. "v_007".

        Tests:
            - test_returns_constructor_id: Build with "v_99"; verify the
              property returns "v_99".
            - test_id_is_read_only: Verify the property exposes no setter.
        """
        return self._visitor_id
