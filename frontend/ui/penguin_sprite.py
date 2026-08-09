"""
AsciiPenguinSprite — the penguin's map representation.

A five-attribute specialisation of
:class:`~frontend.ui.ascii_animal_sprite.AsciiAnimalSprite`. The penguin art
is the tallest of the three, so it is scaled to a slightly wider target to
keep the body proportions readable.

Module owner: Erik (frontend).

Tests:
    - test_penguin_is_slate_blue_by_default: Create a sprite; verify its
      pixmap is the living variant, not the red dead one.
    - test_dead_penguin_switches_pixmap: Call update_state(x, y, True);
      verify the pixmap changes to the red variant.
"""

from __future__ import annotations

from frontend.core.constants import SPECIES_COLORS, SPECIES_LABELS
from frontend.assets.ascii_penguin import ASCII_PENGUIN
from frontend.ui.ascii_animal_sprite import AsciiAnimalSprite


class AsciiPenguinSprite(AsciiAnimalSprite):
    """ASCII-art penguin, slate-blue while alive and red once deceased.

    Tests:
        - test_uses_penguin_art: Verify ASCII_ART is the imported
          ASCII_PENGUIN.
        - test_tooltip_names_species: Create with name "Pingu"; verify the
          tooltip reads "Pingu · Pinguin".
    """

    ASCII_ART = ASCII_PENGUIN
    LIVE_COLOR = SPECIES_COLORS["penguin"]
    TARGET_WIDTH = 120
    FONT_POINT_SIZE = 5
    SPECIES_LABEL = SPECIES_LABELS["penguin"]
