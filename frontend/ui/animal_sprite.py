"""
AnimalSprite — fallback map sprite for species without ASCII art.

Draws an 18 px circle in the species colour with the first letter of the
animal's name inside. It exists so that a species the backend adds later
still renders correctly before anyone draws art for it: the scene falls back
to this class for every unknown species key.

It shares all state handling with the ASCII sprites through
:class:`~frontend.ui.animal_sprite_base.AnimalSpriteBase` and only overrides
the drawing hooks — including the hover highlight, where the circle grows to
21 px and gains a white glow ring.

Module owner: Erik (frontend).

Tests:
    - test_sprite_position_centred: Create a sprite at (100, 200); verify
      sceneBoundingRect().center() is approximately (100, 200).
    - test_dead_state_changes_colour: Call update_state(x, y, True); verify
      the brush is grey and the pen is red.
    - test_hover_calls_callback: Register a hover callback, simulate
      hoverEnterEvent; verify it received the animal id.
"""

from __future__ import annotations

from typing import Optional

from PyQt6.QtWidgets import (
    QGraphicsEllipseItem,
    QGraphicsTextItem,
    QGraphicsItem,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QBrush, QPen, QColor, QFont

from frontend.core.constants import (
    SPECIES_COLORS,
    SPECIES_LABELS,
    C_BORDER,
    C_RED,
    Z_ANIMALS,
)
from frontend.ui.animal_sprite_base import AnimalSpriteBase

SPRITE_SIZE = 18
SPRITE_SIZE_HOVERED = 21
HOVER_PEN_WIDTH = 2
DEAD_FILL = "#30363d"


class AnimalSprite(AnimalSpriteBase, QGraphicsEllipseItem):
    """Coloured circle with the animal's initial, used as generic sprite.

    Tests:
        - test_letter_matches_name: Create with name "Simba"; verify the
          label shows "S".
        - test_unknown_species_uses_grey: Create with species "zebra";
          verify the brush falls back to the neutral grey.
    """

    # Id, species, x, y and name are all required, plus Qt's parent — six
    # instead of the permitted five. Keyword-only so the call site still
    # shows which number is x and which is y.
    # pylint: disable-next=too-many-arguments
    def __init__(
        self,
        *,
        animal_id: str,
        species: str,
        x: float,
        y: float,
        name: str,
        parent: Optional[QGraphicsItem] = None,
    ) -> None:
        """Create the circle, its centred letter and the hover behaviour.

        Args:
            animal_id: Backend animal id, e.g. "a_01".
            species: Lowercase species key from the backend.
            x: Centre X coordinate in map pixels.
            y: Centre Y coordinate in map pixels.
            name: Display name; its first letter becomes the label.
            parent: Optional parent QGraphicsItem.

        Returns:
            None (constructor).

        Tests:
            - test_starts_at_normal_size: Verify the rect is 18×18 px.
            - test_tooltip_names_species: Create a giraffe; verify the
              tooltip reads "<name> · Giraffe".
        """
        super().__init__(
            x - SPRITE_SIZE / 2,
            y - SPRITE_SIZE / 2,
            SPRITE_SIZE,
            SPRITE_SIZE,
            parent,
        )
        self.init_animal(animal_id, name)
        self._species = species
        self._cx = x
        self._cy = y

        self.setAcceptHoverEvents(True)
        self.setZValue(Z_ANIMALS)
        self.setToolTip(f"{name} · {self._species_label()}")

        self.setBrush(QBrush(QColor(self._species_colour())))
        self.setPen(QPen(QColor(C_BORDER), 1))

        self._label = QGraphicsTextItem(name[0].upper() if name else "?", self)
        self._label.setDefaultTextColor(QColor("white"))
        self._label.setFont(QFont("Arial", 9, QFont.Weight.Bold))
        self._label.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
        self._centre_label(SPRITE_SIZE)

    # ── Species helpers ───────────────────────────────────────────────────

    def _species_colour(self) -> str:
        """Return the fill colour configured for this species.

        Returns:
            str: The species colour, or a neutral grey for unknown keys.

        Tests:
            - test_known_species_colour: Create a penguin; verify the slate
              blue from SPECIES_COLORS is returned.
            - test_unknown_species_falls_back: Create species "zebra";
              verify the neutral grey is returned.
        """
        return SPECIES_COLORS.get(self._species, "#aaaaaa")

    def _species_label(self) -> str:
        """Return the German display name of this species.

        Returns:
            str: The mapped label, or the capitalised raw key.

        Tests:
            - test_known_species_label: Create a lion; verify "Löwe".
            - test_unknown_species_is_title_cased: Create species "zebra";
              verify "Zebra".
        """
        return SPECIES_LABELS.get(self._species, self._species.title() or "?")

    def _centre_label(self, size: float) -> None:
        """Centre the letter inside a circle of the given diameter.

        Args:
            size: Current circle diameter in pixels.

        Returns:
            None.

        Tests:
            - test_label_centred_at_normal_size: Create a sprite at
              (100, 200) and call with 18; verify the label centre is at
              the circle centre, not at the scene origin.
            - test_label_recentred_on_hover: Call with 21; verify the label
              stays centred after the sprite grew.
        """
        # The ellipse rect is expressed in item coordinates around (_cx,_cy)
        # while the child label is positioned relative to the item origin —
        # so the circle's top-left corner has to be added, otherwise the
        # letter is drawn at the map origin instead of inside the circle.
        rect = self._label.boundingRect()
        self._label.setPos(
            self._cx - size / 2 + (size - rect.width()) / 2,
            self._cy - size / 2 + (size - rect.height()) / 2 - 0.5,
        )

    # ── AnimalSpriteBase implementation ───────────────────────────────────

    def update_position(self, x: float, y: float) -> None:
        """Move the circle, preserving its current (hovered) size.

        Args:
            x: New centre X coordinate in map pixels.
            y: New centre Y coordinate in map pixels.

        Returns:
            None.

        Tests:
            - test_moves_sprite: Call with (100, 200); verify the rect
              centre is (100, 200).
            - test_keeps_hover_size: Hover the sprite, then move it; verify
              the diameter is still 21 px.
        """
        self._cx = x
        self._cy = y
        size = SPRITE_SIZE_HOVERED if self._hovered else SPRITE_SIZE
        self.setRect(x - size / 2, y - size / 2, size, size)

    def render_alive(self) -> None:
        """Restore the species colour, thin border and white letter.

        Returns:
            None.

        Tests:
            - test_brush_is_species_colour: Revive a dead sprite; verify
              the brush matches SPECIES_COLORS.
            - test_letter_turns_white_again: Revive a dead sprite; verify
              the label colour is white.
        """
        self.setBrush(QBrush(QColor(self._species_colour())))
        self.setPen(QPen(QColor(C_BORDER), 1))
        self._label.setDefaultTextColor(QColor("white"))
        self.setToolTip(f"{self._name} · {self._species_label()}")

    def render_dead(self) -> None:
        """Grey out the circle and mark the letter and border red.

        Returns:
            None.

        Tests:
            - test_brush_turns_grey: Kill a sprite; verify the brush is the
              dead grey.
            - test_tooltip_says_deceased: Kill a sprite; verify the tooltip
              contains "verstorben".
        """
        self.setBrush(QBrush(QColor(DEAD_FILL)))
        self.setPen(QPen(QColor(C_RED), 2))
        self._label.setDefaultTextColor(QColor(C_RED))
        self.setToolTip(f"{self._name} (verstorben)")

    def highlight_on(self) -> None:
        """Grow to 21 px and draw a white glow ring.

        Returns:
            None.

        Tests:
            - test_sprite_grows: Call it; verify the rect is 21×21 px.
            - test_pen_turns_white: Call it; verify the pen colour is
              white.
        """
        size = SPRITE_SIZE_HOVERED
        self.setRect(self._cx - size / 2, self._cy - size / 2, size, size)
        self.setPen(QPen(QColor("#ffffff"), HOVER_PEN_WIDTH))
        self._centre_label(size)

    def highlight_off(self) -> None:
        """Shrink back to 18 px and restore the normal border.

        Returns:
            None.

        Tests:
            - test_sprite_shrinks: Call after highlight_on; verify the rect
              is 18×18 px again.
            - test_pen_restored: Call it; verify the pen colour is the
              default border colour.
        """
        size = SPRITE_SIZE
        self.setRect(self._cx - size / 2, self._cy - size / 2, size, size)
        # A dead sprite keeps its red border — only a living one returns to
        # the neutral outline.
        self.setPen(QPen(QColor(C_RED if self._is_dead else C_BORDER),
                         2 if self._is_dead else 1))
        self._centre_label(size)
