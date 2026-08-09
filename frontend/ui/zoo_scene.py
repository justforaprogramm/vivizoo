"""
ZooScene — QGraphicsScene managing all entity sprites on the 800×600 map.

Owns three sprite dictionaries keyed by backend id (animals, visitors,
enclosures), a dot-grid background, ambient particles, and the day/night
overlay. ``update_entities`` performs the whole sprite batching pass:
create new sprites, move existing ones, drop stale ones.

The overlay follows the backend's four-phase ``time_of_day`` field and
cross-fades between the phase tints defined in ``constants.PHASE_LIGHTING``.

Tests:
    - test_enclosures_created_from_defs: Create a ZooScene; verify
      len(enclosures) == len(ENCLOSURE_DEFS).
    - test_lighting_overlay_exists_at_correct_z: Verify the overlay's
      zValue() equals Z_OVERLAY.
    - test_update_entities_creates_new_animal: Pass a state with one
      animal; verify one sprite is added.

Module owner: Erik (frontend).
"""

from __future__ import annotations

import random
from typing import Optional

from PyQt6.QtWidgets import QGraphicsScene, QGraphicsRectItem
from PyQt6.QtCore import Qt, QObject, QVariantAnimation, QEasingCurve
from PyQt6.QtGui import QBrush, QColor, QImage, QPainter, QPen

from frontend.core.constants import (
    MAP_W,
    MAP_H,
    Z_OVERLAY,
    C_BG_DEEP,
    C_BG_MID,
    LIGHTING_DAY,
    LIGHTING_NIGHT,
    PHASE_LIGHTING,
    ENCLOSURE_DEFS,
)
from frontend.ui.animal_sprite import AnimalSprite
from frontend.ui.lion_sprite import AsciiLionSprite
from frontend.ui.penguin_sprite import AsciiPenguinSprite
from frontend.ui.giraffe_sprite import AsciiGiraffeSprite
from frontend.ui.visitor_sprite import VisitorSprite
from frontend.ui.enclosure_item import EnclosureItem
from frontend.ui.particle import AmbientParticle

PARTICLE_COUNT = 30
LIGHTING_FADE_MS = 800

# Every concrete animal sprite is two things at once: an AnimalSpriteBase
# (the behaviour the scene calls) and a QGraphicsItem (what Qt manages).
# AnimalSpriteBase deliberately carries no Qt state — see entity_sprite.py —
# so this alias names the pair once instead of repeating the species list at
# every use site. Adding a species means extending this one line.
AnimalSpriteT = AnimalSprite | AsciiLionSprite | AsciiPenguinSprite | AsciiGiraffeSprite


# Eight fields instead of seven: three sprite registries (animals, visitors,
# enclosures), the particle list and the four parts of the day/night
# lighting.
# pylint: disable-next=too-many-instance-attributes
class ZooScene(QGraphicsScene):
    """The 2-D zoo map (800×600) holding every spatial entity.

    Tests:
        - test_enclosures_created_from_defs: Create a ZooScene; verify one
          EnclosureItem exists per ENCLOSURE_DEFS entry.
        - test_update_entities_removes_stale_animals: Pass a state without a
          previously seen animal; verify its sprite is removed.
    """

    def __init__(self, parent: Optional[QObject] = None) -> None:
        """Build the background, overlay, particles and static enclosures.

        Args:
            parent: Optional parent object.

        Returns:
            None (constructor).

        Tests:
            - test_scene_rect_matches_map: Verify sceneRect() is
              (0, 0, MAP_W, MAP_H).
            - test_particles_created: Verify PARTICLE_COUNT particles exist
              after construction.
        """
        super().__init__(0, 0, MAP_W, MAP_H, parent)

        self.setBackgroundBrush(self._build_grid_brush())

        # The scene only ever calls the polymorphic AnimalSpriteBase API on
        # these — update_state, set_selected — never a species-specific one.
        self._animals: dict[str, AnimalSpriteT] = {}
        self._visitors: dict[str, VisitorSprite] = {}
        self._enclosures: dict[str, EnclosureItem] = {}

        self._lighting_colour = QColor(*LIGHTING_DAY)
        self._lighting_overlay = QGraphicsRectItem(0, 0, MAP_W, MAP_H)
        self._lighting_overlay.setZValue(Z_OVERLAY)
        self._lighting_overlay.setBrush(QBrush(self._lighting_colour))
        # Without an explicit NoPen the item keeps Qt's default black 1 px
        # outline, which draws a hairline along the map's top and left edge
        # even at the fully transparent NOON tint.
        self._lighting_overlay.setPen(QPen(Qt.PenStyle.NoPen))
        self.addItem(self._lighting_overlay)

        self._lighting_anim = QVariantAnimation()
        self._lighting_anim.setDuration(LIGHTING_FADE_MS)
        self._lighting_anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self._lighting_anim.valueChanged.connect(self._on_lighting_step)
        self._phase: str = ""

        self._particles: list[AmbientParticle] = []
        for _ in range(PARTICLE_COUNT):
            particle = AmbientParticle(
                random.randint(0, MAP_W), random.randint(0, MAP_H)
            )
            self.addItem(particle)
            self._particles.append(particle)

        self._create_enclosures()

    # ── Background grid ─────────────────────────────────────────────────

    @staticmethod
    def _build_grid_brush() -> QBrush:
        """Create the subtle 40 px dot-grid pattern used as map background.

        Returns:
            QBrush: A tiling brush with one dot per grid cell.

        Tests:
            - test_returns_tiling_brush: Call it; verify the brush carries a
              40×40 texture.
            - test_background_colour_matches_theme: Verify the texture is filled
              with C_BG_DEEP.
        """
        grid_size = 40
        img = QImage(grid_size, grid_size, QImage.Format.Format_ARGB32)
        img.fill(QColor(C_BG_DEEP))
        painter = QPainter(img)
        painter.setPen(QColor(C_BG_MID))
        painter.drawPoint(grid_size // 2, grid_size // 2)
        painter.end()
        return QBrush(img)

    # ── Initialisation ────────────────────────────────────────────────────

    def _create_enclosures(self) -> None:
        """Create one EnclosureItem per ENCLOSURE_DEFS entry.

        Returns:
            None.

        Tests:
            - test_creates_one_item_per_definition: Call it; verify the enclosure
              dict length equals len(ENCLOSURE_DEFS).
            - test_items_added_to_scene: Call it; verify each item has this scene
              as its parent scene.
        """
        for edef in ENCLOSURE_DEFS:
            item = EnclosureItem(
                enclosure_id=edef["id"],
                name=edef["name"],
                biome=edef["biome"],
                x=edef["x"],
                y=edef["y"],
                w=edef["w"],
                h=edef["h"],
                capacity=edef["capacity"],
            )
            self.addItem(item)
            self._enclosures[edef["id"]] = item

    # ── Lighting ──────────────────────────────────────────────────────────

    def _on_lighting_step(self, value: QColor) -> None:
        """Paint the interpolated overlay colour during the phase fade.

        Args:
            value: The interpolated QColor supplied by the animation.

        Returns:
            None.

        Tests:
            - test_overlay_brush_follows_value: Call with a red QColor; verify the
              overlay brush is red.
            - test_last_colour_is_remembered: Call it, then start a new fade;
              verify the fade begins at that colour.
        """
        self._lighting_colour = value
        self._lighting_overlay.setBrush(QBrush(value))

    def apply_lighting(self, phase: str, zoo_open: bool = True) -> None:
        """Cross-fade the map overlay to the tint of the given day phase.

        Args:
            phase: The backend's ``system.time_of_day`` value — one of
                "MORNING", "NOON", "EVENING", "NIGHT". Unknown values fall
                back to the day/night tint chosen by ``zoo_open``.
            zoo_open: The backend's ``system.zoo_open`` flag, used only as a
                fallback when the phase is unknown.

        Returns:
            None.

        Tests:
            - test_noon_is_transparent: Call apply_lighting("NOON"); verify
              the target colour has alpha 0.
            - test_night_is_dark: Call apply_lighting("NIGHT"); verify the
              target colour alpha is above 100.
            - test_same_phase_does_not_restart_animation: Call twice with
              the same phase; verify the animation is not restarted.
        """
        if phase == self._phase:
            return

        rgba = PHASE_LIGHTING.get(phase, LIGHTING_DAY if zoo_open else LIGHTING_NIGHT)
        target = QColor(*rgba)

        self._lighting_anim.stop()
        self._lighting_anim.setStartValue(QColor(self._lighting_colour))
        self._lighting_anim.setEndValue(target)
        self._lighting_anim.start()
        self._phase = phase

    # ── Entity Batching ───────────────────────────────────────────────────

    def update_entities(self, game_state: dict) -> None:
        """Create, update and remove every entity sprite from a snapshot.

        Args:
            game_state: The enriched snapshot from
                ``FrontendController.get_state()`` — animals_on_map,
                visitors_on_map and (optionally) enclosures_on_map.

        Returns:
            None.

        Tests:
            - test_creates_new_animal_sprites: Pass one animal; verify one
              sprite exists in the animal dict.
            - test_removes_stale_animals: Pass an empty animals_on_map;
              verify all previously created sprites are removed.
            - test_species_picks_ascii_sprite: Pass a lion; verify the
              created sprite is an AsciiLionSprite.
        """
        self._update_animals(game_state.get("animals_on_map") or [])
        self._update_visitors(game_state.get("visitors_on_map") or [])
        self._update_enclosures(game_state.get("enclosures_on_map") or [])

        for particle in self._particles:
            particle.tick()

    def _update_animals(self, animals: list[dict]) -> None:
        """Batch-update the animal sprites.

        Args:
            animals: The ``animals_on_map`` list of the snapshot.

        Returns:
            None.

        Tests:
            - test_creates_missing_sprites: Pass one unseen animal; verify a
              sprite was created for it.
            - test_removes_stale_sprites: Pass an empty list after creating a
              sprite; verify it was removed from the scene.
        """
        seen: set[str] = set()
        for animal in animals:
            animal_id = animal["id"]
            seen.add(animal_id)
            sprite = self._animals.get(animal_id)
            if sprite is None:
                sprite = self._make_sprite(animal)
                self.addItem(sprite)
                self._animals[animal_id] = sprite
            sprite.update_state(animal["x"], animal["y"], animal.get("is_dead", False))

        for stale_id in set(self._animals) - seen:
            self.removeItem(self._animals.pop(stale_id))

    @staticmethod
    def _make_sprite(animal: dict) -> AnimalSpriteT:
        """Pick the sprite class matching the animal's species.

        Args:
            animal: One entry of ``animals_on_map``.

        Returns:
            The species-specific ASCII sprite, or a generic AnimalSprite
            circle for species without dedicated art.

        Tests:
            - test_lion_gets_ascii_sprite: Pass species "lion"; verify an
              AsciiLionSprite is returned.
            - test_unknown_species_falls_back: Pass species "zebra"; verify a
              generic AnimalSprite is returned.
        """
        animal_id = animal["id"]
        species = animal.get("species", "")
        name = animal.get("name") or animal_id
        x, y = animal["x"], animal["y"]

        if species == "lion":
            return AsciiLionSprite(animal_id=animal_id, x=x, y=y, name=name)
        if species == "penguin":
            return AsciiPenguinSprite(animal_id=animal_id, x=x, y=y, name=name)
        if species == "giraffe":
            return AsciiGiraffeSprite(animal_id=animal_id, x=x, y=y, name=name)
        return AnimalSprite(animal_id=animal_id, species=species, x=x, y=y, name=name)

    def _update_visitors(self, visitors: list[dict]) -> None:
        """Batch-update the visitor dots.

        Args:
            visitors: The ``visitors_on_map`` list of the snapshot.

        Returns:
            None.

        Tests:
            - test_creates_missing_dots: Pass one unseen visitor; verify a dot was
              created.
            - test_removes_departed_visitors: Pass an empty list; verify all dots
              were removed.
        """
        seen: set[str] = set()
        for visitor in visitors:
            visitor_id = visitor["id"]
            seen.add(visitor_id)
            sprite = self._visitors.get(visitor_id)
            if sprite is None:
                sprite = VisitorSprite(
                    visitor_id=visitor_id, x=visitor["x"], y=visitor["y"]
                )
                self.addItem(sprite)
                self._visitors[visitor_id] = sprite
            sprite.update_position(visitor["x"], visitor["y"])

        for stale_id in set(self._visitors) - seen:
            self.removeItem(self._visitors.pop(stale_id))

    def _update_enclosures(self, enclosures: list[dict]) -> None:
        """Push live occupancy and cleanliness into the enclosure items.

        Args:
            enclosures: The ``enclosures_on_map`` list assembled by the
                controller. An empty list leaves the items untouched.

        Returns:
            None.

        Tests:
            - test_pushes_occupancy: Pass an entry with occupied=2; verify the
              item label shows 2.
            - test_empty_list_is_noop: Call with []; verify the items keep their
              previous labels.
        """
        for entry in enclosures:
            item = self._enclosures.get(entry.get("id", ""))
            if item is not None:
                item.update_state(entry.get("occupied", 0), entry.get("cleanliness"))

    # ── Public accessors ──────────────────────────────────────────────────

    @property
    def animals(self) -> dict:
        """Return the animal sprite dictionary keyed by backend id.

        Returns:
            dict: Mapping of animal id to sprite.

        Tests:
            - test_empty_before_first_update: Verify the dict is empty on a
              fresh scene.
            - test_contains_added_animal: Run update_entities with one
              animal; verify its id is a key.
        """
        return self._animals

    @property
    def enclosures(self) -> dict[str, EnclosureItem]:
        """Return the enclosure item dictionary keyed by enclosure id.

        Returns:
            dict[str, EnclosureItem]: One entry per ENCLOSURE_DEFS entry.

        Tests:
            - test_has_all_defs: Verify the dict length equals
              len(ENCLOSURE_DEFS).
            - test_keys_are_ids: Verify "e_01" is among the keys.
        """
        return self._enclosures

    def animal_sprite(self, animal_id: str) -> Optional[AnimalSpriteT]:
        """Return the sprite for one animal id.

        Used by the window to mark the selected animal on the map — the
        selection can be made from the roster table as well, where no sprite
        is involved.

        Args:
            animal_id: Backend entity id (e.g. "a_01").

        Returns:
            AnimalSpriteT | None: The sprite instance, or None when the id is
            unknown (e.g. the animal died in the same frame).

        Tests:
            - test_returns_sprite_for_valid_id: Add an animal; verify the
              lookup returns its sprite.
            - test_returns_none_for_unknown_id: Look up "nonexistent";
              verify None is returned.
        """
        return self._animals.get(animal_id)
