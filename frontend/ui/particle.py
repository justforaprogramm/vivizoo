"""
AmbientParticle — a single drifting dust mote on the zoo map.

Purely decorative: a small dot that floats slowly upward and re-enters at
the bottom once it leaves the top edge, giving the static map a sense of
air and depth. Lives in its own module so ``zoo_scene`` keeps exactly one
class, as required by the project's file-structure rule.

Tests:
    - test_particle_moves_up: Record the y position, call tick(); verify it
      decreased.
    - test_particle_wraps_around: Place a particle above the top edge, call
      tick(); verify it reappears below the bottom edge.

Module owner: Erik (frontend).
"""

from __future__ import annotations

import random
from typing import Optional

from PyQt6.QtWidgets import QGraphicsEllipseItem, QGraphicsItem
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QBrush, QColor, QPen

from frontend.core.constants import MAP_W, MAP_H, Z_VISITORS, C_BORDER

PARTICLE_SPEED = 0.3  # base pixels per tick
PARTICLE_SIZE = 2  # pixels


class AmbientParticle(QGraphicsEllipseItem):
    """Tiny floating dot drifting slowly upward across the map.

    Non-interactive and independent of any backend entity — it exists only
    for atmosphere and is driven by :meth:`tick` from the scene.

    Tests:
        - test_starts_at_given_position: Create at (10, 20); verify the rect
          origin is (10, 20).
        - test_speed_is_randomised: Create two particles; verify their drift
          speeds are drawn from the configured range.
    """

    def __init__(
        self,
        x: float,
        y: float,
        parent: Optional[QGraphicsItem] = None,
    ) -> None:
        """Create a particle at the given position with a random drift speed.

        Args:
            x: Start X coordinate in pixels.
            y: Start Y coordinate in pixels.
            parent: Optional parent QGraphicsItem.

        Returns:
            None (constructor).

        Tests:
            - test_particle_is_small: Verify the bounding rect is
              PARTICLE_SIZE wide and high.
            - test_particle_below_visitors: Verify zValue() is one below
              Z_VISITORS so visitors stay readable.
        """
        super().__init__(x, y, PARTICLE_SIZE, PARTICLE_SIZE, parent)
        self.setBrush(QBrush(QColor(C_BORDER)))
        self.setPen(QPen(Qt.PenStyle.NoPen))
        self.setZValue(Z_VISITORS - 1)
        self._drift_speed = random.uniform(0.5, 1.5) * PARTICLE_SPEED

    @property
    def drift_speed(self) -> float:
        """Return this particle's individual upward speed in px per tick.

        Randomised per particle so the swarm does not move as one block.
        Exposed rather than kept private because it is the only thing worth
        asserting about a decorative dot — a test should not have to reach
        into ``_drift_speed`` to check that the randomisation stayed inside
        its range.

        Returns:
            float: Between 0.5 and 1.5 times PARTICLE_SPEED.

        Tests:
            - test_speed_is_inside_the_configured_range: Create 20
              particles; verify every speed lies between 0.5 and 1.5 times
              PARTICLE_SPEED.
            - test_speed_matches_the_movement: Record the y position, call
              tick(); verify the difference equals drift_speed.
        """
        return self._drift_speed

    def tick(self) -> None:
        """Move the particle up one step, wrapping around at the top edge.

        Returns:
            None.

        Tests:
            - test_particle_ticks_upward: Record the position, call tick();
              verify the y coordinate decreased.
            - test_particle_wraps_around: Move the particle above the top
              edge, call tick(); verify it reappears at the bottom.
        """
        rect = self.rect()
        new_y = rect.y() - self._drift_speed
        if new_y < -PARTICLE_SIZE:
            new_y = MAP_H + PARTICLE_SIZE
            rect.moveLeft(random.randint(0, MAP_W))
        self.setRect(rect.x(), new_y, PARTICLE_SIZE, PARTICLE_SIZE)
