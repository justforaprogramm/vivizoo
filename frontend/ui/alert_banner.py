"""
AlertBanner — lifts urgent backend messages out of the scrolling chat feed.

The chat log receives every message the backend produces, INFO included, and
at five ticks per frame it scrolls faster than anyone can read. A warning
("Simba is starving") therefore disappears within a second. This banner
solves that with the data the backend already sends: whenever
``get_chat_messages()`` contains an entry whose type is in
``constants.ALERT_TYPES``, the newest one is shown here in colour and stays
put for ``constants.ALERT_FRAMES`` render frames before fading out.

No backend change is involved — the banner is a second, slower view onto the
same message stream, and it deliberately shows only what the backend really
sends (``WARNING`` and ``ERROR``; see
``backend/core/message_logger.LogEntry``).

The countdown is driven by the render loop rather than a QTimer so it
follows the simulation: at 5× speed the world moves five times faster and
the banner would otherwise outlive the situation it describes.

Tests:
    - test_banner_hidden_by_default: Create an AlertBanner; verify
      isVisibleTo(parent) is False.
    - test_warning_is_shown: Call push() with one WARNING entry; verify the
      label carries its text and the banner is visible.
    - test_info_is_ignored: Call push() with only INFO entries; verify the
      banner stays hidden.

Module owner: Erik (frontend).
"""

from __future__ import annotations

from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QWidget

from frontend.core.constants import (
    ALERT_FRAMES,
    ALERT_TYPES,
    C_GOLD,
    C_GOLD_GLOW,
    C_RED,
    C_RED_GLOW,
)

_ICONS = {"WARNING": "⚠️", "ERROR": "⛔"}
_COLOURS = {"WARNING": (C_GOLD, C_GOLD_GLOW), "ERROR": (C_RED, C_RED_GLOW)}


class AlertBanner(QFrame):
    """Coloured strip showing the most recent warning or error.

    Hidden whenever there is nothing urgent to report, so it costs no
    vertical space in the normal case.

    Tests:
        - test_error_outranks_warning: Push a WARNING and an ERROR in one
          batch; verify the ERROR is the one displayed.
        - test_expires_after_configured_frames: Push an alert, call tick()
          ALERT_FRAMES times; verify the banner hid itself.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        """Create the hidden banner with its icon and message label.

        Args:
            parent: Optional parent widget.

        Returns:
            None (constructor).

        Tests:
            - test_starts_hidden: Verify the widget is not visible.
            - test_label_starts_empty: Verify the message label has no text
              yet.
        """
        super().__init__(parent)
        self.setVisible(False)
        self.setFixedHeight(28)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 2, 8, 2)
        layout.setSpacing(6)

        self._icon = QLabel("")
        self._icon.setStyleSheet("background: transparent; border: none;")
        layout.addWidget(self._icon)

        self._label = QLabel("")
        self._label.setStyleSheet("background: transparent; border: none;")
        layout.addWidget(self._label, stretch=1)

        self._frames_left = 0

    # ── Public interface ──────────────────────────────────────────────────

    def push(self, messages: list[dict]) -> bool:
        """Show the most urgent entry of a chat batch, if there is one.

        Errors outrank warnings; within one severity the last entry of the
        batch wins, because that is the most recent event.

        Args:
            messages: The batch from ``FrontendController.get_chat_messages()``
                — dicts with "type" and "text". Entries of any other type are
                ignored.

        Returns:
            bool: True when an alert was displayed, False when the batch held
            nothing urgent (the banner is then left untouched).

        Tests:
            - test_returns_false_for_info_only: Push two INFO entries; verify
              False and a still-hidden banner.
            - test_last_warning_wins: Push two WARNINGs; verify the label
              shows the second one.
            - test_error_beats_earlier_error: Push ERROR then WARNING; verify
              the ERROR stays on screen.
        """
        alerts = [m for m in messages if m.get("type") in ALERT_TYPES]
        if not alerts:
            return False

        errors = [m for m in alerts if m.get("type") == "ERROR"]
        chosen = (errors or alerts)[-1]
        self.show_alert(str(chosen.get("type", "WARNING")), str(chosen.get("text", "")))
        return True

    def show_alert(self, severity: str, text: str) -> None:
        """Display one message in the colour matching its severity.

        Args:
            severity: "WARNING" or "ERROR"; anything else is styled as a
                warning so an unknown backend severity is still readable.
            text: The message body.

        Returns:
            None.

        Tests:
            - test_error_is_red: Call with "ERROR"; verify the frame
              stylesheet contains the red colour.
            - test_unknown_severity_falls_back: Call with "PANIC"; verify the
              banner is visible and styled like a warning.
        """
        border, glow = _COLOURS.get(severity, _COLOURS["WARNING"])
        self.setStyleSheet(
            f"QFrame {{ background: #1a1508; border: 1px solid {border};"
            f" border-radius: 6px; }}"
        )
        self._icon.setText(_ICONS.get(severity, "⚠️"))
        self._label.setStyleSheet(
            f"color: {glow}; background: transparent; border: none;"
            " font-size: 11px; font-weight: bold;"
        )
        self._label.setText(text)
        self._frames_left = ALERT_FRAMES
        self.setVisible(True)

    def tick(self) -> None:
        """Count one render frame down and hide the banner when it expires.

        Returns:
            None.

        Tests:
            - test_tick_without_alert_is_noop: Call on a hidden banner; verify
              no exception and it stays hidden.
            - test_hides_on_last_frame: Push an alert, tick ALERT_FRAMES
              times; verify the banner is hidden exactly once the counter
              reaches zero.
        """
        if self._frames_left <= 0:
            return
        self._frames_left -= 1
        if self._frames_left == 0:
            self.setVisible(False)

    @property
    def frames_left(self) -> int:
        """Return how many render frames the current alert still has.

        Returns:
            int: 0 when no alert is showing.

        Tests:
            - test_zero_when_idle: Verify a fresh banner reports 0.
            - test_reset_on_new_alert: Let a banner count down, push a new
              alert; verify the counter is back at ALERT_FRAMES.
        """
        return self._frames_left
