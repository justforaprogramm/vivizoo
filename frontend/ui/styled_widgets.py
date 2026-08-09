"""
Reusable factory functions for creating consistently styled PyQt6 widgets.

``styled_button()`` applies a complete INLINE stylesheet to each button so it
is independent of global QSS timing / polish order, and offers exactly the
three variants the UI uses:

============ ============================= ==============================
variant      meaning                       used by
============ ============================= ==============================
(default)    neutral action                the four ActionPanel buttons
``accent``   the primary action of a form  "Kaufen" in the shop
``small``    secondary control in a header "Leeren" in the chat log
============ ============================= ==============================

Adding a fourth variant means adding one ``_*_CSS`` template and one branch
in :func:`styled_button` — see ``docs/IMPLEMENTATION_PLAN.md`` §5.1 for the destructive
("danger") variant that a sell/remove action would need.

``styled_label()`` applies transparent-background QLabel styling, and
``panel_layout()`` installs the vertical layout every tab panel starts with.

Tests:
    - test_styled_button_default: Create default button; verify it has
      dark background + border.
    - test_styled_button_accent: Create accent=True button; verify
      background is green.
    - test_styled_label_dim: Create dim label; verify colour is C_TEXT_DIM.
    - test_panel_layout_is_installed: Call panel_layout() on a QWidget;
      verify the widget reports the returned layout.

Module owner: Erik (frontend).
"""

from PyQt6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QCursor

from frontend.core.constants import (
    C_BG_CARD,
    C_BG_CARD2,
    C_ACCENT,
    C_ACCENT2,
    C_ACCENT_GLOW,
    C_BORDER,
    C_TEXT,
    C_TEXT_DIM,
)

# ── CSS templates ────────────────────────────────────────────────────────

_NEUTRAL_CSS = (
    f"QPushButton {{"
    f"  background: qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 {C_BG_CARD2},stop:1 {C_BG_CARD});"
    f"  border: 1px solid {C_BORDER}; color: {C_TEXT}; border-radius: 6px;"
    f"  padding: 10px 16px; font-weight: 600; font-size: 12px; min-height: 32px;"
    f"}}"
    f"QPushButton:hover {{"
    f"  background: qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #3a4a5e,stop:1 #2a3a4e);"
    f"  border: 2px solid {C_ACCENT_GLOW}; color: #fff;"
    f"}}"
    f"QPushButton:pressed {{"
    f"  background: {C_ACCENT2}; border: 2px solid {C_ACCENT}; color: #fff;"
    f"}}"
    f"QPushButton:disabled {{"
    f"  color: #555; background: #111; border: 1px solid #1a1a1a;"
    f"}}"
)

_ACCENT_CSS = (
    f"QPushButton {{"
    f"  background: qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 {C_ACCENT_GLOW},stop:1 {C_ACCENT});"
    f"  border: 2px solid {C_ACCENT_GLOW}; color: #fff; border-radius: 6px;"
    f"  padding: 10px 16px; font-weight: bold; font-size: 12px; min-height: 32px;"
    f"}}"
    f"QPushButton:hover {{"
    f"  background: qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 {C_ACCENT},stop:1 {C_ACCENT2});"
    f"  border: 2px solid #fff;"
    f"}}"
    f"QPushButton:pressed {{"
    f"  background: {C_ACCENT2}; border: 2px solid #fff; color: #fff;"
    f"}}"
    f"QPushButton:disabled {{"
    f"  color: #556; background: #1a2e1a; border: 1px solid #223;"
    f"}}"
)

_SMALL_CSS = (
    f"QPushButton {{"
    f"  background: qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 {C_BG_CARD2},stop:1 {C_BG_CARD});"
    f"  border: 1px solid {C_BORDER}; color: {C_TEXT}; border-radius: 4px;"
    f"  padding: 4px 10px; font-weight: 500; font-size: 11px; min-height: 24px;"
    f"}}"
    f"QPushButton:hover {{"
    f"  background: qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #3a4a5e,stop:1 #2a3a4e);"
    f"  border: 1px solid {C_ACCENT_GLOW}; color: #fff;"
    f"}}"
    f"QPushButton:pressed {{"
    f"  background: {C_ACCENT2}; color: #fff;"
    f"}}"
    f"QPushButton:disabled {{"
    f"  color: #555; background: #111; border: 1px solid #1a1a1a;"
    f"}}"
)


def panel_layout(panel: QWidget, spacing: int = 8, margin: int = 4) -> QVBoxLayout:
    """Give a tab panel its standard vertical layout.

    Every panel in the right-hand column opens with the same four lines: a
    styled background attribute (without it Qt ignores the panel's QSS
    background), a vertical layout, one spacing and one margin. Four
    identical lines in four files is exactly the kind of copy pylint
    reports as ``duplicate-code`` — and the kind that drifts apart the day
    one panel gets a different margin by accident.

    Args:
        panel: The panel widget the layout is installed on.
        spacing: Pixels between two children.
        margin: Pixels of padding on all four sides.

    Returns:
        QVBoxLayout: The installed layout, ready to take widgets.

    Tests:
        - test_layout_is_installed: Call it on a bare QWidget; verify
          panel.layout() is the returned object.
        - test_spacing_and_margins_are_applied: Call with spacing=8 and
          margin=4; verify the layout reports both.
        - test_background_attribute_is_set: Call it; verify the panel has
          WA_StyledBackground so its stylesheet is painted.
    """
    panel.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
    layout = QVBoxLayout(panel)
    layout.setSpacing(spacing)
    layout.setContentsMargins(margin, margin, margin, margin)
    return layout


def styled_button(
    text: str,
    accent: bool = False,
    small: bool = False,
) -> QPushButton:
    """Create a QPushButton with self-contained inline QSS.

    Args:
        text: Button label.
        accent: Green primary-action variant.
        small: Compact variant for secondary controls in a header row.

    Returns:
        Styled QPushButton. Hover/pressed/disabled states are built-in.

    Tests:
        - test_default_button_has_dark_bg: Create default button; verify
          stylesheet contains C_BG_CARD colour.
        - test_accent_button_has_green_bg: Create accent=True; verify
          stylesheet contains C_ACCENT colour.
        - test_small_button_is_compact: Create small=True; verify the
          stylesheet asks for a 24 px minimum height instead of 32.
    """
    btn = QPushButton(text)
    btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

    if accent:
        css = _ACCENT_CSS
    elif small:
        css = _SMALL_CSS
    else:
        css = _NEUTRAL_CSS

    btn.setStyleSheet(css)
    return btn


def styled_label(
    text: str = "",
    dim: bool = False,
    bold: bool = False,
) -> QLabel:
    """Create a transparent-background QLabel with optional styling.

    Args:
        text: Initial text.
        dim: Use C_TEXT_DIM colour instead of C_TEXT.
        bold: Bold weight.

    Returns:
        Styled QLabel.

    Tests:
        - test_dim_uses_dim_color: dim=True → stylesheet contains C_TEXT_DIM.
        - test_bold_sets_weight: bold=True → the label font reports bold.
    """
    label = QLabel(text)

    font = label.font()
    font.setBold(bold)
    label.setFont(font)

    fg = C_TEXT_DIM if dim else C_TEXT
    label.setStyleSheet(
        f"background: transparent; border: none; padding: 0; color: {fg};"
    )

    return label
