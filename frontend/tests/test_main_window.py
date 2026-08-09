"""
Tests for the window: render loop, dispatch, selection and shortcuts.

Three of the bugs this project shipped and fixed lived exactly here, and all
three were invisible to a test that called the handler directly:

* the action payload was dropped between signal and slot,
* the selection only existed while the pointer was on the sprite,
* a click fell through the item stack to the enclosure underneath.

The tests below therefore go through the *real* input path — ``QTest``
mouse and key events on the actual viewport — wherever the bug would
otherwise hide. ``docs/test_plan.md`` §5 lists this as its own edge case.

Module owner: Erik (frontend).
"""

from __future__ import annotations

import contextlib
import io
import unittest
import unittest.mock

from PyQt6.QtCore import QPoint, Qt
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QSplitter

import frontend.main as main_module
from frontend.core.constants import (
    C_ACCENT,
    C_BG_DEEP,
    ROSTER_REFRESH_FRAMES,
    TICKS_PER_DAY,
    WINDOW_H,
    WINDOW_MIN_H,
    WINDOW_MIN_W,
    WINDOW_W,
)
from frontend.core.frontend_controller import FrontendController
from frontend.core.main_window import ZooMainWindow
from frontend.main import _create_demo_engine, _get_qss
from frontend.tests.support import FakeEngine, app, state_with_animals
from frontend.ui.help_dialog import SHORTCUTS

# These tests are white-box on purpose. The window exposes no public API
# beyond "show it and let it tick" — its behaviour lives in slots, timers and
# child widgets, and the three bugs named above were only reachable through
# them. Asserting against ``_lbl_status`` or ``_selected_animal_id`` is what
# makes those regressions catchable at all; the alternative would be reading
# pixels. See docs/test_plan.md §4.
# pylint: disable=protected-access

app()


_OPEN: list[ZooMainWindow] = []


def _window(engine: FakeEngine | None = None) -> ZooMainWindow:
    """Build a window on a fake engine and render one frame.

    Windows from earlier tests are closed first: QShortcut uses the
    window-shortcut context, so a key event only fires in the *active*
    window — a stack of leftover windows silently swallows every shortcut
    test.

    Args:
        engine: The engine to inject; a default one is created when omitted.

    Returns:
        ZooMainWindow: A shown, activated window with one frame rendered.
    """
    while _OPEN:
        _OPEN.pop().close()

    controller = FrontendController(engine if engine is not None else FakeEngine())
    window = ZooMainWindow(controller)
    window._timer.stop()  # the tests drive _tick() themselves
    window.show()
    window.activateWindow()
    app().processEvents()
    window._tick()
    _OPEN.append(window)
    return window


class TestClock(unittest.TestCase):
    """The in-day clock derived from the backend's raw tick counter."""

    def test_day_starts_at_six(self) -> None:
        """Tick 0 is MORNING, which must not read as midnight."""
        self.assertEqual(ZooMainWindow.clock_minutes(0), 360)

    def test_noon_phase_boundary_is_twelve(self) -> None:
        """The backend switches to NOON at a quarter of the day."""
        self.assertEqual(ZooMainWindow.clock_minutes(TICKS_PER_DAY // 4), 720)

    def test_stays_within_a_day(self) -> None:
        """The last tick of a day must not overflow into 24:00."""
        self.assertLess(ZooMainWindow.clock_minutes(TICKS_PER_DAY - 1), 1440)

    def test_wraps_at_the_day_boundary(self) -> None:
        """Two consecutive days show the same clock."""
        self.assertEqual(
            ZooMainWindow.clock_minutes(0),
            ZooMainWindow.clock_minutes(TICKS_PER_DAY),
        )


class TestRenderLoop(unittest.TestCase):
    """One frame: advance, poll, render — and survive an empty snapshot."""

    def test_frame_advances_the_simulation(self) -> None:
        """The Qt timer drives tick(), not the backend's own thread."""
        engine = FakeEngine()
        window = _window(engine)
        before = engine.calls.count("tick")
        window._tick()
        self.assertEqual(engine.calls.count("tick"), before + 1)

    def test_empty_snapshot_is_survived(self) -> None:
        """A window without an engine must still open and tick."""
        window = ZooMainWindow(FrontendController(None))
        window._timer.stop()
        window._tick()
        self.assertEqual(window._state, {})

    def test_layout_fits_the_smallest_allowed_window(self) -> None:
        """The tallest tab must not set the floor for the whole window.

        Before the scroll areas the shop tab alone demanded 490 px and the
        column 894 — on a display below that, the window could not be
        resized back into view.
        """
        window = _window()
        self.assertLessEqual(window.minimumSizeHint().height(), WINDOW_MIN_H)
        self.assertLessEqual(window.minimumSizeHint().width(), WINDOW_MIN_W)

    def test_window_is_resizable(self) -> None:
        """A fixed size is a trap on a smaller screen."""
        window = _window()
        self.assertGreater(window.maximumWidth(), WINDOW_W)
        window.resize(WINDOW_MIN_W, WINDOW_MIN_H)
        self.assertEqual(window.width(), WINDOW_MIN_W)

    def test_body_is_a_splitter_with_two_halves(self) -> None:
        """Map and panel column, and neither may be collapsed away."""
        window = _window()
        splitter = window._view.parentWidget()
        assert isinstance(splitter, QSplitter)
        self.assertEqual(splitter.count(), 2)
        self.assertFalse(splitter.childrenCollapsible())

    def test_overlay_follows_a_resize(self) -> None:
        """The alert strip is pixel-positioned, not laid out — without the
        resized signal it would keep its opening-day width forever."""
        window = _window()
        window.resize(WINDOW_MIN_W, WINDOW_MIN_H)
        app().processEvents()
        narrow = window._alert_banner.width()

        window.resize(WINDOW_W + 200, WINDOW_H)
        app().processEvents()
        self.assertGreater(window._alert_banner.width(), narrow)
        self.assertLess(window._alert_banner.width(), window._view.width())

    def test_four_tabs_exist(self) -> None:
        """Actions, roster, shop and statistics."""
        self.assertEqual(_window()._tabs.count(), 4)

    def test_roster_tab_counts_the_animals(self) -> None:
        """The caption is a live population counter."""
        window = _window(
            FakeEngine(state=state_with_animals({"id": "a_01"}, {"id": "a_02"}))
        )
        self.assertIn("(2)", window._tabs.tabText(1))


class TestDispatch(unittest.TestCase):
    """What the buttons actually send to the backend."""

    def setUp(self) -> None:
        """Create a window with one living lion."""
        self.engine = FakeEngine(
            state=state_with_animals({"id": "a_01", "species": "lion"}),
            info={"a_01": {"name": "Simba", "species": "lion", "hp": 90.0,
                           "hunger": 10.0, "welfare": 80.0, "is_dead": False}},
        )
        self.engine.state["inventory"]["MEAT"] = 5
        self.window = _window(self.engine)

    def _actions(self) -> list[tuple]:
        """Return every (action, kwargs) pair the engine received."""
        return [call for call in self.engine.calls if isinstance(call, tuple)
                and call[0] != "get_stats"]

    def test_feed_all_reaches_the_backend(self) -> None:
        """The simplest action, straight through."""
        self.window._action_panel._btn_feed_all.click()
        self.assertIn(("feed_all", {}), self._actions())

    def test_selection_bound_action_carries_its_payload(self) -> None:
        """Regression: the kwargs dict was dropped between signal and slot."""
        self.window._on_animal_selected("a_01")
        self.window._action_panel._btn_heal.click()
        self.assertIn(("heal", {"animal_id": "a_01"}), self._actions())

    def test_failed_action_is_marked_with_a_cross(self) -> None:
        """The user must see that nothing happened."""
        class Failing(FakeEngine):
            """Engine whose every action reports failure."""

            def execute_action(self, action: str, **kwargs: object) -> dict:
                """Report the action as failed instead of running it."""
                return {"success": False, "message": "nope", "chat_entries": []}

        window = _window(Failing())
        window._dispatch("feed_all")
        self.assertTrue(window._lbl_status.text().startswith("❌"))

    def test_action_message_replaces_the_live_summary(self) -> None:
        """And a later frame must not wipe it immediately."""
        self.window._dispatch("feed_all")
        self.window._tick()
        self.assertIn("ok:feed_all", self.window._lbl_status.text())


class TestSelection(unittest.TestCase):
    """The three selection bugs, checked through real input events."""

    def setUp(self) -> None:
        """Create a window with one lion standing inside an enclosure."""
        engine = FakeEngine(
            state=state_with_animals(
                {"id": "a_01", "species": "lion", "x": 150.0, "y": 120.0}
            ),
            info={"a_01": {"name": "Simba", "species": "lion", "hp": 90.0,
                           "hunger": 10.0, "welfare": 80.0, "is_dead": False}},
        )
        engine.state["inventory"]["MEAT"] = 5
        self.window = _window(engine)

    def _click_sprite(self) -> None:
        """Click the lion sprite through the real viewport."""
        sprite = self.window._scene.animal_sprite("a_01")
        assert sprite is not None
        centre = sprite.sceneBoundingRect().center()
        viewport = self.window._view.viewport()
        assert viewport is not None
        QTest.mouseClick(
            viewport,
            Qt.MouseButton.LeftButton,
            pos=self.window._view.mapFromScene(centre),
        )

    def test_hover_only_previews(self) -> None:
        """Hovering must not pin — the pointer has to travel to the button."""
        self.window._on_hover("a_01")
        self.assertIsNone(self.window._selected_animal_id)

    def test_click_pins_the_selection(self) -> None:
        """Regression: the selection used to die with the hover."""
        self._click_sprite()
        self.assertEqual(self.window._selected_animal_id, "a_01")

    def test_selection_survives_the_pointer_leaving(self) -> None:
        """This is the whole point of pinning."""
        self._click_sprite()
        self.window._on_unhover()
        self.assertEqual(self.window._selected_animal_id, "a_01")
        self.assertTrue(self.window._action_panel._btn_heal.isEnabled())

    def test_click_does_not_fall_through_to_the_enclosure(self) -> None:
        """Regression: the enclosure below cleared the fresh selection."""
        self._click_sprite()
        self.assertIsNone(self.window._selected_enclosure_id)

    def test_selected_sprite_is_marked_on_the_map(self) -> None:
        """Roster and map must agree on what is selected."""
        self.window._on_animal_selected("a_01")
        sprite = self.window._scene.animal_sprite("a_01")
        assert sprite is not None
        self.assertTrue(sprite.is_selected)

    def test_roster_click_selects_the_same_animal(self) -> None:
        """The second door into the selection, opened for stacked sprites."""
        table = self.window._animal_list._table
        viewport = table.viewport()
        assert viewport is not None
        QTest.mouseClick(
            viewport,
            Qt.MouseButton.LeftButton,
            pos=table.visualItemRect(table.item(0, 0)).center(),
        )
        self.assertEqual(self.window._selected_animal_id, "a_01")

    def test_empty_map_click_clears_everything(self) -> None:
        """Clicking nothing means selecting nothing."""
        self.window._on_animal_selected("a_01")
        viewport = self.window._view.viewport()
        assert viewport is not None
        QTest.mouseClick(viewport, Qt.MouseButton.LeftButton, pos=QPoint(780, 580))
        self.assertIsNone(self.window._selected_animal_id)
        self.assertIsNone(self.window._selected_enclosure_id)

    def test_gone_animal_drops_the_selection(self) -> None:
        """The backend deletes an animal in the tick it dies."""
        self.window._on_animal_selected("a_01")
        self.window._controller._engine.state = state_with_animals()
        self.window._tick()
        self.assertIsNone(self.window._selected_animal_id)

    def test_enclosure_click_deselects_the_animal(self) -> None:
        """Only one thing can be selected at a time."""
        self.window._on_animal_selected("a_01")
        self.window._on_enclosure_selected("e_01")
        self.assertIsNone(self.window._selected_animal_id)
        self.assertEqual(self.window._selected_enclosure_id, "e_01")


class TestShortcuts(unittest.TestCase):
    """Keyboard control, exercised through real key events."""

    def setUp(self) -> None:
        """Create a window with a stocked inventory and one lion."""
        self.engine = FakeEngine(
            state=state_with_animals({"id": "a_01", "species": "lion"}),
            info={"a_01": {"name": "Simba", "species": "lion", "hp": 50.0,
                           "hunger": 40.0, "welfare": 60.0, "is_dead": False}},
        )
        self.engine.state["inventory"]["MEAT"] = 5
        self.window = _window(self.engine)

    def test_space_toggles_the_pause(self) -> None:
        """The most-used control needs the largest key."""
        QTest.keyClick(self.window, Qt.Key.Key_Space)
        self.assertTrue(self.window._controller.paused)
        QTest.keyClick(self.window, Qt.Key.Key_Space)
        self.assertFalse(self.window._controller.paused)

    def test_s_cycles_the_speed(self) -> None:
        """Speed changes while watching, not by aiming at a button."""
        QTest.keyClick(self.window, Qt.Key.Key_S)
        self.assertNotEqual(self.window._controller.speed, 1.0)

    def test_f_feeds_every_animal(self) -> None:
        """The action reaches the backend, not just the button."""
        QTest.keyClick(self.window, Qt.Key.Key_F)
        self.assertIn(("feed_all", {}), self.engine.calls)

    def test_h_heals_the_selected_animal(self) -> None:
        """Selection-bound shortcuts carry the id."""
        self.window._on_animal_selected("a_01")
        QTest.keyClick(self.window, Qt.Key.Key_H)
        self.assertIn(("heal", {"animal_id": "a_01"}), self.engine.calls)

    def test_h_without_a_selection_explains_itself(self) -> None:
        """A key press that does nothing must say why."""
        QTest.keyClick(self.window, Qt.Key.Key_H)
        self.assertIn("auswählen", self.window._lbl_status.text())
        self.assertNotIn(("heal", {"animal_id": None}), self.engine.calls)

    def test_number_keys_switch_tabs(self) -> None:
        """One key per tab, in the order they are shown."""
        QTest.keyClick(self.window, Qt.Key.Key_3)
        self.assertEqual(self.window._tabs.currentIndex(), 2)

    def test_escape_clears_the_selection(self) -> None:
        """The fastest way out of a wrong selection."""
        self.window._on_animal_selected("a_01")
        QTest.keyClick(self.window, Qt.Key.Key_Escape)
        self.assertIsNone(self.window._selected_animal_id)

    def test_typing_a_name_does_not_trigger_shortcuts(self) -> None:
        """Single-letter shortcuts must not fire inside a text field."""
        self.window._tabs.setCurrentIndex(2)
        edit = self.window._shop_panel._name_edit
        edit.setFocus()
        speed_before = self.window._controller.speed
        QTest.keyClicks(edit, "Sheffe Rex")
        self.assertEqual(edit.text(), "Sheffe Rex")
        self.assertEqual(self.window._controller.speed, speed_before)
        self.assertFalse(self.window._controller.paused)

    def test_every_documented_shortcut_is_bound(self) -> None:
        """The help dialog cannot promise a key that does nothing."""
        bound = {shortcut.key().toString() for shortcut in self.window._shortcuts}
        for keys, action, _text in SHORTCUTS:
            if action == "tabs":  # one binding per tab, generated
                continue
            self.assertIn(keys, bound)


class TestRosterThrottle(unittest.TestCase):
    """The roster costs one backend call per animal — so not every frame."""

    def setUp(self) -> None:
        """Create a window with two animals and count the info queries."""
        self.engine = FakeEngine(
            state=state_with_animals({"id": "a_01"}, {"id": "a_02"}),
            info={
                "a_01": {"name": "Ayla", "species": "lion", "hp": 90.0},
                "a_02": {"name": "Bo", "species": "lion", "hp": 80.0},
            },
        )
        self.window = _window(self.engine)

    def _animal_queries(self) -> int:
        """Count how often an animal id was asked about."""
        return sum(1 for q in self.engine.info_queries if q.startswith("a_"))

    def test_most_frames_are_skipped(self) -> None:
        """Twenty frames must not mean twenty roster rebuilds."""
        frames, animals = 20, 2
        before = self._animal_queries()
        for _ in range(frames):
            self.window._tick()
        queries = self._animal_queries() - before
        self.assertLessEqual(queries, animals * (frames // ROSTER_REFRESH_FRAMES + 1))
        self.assertLess(queries, animals * frames)

    def test_the_due_frame_refreshes(self) -> None:
        """Throttled is not frozen."""
        before = self._animal_queries()
        for _ in range(ROSTER_REFRESH_FRAMES + 1):
            self.window._tick()
        self.assertGreater(self._animal_queries(), before)

    def test_a_new_animal_shows_up_at_once(self) -> None:
        """The id comparison is free, so it need not wait for the throttle."""
        before = self._animal_queries()
        self.engine.state = state_with_animals(
            {"id": "a_01"}, {"id": "a_02"}, {"id": "a_03"}
        )
        self.window._tick()
        self.assertGreater(self._animal_queries(), before)

    def test_selection_bypasses_the_throttle(self) -> None:
        """The table must mirror a map selection in the same moment."""
        self.window._tick()
        before = self._animal_queries()
        self.window._on_animal_selected("a_01")
        self.assertGreater(self._animal_queries(), before)


class TestAccessibility(unittest.TestCase):
    """Names and focus order — invisible to a mouse, essential without one."""

    def setUp(self) -> None:
        """Create a window on a fake engine."""
        self.window = _window()

    def test_every_chip_is_named(self) -> None:
        """A chip's caption is an emoji; a screen reader needs words."""
        for chip in (
            self.window._chip_day, self.window._chip_phase,
            self.window._chip_budget, self.window._chip_revenue,
            self.window._chip_expenses, self.window._chip_ticket,
            self.window._chip_open, self.window._chip_animals,
            self.window._chip_visitors, self.window._chip_enclosures,
            self.window._chip_action,
        ):
            self.assertTrue(chip.accessibleName(), "chip without a name")

    def test_chip_value_reaches_the_accessible_text(self) -> None:
        """The name says what it is, the description what it reads."""
        self.window._chip_budget.set_value("5.000 €")
        self.assertEqual(
            self.window._chip_budget.accessibleDescription(), "5.000 €"
        )

    def test_map_and_controls_are_named(self) -> None:
        """Otherwise they are announced as "view" and "button"."""
        self.assertTrue(self.window._view.accessibleName())
        self.assertTrue(self.window._btn_pause.accessibleName())
        self.assertTrue(self.window._btn_speed.accessibleName())

    def test_disabled_button_explains_itself_accessibly(self) -> None:
        """A tooltip is invisible to anyone who does not hover."""
        panel = self.window._action_panel
        panel.update_state(state_with_animals(), None, None)
        self.assertIn("Kein Tier", panel._btn_heal.accessibleDescription())
        self.assertIn("H", panel._btn_heal.accessibleDescription())

    def test_focus_moves_from_the_controls_into_the_panels(self) -> None:
        """Tab order follows the way someone works, not creation order."""
        self.window._btn_speed.setFocus()
        app().processEvents()
        QTest.keyClick(self.window, Qt.Key.Key_Tab)
        app().processEvents()
        self.assertFalse(self.window._view.hasFocus())


class TestEngineFactory(unittest.TestCase):
    """The entry point: what happens when the backend cannot be loaded."""

    @staticmethod
    def _close_database(engine: object) -> None:
        """Close the in-memory database the demo engine opened.

        The frontend never owns this handle — the gateway lives in the
        backend — but this test made it exist, so this test closes it
        instead of leaving a ResourceWarning in every run.

        Args:
            engine: The engine returned by the factory.
        """
        gateway = getattr(engine, "_persistence", None)
        store = getattr(gateway, "_persistence", None)
        close = getattr(store, "close", None)
        if callable(close):
            close()

    def test_success_returns_an_engine_and_no_reason(self) -> None:
        """With the backend importable the second field stays empty."""
        engine, reason = _create_demo_engine()
        self.addCleanup(self._close_database, engine)
        self.assertIsNotNone(engine)
        self.assertEqual(reason, "")

    def test_failure_reports_a_readable_reason(self) -> None:
        """stderr is invisible to whoever double-clicks the app, so the
        reason has to travel back to the caller for a dialog."""
        # Force the factory to fail by breaking one of its imports, and
        # swallow the stderr line it prints on the way out.
        with unittest.mock.patch.dict("sys.modules", {"backend.core.zoo": None}):
            with contextlib.redirect_stderr(io.StringIO()):
                engine, reason = main_module._create_demo_engine()

        self.assertIsNone(engine)
        self.assertTrue(reason)
        self.assertIn("Backend", reason)

    def test_qss_covers_the_theme_colours(self) -> None:
        """The stylesheet must carry the palette, not hard-coded greys."""
        qss = _get_qss()
        self.assertIn(C_BG_DEEP, qss)
        self.assertIn(C_ACCENT, qss)

    def test_qss_has_no_dead_selectors(self) -> None:
        """Rules for widgets the frontend never creates are noise."""
        qss = _get_qss()
        for dead in ("QToolBar", "QStatusBar", "QSlider", 'accent="true"'):
            self.assertNotIn(dead, qss)


class TestAlertPath(unittest.TestCase):
    """Warnings must reach the banner, not only the scrolling log."""

    def test_warning_raises_the_banner(self) -> None:
        """The banner is fed from the same drained batch as the chat."""
        engine = FakeEngine(
            messages=[{"type": "WARNING", "text": "Simba ist gestresst."}]
        )
        window = _window(engine)
        self.assertTrue(window._alert_banner.isVisible())
        self.assertIn("gestresst", window._alert_banner._label.text())

    def test_info_leaves_the_banner_hidden(self) -> None:
        """Not every message is worth interrupting for."""
        engine = FakeEngine(messages=[{"type": "INFO", "text": "Wetter"}])
        window = _window(engine)
        self.assertFalse(window._alert_banner.isVisible())

    def test_banner_does_not_reserve_layout_space(self) -> None:
        """It overlays the map; the fixed window has no 36 px to spare."""
        window = _window()
        before = window.minimumSizeHint().height()
        window._alert_banner.show_alert("ERROR", "x")
        self.assertEqual(window.minimumSizeHint().height(), before)


if __name__ == "__main__":
    unittest.main()
