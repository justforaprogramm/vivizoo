"""
StatusChip — glass-morphism pill badge used in the top and bottom bars.

A small rounded frame holding a static icon label and a value label whose
text and accent colour are updated every frame from the backend snapshot.
Lives in its own module so ``main_window`` holds exactly one class.

Tests:
    - test_set_value_updates_label: Call set_value("42"); verify the value
      label reads "42".
    - test_set_accent_changes_colour: Call set_accent("#ff0000"); verify the
      value label stylesheet contains #ff0000.

Module owner: Erik (frontend).
"""

from __future__ import annotations

from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QWidget

from frontend.core.constants import C_BG_CARD, C_BG_CARD2, C_BORDER, C_TEXT, C_TEXT_DIM

_CHIP_QSS = (
    "QFrame {"
    f"  background: qlineargradient(x1:0,y1:0,x2:0,y2:1,"
    f"    stop:0 {C_BG_CARD2},stop:1 {C_BG_CARD});"
    f"  border: 1px solid {C_BORDER};"
    "  border-radius: 6px;"
    "  padding: 2px 8px;"
    "}"
)

_LABEL_QSS = "background: transparent; border: none; font-size: 11px;"


class StatusChip(QFrame):
    """Pill badge with an icon label and a dynamic value label.

    Tests:
        - test_icon_text_is_kept: Construct with "💰"; verify the icon label
          shows that text.
        - test_value_defaults_to_empty: Construct without a value; verify
          the value label is empty.
    """

    def __init__(
        self,
        icon_text: str = "",
        value_text: str = "",
        accent_color: str = C_TEXT,
        parent: QWidget | None = None,
    ) -> None:
        """Create a chip with an icon and an initial value.

        Args:
            icon_text: Static leading text, usually an emoji plus caption.
            value_text: Initial value shown after the icon.
            accent_color: Hex colour of the value text.
            parent: Optional parent widget.

        Returns:
            None (constructor).

        Tests:
            - test_layout_has_two_labels: Verify the chip holds exactly the
              icon and the value label.
            - test_accent_applied_at_construction: Construct with a red
              accent; verify the value stylesheet contains that colour.
        """
        super().__init__(parent)
        self.setStyleSheet(_CHIP_QSS)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        self.icon_label = QLabel(icon_text)
        self.icon_label.setStyleSheet(
            f"color: {C_TEXT_DIM}; {_LABEL_QSS} font-weight: 500;"
        )
        layout.addWidget(self.icon_label)

        self.value_label = QLabel(value_text)
        self.value_label.setStyleSheet(
            f"color: {accent_color}; {_LABEL_QSS} font-weight: 700;"
        )
        layout.addWidget(self.value_label)

        self._accent = accent_color

    def set_value(self, text: str) -> None:
        """Update the displayed value text.

        Args:
            text: The new value string.

        Returns:
            None.

        Tests:
            - test_set_value_updates_label: Call with "42"; verify the label
              reads "42".
            - test_set_value_accepts_empty: Call with ""; verify the label
              is cleared without error.
            - test_accessible_text_follows_the_value: Set "5.000 €"; verify
              the accessible description mentions it.
        """
        self.value_label.setText(text)
        # The caption of a chip is an emoji. A screen reader announces the
        # accessible name (set by the window) plus this description, so the
        # value has to travel with it.
        self.setAccessibleDescription(text)

    def set_accent(self, color: str) -> None:
        """Change the accent colour of the value text.

        Args:
            color: Hex colour string, e.g. "#f85149".

        Returns:
            None.

        Tests:
            - test_set_accent_changes_colour: Call with "#ff0000"; verify
              the stylesheet contains that colour.
            - test_set_accent_is_idempotent: Call twice with the same
              colour; verify the stylesheet stays valid.
        """
        if color == self._accent:
            return
        self._accent = color
        self.value_label.setStyleSheet(
            f"color: {color}; {_LABEL_QSS} font-weight: 700;"
        )

    def set_icon(self, text: str) -> None:
        """Change the static icon text.

        Args:
            text: The new icon or caption string.

        Returns:
            None.

        Tests:
            - test_set_icon_updates_label: Call with "🔒"; verify the icon
              label reads "🔒".
            - test_set_icon_keeps_value: Change the icon; verify the value
              label is untouched.
        """
        self.icon_label.setText(text)
