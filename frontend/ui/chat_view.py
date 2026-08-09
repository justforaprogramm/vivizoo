"""
ChatlogWidget — read-only message feed with colour-coded entries.

Displays a scrollable, auto-updating log of backend messages. Each entry is
HTML-formatted with a simulated timestamp and a type-appropriate colour and
is capped at 500 entries to prevent memory bloat.

Messages carry a raw ``tick_count`` rather than a wall-clock field, so the
widget derives the in-game day and clock from it: 480 ticks are one
simulated day, i.e. three simulated minutes per tick.

The backend currently calls its logger without passing a tick, so most
entries arrive stamped with 0. Because the feed is drained once per render
frame, the frame's own tick is the moment the message appeared — callers
therefore pass ``current_tick`` and the widget uses it whenever a message
brings no tick of its own.

At 5× speed the feed scrolls faster than it can be read, so the header
offers a severity filter (``constants.CHAT_FILTERS``) and a clear button.
Filtering hides entries from the view but keeps them buffered: switching
back to "Alle" restores the full history rather than a truncated one.

Tests:
    - test_messages_formatted_with_correct_colors: Append a WARNING message;
      verify the HTML contains the gold colour (#d2991d).
    - test_message_cap_at_500: Append 600 messages; verify only the last
      500 entries remain (oldest 100 truncated).
    - test_empty_append_does_nothing: Call append_messages([]); verify the
      text area is unchanged.
    - test_filter_hides_info: Append one INFO and one ERROR, switch to
      "Nur Warnungen"; verify only the error is rendered while both stay
      buffered.

Module owner: Erik (frontend).
"""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QTextCursor

from frontend.core.constants import (
    CHAT_COLORS,
    CHAT_FILTERS,
    C_TEXT,
    C_TEXT_DIM,
    C_BG_CARD,
    TICKS_PER_DAY,
)
from frontend.ui.styled_widgets import styled_button

_MAX_ENTRIES = 500
_MINUTES_PER_TICK = 24 * 60 / TICKS_PER_DAY  # 480 ticks per day => 3 minutes


class ChatlogWidget(QWidget):
    """Colour-coded chat message feed.

    Keeps the rendered HTML of the last 500 entries so trimming never
    degrades the formatting.

    Tests:
        - test_info_message_is_gray: Append an INFO message; verify the HTML
          contains the gray colour (#8b949e).
        - test_message_cap_at_500: Append 600 messages; verify only the last
          500 entries remain (oldest 100 truncated).
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        """Create the chat log widget with a header and scrollable text area.

        Args:
            parent: Optional parent widget.

        Returns:
            None (constructor).

        Tests:
            - test_starts_empty: Create the widget; verify toPlainText() is
              an empty string.
            - test_text_area_is_read_only: Verify the QTextEdit is read-only
              so the user cannot type into the feed.
        """
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        header_row = QHBoxLayout()
        header_row.setSpacing(6)

        self._header = QLabel("📋 Nachrichten")
        self._header.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        self._header.setStyleSheet(f"color: {C_TEXT}; background: transparent;")
        header_row.addWidget(self._header)
        header_row.addStretch()

        self._filter_combo = QComboBox()
        for label, _types in CHAT_FILTERS:
            self._filter_combo.addItem(label)
        self._filter_combo.setToolTip(
            "Blendet Meldungen aus, ohne sie zu verwerfen — "
            "zurück auf „Alle“ zeigt wieder den ganzen Verlauf."
        )
        self._filter_combo.setStyleSheet(
            f"QComboBox {{ border: 1px solid {C_TEXT_DIM}; padding: 1px 6px;"
            f" font-size: 10px; font-weight: normal; }}"
        )
        self._filter_combo.currentIndexChanged.connect(self._render)
        header_row.addWidget(self._filter_combo)

        self._btn_clear = styled_button("Leeren", small=True)
        self._btn_clear.setToolTip("Verwirft den angezeigten Verlauf.")
        self._btn_clear.clicked.connect(self.clear)
        header_row.addWidget(self._btn_clear)

        layout.addLayout(header_row)

        self._text_edit = QTextEdit()
        self._text_edit.setReadOnly(True)
        self._text_edit.setMinimumHeight(90)
        self._text_edit.setMaximumHeight(190)
        self._text_edit.setStyleSheet(
            f"background-color: {C_BG_CARD};"
            f" color: {C_TEXT};"
            " border: none;"
            " font-family: 'Courier New', monospace;"
            " font-size: 11px;"
        )
        self._text_edit.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded,
        )
        layout.addWidget(self._text_edit)

        # (severity, rendered HTML) — the severity is kept so the filter can
        # re-render without having to parse the HTML back apart.
        self._entries: list[tuple[str, str]] = []

    # ── Public interface ──────────────────────────────────────────────────

    def append_messages(self, messages: list[dict], current_tick: int = 0) -> None:
        """Add HTML-formatted entries to the log.

        Args:
            messages: Dicts as returned by engine.get_chat_messages(), with
                the keys "tick_count", "type" and "text". Missing keys fall
                back to type INFO and empty text.
            current_tick: The tick of the frame in which the messages were
                drained. Used as the timestamp for every entry whose own
                ``tick_count`` is 0, which is what the backend sends today.

        Returns:
            None.

        Tests:
            - test_info_message_is_gray: Append an INFO message; verify the
              HTML contains 'color:#8b949e'.
            - test_error_message_is_red: Append an ERROR message; verify the
              HTML contains 'color:#f85149'.
            - test_own_tick_wins: Append a message with tick_count=480 while
              current_tick is 10; verify the stamp reads "T2 06:00".
            - test_current_tick_used_as_fallback: Append a message without a
              tick while current_tick=480; verify the stamp reads "T2 06:00".
            - test_filtered_out_message_is_still_buffered: With the warning
              filter active, append an INFO message; verify entry_count grew
              although nothing was rendered.
        """
        if not messages:
            return

        visible: list[str] = []
        for msg in messages:
            severity = str(msg.get("type", "INFO"))
            colour = CHAT_COLORS.get(severity, C_TEXT)
            stamp = self.format_timestamp(msg.get("tick_count") or current_tick)
            html = (
                f'<span style="color:{colour};">'
                f'[{stamp}] {msg.get("text", "")}'
                f"</span>"
            )
            self._entries.append((severity, html))
            if self._accepts(severity):
                visible.append(html)

        trimmed = len(self._entries) > _MAX_ENTRIES
        if trimmed:
            self._entries = self._entries[-_MAX_ENTRIES:]

        if trimmed:
            # Dropping the oldest entries invalidates the rendered document,
            # so it has to be rebuilt rather than appended to.
            self._render()
        elif visible:
            self._text_edit.append("<br>".join(visible))
            self._text_edit.ensureCursorVisible()

        self._update_header()

    def _accepts(self, severity: str) -> bool:
        """Return whether the active filter lets this severity through.

        Args:
            severity: The message type, e.g. "WARNING".

        Returns:
            bool: True when the entry should be rendered.

        Tests:
            - test_all_filter_accepts_everything: With filter 0 active;
              verify an INFO entry is accepted.
            - test_warning_filter_rejects_info: With the warning filter
              active; verify INFO is rejected and ERROR accepted.
        """
        index = max(0, min(self._filter_combo.currentIndex(), len(CHAT_FILTERS) - 1))
        accepted = CHAT_FILTERS[index][1]
        return accepted is None or severity in accepted

    def _render(self) -> None:
        """Rebuild the whole document from the buffered entries.

        Used whenever the visible set changes as a whole: after a filter
        switch and after the 500-entry cap dropped the oldest messages.

        Returns:
            None.

        Tests:
            - test_only_accepted_entries_rendered: Buffer one INFO and one
              ERROR, activate the warning filter, call it; verify the plain
              text holds only the error.
            - test_cursor_ends_at_bottom: Call it with 600 buffered entries;
              verify the view is scrolled to the newest entry, not the top.
        """
        self._text_edit.setHtml(
            "<br>".join(html for severity, html in self._entries
                        if self._accepts(severity))
        )
        # setHtml resets the cursor to position 0; without moving it back the
        # feed would stay pinned to the top from the 500th message on.
        cursor = self._text_edit.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self._text_edit.setTextCursor(cursor)
        self._text_edit.ensureCursorVisible()
        self._update_header()

    def _update_header(self) -> None:
        """Show how many entries are buffered next to the header caption.

        Returns:
            None.

        Tests:
            - test_header_shows_count: Append three messages; verify the
              header text ends with "3".
            - test_header_without_entries: Call on an empty log; verify the
              plain caption without a number.
        """
        count = len(self._entries)
        self._header.setText(
            f"📋 Nachrichten · {count}" if count else "📋 Nachrichten"
        )

    @staticmethod
    def format_timestamp(tick_count: object) -> str:
        """Convert a raw backend tick number into a day and clock stamp.

        Args:
            tick_count: The message's ``tick_count``. Non-numeric values are
                treated as tick 0.

        Returns:
            str: A stamp such as ``"T2 07:30"`` — simulated day number and
            in-day clock (480 ticks = 24 h).

        Tests:
            - test_tick_zero_is_day_one_morning: format_timestamp(0)
              returns "T1 06:00" — the backend's day starts in MORNING.
            - test_tick_480_starts_day_two: format_timestamp(480) returns
              "T2 06:00".
            - test_non_numeric_is_tolerated: format_timestamp(None) returns
              "T1 06:00" instead of raising.
        """
        try:
            ticks = int(tick_count)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            ticks = 0
        ticks = max(0, ticks)

        day = ticks // TICKS_PER_DAY + 1
        # Same quarter-day anchor as the toolbar clock: the backend's day
        # starts in the MORNING phase, which reads as 06:00.
        minutes = (int((ticks % TICKS_PER_DAY) * _MINUTES_PER_TICK) + 360) % 1440
        return f"T{day} {minutes // 60:02d}:{minutes % 60:02d}"

    def clear(self) -> None:
        """Remove all messages and reset the entry buffer.

        Bound to the "Leeren" button in the header.

        Returns:
            None.

        Tests:
            - test_clear_empties_text: Add messages, call clear(); verify
              toPlainText() is empty.
            - test_clear_resets_counter: Call clear(); verify entry_count is
              0 and the header shows no number.
        """
        self._text_edit.clear()
        self._entries.clear()
        self._update_header()

    @property
    def entry_count(self) -> int:
        """Return how many entries are currently buffered.

        Buffered, not rendered: an active filter hides entries from the view
        but keeps them counted here.

        Returns:
            int: Between 0 and 500.

        Tests:
            - test_count_grows_with_appends: Append 3 messages; verify the
              count is 3.
            - test_count_caps_at_max: Append 600 messages; verify the count
              is exactly 500.
        """
        return len(self._entries)
