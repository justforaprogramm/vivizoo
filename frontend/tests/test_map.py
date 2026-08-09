"""
Map tests: sprites, enclosure items, the scene and the zoom view.

Everything drawn on the 800×600 map lives here; the panels of the right-hand
column are tested in ``test_widgets.py``. The split is not cosmetic — the two
halves fail for different reasons. A map test breaks when the *geometry*
changes (a sprite centred on the wrong point, a zoom that overshoots its
clamp); a panel test breaks when a *value* is formatted or gated wrongly.

Following ``docs/test_plan.md`` §4 these check invariants and colour
constants rather than pixels, and they never wait for an animation.

Module owner: Erik (frontend).
"""

from __future__ import annotations

import unittest

from PyQt6.QtCore import QPoint, QPointF, Qt
from PyQt6.QtGui import QWheelEvent

from frontend.core.constants import C_GOLD, C_RED, ENCLOSURE_DEFS
from frontend.tests.support import app, state_with_animals
from frontend.ui.animal_sprite import AnimalSprite
from frontend.ui.enclosure_item import EnclosureItem
from frontend.ui.entity_sprite import EntitySprite
from frontend.ui.lion_sprite import AsciiLionSprite
from frontend.ui.particle import PARTICLE_SPEED, AmbientParticle
from frontend.ui.zoo_scene import ZooScene
from frontend.ui.zoo_view import ZooGraphicsView

app()  # exactly one QApplication for the whole module

# White-box on purpose: a sprite's state is its Qt geometry and its private
# fields, and the scene's lighting fade is a QVariantAnimation nobody exposes.
# See docs/test_plan.md §4.
# pylint: disable=protected-access


class TestSprites(unittest.TestCase):
    """The template method, the death transition and the selection glow."""

    def test_ascii_sprite_is_centred(self) -> None:
        """setPos places the centre, not the top-left corner."""
        sprite = AsciiLionSprite(animal_id="a_01", x=200.0, y=300.0, name="Simba")
        centre = sprite.sceneBoundingRect().center()
        self.assertAlmostEqual(centre.x(), 200.0, delta=1.0)
        self.assertAlmostEqual(centre.y(), 300.0, delta=1.0)

    def test_update_state_moves_the_sprite(self) -> None:
        """The template method always updates the position first."""
        sprite = AsciiLionSprite(animal_id="a_01", x=0.0, y=0.0, name="Simba")
        sprite.update_state(120.0, 140.0, False)
        self.assertEqual((sprite.pos().x(), sprite.pos().y()), (120.0, 140.0))

    def test_death_transition_switches_the_pixmap(self) -> None:
        """A dead animal must look dead."""
        sprite = AsciiLionSprite(animal_id="a_01", x=0.0, y=0.0, name="Simba")
        alive = sprite.pixmap().toImage()
        sprite.update_state(0.0, 0.0, True)
        self.assertTrue(sprite.is_dead)
        self.assertNotEqual(alive, sprite.pixmap().toImage())
        self.assertIn("verstorben", sprite.toolTip())

    def test_revival_restores_the_living_look(self) -> None:
        """The hooks are symmetric."""
        sprite = AsciiLionSprite(animal_id="a_01", x=0.0, y=0.0, name="Simba")
        sprite.update_state(0.0, 0.0, True)
        sprite.update_state(0.0, 0.0, False)
        self.assertFalse(sprite.is_dead)
        self.assertNotIn("verstorben", sprite.toolTip())

    def test_pixmaps_are_cached_per_species_and_colour(self) -> None:
        """Rendering ASCII art once per colour is enough."""
        first = AsciiLionSprite._pixmap_for("#ffffff")
        second = AsciiLionSprite._pixmap_for("#ffffff")
        self.assertIs(first, second)

    def test_click_reports_the_animal_id(self) -> None:
        """Clicking is what pins the selection."""
        received: list[str] = []
        sprite = AsciiLionSprite(animal_id="a_07", x=0.0, y=0.0, name="Simba")
        sprite.set_click_callback(received.append)
        sprite.mousePressEvent(None)
        self.assertEqual(received, ["a_07"])

    def test_selection_glow_can_be_toggled(self) -> None:
        """The glow works for pixmap sprites without a subclass override."""
        sprite = AsciiLionSprite(animal_id="a_01", x=0.0, y=0.0, name="Simba")
        sprite.set_selected(True)
        self.assertTrue(sprite.is_selected)
        self.assertIsNotNone(sprite.graphicsEffect())
        sprite.set_selected(False)
        self.assertIsNone(sprite.graphicsEffect())

    def test_ellipse_sprite_uses_the_species_colour(self) -> None:
        """The fallback sprite is the second rendering of one interface."""
        sprite = AnimalSprite(
            animal_id="a_01", species="penguin", x=10.0, y=10.0, name="Pingu"
        )
        self.assertEqual(sprite.brush().color().name(), "#7986cb")

    def test_unknown_species_falls_back_to_grey(self) -> None:
        """A species the frontend has no art for still renders."""
        sprite = AnimalSprite(
            animal_id="a_01", species="zebra", x=0.0, y=0.0, name="Marty"
        )
        self.assertEqual(sprite.brush().color().name(), "#aaaaaa")

    def test_hover_grows_the_ellipse_and_shrinks_back(self) -> None:
        """The highlight hook is overridden only where it means something."""
        sprite = AnimalSprite(
            animal_id="a_01", species="lion", x=50.0, y=50.0, name="Simba"
        )
        sprite.highlight_on()
        grown = sprite.rect().width()
        sprite.highlight_off()
        self.assertGreater(grown, sprite.rect().width())

    def test_base_hooks_are_abstract(self) -> None:
        """The contract is enforced, not merely documented."""
        with self.assertRaises(NotImplementedError):
            EntitySprite().update_position(0.0, 0.0)


class TestEnclosureItem(unittest.TestCase):
    """Border states and the click callback."""

    def _item(self) -> EnclosureItem:
        """Build one savanna enclosure with capacity 5."""
        return EnclosureItem(
            enclosure_id="e_01", name="Savanne 1", biome="savanna",
            x=0.0, y=0.0, w=100.0, h=80.0, capacity=5,
        )

    def test_clean_enclosure_has_a_dashed_border(self) -> None:
        """The neutral state must stay unobtrusive."""
        item = self._item()
        item.update_state(2, 95.0)
        self.assertEqual(item.pen().style(), Qt.PenStyle.DashLine)

    def test_dirty_enclosure_turns_gold(self) -> None:
        """45 % is the warning band."""
        item = self._item()
        item.update_state(2, 45.0)
        self.assertEqual(item.pen().color().name(), C_GOLD)

    def test_filthy_enclosure_turns_red(self) -> None:
        """Below 30 % it is critical."""
        item = self._item()
        item.update_state(2, 10.0)
        self.assertEqual(item.pen().color().name(), C_RED)

    def test_over_capacity_gets_a_solid_red_border(self) -> None:
        """Overcrowding outranks the cleanliness warning."""
        item = self._item()
        item.update_state(9, 100.0)
        self.assertEqual(item.pen().style(), Qt.PenStyle.SolidLine)
        self.assertEqual(item.pen().color().name(), C_RED)

    def test_label_reports_occupancy_and_cleanliness(self) -> None:
        """Both live backend values are on the map itself."""
        item = self._item()
        item.update_state(3, 88.0)
        self.assertIn("3/5", item.toolTip())
        self.assertIn("88", item.toolTip())

    def test_click_reports_the_enclosure_id(self) -> None:
        """The callback replaces a signal Qt6 cannot offer here."""
        received: list[str] = []
        item = self._item()
        item.set_click_callback(received.append)
        item.mousePressEvent(None)
        self.assertEqual(received, ["e_01"])


class TestZooScene(unittest.TestCase):
    """Sprite batching, species dispatch and the lighting overlay."""

    def setUp(self) -> None:
        """Create a fresh scene."""
        self.scene = ZooScene()

    def test_enclosures_come_from_the_definitions(self) -> None:
        """The map geometry is frontend-owned and complete."""
        self.assertEqual(len(self.scene.enclosures), len(ENCLOSURE_DEFS))

    def test_species_picks_the_matching_sprite_class(self) -> None:
        """Polymorphism starts at construction."""
        self.scene.update_entities(
            state_with_animals({"id": "a_01", "species": "lion"})
        )
        self.assertIsInstance(self.scene.animals["a_01"], AsciiLionSprite)

    def test_unknown_species_falls_back_to_the_circle(self) -> None:
        """A new backend species renders before anyone draws art."""
        self.scene.update_entities(
            state_with_animals({"id": "a_01", "species": "zebra"})
        )
        self.assertIsInstance(self.scene.animals["a_01"], AnimalSprite)

    def test_stale_sprites_are_removed(self) -> None:
        """An animal that leaves the snapshot leaves the map."""
        self.scene.update_entities(state_with_animals({"id": "a_01"}))
        self.scene.update_entities(state_with_animals())
        self.assertEqual(self.scene.animals, {})

    def test_existing_sprites_are_reused(self) -> None:
        """A moving animal keeps its sprite object."""
        self.scene.update_entities(state_with_animals({"id": "a_01"}))
        first = self.scene.animal_sprite("a_01")
        self.scene.update_entities(
            state_with_animals({"id": "a_01", "x": 400.0})
        )
        self.assertIs(self.scene.animal_sprite("a_01"), first)

    def test_lookup_of_an_unknown_id_returns_none(self) -> None:
        """The window tolerates a sprite that no longer exists."""
        self.assertIsNone(self.scene.animal_sprite("a_99"))

    def test_night_is_darker_than_noon(self) -> None:
        """The four phases must actually differ."""
        self.scene.apply_lighting("NOON")
        self.scene._lighting_anim.stop()
        self.scene.apply_lighting("NIGHT")
        self.assertGreater(self.scene._lighting_anim.endValue().alpha(), 100)

    def test_repeating_a_phase_does_not_restart_the_fade(self) -> None:
        """Ten frames per second must not restart an 800 ms animation."""
        self.scene.apply_lighting("NIGHT")
        self.scene._lighting_anim.stop()
        self.scene.apply_lighting("NIGHT")
        self.assertEqual(
            self.scene._lighting_anim.state().value, 0  # still stopped
        )

    def test_unknown_phase_uses_the_open_fallback(self) -> None:
        """A phase the frontend does not know must not blank the map."""
        self.scene.apply_lighting("SIESTA", zoo_open=True)
        self.assertEqual(self.scene._lighting_anim.endValue().alpha(), 0)


class TestZooView(unittest.TestCase):
    """Zoom clamping and the empty-space click."""

    def setUp(self) -> None:
        """Create a view onto a fresh scene."""
        self.view = ZooGraphicsView(ZooScene())

    def _zoom(self, steps: int, inwards: bool) -> None:
        """Apply n wheel notches in one direction.

        Args:
            steps: How many notches.
            inwards: True to zoom in, False to zoom out.
        """
        delta = QPoint(0, 120 if inwards else -120)
        for _ in range(steps):
            self.view.wheelEvent(
                QWheelEvent(
                    QPointF(10.0, 10.0), QPointF(10.0, 10.0), QPoint(), delta,
                    Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier,
                    Qt.ScrollPhase.NoScrollPhase, False,
                )
            )

    def test_starts_unscaled(self) -> None:
        """The whole map fits at 1.0."""
        self.assertAlmostEqual(self.view.transform().m11(), 1.0)

    def test_zoom_in_is_clamped_exactly(self) -> None:
        """50 notches end at 3.0, not at 3.06."""
        self._zoom(50, inwards=True)
        self.assertAlmostEqual(self.view.transform().m11(), 3.0, places=6)

    def test_zoom_out_is_clamped_exactly(self) -> None:
        """The lower bound is just as exact."""
        self._zoom(50, inwards=False)
        self.assertAlmostEqual(self.view.transform().m11(), 0.3, places=6)

    def test_none_event_is_ignored(self) -> None:
        """Qt may hand out None; that must not raise."""
        self.view.wheelEvent(None)
        self.view.mousePressEvent(None)

class TestAmbientParticle(unittest.TestCase):
    """The decorative dust motes: drift speed and the wrap-around."""

    def test_speed_is_inside_the_configured_range(self) -> None:
        """Randomised per particle, so the swarm does not move as one block."""
        for _ in range(20):
            speed = AmbientParticle(10.0, 20.0).drift_speed
            self.assertGreaterEqual(speed, 0.5 * PARTICLE_SPEED)
            self.assertLessEqual(speed, 1.5 * PARTICLE_SPEED)

    def test_tick_moves_up_by_exactly_the_drift_speed(self) -> None:
        """The public speed really is the one that is applied."""
        particle = AmbientParticle(10.0, 200.0)
        before = particle.rect().y()
        particle.tick()
        self.assertAlmostEqual(before - particle.rect().y(), particle.drift_speed)

    def test_particle_wraps_around_at_the_top(self) -> None:
        """A mote leaving the top edge reappears below the bottom."""
        particle = AmbientParticle(10.0, -10.0)
        particle.tick()
        self.assertGreater(particle.rect().y(), 0)


if __name__ == "__main__":
    unittest.main()
