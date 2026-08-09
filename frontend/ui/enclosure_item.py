"""
EnclosureItem — visual representation of an enclosure on the zoo map.

Rendered as a biome-coloured rectangle with dashed border and a label
showing the enclosure name. Uses a callback instead of PyQt signals
because QGraphicsRectItem is not a QObject in Qt6.

Tests:
    - test_rect_position_matches_constructor: Create item at (50,60,200,150);
      verify bounding rect matches.
    - test_over_capacity_shows_red_border: Call update_state with count > capacity;
      verify pen colour is red and width >= 2.
    - test_click_triggers_callback: Set a callback; simulate mousePressEvent;
      verify callback invoked with correct enclosure_id.
"""

from __future__ import annotations

from typing import Callable, Optional

from PyQt6.QtWidgets import (
    QGraphicsRectItem,
    QGraphicsTextItem,
    QGraphicsItem,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QBrush, QPen, QColor, QFont, QLinearGradient

from frontend.core.constants import (
    BIOME_COLORS,
    C_BORDER,
    C_RED,
    C_TEXT_DIM,
    Z_ENCLOSURES,
)


class EnclosureItem(QGraphicsRectItem):
    """Biome-coloured enclosure rectangle with label.

    QGraphicsRectItem is NOT a QObject in Qt6, so we cannot use
    pyqtSignal. Instead, register a callback via set_click_callback().

    Tests:
        - test_rect_position_matches_constructor: Create at (50,60,200,150);
          verify bounding rect matches (50,60,200,150).
        - test_over_capacity_shows_solid_red_border: Call update_state with
          count > capacity; verify pen colour is red and width >= 2.
    """

    def __init__(
        self,
        enclosure_id: str,
        name: str,
        biome: str,
        x: float,
        y: float,
        w: float,
        h: float,
        capacity: int,
        parent: Optional[QGraphicsItem] = None,
    ) -> None:
        """Create an enclosure rectangle.

        Args:
            enclosure_id: Unique id (e.g. "e_01").
            name: Display name (e.g. "Savanne 1").
            biome: "savanna" | "ice" | "water".
            x, y: Top-left corner pixel coordinates.
            w, h: Width and height in pixels.
            capacity: Maximum animal count.
            parent: Optional parent QGraphicsItem.
        """
        super().__init__(x, y, w, h, parent)
        self._enclosure_id = enclosure_id
        self._name = name
        self._biome = biome
        self._capacity = capacity
        self._current_count = 0
        self._click_callback: Callable[[str], None] | None = None

        self.setZValue(Z_ENCLOSURES)
        self.setAcceptHoverEvents(False)

        # Semi-transparent biome fill
        fill = BIOME_COLORS.get(biome, "#222222")
        # Tier 1: biome gradient fill (depth effect)
        from frontend.core.constants import BIOME_COLORS_LIGHT

        light = BIOME_COLORS_LIGHT.get(biome, fill)

        # Create gradient from lighter top to darker bottom
        gradient = QLinearGradient(x, y, x, y + h)
        gradient.setColorAt(0, QColor(light))
        gradient.setColorAt(0.15, QColor(fill))
        gradient.setColorAt(0.85, QColor(fill))
        gradient.setColorAt(1, QColor(fill).darker(120))

        self.setBrush(QBrush(gradient))
        self.setPen(QPen(QColor(C_BORDER), 1, Qt.PenStyle.DashLine))

        # Label at the bottom centre of the rectangle
        self._label = QGraphicsTextItem(f"{name} · Lv.1", self)
        self._label.setDefaultTextColor(QColor(C_TEXT_DIM))
        font = QFont("Arial", 9)
        self._label.setFont(font)
        label_rect = self._label.boundingRect()
        self._label.setPos(
            x + (w - label_rect.width()) / 2,
            y + h - label_rect.height() - 4,
        )
        self._label.setAcceptedMouseButtons(Qt.MouseButton.NoButton)

    # ── Callback registration ───────────────────────────────────────────

    def set_click_callback(self, callback: Callable[[str], None]) -> None:
        """Register a function to be called when the enclosure is clicked.

        Args:
            callback: Function that receives the enclosure_id string.

        Tests:
            - test_callback_registered: Set a mock callback; simulate
              mousePressEvent; verify callback called with enclosure_id.
        """
        self._click_callback = callback

    # ── Public interface ──────────────────────────────────────────────────

    def update_state(self, current_count: int) -> None:
        """Update the enclosure's visual state based on population.

        Args:
            current_count: Number of animals currently inside.

        Tests:
            - test_normal_count_shows_dashed_border: Call with count <= capacity;
              verify pen style is DashLine.
            - test_over_capacity_shows_solid_red_border: Call with
              count > capacity; verify pen colour is red and style is SolidLine.
        """
        self._current_count = current_count

        if current_count > self._capacity:
            pen = QPen(QColor(C_RED), 3, Qt.PenStyle.SolidLine)
            self.setPen(pen)
        else:
            pen = QPen(QColor(C_BORDER), 1, Qt.PenStyle.DashLine)
            self.setPen(pen)

        # Update label (level shown as 1 for Phase 1)
        self._label.setPlainText(
            f"{self._name} · Lv.1 · {current_count}/{self._capacity}"
        )

    @property
    def enclosure_id(self) -> str:
        """Return the enclosure identifier.

        Tests:
            - test_returns_constructor_id: Create with id "e_42"; verify
              enclosure_id property returns "e_42".
        """
        return self._enclosure_id

    # ── Mouse events ──────────────────────────────────────────────────────

    def mousePressEvent(self, event: object) -> None:
        """Invoke the click callback if registered.

        Tests:
            - test_click_triggers_callback: Set a mock callback, simulate
              mousePressEvent; verify callback called with enclosure_id.
        """
        if self._click_callback is not None:
            self._click_callback(self._enclosure_id)
        super().mousePressEvent(event)
