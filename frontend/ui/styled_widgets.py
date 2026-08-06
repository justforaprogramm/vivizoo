"""
Reusable factory functions for creating consistently styled PyQt6 widgets.

styled_button() applies a complete INLINE stylesheet to each button
so it is independent of global QSS timing / polish order.

styled_label() applies transparent-background QLabel styling.

Tests:
    - test_styled_button_default: Create default button; verify it has
      dark background + border.
    - test_styled_button_accent: Create accent=True button; verify
      background is green.
    - test_styled_label_dim: Create dim label; verify colour is C_TEXT_DIM.
"""

from PyQt6.QtWidgets import QPushButton, QLabel
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QCursor

try:
    from frontend.core.constants import (
        C_BG_CARD, C_BG_CARD2,
        C_ACCENT, C_ACCENT2, C_ACCENT_GLOW,
        C_RED, C_RED_GLOW,
        C_BORDER, C_TEXT, C_TEXT_DIM,
    )
except ImportError:
    C_BG_CARD = C_BG_CARD2 = "#1c2333"
    C_ACCENT = C_ACCENT2 = C_ACCENT_GLOW = "#3fb950"
    C_RED = C_RED_GLOW = "#f85149"
    C_BORDER = "#30363d"
    C_TEXT = C_TEXT_DIM = "#888"

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

_DANGER_CSS = (
    f"QPushButton {{"
    f"  background: qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 {C_RED_GLOW},stop:1 {C_RED});"
    f"  border: 2px solid {C_RED_GLOW}; color: #fff; border-radius: 6px;"
    f"  padding: 10px 16px; font-weight: bold; font-size: 12px; min-height: 32px;"
    f"}}"
    f"QPushButton:hover {{"
    f"  background: qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 {C_RED},stop:1 #b22222);"
    f"  border: 2px solid #fff;"
    f"}}"
    f"QPushButton:pressed {{"
    f"  background: #b22222; border: 2px solid #fff; color: #fff;"
    f"}}"
    f"QPushButton:disabled {{"
    f"  color: #556; background: #2e1a1a; border: 1px solid #322;"
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


def styled_button(
    text: str,
    accent: bool = False,
    danger: bool = False,
    small: bool = False,
) -> QPushButton:
    """Create a QPushButton with self-contained inline QSS.

    Args:
        text: Button label.
        accent: Green variant.
        danger: Red variant.
        small: Compact variant.

    Returns:
        Styled QPushButton. Hover/pressed/disabled states are built-in.

    Tests:
        - test_default_button_has_dark_bg: Create default button; verify
          stylesheet contains C_BG_CARD colour.
        - test_accent_button_has_green_bg: Create accent=True; verify
          stylesheet contains C_ACCENT colour.
        - test_danger_button_has_red_bg: Create danger=True; verify
          stylesheet contains C_RED colour.
    """
    btn = QPushButton(text)
    btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

    if accent:
        css = _ACCENT_CSS
    elif danger:
        css = _DANGER_CSS
    elif small:
        css = _SMALL_CSS
    else:
        css = _NEUTRAL_CSS

    btn.setStyleSheet(css)
    return btn


def styled_label(
    text: str = "",
    dim: bool = False,
    large: bool = False,
    bold: bool = False,
    color: str | None = None,
    size: int | None = None,
) -> QLabel:
    """Create a transparent-background QLabel with optional styling.

    Args:
        text: Initial text.
        dim: Use C_TEXT_DIM colour.
        large: 18 pt font.
        bold: Bold weight.
        color: Override hex colour.
        size: Override point size.

    Returns:
        Styled QLabel.

    Tests:
        - test_dim_uses_dim_color: dim=True → stylesheet contains C_TEXT_DIM.
        - test_large_has_18pt: large=True → font size is 18.
    """
    label = QLabel(text)
    label.setStyleSheet("background: transparent; border: none; padding: 0;")

    font = label.font()
    if bold:
        font.setBold(True)
    pt = size if size is not None else (18 if large else None)
    if pt is not None:
        font.setPointSize(pt)
    label.setFont(font)

    fg = color or (C_TEXT_DIM if dim else C_TEXT)
    label.setStyleSheet(f"{label.styleSheet()} color: {fg};")

    return label
