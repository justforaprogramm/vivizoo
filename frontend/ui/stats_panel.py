"""
StatsPanel — day-end statistics table fed by ``engine.get_stats()``.

The backend writes one summary row per finished simulated day (480 ticks)
through its persistence gateway. Those rows are the only place where
``reputation_end_of_day`` and ``avg_happiness`` are exposed to the
frontend — the live snapshot does not carry them — so this panel is what
makes them visible at all.

Above the table sits a :class:`~frontend.ui.trend_chart.TrendChart` fed from
the same rows: the table answers "what happened on day 7?", the chart answers
"is the zoo getting better?".

Without a persistence gateway the backend returns an empty list; the panel
then shows an explanatory hint instead of an empty table.

Tests:
    - test_empty_stats_shows_hint: Call refresh([]); verify the hint label
      is visible and the table is hidden.
    - test_rows_match_stats_length: Call refresh with 3 day dicts; verify
      the table has exactly 3 rows.
    - test_newest_day_is_last_row: Call refresh with days 1..3; verify the
      last row shows day 3.

Module owner: Erik (frontend).
"""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QWidget,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

from frontend.core.constants import (
    C_ACCENT,
    C_BG_CARD,
    C_BG_PANEL,
    C_BORDER,
    C_RED,
    C_TEXT,
    C_TEXT_DIM,
    TREND_METRICS,
)
from frontend.ui.styled_widgets import panel_layout
from frontend.ui.trend_chart import TrendChart

_COLUMNS = ("Tag", "Besucher", "Gewinn", "Ø Wohl", "Ruf", "Tote")

_TABLE_QSS = (
    f"QTableWidget {{ background: {C_BG_CARD}; color: {C_TEXT};"
    f" border: 1px solid {C_BORDER}; border-radius: 4px;"
    f" gridline-color: {C_BORDER}; font-size: 11px; }}"
    f"QHeaderView::section {{ background: {C_BG_PANEL}; color: {C_TEXT_DIM};"
    f" border: none; border-bottom: 1px solid {C_BORDER}; padding: 4px;"
    f" font-size: 11px; font-weight: bold; }}"
    "QTableWidget::item { padding: 2px 4px; }"
)


class StatsPanel(QWidget):
    """Table of the most recent day-end summaries.

    Tests:
        - test_starts_with_hint: Create the panel; verify the hint is
          visible before the first refresh.
        - test_profit_is_colour_coded: Refresh with a negative profit;
          verify that cell uses the red colour.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        """Build the header, the hint label and the (initially hidden) table.

        Args:
            parent: Optional parent widget.

        Returns:
            None (constructor).

        Tests:
            - test_table_has_six_columns: Verify the table's column count
              matches the header tuple.
            - test_table_is_read_only: Verify no edit triggers are enabled.
        """
        super().__init__(parent)
        layout = panel_layout(self)

        header_row = QHBoxLayout()
        header_row.setSpacing(6)

        header = QLabel("📊 Tagesstatistik")
        header.setStyleSheet(
            f"color: {C_TEXT}; font-size: 13px; font-weight: bold; padding: 2px 0;"
        )
        header_row.addWidget(header)
        header_row.addStretch()

        self._metric_combo = QComboBox()
        for label, _key in TREND_METRICS:
            self._metric_combo.addItem(label)
        self._metric_combo.setAccessibleName("Kennzahl des Diagramms")
        self._metric_combo.setToolTip(
            "Welche Spalte der Tagesstatistik das Diagramm zeichnet."
        )
        self._metric_combo.setStyleSheet(
            f"QComboBox {{ border: 1px solid {C_TEXT_DIM}; padding: 1px 6px;"
            f" font-size: 10px; font-weight: normal; }}"
        )
        self._metric_combo.currentIndexChanged.connect(self._on_metric_changed)
        header_row.addWidget(self._metric_combo)

        layout.addLayout(header_row)

        self._summary = QLabel("—")
        self._summary.setWordWrap(True)
        self._summary.setStyleSheet(f"color: {C_TEXT_DIM}; font-size: 11px;")
        layout.addWidget(self._summary)

        self._hint = QLabel(
            "Noch keine abgeschlossenen Tage.\n"
            "Das Backend schreibt eine Zeile pro Spieltag (480 Ticks) — "
            "mit höherer Geschwindigkeit geht es schneller."
        )
        self._hint.setWordWrap(True)
        self._hint.setStyleSheet(f"color: {C_TEXT_DIM}; font-size: 11px;")
        layout.addWidget(self._hint)

        self._chart = TrendChart()
        layout.addWidget(self._chart)

        self._table = QTableWidget(0, len(_COLUMNS))
        self._table.setHorizontalHeaderLabels(list(_COLUMNS))
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self._table.setStyleSheet(_TABLE_QSS)
        self._table.setMinimumHeight(120)
        head = self._table.horizontalHeader()
        if head is not None:
            head.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._table.setVisible(False)
        layout.addWidget(self._table)

        layout.addStretch()
        self._day_count = 0
        # Kept so switching the metric can redraw without another backend
        # call — the day summaries do not change between two switches.
        self._stats: list[dict] = []

    # ── Public interface ──────────────────────────────────────────────────

    def refresh(self, stats: list[dict]) -> None:
        """Rebuild the table from a list of day-end summaries.

        Args:
            stats: The list from ``FrontendController.get_stats()``, oldest
                first. Each entry carries day_id, total_visitors, revenue,
                expenses, profit_loss, avg_animal_welfare, avg_happiness,
                reputation_end_of_day and animals_died.

        Returns:
            None.

        Tests:
            - test_empty_hides_table: Call with []; verify the table is
              hidden and the hint is visible.
            - test_rows_match_input_length: Call with 4 entries; verify the
              table has 4 rows.
            - test_summary_reports_latest_day: Call with days 1..2; verify
              the summary line mentions day 2.
            - test_chart_receives_same_rows: Call with three days; verify the
              chart reports three bars.
        """
        self._day_count = len(stats)
        self._stats = list(stats)
        self._chart.set_days(stats, self._selected_metric())
        if not stats:
            self._table.setVisible(False)
            self._hint.setVisible(True)
            self._summary.setText("—")
            return

        self._hint.setVisible(False)
        self._table.setVisible(True)
        self._table.setRowCount(len(stats))

        for row, day in enumerate(stats):
            profit = float(day.get("profit_loss", 0.0))
            self._set_cell(row, 0, str(day.get("day_id", "?")))
            self._set_cell(row, 1, str(day.get("total_visitors", 0)))
            self._set_cell(
                row,
                2,
                f"{profit:,.0f}".replace(",", "."),
                C_ACCENT if profit >= 0 else C_RED,
            )
            self._set_cell(row, 3, f'{float(day.get("avg_animal_welfare", 0)):.0f}')
            self._set_cell(row, 4, str(day.get("reputation_end_of_day", 0)))
            deaths = int(day.get("animals_died", 0))
            self._set_cell(row, 5, str(deaths), C_RED if deaths else C_TEXT_DIM)

        latest = stats[-1]
        self._summary.setText(
            f'Tag {latest.get("day_id", "?")}:  '
            f'Einnahmen {float(latest.get("revenue", 0)):,.0f} €  ·  '
            f'Ausgaben {float(latest.get("expenses", 0)):,.0f} €  ·  '
            f'Ø Zufriedenheit {float(latest.get("avg_happiness", 0)):.0f}%'.replace(
                ",", "."
            )
        )

    @property
    def day_count(self) -> int:
        """Return how many day rows are currently shown.

        Returns:
            int: 0 before the first finished day.

        Tests:
            - test_zero_before_refresh: Verify a fresh panel reports 0.
            - test_matches_last_refresh: Refresh with 3 days; verify the
              property returns 3.
        """
        return self._day_count

    # ── Internal helpers ──────────────────────────────────────────────────

    def _selected_metric(self) -> str:
        """Return the field name the metric combo currently points at.

        Returns:
            str: One of the keys in ``constants.TREND_METRICS``; the first
            one when the index is somehow out of range.

        Tests:
            - test_defaults_to_first_metric: Verify a fresh panel reports
              TREND_METRICS[0][1].
            - test_follows_the_combo: Select index 1; verify the second key
              is returned.
        """
        index = self._metric_combo.currentIndex()
        if not 0 <= index < len(TREND_METRICS):
            index = 0
        return TREND_METRICS[index][1]

    def _on_metric_changed(self) -> None:
        """Redraw the chart with the newly chosen metric.

        No backend call is involved: the day summaries are already here, only
        a different column of them is read.

        Returns:
            None.

        Tests:
            - test_switch_repaints_from_cache: Refresh with three days,
              switch the metric; verify the chart still shows three bars.
            - test_switch_without_data_is_safe: Switch before the first
              refresh; verify no exception.
        """
        self._chart.set_days(self._stats, self._selected_metric())

    def _set_cell(self, row: int, column: int, text: str, colour: str = C_TEXT) -> None:
        """Write one read-only, centred table cell.

        Args:
            row: Zero-based row index.
            column: Zero-based column index.
            text: The cell text.
            colour: Hex text colour.

        Returns:
            None.
        
        Tests:
            - test_cell_text_written: Call with "42"; verify that cell reads
              "42".
            - test_cell_colour_applied: Call with the red colour; verify the item
              foreground is red.
        """
        item = QTableWidgetItem(text)
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        item.setForeground(QColor(colour))
        self._table.setItem(row, column, item)
