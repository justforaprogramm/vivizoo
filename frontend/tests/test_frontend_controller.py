"""
Tests for the marshalling layer between the UI and the engine.

Covers what the controller *adds* on top of plain delegation: animal names,
the enclosure list, the speed budget, the chat buffer and the error paths
that keep a broken backend from taking the window down with it.

Module owner: Erik (frontend).
"""

from __future__ import annotations

import unittest

from frontend.core.constants import ENCLOSURE_DEFS, SPEED_STEPS
from frontend.core.frontend_controller import FrontendController
from frontend.tests.support import FakeEngine, state_with_animals


class TestWithoutEngine(unittest.TestCase):
    """Standalone mode must degrade, never crash."""

    def setUp(self) -> None:
        """Create a controller with no engine attached."""
        self.controller = FrontendController(None)

    def test_state_is_empty(self) -> None:
        """get_state() answers {} instead of raising."""
        self.assertEqual(self.controller.get_state(), {})

    def test_stats_and_chat_are_empty(self) -> None:
        """Both list-returning readers answer []."""
        self.assertEqual(self.controller.get_stats(), [])
        self.assertEqual(self.controller.get_chat_messages(), [])

    def test_animal_details_are_empty(self) -> None:
        """The roster stays empty rather than querying a missing engine."""
        self.assertEqual(self.controller.get_animal_details(), [])

    def test_action_reports_failure(self) -> None:
        """An action returns a failure dict the UI can display."""
        result = self.controller.execute_action("feed_all")
        self.assertFalse(result["success"])
        self.assertIn("Engine", result["message"])

    def test_advance_tick_returns_zero(self) -> None:
        """Nothing to drive means no steps were computed."""
        self.assertEqual(self.controller.advance_tick(), 0)


class TestEnrichment(unittest.TestCase):
    """get_state() adds names and the enclosure list."""

    def setUp(self) -> None:
        """Attach a fake engine with two named animals."""
        self.engine = FakeEngine(
            state=state_with_animals(
                {"id": "a_01", "species": "lion"},
                {"id": "a_02", "species": "giraffe"},
            ),
            info={
                "a_01": {"name": "Simba", "hp": 90.0, "hunger": 10.0,
                         "welfare": 80.0, "species": "lion"},
                "a_02": {"name": "Melman", "hp": 70.0, "hunger": 40.0,
                         "welfare": 60.0, "species": "giraffe"},
                "e_01": {"name": "Savanne 1", "biome": "savanna",
                         "cleanliness": 88.0, "free_slots": 3},
            },
        )
        self.controller = FrontendController(self.engine)

    def test_every_animal_gets_a_name(self) -> None:
        """The raw snapshot carries no name; the controller resolves it."""
        animals = self.controller.get_state()["animals_on_map"]
        self.assertEqual([a["name"] for a in animals], ["Simba", "Melman"])

    def test_names_are_cached(self) -> None:
        """A second frame must not query the engine again."""
        self.controller.get_state()
        first = self.engine.info_queries.count("a_01")
        self.controller.get_state()
        self.assertEqual(self.engine.info_queries.count("a_01"), first)

    def test_cache_is_pruned_when_an_animal_leaves(self) -> None:
        """A dead animal must not keep its cache entry forever."""
        self.controller.get_state()
        self.engine.state = state_with_animals({"id": "a_01"})
        self.controller.get_state()
        self.engine.info_queries.clear()
        self.controller.get_animal_name("a_02")
        self.assertIn("a_02", self.engine.info_queries)

    def test_enclosure_list_is_added(self) -> None:
        """One entry per ENCLOSURE_DEFS entry, with live values merged in."""
        enclosures = self.controller.get_state()["enclosures_on_map"]
        self.assertEqual(len(enclosures), len(ENCLOSURE_DEFS))
        first = enclosures[0]
        self.assertEqual(first["cleanliness"], 88.0)
        self.assertEqual(first["occupied"], first["capacity"] - 3)

    def test_unknown_enclosure_keeps_static_values(self) -> None:
        """An id the backend does not know must not blank the map."""
        self.engine.info = {}
        entry = self.controller.get_state()["enclosures_on_map"][0]
        self.assertIsNone(entry["cleanliness"])
        self.assertEqual(entry["name"], ENCLOSURE_DEFS[0]["name"])


class TestAnimalDetails(unittest.TestCase):
    """The roster payload joins the map entry and the hover payload."""

    def setUp(self) -> None:
        """Attach an engine with three animals in reverse alphabetical order."""
        self.controller = FrontendController(
            FakeEngine(
                state=state_with_animals(
                    {"id": "a_01"}, {"id": "a_02"}, {"id": "a_03"}
                ),
                info={
                    "a_01": {"name": "Cleo", "hp": 50.0},
                    "a_02": {"name": "Ayla", "hp": 60.0},
                    "a_03": {"name": "Bo", "hp": 70.0},
                },
            )
        )

    def test_sorted_by_name(self) -> None:
        """A stable, readable order beats the backend's insertion order."""
        names = [a["name"] for a in self.controller.get_animal_details()]
        self.assertEqual(names, ["Ayla", "Bo", "Cleo"])

    def test_map_and_hover_fields_are_merged(self) -> None:
        """Position comes from the map, hp from the hover payload."""
        entry = self.controller.get_animal_details()[0]
        self.assertIn("x", entry)
        self.assertEqual(entry["hp"], 60.0)

    def test_falls_back_to_the_id_without_hover_data(self) -> None:
        """An animal the backend cannot describe still gets a row."""
        controller = FrontendController(
            FakeEngine(state=state_with_animals({"id": "a_09"}))
        )
        self.assertEqual(controller.get_animal_details()[0]["name"], "a_09")


class TestPacing(unittest.TestCase):
    """Pause and the fractional speed budget."""

    def setUp(self) -> None:
        """Attach a recording engine."""
        self.engine = FakeEngine()
        self.controller = FrontendController(self.engine)

    def test_one_tick_per_frame_at_normal_speed(self) -> None:
        """Speed 1.0 computes exactly one step per frame."""
        self.assertEqual(self.controller.advance_tick(), 1)
        self.assertEqual(self.engine.calls.count("tick"), 1)

    def test_double_speed_ticks_twice(self) -> None:
        """Speed 2.0 computes two steps in the same frame."""
        while self.controller.speed != 2.0:
            self.controller.cycle_speed()
        self.controller.advance_tick()
        self.assertEqual(self.engine.calls.count("tick"), 2)

    def test_half_speed_ticks_every_second_frame(self) -> None:
        """The fractional budget carries over instead of being lost."""
        while self.controller.speed != 0.5:
            self.controller.cycle_speed()
        first = self.controller.advance_tick()
        second = self.controller.advance_tick()
        self.assertEqual((first, second), (0, 1))

    def test_speed_cycle_wraps(self) -> None:
        """Cycling through every step returns to the first."""
        for _ in SPEED_STEPS:
            self.controller.cycle_speed()
        self.assertEqual(self.controller.speed, SPEED_STEPS[0])

    def test_pause_blocks_ticks(self) -> None:
        """A paused controller must not advance the simulation."""
        self.assertTrue(self.controller.toggle_pause())
        self.assertEqual(self.controller.advance_tick(), 0)
        self.assertNotIn("tick", self.engine.calls)

    def test_paused_property_tracks_the_toggle(self) -> None:
        """The window reads this instead of keeping its own copy."""
        self.controller.toggle_pause()
        self.assertTrue(self.controller.paused)
        self.controller.toggle_pause()
        self.assertFalse(self.controller.paused)


class TestChatBuffer(unittest.TestCase):
    """Messages produced mid-frame must survive until the UI asks."""

    def test_messages_are_buffered_per_tick(self) -> None:
        """At speed 2 the messages of both steps reach the UI."""
        engine = FakeEngine(messages=[{"type": "INFO", "text": "eins"}])
        controller = FrontendController(engine)
        while controller.speed != 2.0:
            controller.cycle_speed()
        engine.messages = [{"type": "INFO", "text": "eins"}]
        controller.advance_tick()
        engine.messages = [{"type": "INFO", "text": "zwei"}]
        drained = controller.get_chat_messages()
        self.assertEqual([m["text"] for m in drained], ["eins", "zwei"])

    def test_second_drain_is_empty(self) -> None:
        """The buffer is drained, not copied."""
        controller = FrontendController(
            FakeEngine(messages=[{"type": "INFO", "text": "x"}])
        )
        controller.get_chat_messages()
        self.assertEqual(controller.get_chat_messages(), [])


class TestErrorPaths(unittest.TestCase):
    """A broken backend must produce a message, not a traceback."""

    def test_value_error_becomes_a_failure_dict(self) -> None:
        """An unknown action name is reported, not raised."""
        class Rejecting(FakeEngine):
            """Engine that rejects every action name."""

            def execute_action(self, action: str, **kwargs: object) -> dict:
                """Raise the ValueError a real engine raises."""
                raise ValueError("Unknown action 'fly'.")

        result = FrontendController(Rejecting()).execute_action("fly")
        self.assertFalse(result["success"])
        self.assertIn("fly", result["message"])

    def test_type_error_surfaces_the_backend_message(self) -> None:
        """The real cause must reach the user — see buy_animal."""
        class Broken(FakeEngine):
            """Engine reproducing the real buy_animal TypeError."""

            def execute_action(self, action: str, **kwargs: object) -> dict:
                """Raise the backend's actual signature error."""
                raise TypeError("missing 2 required positional arguments")

        result = FrontendController(Broken()).execute_action("buy_animal")
        self.assertFalse(result["success"])
        self.assertIn("positional", result["message"])

    def test_engine_without_actions_is_reported(self) -> None:
        """An engine that cannot act says so instead of failing silently."""
        class Mute:  # pylint: disable=too-few-public-methods
            """Engine stub that answers snapshots but knows no actions."""

            def get_game_state(self) -> dict:
                """Return an empty snapshot."""
                return {}

        result = FrontendController(Mute()).execute_action("feed_all")
        self.assertFalse(result["success"])

    def test_non_dict_state_is_ignored(self) -> None:
        """A malformed snapshot must not reach the widgets."""
        class Odd(FakeEngine):
            """Engine returning a list where a dict is documented."""

            def get_game_state(self) -> list:  # type: ignore[override]
                """Return a malformed snapshot on purpose."""
                return []

        self.assertEqual(FrontendController(Odd()).get_state(), {})


if __name__ == "__main__":
    unittest.main()
