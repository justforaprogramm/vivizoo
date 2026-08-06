"""
AsciiGiraffeSprite — visual representation of a Giraffe on the zoo map.

Uses callbacks instead of PyQt signals because QGraphicsPixmapItem
is not a QObject in Qt6.

Tests:
    - test_pixmap_cache_returns_same_object: Call _render_giraffe_pixmap("#d4a44a")
      twice; verify the same QPixmap object is returned.
    - test_dead_giraffe_renders_in_red: Call update_state(x, y, is_dead=True);
      verify the pixmap changes to the red variant.
"""

from __future__ import annotations

from typing import Callable, Optional

from PyQt6.QtWidgets import QGraphicsPixmapItem, QGraphicsItem
from PyQt6.QtCore import Qt
from PyQt6.QtGui import (
    QPixmap,
    QImage,
    QPainter,
    QFont,
    QFontMetrics,
    QColor,
)

from frontend.core.constants import Z_ANIMALS, C_RED, SPECIES_COLORS
from frontend.assets.ascii_giraffe import ASCII_GIRAFFE

_GIRAFFE_CACHE: dict[str, QPixmap] = {}
_GIRAFFE_LIVE = SPECIES_COLORS.get("giraffe", "#d4a44a")


def _render_giraffe_pixmap(color: str) -> QPixmap:
    """Render ASCII_GIRAFFE text to a cached QPixmap.

    Tests:
        - test_render_returns_pixmap: Verify a QPixmap is returned.
        - test_cache_is_populated: Verify key exists in _GIRAFFE_CACHE after call.
    """
    if color in _GIRAFFE_CACHE:
        return _GIRAFFE_CACHE[color]

    lines = ASCII_GIRAFFE.split("\n")
    if not lines:
        return QPixmap()

    font = QFont("Courier New", 5)
    fm = QFontMetrics(font)
    char_w = fm.maxWidth()
    line_h = fm.height()

    max_cols = max(len(line) for line in lines) if lines else 1
    img_w = max_cols * char_w + 4
    img_h = len(lines) * line_h + 4

    image = QImage(img_w, img_h, QImage.Format.Format_ARGB32)
    image.fill(QColor(0, 0, 0, 0))

    painter = QPainter(image)
    painter.setFont(font)
    painter.setPen(QColor(color))
    for i, line in enumerate(lines):
        painter.drawText(2, (i + 1) * line_h, line)
    painter.end()

    target_w = 100
    scaled = image.scaled(
        target_w, img_h,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )
    pixmap = QPixmap.fromImage(scaled)
    _GIRAFFE_CACHE[color] = pixmap
    return pixmap


class AsciiGiraffeSprite(QGraphicsPixmapItem):
    """ASCII-art giraffe on the zoo map.

    Renders a cached QPixmap from ASCII_GIRAFFE text. Warm sand
    (#d4a44a) when alive, red (#f85149) when dead. 100×113 px.

    Tests:
        - test_giraffe_is_warm_sand_by_default: Create sprite; verify
          pixmap is not the dead (red) variant.
        - test_dead_giraffe_switches_pixmap: Call update_state(x, y, True);
          verify the pixmap changes to the red dead variant.
    """

    def __init__(
        self,
        animal_id: str,
        x: float,
        y: float,
        name: str,
        parent: Optional[QGraphicsItem] = None,
    ) -> None:
        super().__init__(parent)
        self._animal_id = animal_id
        self._name = name
        self._is_dead = False
        self._hover_callback: Callable[[str], None] | None = None
        self._unhover_callback: Callable[[], None] | None = None

        self._pixmap = _render_giraffe_pixmap(_GIRAFFE_LIVE)
        self.setPixmap(self._pixmap)
        self.setOffset(-self._pixmap.width() / 2, -self._pixmap.height() / 2)
        self.setPos(x, y)
        self.setZValue(Z_ANIMALS)
        self.setAcceptHoverEvents(True)
        self.setToolTip(f"{name} · Giraffe")

    # ── Callbacks ───────────────────────────────────────────────────────

    def set_hover_callback(self, cb: Callable[[str], None]) -> None:
        """Register a callback invoked on hover enter with the animal_id.

        Tests:
            - test_hover_calls_callback: Register mock; simulate hover;
              verify callback received correct animal_id.
        """
        self._hover_callback = cb

    def set_unhover_callback(self, cb: Callable[[], None]) -> None:
        """Register a callback invoked on hover leave.

        Tests:
            - test_unhover_calls_callback: Register mock; simulate unhover;
              verify callback was invoked.
        """
        self._unhover_callback = cb

    # ── Public interface ──────────────────────────────────────────────────

    def update_state(self, x: float, y: float, is_dead: bool) -> None:
        """Update position and optionally switch to dead/revived pixmap.

        Args:
            x: New X pixel coordinate.
            y: New Y pixel coordinate.
            is_dead: If True, render red (dead) pixmap; False restores warm sand.

        Tests:
            - test_update_moves_sprite: Call (200, 300, False); verify
              pos() approx (200, 300).
            - test_dead_switches_color: Call (x, y, True); verify pixmap
              is the red C_RED variant.
        """
        self.setPos(x, y)
        if is_dead and not self._is_dead:
            self._pixmap = _render_giraffe_pixmap(C_RED)
            self.setPixmap(self._pixmap)
            self._is_dead = True
            self.setToolTip(f"{self._name} (verstorben)")
        elif not is_dead and self._is_dead:
            self._pixmap = _render_giraffe_pixmap(_GIRAFFE_LIVE)
            self.setPixmap(self._pixmap)
            self._is_dead = False
            self.setToolTip(f"{self._name} · Giraffe")

    @property
    def animal_id(self) -> str:
        """Return the backend animal identifier.

        Tests:
            - test_returns_correct_id: Create with id "a_08"; verify
              animal_id property returns "a_08".
        """
        return self._animal_id

    # ── Hover events ──────────────────────────────────────────────────────

    def hoverEnterEvent(self, event: object) -> None:
        """Fire hover callback with this giraffe's animal_id.

        Tests:
            - test_hover_fires_callback: Set mock callback; simulate
              hoverEnterEvent; verify callback invoked with animal_id.
        """
        if self._hover_callback:
            self._hover_callback(self._animal_id)
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event: object) -> None:
        """Fire unhover callback.

        Tests:
            - test_unhover_fires_callback: Set mock callback; simulate
              hoverLeaveEvent; verify callback was invoked.
        """
        if self._unhover_callback:
            self._unhover_callback()
        super().hoverLeaveEvent(event)