"""
AsciiLionSprite — the lion's map representation.

A five-attribute specialisation of
:class:`~frontend.ui.ascii_animal_sprite.AsciiAnimalSprite`; every behaviour
(rendering, caching, hover, death) is inherited. The lion is drawn at 6 pt
before scaling because its art is the coarsest of the three species and
gains the most detail from the larger glyphs.

Module owner: Erik (frontend).

Tests:
    - test_lion_is_golden_by_default: Create a sprite; verify its pixmap is
      the golden variant, not the red dead one.
    - test_dead_lion_switches_pixmap: Call update_state(x, y, True); verify
      the pixmap changes to the red variant.
"""

from __future__ import annotations

from frontend.core.constants import SPECIES_COLORS, SPECIES_LABELS
from frontend.assets.ascii_lion import ASCII_LION
from frontend.ui.ascii_animal_sprite import AsciiAnimalSprite


class AsciiLionSprite(AsciiAnimalSprite):
    """ASCII-art lion, golden while alive and red once deceased.

    Tests:
        - test_uses_lion_art: Verify ASCII_ART is the imported ASCII_LION.
        - test_tooltip_names_species: Create with name "Simba"; verify the
          tooltip reads "Simba · Löwe".
    """

    ASCII_ART = ASCII_LION
    LIVE_COLOR = SPECIES_COLORS["lion"]
    TARGET_WIDTH = 100
    FONT_POINT_SIZE = 6
    SPECIES_LABEL = SPECIES_LABELS["lion"]
