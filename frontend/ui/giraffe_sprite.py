"""
AsciiGiraffeSprite — the giraffe's map representation.

A five-attribute specialisation of
:class:`~frontend.ui.ascii_animal_sprite.AsciiAnimalSprite`. Adding this
species required no new logic — proof that the sprite hierarchy is
extensible in the way the project's modularity criterion asks for.

Module owner: Erik (frontend).

Tests:
    - test_giraffe_is_warm_sand_by_default: Create a sprite; verify its
      pixmap is the living variant, not the red dead one.
    - test_dead_giraffe_switches_pixmap: Call update_state(x, y, True);
      verify the pixmap changes to the red variant.
"""

from __future__ import annotations

from frontend.core.constants import SPECIES_COLORS, SPECIES_LABELS
from frontend.assets.ascii_giraffe import ASCII_GIRAFFE
from frontend.ui.ascii_animal_sprite import AsciiAnimalSprite


class AsciiGiraffeSprite(AsciiAnimalSprite):
    """ASCII-art giraffe, warm sand while alive and red once deceased.

    Tests:
        - test_uses_giraffe_art: Verify ASCII_ART is the imported
          ASCII_GIRAFFE.
        - test_tooltip_names_species: Create with name "Melman"; verify the
          tooltip reads "Melman · Giraffe".
    """

    ASCII_ART = ASCII_GIRAFFE
    LIVE_COLOR = SPECIES_COLORS["giraffe"]
    TARGET_WIDTH = 100
    FONT_POINT_SIZE = 5
    SPECIES_LABEL = SPECIES_LABELS["giraffe"]
