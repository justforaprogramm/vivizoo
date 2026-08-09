"""
Invariants of ``core/constants.py`` — the values every widget reads.

These are cheap checks with real value: a typo in a colour or a price is
invisible in the running app until someone compares it with the backend.

Module owner: Erik (frontend).
"""

from __future__ import annotations

import re
import unittest

from frontend.core import constants as C


class TestColours(unittest.TestCase):
    """Every C_* colour must be a valid hex triple."""

    def test_all_colour_constants_are_hex(self) -> None:
        """Each C_* string matches #rrggbb."""
        pattern = re.compile(r"^#[0-9a-fA-F]{6}$")
        for name in dir(C):
            if not name.startswith("C_"):
                continue
            value = getattr(C, name)
            if isinstance(value, str):
                self.assertRegex(value, pattern, f"{name} is not a hex colour")

    def test_chat_colours_cover_backend_severities(self) -> None:
        """The four severities LogEntry documents all have a colour."""
        for severity in ("INFO", "WARNING", "ERROR", "SUCCESS"):
            self.assertIn(severity, C.CHAT_COLORS)

    def test_alert_types_are_known_severities(self) -> None:
        """The banner only reacts to severities the chat can colour."""
        for severity in C.ALERT_TYPES:
            self.assertIn(severity, C.CHAT_COLORS)


class TestGeometry(unittest.TestCase):
    """Enclosure rectangles must stay inside the map."""

    def test_enclosures_within_map_bounds(self) -> None:
        """No rectangle leaves (0, 0, MAP_W, MAP_H)."""
        for edef in C.ENCLOSURE_DEFS:
            self.assertGreaterEqual(edef["x"], 0)
            self.assertGreaterEqual(edef["y"], 0)
            self.assertLessEqual(edef["x"] + edef["w"], C.MAP_W)
            self.assertLessEqual(edef["y"] + edef["h"], C.MAP_H)

    def test_enclosure_ids_are_unique(self) -> None:
        """Two enclosures with the same id would shadow each other."""
        ids = [edef["id"] for edef in C.ENCLOSURE_DEFS]
        self.assertEqual(len(ids), len(set(ids)))

    def test_every_biome_has_colours_and_a_label(self) -> None:
        """A missing biome would render as the fallback grey."""
        for edef in C.ENCLOSURE_DEFS:
            biome = edef["biome"]
            self.assertIn(biome, C.BIOME_COLORS)
            self.assertIn(biome, C.BIOME_COLORS_LIGHT)
            self.assertIn(biome, C.BIOME_LABELS)


class TestSpeciesTables(unittest.TestCase):
    """The four per-species tables must describe the same species."""

    def test_species_tables_agree(self) -> None:
        """Colours, labels, food and prices cover identical keys."""
        expected = set(C.SPECIES_COLORS)
        self.assertEqual(set(C.SPECIES_LABELS), expected)
        self.assertEqual(set(C.SPECIES_FOOD), expected)
        self.assertEqual(set(C.ANIMAL_PRICES), expected)

    def test_preferred_food_is_a_real_inventory_key(self) -> None:
        """A species cannot prefer food the inventory does not stock."""
        for food in C.SPECIES_FOOD.values():
            self.assertIn(food, C.INVENTORY_KEYS)

    def test_shop_sells_a_subset_of_the_inventory(self) -> None:
        """The shop must not offer something the backend cannot store."""
        self.assertTrue(set(C.SHOP_FOOD_TYPES).issubset(set(C.INVENTORY_KEYS)))

    def test_every_inventory_key_has_a_price_and_label(self) -> None:
        """An unpriced key would render as 0 € in the shop."""
        for key in C.INVENTORY_KEYS:
            self.assertIn(key, C.FOOD_PRICES)
            self.assertIn(key, C.FOOD_LABELS)


class TestPacing(unittest.TestCase):
    """Tick pacing and the four day phases."""

    def test_ticks_per_day_divides_into_four_phases(self) -> None:
        """The backend switches phase every TICKS_PER_DAY // 4 ticks."""
        self.assertEqual(C.TICKS_PER_DAY % 4, 0)

    def test_ticks_per_day_divides_the_clock(self) -> None:
        """One tick must be a whole number of simulated minutes."""
        self.assertEqual((24 * 60) % C.TICKS_PER_DAY, 0)

    def test_all_four_phases_have_lighting_and_labels(self) -> None:
        """A missing phase would fall back to the zoo_open tint."""
        for phase in ("MORNING", "NOON", "EVENING", "NIGHT"):
            self.assertIn(phase, C.PHASE_LIGHTING)
            self.assertIn(phase, C.PHASE_LABELS)
            self.assertIn(phase, C.PHASE_ICONS)

    def test_speed_steps_start_at_normal_speed(self) -> None:
        """Cycling must begin at 1× and contain no zero."""
        self.assertEqual(C.SPEED_STEPS[0], 1.0)
        self.assertTrue(all(step > 0 for step in C.SPEED_STEPS))


class TestThresholds(unittest.TestCase):
    """Warning thresholds must be ordered warn > critical."""

    def test_cleanliness_thresholds_ordered(self) -> None:
        """Gold must trigger before red."""
        self.assertGreater(C.CLEAN_WARN, C.CLEAN_CRITICAL)

    def test_value_thresholds_ordered(self) -> None:
        """The roster grading uses the same ordering rule."""
        self.assertGreater(C.VALUE_WARN, C.VALUE_CRITICAL)


if __name__ == "__main__":
    unittest.main()
