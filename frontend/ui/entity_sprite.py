"""
EntitySprite — abstract base for every sprite the ZooScene manages.

Defines the smallest contract the scene relies on: each sprite knows the
backend id it represents and can be moved to a new map coordinate. The
scene therefore never needs to know *which* concrete sprite it is holding —
it just calls ``update_position`` (visitors) or ``update_state``
(animals, see :class:`~frontend.ui.animal_sprite_base.AnimalSpriteBase`).

The class is deliberately a plain Python base rather than an ``abc.ABC``:
Qt's sip wrapper types bring their own metaclass, and mixing it with
``ABCMeta`` raises a metaclass conflict. Abstract methods therefore raise
``NotImplementedError`` instead of being decorated.

Module owner: Erik (frontend).

Tests:
    - test_update_position_is_abstract: Call EntitySprite().update_position;
      verify NotImplementedError is raised.
    - test_entity_id_is_abstract: Access EntitySprite().entity_id; verify
      NotImplementedError is raised.
"""

from __future__ import annotations


class EntitySprite:
    """Interface every map sprite implements.

    Subclasses combine this base with a concrete Qt graphics item, e.g.
    ``class VisitorSprite(EntitySprite, QGraphicsEllipseItem)``. Because
    this base carries no Qt state, it must always come first in the base
    list so its methods win in the MRO.

    Tests:
        - test_subclass_is_instance: Verify a VisitorSprite is an instance
          of EntitySprite, proving the polymorphic contract holds.
        - test_base_has_no_qt_state: Verify EntitySprite can be constructed
          without a running QApplication.
    """

    def update_position(self, x: float, y: float) -> None:
        """Move the sprite so its visual centre sits on the given point.

        Args:
            x: Target centre X coordinate in map pixels.
            y: Target centre Y coordinate in map pixels.

        Returns:
            None.

        Raises:
            NotImplementedError: Always — concrete sprites must override it.

        Tests:
            - test_raises_on_base_class: Call on a bare EntitySprite;
              verify NotImplementedError.
            - test_subclass_moves_sprite: Call on a VisitorSprite with
              (300, 400); verify its centre is at (300, 400).
        """
        raise NotImplementedError("Concrete sprites must implement update_position")

    @property
    def entity_id(self) -> str:
        """Return the backend id this sprite represents.

        Returns:
            str: The animal or visitor id, e.g. "a_01" / "v_007".

        Raises:
            NotImplementedError: Always — concrete sprites must override it.

        Tests:
            - test_entity_id_raises_on_base_class: Access on a bare
              EntitySprite; verify NotImplementedError.
            - test_subclass_returns_constructor_id: Build a sprite with id
              "a_42"; verify the property returns "a_42".
        """
        raise NotImplementedError("Concrete sprites must implement entity_id")
