"""
ZooScene — QGraphicsScene managing all entity sprites on the 800×600 map.

Tier 1: Gradient enclosures.
Tier 3: Dot-grid map background, ambient floating particles,
        smooth day/night lighting transition (QPropertyAnimation).

Tests:
    - test_enclosures_created_from_defs, test_lighting_overlay_exists_at_correct_z,
      test_update_entities_creates_new_animal, test_apply_lighting_sets_dark_overlay.
"""

from __future__ import annotations

import random
from typing import Optional

from PyQt6.QtWidgets import (
    QGraphicsScene,
    QGraphicsRectItem,
    QGraphicsEllipseItem,
    QGraphicsItem,
)
from PyQt6.QtCore import Qt, QVariantAnimation, QEasingCurve
from PyQt6.QtGui import QBrush, QColor, QPen

from frontend.core.constants import (
    MAP_W,
    MAP_H,
    Z_OVERLAY,
    Z_VISITORS,
    C_BG_DEEP,
    C_BG_MID,
    C_BORDER,
    LIGHTING_DAY,
    LIGHTING_NIGHT,
    ENCLOSURE_DEFS,
)
from frontend.ui.animal_sprite import AnimalSprite
from frontend.ui.lion_sprite import AsciiLionSprite
from frontend.ui.penguin_sprite import AsciiPenguinSprite
from frontend.ui.giraffe_sprite import AsciiGiraffeSprite
from frontend.ui.visitor_sprite import VisitorSprite
from frontend.ui.enclosure_item import EnclosureItem

# ── Tier 3: Particle config ──────────────────────────────────────────────
PARTICLE_COUNT = 30
PARTICLE_SPEED = 0.3  # px per tick
PARTICLE_SIZE = 2  # px


class _Particle(QGraphicsEllipseItem):
    """Tiny floating dot drifting slowly upward."""

    def __init__(self, x: float, y: float, parent: Optional[QGraphicsItem] = None):
        super().__init__(x, y, PARTICLE_SIZE, PARTICLE_SIZE, parent)
        self.setBrush(QBrush(QColor(C_BORDER)))
        self.setPen(QPen(Qt.PenStyle.NoPen))
        self.setZValue(Z_VISITORS - 1)  # below visitors, above animals
        self._drift_speed = random.uniform(0.5, 1.5) * PARTICLE_SPEED
        self._wobble_phase = random.random() * 6.28

    def tick(self) -> None:
        """Move upward and reset when off-screen.

        Tests:
            - test_particle_ticks_upward: Record position, call tick();
              verify y coordinate decreased (particle moved up).
            - test_particle_wraps_around: Move particle above MAP_H;
              call tick(); verify it reappears at the top.
        """
        rect = self.rect()
        new_y = rect.y() - self._drift_speed
        if new_y < -PARTICLE_SIZE:
            new_y = MAP_H + PARTICLE_SIZE
            rect.moveLeft(random.randint(0, MAP_W))
        self.setRect(rect.x(), new_y, PARTICLE_SIZE, PARTICLE_SIZE)


class ZooScene(QGraphicsScene):
    """The 2-D zoo map (800×600) holding all spatial entity representations.

    Manages animal, visitor, and enclosure sprites as dicts keyed by
    backend ID. Handles lighting overlay and ambient particle effects.

    Tests:
        - test_enclosures_created_from_defs: Create ZooScene; verify
          len(_enclosures) == len(ENCLOSURE_DEFS).
        - test_lighting_overlay_exists_at_correct_z: Verify overlay
          zValue() == Z_OVERLAY.
        - test_update_entities_creates_new_animal: Pass game_state with
          1 animal; verify 1 new sprite added.
        - test_apply_lighting_sets_dark_overlay: Call apply_lighting(False);
          verify overlay opacity > 0 (dark).
    """

    def __init__(self, parent: Optional[object] = None) -> None:
        super().__init__(0, 0, MAP_W, MAP_H, parent)

        # ── Tier 3: Dot-grid background ──────────────────────────────────
        self.setBackgroundBrush(self._build_grid_brush())

        # Entity dictionaries
        self._animals: dict[
            str,
            AnimalSprite | AsciiLionSprite | AsciiPenguinSprite | AsciiGiraffeSprite,
        ] = {}
        self._visitors: dict[str, VisitorSprite] = {}
        self._enclosures: dict[str, EnclosureItem] = {}

        # Lighting overlay (topmost)
        self._lighting_overlay = QGraphicsRectItem(0, 0, MAP_W, MAP_H)
        self._lighting_overlay.setZValue(Z_OVERLAY)
        self._lighting_overlay.setBrush(QBrush(QColor(*LIGHTING_DAY)))
        self.addItem(self._lighting_overlay)

        # ── Tier 3: Smooth lighting transition animation ─────────────────
        self._lighting_anim = QVariantAnimation()
        self._lighting_anim.setDuration(800)
        self._lighting_anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self._lighting_anim.valueChanged.connect(self._on_lighting_step)
        self._lighting_is_night = False

        # ── Tier 3: Ambient particles ────────────────────────────────────
        self._particles: list[_Particle] = []
        for _ in range(PARTICLE_COUNT):
            px = random.randint(0, MAP_W)
            py = random.randint(0, MAP_H)
            p = _Particle(px, py)
            self.addItem(p)
            self._particles.append(p)

        # ── Static enclosures ─────────────────────────────────────────────
        self._create_enclosures()

    # ── Background grid ─────────────────────────────────────────────────

    @staticmethod
    def _build_grid_brush() -> QBrush:
        """Create a subtle dot-grid pattern for game-map aesthetic."""
        from PyQt6.QtGui import QImage, QPainter

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

    def _on_lighting_step(self, value: float) -> None:
        """Update the overlay opacity during the fade animation."""
        self._lighting_overlay.setOpacity(value)

    def apply_lighting(self, zoo_open: bool) -> None:
        """Smoothly transition between day and night.

        Tier 3: Uses QVariantAnimation to ramp overlay opacity instead of
        instant colour swap.

        Args:
            zoo_open: True → fade to transparent (day), False → fade to dark.

        Tests:
            - test_day_is_transparent: Call apply_lighting(True); verify
              overlay opacity transitions toward 0.0.
            - test_night_is_dark: Call apply_lighting(False); verify
              overlay brush opacity > 0 (semi-transparent black).
            - test_no_op_when_already_at_target: Call with same state
              twice; verify animation does not restart unnecessarily.
        """
        start = self._lighting_overlay.opacity()
        target = 0.0 if zoo_open else 1.0
        if abs(start - target) < 0.01:
            return  # already at target

        if zoo_open:
            self._lighting_overlay.setBrush(QBrush(QColor(*LIGHTING_DAY)))
        else:
            self._lighting_overlay.setBrush(QBrush(QColor(*LIGHTING_NIGHT)))

        self._lighting_anim.stop()
        self._lighting_anim.setStartValue(start)
        self._lighting_anim.setEndValue(target)
        self._lighting_anim.start()
        self._lighting_is_night = not zoo_open

    # ── Entity Batching ───────────────────────────────────────────────────

    def update_entities(self, game_state: dict) -> None:
        """Create, update, and remove all entity sprites from game state.

        Args:
            game_state: Full state dict (animals_on_map, visitors_on_map).

        Tests:
            - test_creates_new_animal_sprites: Pass 1 animal; verify scene
              now has 1 animal sprite in _animals dict.
            - test_removes_stale_animals: Pass empty animals_on_map list;
              verify all previously created sprites are removed from scene.
            - test_visitors_created_and_updated: Pass 2 visitors; verify
              _visitors dict has 2 entries with correct positions.
        """
        # Animals
        backend_ids: set[str] = set()
        for a in game_state.get("animals_on_map", []):
            aid = a["id"]
            backend_ids.add(aid)
            if aid in self._animals:
                sprite = self._animals[aid]
            else:
                if a["species"] == "lion":
                    sprite = AsciiLionSprite(
                        animal_id=aid,
                        x=a["x"],
                        y=a["y"],
                        name=a.get("name", "Löwe"),
                    )
                elif a["species"] == "penguin":
                    sprite = AsciiPenguinSprite(
                        animal_id=aid,
                        x=a["x"],
                        y=a["y"],
                        name=a.get("name", "Pingu"),
                    )
                elif a["species"] == "giraffe":
                    sprite = AsciiGiraffeSprite(
                        animal_id=aid,
                        x=a["x"],
                        y=a["y"],
                        name=a.get("name", "Giraffe"),
                    )
                else:
                    sprite = AnimalSprite(
                        animal_id=aid,
                        species=a["species"],
                        x=a["x"],
                        y=a["y"],
                        name=a.get("name", "?"),
                    )
                self.addItem(sprite)
                self._animals[aid] = sprite
            sprite.update_state(a["x"], a["y"], a.get("is_dead", False))

        for stale_id in set(self._animals) - backend_ids:
            self.removeItem(self._animals.pop(stale_id))

        # Visitors
        visitor_ids: set[str] = set()
        for v in game_state.get("visitors_on_map", []):
            vid = v["id"]
            visitor_ids.add(vid)
            if vid in self._visitors:
                sprite = self._visitors[vid]
            else:
                sprite = VisitorSprite(visitor_id=vid, x=v["x"], y=v["y"])
                self.addItem(sprite)
                self._visitors[vid] = sprite
            sprite.update_state(v["x"], v["y"])

        for stale_id in set(self._visitors) - visitor_ids:
            self.removeItem(self._visitors.pop(stale_id))

        # Enclosure counts
        counts: dict[str, int] = {}
        for a in game_state.get("animals_on_map", []):
            eid = a.get("enclosure_id", "")
            if eid:
                counts[eid] = counts.get(eid, 0) + 1
        for eid, item in self._enclosures.items():
            item.update_state(counts.get(eid, 0))

        # ── Tier 3: Animate particles ────────────────────────────────────
        for p in self._particles:
            p.tick()

    def clear_all(self) -> None:
        """Remove all dynamic entities (animals + visitors). Enclosures persist.

        Tests:
            - test_clear_removes_all_animals: Add 3 animals, call clear_all;
              verify _animals dict is empty.
            - test_clear_removes_all_visitors: Add 5 visitors, call clear_all;
              verify _visitors dict is empty.
            - test_clear_preserves_enclosures: Call clear_all; verify
              _enclosures dict still has ENCLOSURE_DEFS length.
        """
        for sprite in list(self._animals.values()):
            self.removeItem(sprite)
        self._animals.clear()
        for sprite in list(self._visitors.values()):
            self.removeItem(sprite)
        self._visitors.clear()

    # ── Public accessors (used by ZooMainWindow) ─────────────────────────

    @property
    def animals(self) -> dict:
        """Return the animal sprite dictionary (public accessor)."""
        return self._animals

    @property
    def enclosures(self) -> dict[str, EnclosureItem]:
        """Return the enclosure item dictionary (public accessor)."""
        return self._enclosures

    def animal_sprite(
        self, animal_id: str
    ) -> Optional[
        AnimalSprite | AsciiLionSprite | AsciiPenguinSprite | AsciiGiraffeSprite
    ]:
        """Return the sprite for a given animal ID.

        Args:
            animal_id: Backend entity id (e.g. "a_01").

        Returns:
            The sprite instance, or None if not found.

        Tests:
            - test_returns_sprite_for_valid_id: Add animal; call animal_sprite
              with its id; verify it returns the sprite.
            - test_returns_none_for_unknown_id: Call animal_sprite("nonexistent");
              verify None returned.
        """
        return self._animals.get(animal_id)

    def enclosure_item(self, enclosure_id: str) -> Optional[EnclosureItem]:
        """Return the enclosure item for a given enclosure ID.

        Args:
            enclosure_id: Enclosure id (e.g. "e_01").

        Returns:
            The EnclosureItem, or None if not found.

        Tests:
            - test_returns_enclosure_for_valid_id: Verify enclosure_item("e_01")
              returns an EnclosureItem instance.
            - test_returns_none_for_unknown_id: Call enclosure_item("e_99");
              verify None returned.
        """
        return self._enclosures.get(enclosure_id)
