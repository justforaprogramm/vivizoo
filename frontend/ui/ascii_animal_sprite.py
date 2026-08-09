"""
AsciiAnimalSprite — shared ASCII-art pixmap sprite for the zoo map.

Renders a block of ASCII art into a QPixmap once per colour, caches it, and
shows it centred on the animal's map coordinate. Everything species-specific
is a class attribute, so adding a new ASCII species is a five-line subclass
and no new logic at all:

.. code-block:: python

    class AsciiZebraSprite(AsciiAnimalSprite):
        ASCII_ART = ASCII_ZEBRA
        LIVE_COLOR = "#dddddd"
        TARGET_WIDTH = 100
        FONT_POINT_SIZE = 5
        SPECIES_LABEL = "Zebra"

Why a pixmap instead of a QGraphicsTextItem: at the 3–6 pt sizes needed to
fit the map, Qt renders text without anti-aliasing and the art becomes
unreadable. Drawing at a legible size and scaling down with
``SmoothTransformation`` keeps the silhouette crisp.

Module owner: Erik (frontend).

Tests:
    - test_pixmap_cache_returns_same_object: Render the same species and
      colour twice; verify the identical QPixmap instance comes back.
    - test_dead_sprite_uses_red_pixmap: Call update_state(x, y, True);
      verify the pixmap differs from the living one.
"""

from __future__ import annotations

from typing import Optional

from PyQt6.QtWidgets import QGraphicsPixmapItem, QGraphicsItem
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QImage, QPainter, QFont, QFontMetrics, QColor

from frontend.core.constants import Z_ANIMALS, C_RED
from frontend.ui.animal_sprite_base import AnimalSpriteBase

# Cache key is (subclass name, colour) so all species share one dict while
# never colliding. Two entries per species: alive and dead.
_PIXMAP_CACHE: dict[tuple[str, str], QPixmap] = {}


class AsciiAnimalSprite(AnimalSpriteBase, QGraphicsPixmapItem):
    """Animal drawn as scaled-down ASCII art.

    Concrete species subclasses only override the five class attributes.

    Attributes:
        ASCII_ART: The multi-line art block to render.
        LIVE_COLOR: Hex colour used while the animal is alive.
        TARGET_WIDTH: Width in pixels the rendered art is scaled to.
        FONT_POINT_SIZE: Point size the art is drawn at before scaling.
        SPECIES_LABEL: German species name used in the tooltip.

    Tests:
        - test_sprite_centred_on_coordinate: Create at (200, 300); verify
          the scene bounding rect centre is (200, 300).
        - test_subclass_attributes_drive_colour: Create a lion and a
          penguin; verify their living pixmaps differ.
    """

    ASCII_ART: str = ""
    LIVE_COLOR: str = "#cccccc"
    TARGET_WIDTH: int = 100
    FONT_POINT_SIZE: int = 5
    SPECIES_LABEL: str = "Tier"

    def __init__(
        self,
        animal_id: str,
        x: float,
        y: float,
        name: str,
        parent: Optional[QGraphicsItem] = None,
    ) -> None:
        """Create the sprite and place it centred on the given coordinate.

        Args:
            animal_id: Backend animal id, e.g. "a_01".
            x: Centre X coordinate in map pixels.
            y: Centre Y coordinate in map pixels.
            name: Display name used in the tooltip.
            parent: Optional parent QGraphicsItem.

        Returns:
            None (constructor).

        Tests:
            - test_accepts_hover_events: Create a sprite; verify
              acceptHoverEvents() is True so the info panel can react.
            - test_z_value_is_animal_layer: Verify zValue() equals
              Z_ANIMALS so animals draw above enclosures.
        """
        super().__init__(parent)
        self.init_animal(animal_id, name)

        self.setPixmap(self._pixmap_for(self.LIVE_COLOR))
        self._recentre_offset()
        self.setPos(x, y)
        self.setZValue(Z_ANIMALS)
        self.setAcceptHoverEvents(True)
        self.setToolTip(f"{name} · {self.SPECIES_LABEL}")

    # ── EntitySprite / AnimalSpriteBase implementation ───────────────────

    def update_position(self, x: float, y: float) -> None:
        """Move the pixmap so its centre sits on the given coordinate.

        Args:
            x: New centre X coordinate in map pixels.
            y: New centre Y coordinate in map pixels.

        Returns:
            None.

        Tests:
            - test_moves_sprite: Call with (250, 120); verify pos() is
              (250, 120).
            - test_offset_keeps_it_centred: Call it; verify the scene
              bounding rect centre matches the requested point.
        """
        self.setPos(x, y)

    def render_alive(self) -> None:
        """Switch back to the living (species-coloured) pixmap.

        Returns:
            None.

        Tests:
            - test_restores_live_pixmap: Kill then revive a sprite; verify
              the pixmap equals the cached living variant.
            - test_restores_tooltip: Revive a sprite; verify the tooltip
              names the species again.
        """
        self.setPixmap(self._pixmap_for(self.LIVE_COLOR))
        self._recentre_offset()
        self.setToolTip(f"{self._name} · {self.SPECIES_LABEL}")

    def render_dead(self) -> None:
        """Switch to the red pixmap and mark the tooltip as deceased.

        Returns:
            None.

        Tests:
            - test_uses_red_pixmap: Kill a sprite; verify its pixmap is the
              cached red variant.
            - test_tooltip_says_deceased: Kill a sprite; verify the tooltip
              contains "verstorben".
        """
        self.setPixmap(self._pixmap_for(C_RED))
        self._recentre_offset()
        self.setToolTip(f"{self._name} (verstorben)")

    # ── Internal helpers ──────────────────────────────────────────────────

    def _recentre_offset(self) -> None:
        """Offset the pixmap by half its size so setPos centres the sprite.

        Returns:
            None.

        Tests:
            - test_offset_is_half_the_pixmap: Verify the offset equals minus
              half the pixmap width and height.
            - test_called_after_pixmap_swap: Swap to the dead pixmap of a
              different size; verify the sprite stays centred.
        """
        pixmap = self.pixmap()
        self.setOffset(-pixmap.width() / 2, -pixmap.height() / 2)

    @classmethod
    def _pixmap_for(cls, color: str) -> QPixmap:
        """Return the cached pixmap of this species in the given colour.

        Args:
            color: Hex colour the ASCII art is drawn in.

        Returns:
            QPixmap: The rendered art, scaled to TARGET_WIDTH. Rendered on
            the first call and served from the cache afterwards.

        Tests:
            - test_second_call_is_cached: Call twice with the same colour;
              verify the identical object is returned.
            - test_different_species_do_not_collide: Call for a lion and a
              penguin with the same colour; verify two distinct pixmaps.
        """
        key = (cls.__name__, color)
        cached = _PIXMAP_CACHE.get(key)
        if cached is not None:
            return cached

        pixmap = cls._render_pixmap(color)
        _PIXMAP_CACHE[key] = pixmap
        return pixmap

    @classmethod
    def _render_pixmap(cls, color: str) -> QPixmap:
        """Draw the ASCII art into a transparent, scaled-down pixmap.

        Uses ``QFontMetrics`` rather than ``QPainter.fontMetrics()`` so the
        rendering also works on the offscreen platform, where no painter is
        active yet when the size has to be computed.

        Args:
            color: Hex colour the glyphs are drawn in.

        Returns:
            QPixmap: The finished pixmap, or an empty one for empty art.

        Tests:
            - test_returns_non_null_pixmap: Render a species; verify the
              pixmap is not null and TARGET_WIDTH wide.
            - test_empty_art_returns_empty_pixmap: Render a subclass with
              ASCII_ART = ""; verify an empty pixmap comes back.
        """
        lines = cls.ASCII_ART.split("\n")
        if not cls.ASCII_ART.strip():
            return QPixmap()

        font = QFont("Courier New", cls.FONT_POINT_SIZE)
        metrics = QFontMetrics(font)
        char_width = metrics.maxWidth()
        line_height = metrics.height()

        width = max(len(line) for line in lines) * char_width + 4
        height = len(lines) * line_height + 4

        image = QImage(width, height, QImage.Format.Format_ARGB32)
        image.fill(QColor(0, 0, 0, 0))

        painter = QPainter(image)
        painter.setFont(font)
        painter.setPen(QColor(color))
        for index, line in enumerate(lines):
            painter.drawText(2, (index + 1) * line_height, line)
        painter.end()

        scaled = image.scaled(
            cls.TARGET_WIDTH,
            height,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        return QPixmap.fromImage(scaled)
