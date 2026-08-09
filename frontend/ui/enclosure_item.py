"""
EnclosureItem — visual representation of an enclosure on the zoo map.

Rendered as a biome-coloured rectangle with a dashed border and a label
that shows the live occupancy and cleanliness the backend reports for that
enclosure id. Uses a callback instead of PyQt signals because
QGraphicsRectItem is not a QObject in Qt6.

Tests:
    - test_rect_position_matches_constructor: Create an item at
      (50, 60, 200, 150); verify the bounding rect matches.
    - test_over_capacity_shows_red_border: Call update_state with a count
      above the capacity; verify the pen is red and at least 2 px wide.
    - test_click_triggers_callback: Register a callback; simulate
      mousePressEvent; verify it is invoked with the enclosure id.

Module owner: Erik (frontend).
"""

from __future__ import annotations

from typing import Callable, Optional

from PyQt6.QtWidgets import (
    QGraphicsRectItem,
    QGraphicsSceneMouseEvent,
    QGraphicsTextItem,
    QGraphicsItem,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QBrush, QPen, QColor, QFont, QLinearGradient

from frontend.core.constants import (
    BIOME_COLORS,
    BIOME_COLORS_LIGHT,
    CLEAN_CRITICAL,
    CLEAN_WARN,
    C_BORDER,
    C_GOLD,
    C_RED,
    C_TEXT_DIM,
    Z_ENCLOSURES,
)


# Twelve fields instead of seven: id, name, biome, capacity, current count,
# cleanliness, click callback, the four geometry values and the text label.
# pylint: disable-next=too-many-instance-attributes
class EnclosureItem(QGraphicsRectItem):
    """Biome-coloured enclosure rectangle with a live status label.

    QGraphicsRectItem is NOT a QObject in Qt6, so pyqtSignal cannot be used.
    Register a callback via :meth:`set_click_callback` instead.

    Tests:
        - test_rect_position_matches_constructor: Create at
          (50, 60, 200, 150); verify the bounding rect matches.
        - test_over_capacity_shows_solid_red_border: Call update_state with
          a count above the capacity; verify the pen is red and solid.
    """

    # Eight values describe an enclosure, pylint allows five parameters.
    # Collapsing them into a dict would cost every type check; making them
    # keyword-only costs nothing and stops anyone swapping w and h. Every
    # caller names the arguments anyway.
    # pylint: disable-next=too-many-arguments
    def __init__(
        self,
        *,
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
            x: Left edge in pixels.
            y: Top edge in pixels.
            w: Width in pixels.
            h: Height in pixels.
            capacity: Maximum animal count.
            parent: Optional parent QGraphicsItem.

        Returns:
            None (constructor).

        Tests:
            - test_biome_colour_applied: Create with biome "ice"; verify the
              brush uses the ice gradient colours.
            - test_label_shows_name: Create with name "Savanne 1"; verify
              the label text starts with that name.
        """
        super().__init__(x, y, w, h, parent)
        self._enclosure_id = enclosure_id
        self._name = name
        self._biome = biome
        self._capacity = capacity
        self._current_count = 0
        self._cleanliness: float | None = None
        self._click_callback: Callable[[str], None] | None = None
        self._x = x
        self._y = y
        self._w = w
        self._h = h

        self.setZValue(Z_ENCLOSURES)
        self.setAcceptHoverEvents(False)
        self.setToolTip(name)

        fill = BIOME_COLORS.get(biome, "#222222")
        light = BIOME_COLORS_LIGHT.get(biome, fill)

        gradient = QLinearGradient(x, y, x, y + h)
        gradient.setColorAt(0, QColor(light))
        gradient.setColorAt(0.15, QColor(fill))
        gradient.setColorAt(0.85, QColor(fill))
        gradient.setColorAt(1, QColor(fill).darker(120))

        self.setBrush(QBrush(gradient))
        self.setPen(QPen(QColor(C_BORDER), 1, Qt.PenStyle.DashLine))

        self._label = QGraphicsTextItem(name, self)
        self._label.setDefaultTextColor(QColor(C_TEXT_DIM))
        self._label.setFont(QFont("Arial", 9))
        self._label.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
        self._centre_label()

    # ── Callback registration ───────────────────────────────────────────

    def set_click_callback(self, callback: Callable[[str], None]) -> None:
        """Register a function called when the enclosure is clicked.

        Args:
            callback: Receives the enclosure id string.

        Returns:
            None.

        Tests:
            - test_callback_registered: Register a mock; simulate
              mousePressEvent; verify it is called with the enclosure id.
            - test_callback_can_be_replaced: Register two callbacks in turn;
              verify only the second one fires.
        """
        self._click_callback = callback

    # ── Public interface ──────────────────────────────────────────────────

    def update_state(
        self,
        current_count: int,
        cleanliness: float | None = None,
    ) -> None:
        """Update the label and border from the backend's live values.

        Args:
            current_count: Animals currently inside, derived from the
                backend's ``free_slots``.
            cleanliness: The enclosure's cleanliness in 0–100, or None when
                the backend does not report it.

        Returns:
            None.

        Tests:
            - test_normal_count_shows_dashed_border: Call with a count at or
              below capacity and full cleanliness; verify the pen style is
              DashLine.
            - test_over_capacity_shows_solid_red_border: Call with a count
              above capacity; verify the pen is red and solid.
            - test_dirty_enclosure_turns_gold: Call with cleanliness=45;
              verify the pen colour is the gold warning colour.
        """
        self._current_count = current_count
        self._cleanliness = cleanliness

        if current_count > self._capacity:
            self.setPen(QPen(QColor(C_RED), 3, Qt.PenStyle.SolidLine))
        elif cleanliness is not None and cleanliness < CLEAN_CRITICAL:
            self.setPen(QPen(QColor(C_RED), 2, Qt.PenStyle.DashLine))
        elif cleanliness is not None and cleanliness < CLEAN_WARN:
            self.setPen(QPen(QColor(C_GOLD), 2, Qt.PenStyle.DashLine))
        else:
            self.setPen(QPen(QColor(C_BORDER), 1, Qt.PenStyle.DashLine))

        text = f"{self._name} · {current_count}/{self._capacity}"
        if cleanliness is not None:
            text += f" · 🧹 {cleanliness:.0f}%"
        self._label.setPlainText(text)
        self._centre_label()
        self.setToolTip(text)

    @property
    def enclosure_id(self) -> str:
        """Return the enclosure identifier.

        Returns:
            str: The id passed to the constructor, e.g. "e_01".

        Tests:
            - test_returns_constructor_id: Create with id "e_42"; verify the
              property returns "e_42".
            - test_id_is_read_only: Verify the property has no setter.
        """
        return self._enclosure_id

    # ── Internal helpers ──────────────────────────────────────────────────

    def _centre_label(self) -> None:
        """Re-centre the label at the bottom edge after a text change.

        Returns:
            None.

        Tests:
            - test_label_centred_horizontally: Call it; verify the label midpoint
              matches the rectangle midpoint.
            - test_recentres_after_text_change: Set a longer text, call it; verify
              the label is centred again.
        """
        rect = self._label.boundingRect()
        self._label.setPos(
            self._x + (self._w - rect.width()) / 2,
            self._y + self._h - rect.height() - 4,
        )

    # ── Mouse events ──────────────────────────────────────────────────────

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent | None) -> None:
        """Invoke the click callback if one is registered.

        Args:
            event: The Qt mouse press event, accepted so it stops here.

        Returns:
            None.

        The event is accepted so a click that already selected an animal
        standing on this enclosure does not continue down the item stack.

        Tests:
            - test_click_triggers_callback: Register a mock; simulate
              mousePressEvent; verify it is called with the enclosure id.
            - test_click_without_callback_is_safe: Simulate a click with no
              callback registered; verify no exception is raised.
        """
        if self._click_callback is not None:
            self._click_callback(self._enclosure_id)
        if event is not None:
            event.accept()
