"""
Panel tests: chat log, alert banner, roster, chart and the four tab panels.

Everything the right-hand column shows is checked here; the map itself —
sprites, enclosure items, scene and zoom view — lives in ``test_map.py``.

All of these need a QApplication, so they share the singleton from
``support.app()``. Following ``docs/test_plan.md`` §4 they check invariants
and colour constants rather than pixels, and they never wait for an
animation to finish.

Module owner: Erik (frontend).
"""

from __future__ import annotations

import unittest

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QTableWidgetItem, QWidget

from frontend.core.constants import (
    C_ACCENT,
    C_GOLD,
    C_RED,
    CHAT_COLORS,
    ENCLOSURE_DEFS,
    FOOD_PRICES,
    TREND_METRICS,
)
from frontend.tests.support import app, state_with_animals
from frontend.ui.action_panel import ActionPanel
from frontend.ui.alert_banner import AlertBanner
from frontend.ui.animal_list_panel import AnimalListPanel
from frontend.ui.chat_view import ChatlogWidget
from frontend.ui.entity_info_panel import EntityInfoPanel
from frontend.ui.help_dialog import SHORTCUTS, HelpDialog
from frontend.ui.numeric_table_item import NumericTableItem
from frontend.ui.shop_panel import ShopPanel
from frontend.ui.stats_panel import StatsPanel
from frontend.ui.styled_widgets import panel_layout, styled_button, styled_label
from frontend.ui.trend_chart import TrendChart

app()  # exactly one QApplication for the whole module

# White-box on purpose: a panel's contract is what it *shows*, and that lives
# in its child widgets. Reading ``_table`` or ``_btn_heal`` is how these tests
# check the rendered result without comparing pixels — see
# docs/test_plan.md §4.
# pylint: disable=protected-access


def _day(day_id: int, profit: float = 100.0) -> dict:
    """Build one day-summary row in the backend's documented shape.

    Args:
        day_id: The day number.
        profit: The day's profit_loss value.

    Returns:
        dict: A complete stats row.
    """
    return {
        "day_id": day_id,
        "total_visitors": 40,
        "revenue": 600.0,
        "expenses": 600.0 - profit,
        "profit_loss": profit,
        "avg_animal_welfare": 70.0,
        "avg_happiness": 80.0,
        "reputation_end_of_day": 75,
        "animals_died": 0,
    }


class TestChatlog(unittest.TestCase):
    """Timestamps, colour coding, the 500 cap and the severity filter."""

    def setUp(self) -> None:
        """Create an empty chat log."""
        self.chat = ChatlogWidget()

    def test_day_starts_at_six_in_the_morning(self) -> None:
        """Tick 0 is the MORNING phase, which reads as 06:00."""
        self.assertEqual(self.chat.format_timestamp(0), "T1 06:00")

    def test_next_day_starts_at_tick_480(self) -> None:
        """480 ticks are one simulated day."""
        self.assertEqual(self.chat.format_timestamp(480), "T2 06:00")

    def test_non_numeric_tick_is_tolerated(self) -> None:
        """A malformed tick must not break the feed."""
        self.assertEqual(self.chat.format_timestamp(None), "T1 06:00")

    def test_severity_colour_is_applied(self) -> None:
        """A warning is rendered in the gold warning colour."""
        self.chat.append_messages([{"type": "WARNING", "text": "hunger"}], 0)
        self.assertIn(CHAT_COLORS["WARNING"], self.chat._text_edit.toHtml())

    def test_receiving_frame_stamps_untimed_messages(self) -> None:
        """The backend sends tick_count 0; the frame's tick is used."""
        self.chat.append_messages([{"type": "INFO", "text": "x"}], 480)
        self.assertIn("T2 06:00", self.chat._text_edit.toPlainText())

    def test_cap_keeps_the_newest_entries(self) -> None:
        """600 messages leave the last 500."""
        self.chat.append_messages(
            [{"type": "INFO", "text": f"m{i}"} for i in range(600)], 0
        )
        self.assertEqual(self.chat.entry_count, 500)
        self.assertIn("m599", self.chat._text_edit.toPlainText())

    def test_empty_batch_changes_nothing(self) -> None:
        """An empty drain must not touch the document."""
        self.chat.append_messages([], 0)
        self.assertEqual(self.chat.entry_count, 0)

    def test_filter_hides_but_keeps_entries(self) -> None:
        """Filtering is a view, not a delete."""
        self.chat.append_messages(
            [{"type": "INFO", "text": "leise"}, {"type": "ERROR", "text": "laut"}], 0
        )
        self.chat._filter_combo.setCurrentIndex(1)
        shown = self.chat._text_edit.toPlainText()
        self.assertNotIn("leise", shown)
        self.assertIn("laut", shown)
        self.assertEqual(self.chat.entry_count, 2)

    def test_clear_empties_everything(self) -> None:
        """The clear button drops the buffer and the document."""
        self.chat.append_messages([{"type": "INFO", "text": "x"}], 0)
        self.chat.clear()
        self.assertEqual(self.chat.entry_count, 0)
        self.assertEqual(self.chat._text_edit.toPlainText(), "")

    def test_header_reports_the_count(self) -> None:
        """The header doubles as an entry counter."""
        self.chat.append_messages(
            [{"type": "INFO", "text": "a"}, {"type": "INFO", "text": "b"}], 0
        )
        self.assertIn("2", self.chat._header.text())


class TestAlertBanner(unittest.TestCase):
    """Only warnings and errors are lifted out of the feed."""

    def setUp(self) -> None:
        """Create a hidden banner."""
        self.banner = AlertBanner()

    def test_hidden_initially(self) -> None:
        """Nothing urgent means no banner."""
        self.assertEqual(self.banner.frames_left, 0)

    def test_info_is_ignored(self) -> None:
        """An informational message stays in the chat log only."""
        self.assertFalse(self.banner.push([{"type": "INFO", "text": "x"}]))
        self.assertEqual(self.banner.frames_left, 0)

    def test_warning_is_shown(self) -> None:
        """A warning becomes visible with its text."""
        self.assertTrue(self.banner.push([{"type": "WARNING", "text": "Hunger"}]))
        self.assertEqual(self.banner._label.text(), "Hunger")

    def test_error_outranks_warning(self) -> None:
        """In one batch the error is the one worth showing."""
        self.banner.push(
            [{"type": "ERROR", "text": "tot"}, {"type": "WARNING", "text": "hungrig"}]
        )
        self.assertEqual(self.banner._label.text(), "tot")

    def test_last_warning_wins(self) -> None:
        """Within one severity the most recent entry is shown."""
        self.banner.push(
            [{"type": "WARNING", "text": "erst"}, {"type": "WARNING", "text": "dann"}]
        )
        self.assertEqual(self.banner._label.text(), "dann")

    def test_alert_expires(self) -> None:
        """The countdown runs in render frames and then hides the strip."""
        self.banner.push([{"type": "WARNING", "text": "x"}])
        frames = self.banner.frames_left
        for _ in range(frames):
            self.banner.tick()
        self.assertEqual(self.banner.frames_left, 0)
        self.assertFalse(self.banner.isVisible())

    def test_tick_without_alert_is_safe(self) -> None:
        """Ticking an idle banner must not underflow the counter."""
        self.banner.tick()
        self.assertEqual(self.banner.frames_left, 0)


# setUp is the only public method — a fixture that just shares the set-up
# needs no more than that.
# pylint: disable-next=too-few-public-methods
class _RosterFixture:
    """Shared fixture: a roster with one healthy and one dead animal.

    A plain mixin, not a TestCase: as a TestCase, unittest would collect it
    *and* both subclasses, and every inherited test would run three times.
    """

    def setUp(self) -> None:
        """Create a roster with one healthy and one dead animal."""
        self.panel = AnimalListPanel()
        self.animals = [
            {
                "id": "a_01",
                "name": "Ayla",
                "species": "lion",
                "hp": 81.7,
                "hunger": 10.0,
                "welfare": 70.0,
                "is_dead": False,
            },
            {
                "id": "a_02",
                "name": "Bo",
                "species": "penguin",
                "hp": 10.0,
                "hunger": 95.0,
                "welfare": 15.0,
                "is_dead": True,
            },
        ]
        self.panel.refresh(self.animals)

    def _row_of(self, animal_id: str) -> int:
        """Return the row an animal currently occupies.

        Args:
            animal_id: The id to look for.

        Returns:
            int: The row index, or -1 when the animal is not in the table.
        """
        return self.panel._rows_by_id().get(animal_id, -1)


class TestAnimalListPanel(_RosterFixture, unittest.TestCase):
    """Rows, rounded values, colour coding and the text markers."""

    def test_one_row_per_animal(self) -> None:
        """Every animal is reachable, however the sprites overlap."""
        self.assertEqual(self.panel._table.rowCount(), 2)

    def test_values_are_rounded(self) -> None:
        """81.7 reads as 82, not as 81.7000000001."""
        row = self._row_of("a_01")
        self.assertEqual(self.panel._table.item(row, 2).text(), "82")

    def test_species_is_translated(self) -> None:
        """The backend key "lion" is shown in German."""
        row = self._row_of("a_01")
        self.assertEqual(self.panel._table.item(row, 1).text(), "Löwe")

    def test_dead_animal_is_marked(self) -> None:
        """A dead animal is unmistakable in the list too."""
        item = self.panel._table.item(self._row_of("a_02"), 0)
        self.assertTrue(item.text().endswith("✝"))
        self.assertEqual(item.foreground().color().name(), C_RED)

    def test_critical_values_carry_a_text_marker(self) -> None:
        """Colour alone excludes anyone who cannot see red against green."""
        row = self._row_of("a_02")
        for column in (2, 3, 4):
            self.assertTrue(
                self.panel._table.item(row, column).text().startswith("!!"),
                f"column {column} has no marker",
            )

    def test_healthy_values_carry_no_marker(self) -> None:
        """A marker on every row would say nothing."""
        row = self._row_of("a_01")
        self.assertFalse(self.panel._table.item(row, 2).text().startswith("!"))

    def test_low_welfare_is_red(self) -> None:
        """Welfare 15 is below the critical threshold."""
        row = self._row_of("a_02")
        self.assertEqual(
            self.panel._table.item(row, 4).foreground().color().name(), C_RED
        )

    def test_high_hunger_is_red(self) -> None:
        """Hunger is inverted: 95 means nearly starved."""
        row = self._row_of("a_02")
        self.assertEqual(
            self.panel._table.item(row, 3).foreground().color().name(), C_RED
        )

    def test_full_health_is_green(self) -> None:
        """A healthy animal reads green."""
        row = self._row_of("a_01")
        self.assertEqual(
            self.panel._table.item(row, 2).foreground().color().name(), C_ACCENT
        )

    def test_click_emits_the_animal_id(self) -> None:
        """This is the path that makes stacked sprites selectable."""
        received: list[str] = []
        self.panel.animal_selected.connect(received.append)
        table = self.panel._table
        row = self._row_of("a_02")
        QTest.mouseClick(
            table.viewport(),
            Qt.MouseButton.LeftButton,
            pos=table.visualItemRect(table.item(row, 0)).center(),
        )
        self.assertEqual(received, ["a_02"])


class TestAnimalListInteraction(_RosterFixture, unittest.TestCase):
    """Sorting, filtering, selection — everything the user does to it.

    Split off from the rendering tests so neither class grows past what
    still reads as one topic.
    """

    def test_sorting_is_numeric_not_alphabetic(self) -> None:
        """Sorted by HP, 10 must come before 82 — "10" < "82" as text only
        by accident, and "9" would break it."""
        self.panel.refresh(
            [
                {
                    "id": "a_01",
                    "name": "Ayla",
                    "species": "lion",
                    "hp": 100.0,
                    "hunger": 0.0,
                    "welfare": 100.0,
                    "is_dead": False,
                },
                {
                    "id": "a_02",
                    "name": "Bo",
                    "species": "lion",
                    "hp": 9.0,
                    "hunger": 0.0,
                    "welfare": 100.0,
                    "is_dead": False,
                },
            ]
        )
        self.panel._table.sortByColumn(2, Qt.SortOrder.AscendingOrder)
        self.assertEqual(self.panel._table.item(0, 2).text(), "!! 9")

    def test_click_after_sorting_reports_the_right_animal(self) -> None:
        """The id travels with the row, not with the index."""
        received: list[str] = []
        self.panel.animal_selected.connect(received.append)
        self.panel._table.sortByColumn(0, Qt.SortOrder.DescendingOrder)
        expected = self.panel._table.item(0, 0).data(Qt.ItemDataRole.UserRole)
        self.panel._on_cell_clicked(0, 0)
        self.assertEqual(received, [str(expected)])

    def test_attention_filter_hides_healthy_animals(self) -> None:
        """On a good day the interesting list is the empty one."""
        self.panel._filter_combo.setCurrentIndex(1)
        self.assertTrue(self.panel._table.isRowHidden(self._row_of("a_01")))
        self.assertFalse(self.panel._table.isRowHidden(self._row_of("a_02")))

    def test_all_filter_shows_everything_again(self) -> None:
        """Filtering is a view, not a delete."""
        self.panel._filter_combo.setCurrentIndex(1)
        self.panel._filter_combo.setCurrentIndex(0)
        for row in range(self.panel._table.rowCount()):
            self.assertFalse(self.panel._table.isRowHidden(row))

    def test_selection_mirrors_the_map(self) -> None:
        """A selection made on the map highlights the matching row."""
        self.panel.refresh(self.animals, "a_02")
        self.assertEqual(self.panel._table.currentRow(), self._row_of("a_02"))

    def test_unknown_selection_clears_the_highlight(self) -> None:
        """An id that is not in the list must not raise."""
        self.panel.refresh(self.animals, "a_99")
        self.assertEqual(self.panel._table.selectedItems(), [])

    def test_shrinking_list_removes_rows(self) -> None:
        """A dead animal leaves the snapshot and the table."""
        self.panel.refresh(self.animals[:1])
        self.assertEqual(self.panel._table.rowCount(), 1)

    def test_value_update_keeps_the_row_objects(self) -> None:
        """Recreating the cells would drop the user's selection."""
        row = self._row_of("a_01")
        item = self.panel._table.item(row, 2)
        self.animals[0]["hp"] = 40.0
        self.panel.refresh(self.animals)
        self.assertIs(self.panel._table.item(self._row_of("a_01"), 2), item)
        self.assertEqual(item.text(), "! 40")

    def test_empty_list_shows_the_hint(self) -> None:
        """An empty zoo explains itself instead of showing a blank grid."""
        self.panel.refresh([])
        self.assertFalse(self.panel._table.isVisible())
        self.assertTrue(self.panel._hint.isVisibleTo(self.panel))

    def test_table_is_named_for_screen_readers(self) -> None:
        """An unnamed table is announced as "table" and nothing else."""
        self.assertTrue(self.panel._table.accessibleName())


class TestNumericTableItem(unittest.TestCase):
    """The cell that made numeric sorting possible."""

    def test_sorts_by_value_not_text(self) -> None:
        """As text, "100" would come before "9"."""
        self.assertTrue(NumericTableItem("9", 9.0) < NumericTableItem("100", 100.0))

    def test_marker_does_not_affect_order(self) -> None:
        """The "!!" prefix is decoration, not data."""
        low = NumericTableItem("!! 12", 12.0)
        high = NumericTableItem("95", 95.0)
        self.assertTrue(low < high)

    def test_value_is_kept(self) -> None:
        """The number survives the formatting."""
        self.assertEqual(NumericTableItem("!! 12", 12.0).value, 12.0)

    def test_update_changes_both(self) -> None:
        """Reusing an item must update text and ordering together."""
        item = NumericTableItem("9", 9.0)
        item.set_value("! 45", 45.0)
        self.assertEqual((item.text(), item.value), ("! 45", 45.0))

    def test_comparison_with_a_plain_item_is_safe(self) -> None:
        """A mixed column must not raise AttributeError."""
        self.assertIsInstance(
            NumericTableItem("9", 9.0) < QTableWidgetItem("abc"), bool
        )


class TestTrendChart(unittest.TestCase):
    """The hand-painted trend chart and its four metrics."""

    def setUp(self) -> None:
        """Create an empty chart."""
        self.chart = TrendChart()

    def test_starts_empty(self) -> None:
        """No finished day, no bars."""
        self.assertEqual(self.chart.day_count, 0)

    def test_stores_one_bar_per_day(self) -> None:
        """Three finished days become three bars."""
        self.chart.set_days([_day(1), _day(2), _day(3)])
        self.assertEqual(self.chart.day_count, 3)

    def test_older_days_scroll_out(self) -> None:
        """The chart caps its width; the table keeps the full history."""
        self.chart.set_days([_day(i) for i in range(30)])
        self.assertLessEqual(self.chart.day_count, 14)

    def test_missing_field_counts_as_zero(self) -> None:
        """A malformed row must not break the paint pass."""
        self.chart.set_days([{"day_id": 1}])
        self.assertEqual(self.chart.day_count, 1)

    def test_defaults_to_the_first_metric(self) -> None:
        """Profit is what a zoo director looks at first."""
        self.assertEqual(self.chart.metric_key, TREND_METRICS[0][1])

    def test_metric_switch_reads_another_field(self) -> None:
        """All four metrics live in the same day summary."""
        self.chart.set_days([_day(1)], "total_visitors")
        self.assertEqual(self.chart.metric_key, "total_visitors")
        self.assertEqual(self.chart._values, [40.0])

    def test_metric_is_remembered(self) -> None:
        """The render loop refreshes without resetting the user's choice."""
        self.chart.set_days([_day(1)], "reputation_end_of_day")
        self.chart.set_days([_day(1), _day(2)])
        self.assertEqual(self.chart.metric_key, "reputation_end_of_day")

    def test_unknown_metric_is_ignored(self) -> None:
        """A typo must not blank the chart."""
        self.chart.set_days([_day(1)], "does_not_exist")
        self.assertEqual(self.chart.metric_key, TREND_METRICS[0][1])

    def test_paints_without_data(self) -> None:
        """The placeholder path is exercised, not just the bar path."""
        self.chart.resize(200, 80)
        self.chart.render(QPixmap(200, 80))

    def test_paints_mixed_signs(self) -> None:
        """Profit and loss share one scale around the zero line."""
        self.chart.set_days([_day(1, 100.0), _day(2, -50.0)])
        self.chart.resize(200, 80)
        self.chart.render(QPixmap(200, 80))

    def test_paints_a_non_negative_metric(self) -> None:
        """Visitors have no zero crossing; the baseline sits at the bottom."""
        self.chart.set_days([_day(1), _day(2)], "total_visitors")
        self.chart.resize(200, 80)
        self.chart.render(QPixmap(200, 80))

    def test_property_does_not_shadow_qpaintdevice(self) -> None:
        """A property named "metric" would break QWidget.render() — Qt calls
        QPaintDevice.metric() from inside the paint pass."""
        self.assertTrue(callable(self.chart.metric))


class TestActionPanel(unittest.TestCase):
    """Button enabling is the frontend's own precondition check."""

    def setUp(self) -> None:
        """Create a panel with one living lion on the map."""
        self.panel = ActionPanel()
        self.state = state_with_animals(
            {"id": "a_01", "species": "lion", "name": "Simba"}
        )
        self.state["enclosures_on_map"] = [
            {
                "id": "e_01",
                "name": "Savanne 1",
                "capacity": 5,
                "cleanliness": 45.0,
                "occupied": 1,
            }
        ]

    def test_all_buttons_start_disabled(self) -> None:
        """Nothing is actionable before the first snapshot."""
        for button in (
            self.panel._btn_feed_all,
            self.panel._btn_feed_one,
            self.panel._btn_heal,
            self.panel._btn_clean,
        ):
            self.assertFalse(button.isEnabled())

    def test_feed_all_needs_matching_stock(self) -> None:
        """A full fish tank cannot feed a lion."""
        self.state["inventory"]["FISH"] = 10
        self.panel.update_state(self.state, None, None)
        self.assertFalse(self.panel._btn_feed_all.isEnabled())
        self.assertIn("nur ihr eigenes Futter", self.panel._btn_feed_all.toolTip())

    def test_feed_all_enabled_with_matching_stock(self) -> None:
        """Meat in stock and a living lion is enough."""
        self.state["inventory"]["MEAT"] = 3
        self.panel.update_state(self.state, None, None)
        self.assertTrue(self.panel._btn_feed_all.isEnabled())

    def test_heal_needs_a_selection(self) -> None:
        """Without a selected animal the button explains why."""
        self.panel.update_state(self.state, None, None)
        self.assertFalse(self.panel._btn_heal.isEnabled())
        self.assertIn("Kein Tier", self.panel._btn_heal.toolTip())

    def test_heal_enabled_for_a_living_selection(self) -> None:
        """A selected, living animal can be healed."""
        self.panel.update_state(self.state, "a_01", None)
        self.assertTrue(self.panel._btn_heal.isEnabled())

    def test_heal_disabled_for_a_dead_animal(self) -> None:
        """The backend would reject it; the UI says so first."""
        self.state["animals_on_map"][0]["is_dead"] = True
        self.panel.update_state(self.state, "a_01", None)
        self.assertFalse(self.panel._btn_heal.isEnabled())

    def test_feed_one_names_the_missing_food(self) -> None:
        """A greyed-out button must never be a mystery."""
        self.panel.update_state(self.state, "a_01", None)
        self.assertIn("Fleisch", self.panel._btn_feed_one.toolTip())

    def test_clean_reports_the_current_cleanliness(self) -> None:
        """The tooltip carries the value the action will reset."""
        self.panel.update_state(self.state, None, "e_01")
        self.assertTrue(self.panel._btn_clean.isEnabled())
        self.assertIn("45", self.panel._btn_clean.toolTip())

    def test_signal_carries_the_selection(self) -> None:
        """The payload dict is what makes heal reach the right animal."""
        received: list[tuple] = []
        self.panel.action_triggered.connect(
            lambda action, params: received.append((action, params))
        )
        self.panel.update_state(self.state, "a_01", None)
        self.panel._btn_heal.click()
        self.assertEqual(received, [("heal", {"animal_id": "a_01"})])

    def test_no_signal_without_a_selection(self) -> None:
        """An action without its target is never sent."""
        received: list[tuple] = []
        self.panel.action_triggered.connect(
            lambda action, params: received.append((action, params))
        )
        self.panel._emit_selected("heal")
        self.assertEqual(received, [])


class TestShopPanel(unittest.TestCase):
    """Price preview, budget gating and the purchase payloads."""

    def setUp(self) -> None:
        """Create a shop panel with a wealthy zoo."""
        self.panel = ShopPanel()
        self.state = state_with_animals()
        self.state["enclosures_on_map"] = [
            {**edef, "cleanliness": 90.0, "free_slots": 2, "occupied": 3}
            for edef in ENCLOSURE_DEFS
        ]
        # Without a snapshot the panel assumes a budget of zero and disables
        # both buy buttons — a click would then be silently swallowed.
        self.panel.update_state(self.state)

    def test_total_is_price_times_amount(self) -> None:
        """The preview must match what the backend will charge."""
        self.panel._food_combo.setCurrentIndex(0)
        self.panel._food_spin.setValue(5)
        food = self.panel._food_combo.currentData()
        expected = f"{FOOD_PRICES[food] * 5:,.0f}".replace(",", ".")
        self.assertIn(expected, self.panel._food_total.text())

    def test_buy_buttons_disabled_when_broke(self) -> None:
        """The UI refuses before the backend has to."""
        self.state["finances"]["money"] = 1.0
        self.panel.update_state(self.state)
        self.assertFalse(self.panel._btn_buy_food.isEnabled())
        self.assertFalse(self.panel._btn_buy_animal.isEnabled())

    def test_inventory_label_lists_every_key(self) -> None:
        """MEDICINE is displayed although it is not for sale."""
        self.state["inventory"] = {"MEAT": 4, "PLANTS": 3, "FISH": 2, "MEDICINE": 1}
        self.panel.update_state(self.state)
        text = self.panel._food_inv_label.text()
        for label in ("Fleisch", "Pflanzen", "Fisch", "Medikamente"):
            self.assertIn(label, text)

    def test_enclosure_info_shows_occupancy(self) -> None:
        """Occupancy comes from the backend's free_slots."""
        self.panel.update_state(self.state)
        self.assertIn("3 /", self.panel._enclosure_info.text())

    def test_buy_food_payload(self) -> None:
        """Type and amount reach the signal unchanged."""
        received: list[tuple] = []
        self.panel.buy_food.connect(lambda t, a: received.append((t, a)))
        self.panel._food_spin.setValue(7)
        self.panel._btn_buy_food.click()
        self.assertEqual(received[0][1], 7)

    def test_buy_animal_sends_all_three_kwargs(self) -> None:
        """Name and target enclosure must not be dropped."""
        received: list[tuple] = []
        self.panel.buy_animal.connect(lambda s, n, e: received.append((s, n, e)))
        self.panel._name_edit.setText("Nala")
        self.panel._btn_buy_animal.click()
        species, name, enclosure = received[0]
        self.assertEqual(name, "Nala")
        self.assertTrue(species)
        self.assertTrue(enclosure)

    def test_name_field_is_cleared_after_purchase(self) -> None:
        """The next purchase must not reuse the previous name."""
        self.panel._name_edit.setText("Nala")
        self.panel._btn_buy_animal.click()
        self.assertEqual(self.panel._name_edit.text(), "")


class TestEntityInfoPanel(unittest.TestCase):
    """Two forms, one placeholder, and the inverted hunger scale."""

    def setUp(self) -> None:
        """Create the info panel."""
        self.panel = EntityInfoPanel()

    def test_starts_with_the_placeholder(self) -> None:
        """Nothing selected, nothing claimed."""
        self.assertTrue(self.panel._placeholder.isVisibleTo(self.panel))

    def test_unknown_id_shows_the_placeholder(self) -> None:
        """The backend answers {} for an unknown id."""
        self.panel.show_entity({})
        self.assertTrue(self.panel._placeholder.isVisibleTo(self.panel))

    def test_animal_payload_fills_the_form(self) -> None:
        """Every field the backend sends is rendered."""
        self.panel.show_entity(
            {
                "name": "Simba",
                "species": "lion",
                "age_days": 3,
                "hp": 90.0,
                "hunger": 20.0,
                "welfare": 80.0,
                "is_dead": False,
                "status_effects": ["Stressed"],
            }
        )
        self.assertIn("Simba", self.panel._lbl_name.text())
        self.assertIn("Löwe", self.panel._lbl_name.text())
        self.assertEqual(self.panel._hp_bar.value(), 90)
        self.assertIn("Stressed", self.panel._lbl_effects.text())

    def test_high_hunger_turns_the_bar_red(self) -> None:
        """0 = full, 100 = starving — the colour scale is inverted."""
        self.panel.show_entity({"name": "x", "hunger": 95.0})
        self.assertIn(C_RED, self.panel._hunger_bar.styleSheet())

    def test_low_hunger_is_green(self) -> None:
        """A satiated animal must not look alarming."""
        self.panel.show_entity({"name": "x", "hunger": 5.0})
        self.assertIn(C_ACCENT, self.panel._hunger_bar.styleSheet())

    def test_dead_animal_is_reported(self) -> None:
        """The status line says so in plain German."""
        self.panel.show_entity({"name": "x", "is_dead": True})
        self.assertEqual(self.panel._lbl_status.text(), "verstorben")

    def test_enclosure_form_shows_occupancy(self) -> None:
        """capacity minus free_slots is what a keeper wants to read."""
        self.panel.show_enclosure(
            {
                "name": "Savanne 1",
                "biome": "savanna",
                "capacity": 5,
                "free_slots": 2,
                "cleanliness": 88.0,
            }
        )
        self.assertIn("3 / 5", self.panel._lbl_enc_slots.text())
        self.assertTrue(self.panel._enclosure_box.isVisibleTo(self.panel))

    def test_dirty_enclosure_turns_gold(self) -> None:
        """45 % is below the warning threshold but above critical."""
        self.panel.show_enclosure({"name": "x", "cleanliness": 45.0})
        self.assertIn(C_GOLD, self.panel._clean_bar.styleSheet())

    def test_forms_are_mutually_exclusive(self) -> None:
        """Showing an enclosure hides the animal form."""
        self.panel.show_entity({"name": "x"})
        self.panel.show_enclosure({"name": "y"})
        self.assertFalse(self.panel._animal_box.isVisibleTo(self.panel))


class TestStatsPanel(unittest.TestCase):
    """The day table and its chart."""

    def setUp(self) -> None:
        """Create the statistics panel."""
        self.panel = StatsPanel()

    def test_empty_shows_the_hint(self) -> None:
        """Without persistence the backend returns []."""
        self.panel.refresh([])
        self.assertFalse(self.panel._table.isVisible())
        self.assertEqual(self.panel.day_count, 0)

    def test_one_row_per_day(self) -> None:
        """Three finished days become three rows."""
        self.panel.refresh([_day(1), _day(2), _day(3)])
        self.assertEqual(self.panel._table.rowCount(), 3)
        self.assertEqual(self.panel.day_count, 3)

    def test_loss_is_coloured_red(self) -> None:
        """A negative profit must be visible at a glance."""
        self.panel.refresh([_day(1, -200.0)])
        self.assertEqual(
            self.panel._table.item(0, 2).foreground().color().name(), C_RED
        )

    def test_summary_names_the_latest_day(self) -> None:
        """The summary line reports the most recent day."""
        self.panel.refresh([_day(1), _day(2)])
        self.assertIn("Tag 2", self.panel._summary.text())

    def test_chart_receives_the_same_rows(self) -> None:
        """Table and chart never disagree about the history."""
        self.panel.refresh([_day(1), _day(2)])
        self.assertEqual(self.panel._chart.day_count, 2)

    def test_metric_switch_uses_the_cached_rows(self) -> None:
        """Switching the metric must not need another backend call."""
        self.panel.refresh([_day(1), _day(2), _day(3)])
        self.panel._metric_combo.setCurrentIndex(1)
        self.assertEqual(self.panel._chart.metric_key, TREND_METRICS[1][1])
        self.assertEqual(self.panel._chart.day_count, 3)

    def test_metric_switch_before_any_data_is_safe(self) -> None:
        """The user can touch the combo before the first day closes."""
        self.panel._metric_combo.setCurrentIndex(2)
        self.assertEqual(self.panel._chart.day_count, 0)


class TestStyledWidgets(unittest.TestCase):
    """The three button variants and the label helper."""

    def test_default_button_is_dark(self) -> None:
        """The neutral variant uses the card background."""
        self.assertIn("#1c2333", styled_button("x").styleSheet())

    def test_accent_button_is_green(self) -> None:
        """The primary action stands out."""
        self.assertIn(C_ACCENT, styled_button("x", accent=True).styleSheet())

    def test_small_button_is_compact(self) -> None:
        """The header variant is 24 px, not 32."""
        self.assertIn("min-height: 24px", styled_button("x", small=True).styleSheet())

    def test_dim_label_uses_the_dim_colour(self) -> None:
        """Secondary text must be visibly secondary."""
        self.assertIn("#8b949e", styled_label("x", dim=True).styleSheet())

    def test_bold_label_reports_bold(self) -> None:
        """The flag reaches the font, not just the stylesheet."""
        self.assertTrue(styled_label("x", bold=True).font().bold())

    def test_panel_layout_is_installed_on_the_panel(self) -> None:
        """The helper replaces four copied lines in four panels."""
        panel = QWidget()
        layout = panel_layout(panel)
        self.assertIs(panel.layout(), layout)

    def test_panel_layout_applies_spacing_and_margins(self) -> None:
        """A panel that opts out of the default says so at the call site."""
        # The panel has to stay referenced: Qt deletes the layout with its
        # widget, and a temporary would be collected before the assertion.
        panel = QWidget()
        layout = panel_layout(panel, spacing=6, margin=4)
        self.assertEqual(layout.spacing(), 6)
        self.assertEqual(layout.contentsMargins().left(), 4)


class TestHelpDialog(unittest.TestCase):
    """The cheat sheet is generated from the binding table."""

    def test_one_line_per_shortcut(self) -> None:
        """Documentation and bindings cannot drift apart."""
        self.assertEqual(len(HelpDialog.shortcut_lines()), len(SHORTCUTS))

    def test_every_key_appears(self) -> None:
        """Each registered key is printed."""
        text = "\n".join(HelpDialog.shortcut_lines())
        for key, _action, _description in SHORTCUTS:
            self.assertIn(key, text)

    def test_legend_explains_the_dead_marker(self) -> None:
        """The red cross needs an explanation somewhere."""
        self.assertTrue(any("verstorben" in line for line in HelpDialog.legend_lines()))

    def test_dialog_is_modal(self) -> None:
        """The simulation keeps running behind it, but no stray clicks."""
        self.assertTrue(HelpDialog().isModal())


if __name__ == "__main__":
    unittest.main()
