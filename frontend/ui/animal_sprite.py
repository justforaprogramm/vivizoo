"""
AnimalSprite — visual representation of species without ASCII art on the zoo map.

Rendered as a coloured 18×18 px ellipse with the first letter of the
animal's name centred inside. Lions, Penguins, and Giraffes use
dedicated ASCII sprite classes instead.

Tier 2: Hover highlight — white glow ring and slight size bump (18→21 px)
for satisfying game-like feedback.

Uses callbacks instead of PyQt signals because QGraphicsEllipseItem
is not a QObject in Qt6.

Tests:
    - test_sprite_position_centred: Create sprite at (100, 200). Verify
      sceneBoundingRect().center() approx equals (100, 200).
    - test_dead_state_changes_color: Call update_state(x, y, is_dead=True).
      Verify brush colour is gray and border is red.
    - test_hover_calls_callback: Set a hover callback; simulate
      hoverEnterEvent; verify callback invoked with correct animal_id.
"""

from __future__ import annotations

from typing import Callable, Optional

from PyQt6.QtWidgets import (
    QGraphicsEllipseItem,
    QGraphicsTextItem,
    QGraphicsItem,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QBrush, QPen, QColor, QFont

from frontend.core.constants import SPECIES_COLORS, C_BORDER, C_RED, Z_ANIMALS

SPRITE_SIZE = 18
SPRITE_SIZE_HOVERED = 21  # Size on hover (pop effect)
HOVER_PEN_WIDTH = 2  # Glow ring width on hover


class AnimalSprite(QGraphicsEllipseItem):
    """Circle + first-letter label for an animal on the map.

    Fallback sprite for species without dedicated ASCII art. Renders
    as an 18×18px colored ellipse with the first letter of the animal's
    name. Grows to 21×21 with white glow ring on hover.

    Tests:
        - test_sprite_position_centred: Create sprite at (100, 200). Verify
          sceneBoundingRect().center() approx equals (100, 200).
        - test_dead_state_changes_color: Call update_state(x, y, is_dead=True).
          Verify brush colour is gray and border is red.
    """

    def __init__(
        self,
        animal_id: str,
        species: str,
        x: float,
        y: float,
        name: str,
        parent: Optional[QGraphicsItem] = None,
    ) -> None:
        super().__init__(
            x - SPRITE_SIZE / 2,
            y - SPRITE_SIZE / 2,
            SPRITE_SIZE,
            SPRITE_SIZE,
            parent,
        )
        self._animal_id = animal_id
        self._species = species
        self._name = name
        self._is_dead = False
        self._hovered = False
        self._cx = x
        self._cy = y
        self._hover_callback: Callable[[str], None] | None = None
        self._unhover_callback: Callable[[], None] | None = None

        self.setAcceptHoverEvents(True)
        self.setZValue(Z_ANIMALS)
        self.setToolTip(f"{name} · {species.title()}")

        fill = SPECIES_COLORS.get(species, "#aaaaaa")
        self.setBrush(QBrush(QColor(fill)))
        self.setPen(QPen(QColor(C_BORDER), 1))

        self._label = QGraphicsTextItem(name[0].upper() if name else "?", self)
        self._label.setDefaultTextColor(QColor("white"))
        font = QFont("Arial", 9, QFont.Weight.Bold)
        self._label.setFont(font)
        rect = self._label.boundingRect()
        self._label.setPos(
            (SPRITE_SIZE - rect.width()) / 2,
            (SPRITE_SIZE - rect.height()) / 2 - 0.5,
        )
        self._label.setAcceptedMouseButtons(Qt.MouseButton.NoButton)

    # ── Callbacks ───────────────────────────────────────────────────────

    def set_hover_callback(self, cb: Callable[[str], None]) -> None:
        """Register a callback invoked on hover enter with the animal_id.

        Tests:
            - test_callback_invoked_on_hover: Register a mock callback,
              simulate hoverEnterEvent; verify callback called with animal_id.
        """
        self._hover_callback = cb

    def set_unhover_callback(self, cb: Callable[[], None]) -> None:
        """Register a callback invoked on hover leave.

        Tests:
            - test_callback_invoked_on_unhover: Register a mock callback,
              simulate hoverLeaveEvent; verify callback was called.
        """
        self._unhover_callback = cb

    # ── Public interface ──────────────────────────────────────────────────

    def update_state(self, x: float, y: float, is_dead: bool) -> None:
        """Update the sprite's visual state and position.

        Args:
            x: New X pixel coordinate on the map.
            y: New Y pixel coordinate on the map.
            is_dead: If True, render in grayscale with red border.

        Tests:
            - test_update_state_moves_sprite: Call (100, 200, False), verify
              sceneBoundingRect().center() approx (100, 200).
            - test_dead_changes_brush: Call (x, y, True), verify brush is
              gray (#30363d) and pen is red (#f85149).
        """
        self._cx = x
        self._cy = y
        half = (SPRITE_SIZE_HOVERED if self._hovered else SPRITE_SIZE) / 2
        self.setRect(x - half, y - half, half * 2, half * 2)

        if is_dead and not self._is_dead:
            self.setBrush(QBrush(QColor("#30363d")))
            self.setPen(QPen(QColor(C_RED), 2))
            self._label.setDefaultTextColor(QColor(C_RED))
            self._is_dead = True
            self.setToolTip(f"{self._name} (verstorben)")
        elif not is_dead and self._is_dead:
            fill = SPECIES_COLORS.get(self._species, "#aaaaaa")
            self.setBrush(QBrush(QColor(fill)))
            self.setPen(QPen(QColor(C_BORDER), 1))
            self._label.setDefaultTextColor(QColor("white"))
            self._is_dead = False
            self.setToolTip(f"{self._name} · {self._species.title()}")

    @property
    def animal_id(self) -> str:
        """Return the backend animal identifier.

        Tests:
            - test_returns_constructor_id: Create sprite with id "a_42",
              verify animal_id property returns "a_42".
        """
        return self._animal_id

    # ── Hover events (Tier 2: glow ring + size pop) ──────────────────────

    def hoverEnterEvent(self, event: object) -> None:
        """Start hover highlight: grow to 21px with white glow ring.

        Tests:
            - test_hover_grows_sprite: Simulate hoverEnterEvent; verify
              bounding rect > 18×18 px (grew to 21×21).
            - test_dead_ignores_hover: Set is_dead=True, simulate hover;
              verify no size change and callback still fires.
        """
        if not self._is_dead:
            self._hovered = True
            half = SPRITE_SIZE_HOVERED / 2
            self.setRect(
                self._cx - half,
                self._cy - half,
                SPRITE_SIZE_HOVERED,
                SPRITE_SIZE_HOVERED,
            )
            self.setPen(QPen(QColor("#ffffff"), HOVER_PEN_WIDTH))
            rect = self._label.boundingRect()
            self._label.setPos(
                (SPRITE_SIZE_HOVERED - rect.width()) / 2,
                (SPRITE_SIZE_HOVERED - rect.height()) / 2 - 0.5,
            )

        if self._hover_callback:
            self._hover_callback(self._animal_id)
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event: object) -> None:
        """End hover highlight: restore 18×18 px size and original border.

        Tests:
            - test_unhover_restores_size: Simulate hoverLeaveEvent; verify
              bounding rect returns to 18×18 px.
            - test_unhover_fires_callback: Verify unhover callback is
              invoked exactly once.
        """
        if not self._is_dead:
            self._hovered = False
            half = SPRITE_SIZE / 2
            self.setRect(self._cx - half, self._cy - half, SPRITE_SIZE, SPRITE_SIZE)
            self.setPen(QPen(QColor(C_BORDER), 1))
            rect = self._label.boundingRect()
            self._label.setPos(
                (SPRITE_SIZE - rect.width()) / 2,
                (SPRITE_SIZE - rect.height()) / 2 - 0.5,
            )

        if self._unhover_callback:
            self._unhover_callback()
        super().hoverLeaveEvent(event)
