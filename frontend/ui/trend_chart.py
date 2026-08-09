"""
TrendChart — a hand-painted bar chart of the finished simulated days.

The statistics table lists the day rows the backend persists, but a table
answers "what happened on day 7?", never "is the zoo getting better?". This
widget answers the second question by painting one value per finished day as
a bar above or below a zero line, so a run of losses is visible at a glance.

Which value is drawn is chosen by the caller from ``constants.TREND_METRICS``
— profit, visitors, average welfare or reputation. All four live in the same
``get_stats()`` row, so switching costs one field name and no backend call.

It is drawn with :class:`QPainter` in :meth:`paintEvent` rather than composed
from child widgets, for two reasons: a chart of *n* days would otherwise need
*n* widgets recreated on every day change, and a custom ``paintEvent`` is the
idiomatic Qt way to add a new kind of visual — the widget stays a normal
``QWidget`` that any layout can hold.

Data source: ``engine.get_stats()`` via ``FrontendController.get_stats()``.
The backend only writes those rows when a persistence gateway is attached, so
the chart shows an explanatory placeholder until the first day closes.

Tests:
    - test_empty_data_paints_placeholder: Call set_days([]) and render into
      a QPixmap; verify no exception and the widget stays empty.
    - test_bars_scale_to_maximum: Set two days with profits 100 and 200;
      verify the taller bar is the second one.
    - test_metric_switch_reads_another_field: Switch to "total_visitors";
      verify the stored values come from that field.

Module owner: Erik (frontend).
"""

from __future__ import annotations

from PyQt6.QtWidgets import QSizePolicy, QWidget
from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QColor, QPainter, QPaintEvent, QPen

from frontend.core.constants import (
    C_ACCENT,
    C_BG_CARD,
    C_BORDER,
    C_RED,
    C_TEXT_DIM,
    TREND_METRICS,
)

_MAX_BARS = 14  # older days scroll out of view; the table still lists them
_PADDING = 6
_MAX_BAR_WIDTH = 26  # px — one lonely day must not become a full-width block


class TrendChart(QWidget):
    """Zero-line bar chart of one metric across the last finished days.

    Tests:
        - test_starts_empty: Create the chart; verify day_count is 0.
        - test_keeps_only_the_last_days: Feed 30 days; verify only the last
          _MAX_BARS are kept for painting.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        """Create the chart at a fixed, layout-friendly height.

        Args:
            parent: Optional parent widget.

        Returns:
            None (constructor).

        Tests:
            - test_has_minimum_height: Verify the widget requests at least
              70 px so the bars stay readable.
            - test_expands_horizontally: Verify the horizontal size policy is
              Expanding.
        """
        super().__init__(parent)
        self.setMinimumHeight(72)
        self.setMaximumHeight(96)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setAccessibleName("Verlauf der Tageskennzahl")
        self._values: list[float] = []
        self._metric: str = TREND_METRICS[0][1]
        self._label: str = TREND_METRICS[0][0]
        self._update_tooltip()

    # ── Public interface ──────────────────────────────────────────────────

    def set_days(self, stats: list[dict], metric: str | None = None) -> None:
        """Take the day summaries and repaint.

        Args:
            stats: The list from ``FrontendController.get_stats()``, oldest
                first. Only the active metric's field is read; missing or
                non-numeric values count as zero.
            metric: Field name from ``constants.TREND_METRICS``. Omitting it
                keeps the metric currently shown, so the render loop can
                refresh without resetting the user's choice.

        Returns:
            None.

        Tests:
            - test_stores_values_in_order: Pass days with 10, 20, 30; verify
              the internal list is [10, 20, 30].
            - test_missing_field_is_zero: Pass a day dict without the active
              field; verify 0.0 is stored instead of raising.
            - test_metric_is_remembered: Call once with "total_visitors",
              then without a metric; verify visitors are still read.
            - test_unknown_metric_is_ignored: Pass "does_not_exist"; verify
              the previous metric stays active.
        """
        if metric is not None:
            for label, key in TREND_METRICS:
                if key == metric:
                    self._metric, self._label = key, label
                    self._update_tooltip()
                    break

        values: list[float] = []
        for day in stats:
            try:
                values.append(float(day.get(self._metric, 0.0)))
            except (TypeError, ValueError):
                values.append(0.0)
        self._values = values[-_MAX_BARS:]
        self.update()

    @property
    def day_count(self) -> int:
        """Return how many days the chart is currently painting.

        Returns:
            int: 0 before the first finished day, at most _MAX_BARS.

        Tests:
            - test_zero_initially: Verify a fresh chart reports 0.
            - test_capped_at_max: Feed 30 days; verify the count is
              _MAX_BARS.
        """
        return len(self._values)

    @property
    def metric_key(self) -> str:
        """Return the field name the chart currently draws.

        Deliberately **not** called ``metric``: ``QWidget`` inherits
        ``QPaintDevice.metric()``, which Qt calls internally to ask for the
        widget's DPI and size. A property of that name shadows the virtual,
        Qt receives a string where it expects a callable and aborts the
        process from inside ``paintEvent`` — with a bare
        ``TypeError: 'str' object is not callable`` and no traceback.

        Returns:
            str: One of the keys in ``constants.TREND_METRICS``.

        Tests:
            - test_defaults_to_the_first_metric: Verify a fresh chart draws
              TREND_METRICS[0].
            - test_tracks_set_days: Switch to "reputation_end_of_day";
              verify the property reports it.
            - test_does_not_shadow_qpaintdevice: Verify the widget still
              renders into a QPixmap without aborting.
        """
        return self._metric

    def _update_tooltip(self) -> None:
        """Restate in words what the bars and the zero line mean.

        Returns:
            None.

        Tests:
            - test_tooltip_names_the_metric: Switch to "Besucher"; verify the
              tooltip mentions it.
            - test_tooltip_explains_the_colours: Verify the text says what
              red below the line means.
        """
        self.setToolTip(
            f"{self._label} je abgeschlossenem Tag — grün über, "
            "rot unter der Nulllinie."
        )
        self.setAccessibleDescription(self.toolTip())

    # ── Painting ──────────────────────────────────────────────────────────

    def paintEvent(self, event: QPaintEvent | None) -> None:  # noqa: N802
        """Paint the card background, the zero line and one bar per day.

        Args:
            event: The Qt paint event; unused, the whole widget is redrawn.

        Returns:
            None.

        Tests:
            - test_paints_without_data: Render an empty chart into a QPixmap;
              verify no exception is raised.
            - test_negative_profit_paints_below_zero: Render one day with
              profit -100; verify the painted bar starts at the zero line and
              extends downwards.
        """
        del event  # the widget always repaints in full

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor(C_BG_CARD))
        painter.setPen(QPen(QColor(C_BORDER), 1))
        painter.drawRect(self.rect().adjusted(0, 0, -1, -1))

        if not self._values:
            painter.setPen(QPen(QColor(C_TEXT_DIM)))
            painter.drawText(
                self.rect(),
                int(Qt.AlignmentFlag.AlignCenter),
                "Noch keine abgeschlossenen Tage",
            )
            painter.end()
            return

        self._paint_bars(painter)
        painter.end()

    def _scale(self, height: float) -> tuple[float, float]:
        """Work out the value range and where the zero line belongs.

        The zero line sits where the positive range ends, so bars of both
        signs share one scale instead of each using the full height. For a
        metric that is never negative (visitors, welfare) it ends up at the
        bottom edge, which is exactly where a baseline belongs.

        Args:
            height: The drawable height in pixels, padding already removed.

        Returns:
            tuple[float, float]: The total value span (never zero, so it can
            be divided by) and the zero line's y coordinate.

        Tests:
            - test_mixed_signs_centre_the_line: Pass +100 and -100; verify
              the zero line sits in the vertical middle.
            - test_only_positive_values_put_the_line_at_the_bottom: Pass 10
              and 20; verify the zero line is at the lower edge.
            - test_all_zero_values_do_not_divide_by_zero: Feed three zeros;
              verify the span is 1.0 instead of 0.
        """
        peak_up = max([v for v in self._values if v > 0] or [0.0])
        peak_down = abs(min([v for v in self._values if v < 0] or [0.0]))
        span = peak_up + peak_down
        if span <= 0:
            span = 1.0
        return span, _PADDING + height * (peak_up / span)

    def _paint_bars(self, painter: QPainter) -> None:
        """Draw the zero line and the profit bars into an open painter.

        Args:
            painter: The active painter of :meth:`paintEvent`.

        Returns:
            None.

        Tests:
            - test_zero_line_is_centred_for_mixed_signs: Paint +100 and -100;
              verify the zero line sits in the vertical middle.
            - test_all_positive_puts_zero_line_at_bottom: Paint 10 and 20;
              verify the zero line is at the bottom edge.
            - test_single_day_bar_is_not_full_width: Paint one day; verify
              the bar is at most _MAX_BAR_WIDTH wide.
        """
        width = self.width() - 2 * _PADDING
        height = self.height() - 2 * _PADDING
        count = len(self._values)
        slot = width / count
        # Bars grow with the data, not with the empty space around it: with a
        # single finished day a 70 %-of-the-widget block reads as a filled
        # progress bar, not as one value in a series.
        bar_width = max(2.0, min(slot * 0.7, _MAX_BAR_WIDTH))

        span, zero_y = self._scale(height)

        painter.setPen(QPen(QColor(C_BORDER), 1, Qt.PenStyle.DashLine))
        painter.drawLine(_PADDING, int(zero_y), _PADDING + int(width), int(zero_y))

        painter.setPen(QPen(Qt.PenStyle.NoPen))
        for index, value in enumerate(self._values):
            bar_height = abs(value) / span * height
            left = _PADDING + index * slot + (slot - bar_width) / 2
            top = zero_y - bar_height if value >= 0 else zero_y
            painter.setBrush(QColor(C_ACCENT if value >= 0 else C_RED))
            painter.drawRoundedRect(
                QRectF(left, top, bar_width, max(1.0, bar_height)), 2.0, 2.0
            )
