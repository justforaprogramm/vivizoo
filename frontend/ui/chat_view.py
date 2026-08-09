"""
ChatlogWidget — read-only message feed with color-coded entries.

Displays a scrollable, auto-updating log of backend messages.
Each message is HTML-formatted with a timestamp and type-appropriate
colour. Capped at 500 entries to prevent memory bloat.

Tests:
    - test_messages_formatted_with_correct_colors: Append a WARNING message;
      verify the HTML text contains the gold colour (#d2991d).
    - test_message_cap_at_500: Append 600 messages; verify only the last
      500 entries remain visible (oldest 100 truncated).
    - test_empty_append_does_nothing: Call append_messages([]);
      verify the text area is unchanged.
"""

from __future__ import annotations

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QLabel
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from frontend.core.constants import CHAT_COLORS, C_TEXT, C_BG_CARD

_MAX_ENTRIES = 500


class ChatlogWidget(QWidget):
    """Colour-coded chat message feed.

    Tests:
        - test_info_message_is_gray: Append INFO message; verify the HTML
          contains the gray colour (#8b949e).
        - test_message_cap_at_500: Append 600 messages; verify only the
          last 500 entries remain (oldest 100 truncated).
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        """Create the chat log widget with a header and scrollable text area.

        Args:
            parent: Optional parent widget.
        """
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Header
        header = QLabel("📋 Nachrichten")
        header.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        header.setStyleSheet(f"color: {C_TEXT}; background: transparent;")
        layout.addWidget(header)

        # Text area
        self._text_edit = QTextEdit()
        self._text_edit.setReadOnly(True)
        self._text_edit.setMinimumHeight(150)
        self._text_edit.setMaximumHeight(200)
        self._text_edit.setStyleSheet(
            f"background-color: {C_BG_CARD};"
            f" color: {C_TEXT};"
            " border: none;"
            " font-family: 'Courier New', monospace;"
            " font-size: 11px;"
        )
        self._text_edit.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff,
        )
        layout.addWidget(self._text_edit)

        self._entry_count = 0

    # ── Public interface ──────────────────────────────────────────────────

    def append_messages(self, messages: list[dict]) -> None:
        """Add HTML-formatted entries to the log.

        Args:
            messages: List of dicts with keys "time", "type", "text".
                type ∈ {"INFO", "WARNING", "ERROR", "SUCCESS", "EVENT"}.

        Tests:
            - test_info_message_is_gray: Append INFO message; verify
              the HTML contains 'color:#8b949e'.
            - test_error_message_is_red: Append ERROR message; verify
              the HTML contains 'color:#f85149'.
        """
        if not messages:
            return

        html_parts: list[str] = []
        for msg in messages:
            msg_type = msg.get("type", "INFO")
            colour = CHAT_COLORS.get(msg_type, C_TEXT)
            html_parts.append(
                f'<span style="color:{colour};">'
                f'[{msg.get("time", "--:--")}] {msg.get("text", "")}'
                f"</span>"
            )

        self._text_edit.append("<br>".join(html_parts))
        self._entry_count += len(messages)

        # Trim to max entries
        if self._entry_count > _MAX_ENTRIES:
            self._trim_to_max()

        # Auto-scroll
        self._text_edit.ensureCursorVisible()

    def clear(self) -> None:
        """Remove all messages and reset the counter.

        Tests:
            - test_clear_empties_text: Add messages, call clear();
              verify toPlainText() is empty.
        """
        self._text_edit.clear()
        self._entry_count = 0

    # ── Helpers ───────────────────────────────────────────────────────────

    def _trim_to_max(self) -> None:
        """Keep only the last _MAX_ENTRIES lines in the text area."""
        lines = self._text_edit.toPlainText().split("\n")
        if len(lines) > _MAX_ENTRIES:
            self._text_edit.clear()
            self._text_edit.setPlainText("\n".join(lines[-_MAX_ENTRIES:]))
            self._entry_count = _MAX_ENTRIES
