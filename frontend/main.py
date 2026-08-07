"""
vivizoo — Frontend entry point.

Usage:
    python -m frontend.main              # Run with auto-created demo engine
    python -m frontend.main --no-engine  # Run without backend (empty window)

Creates the PyQt6 QApplication, applies the full QSS Dark Theme,
instantiates (or attempts to import) the backend SimulationEngine,
and launches the ZooMainWindow.

Module owner: Erik (frontend).

Tests:
    - test_qss_returns_non_empty_string: Call _get_qss(); verify
      returned string is non-empty and contains C_BG_DEEP colour.
    - test_launch_no_engine_does_not_crash: Call launch_frontend with
      QT_QPA_PLATFORM=offscreen; verify window opens without errors.
    - test_create_demo_engine_falls_back_to_none: Run in environment
      without sqlalchemy installed; verify returns None gracefully.
"""

from __future__ import annotations

import sys

from PyQt6.QtWidgets import QApplication

from frontend.core.constants import (
    C_BG_DEEP,
    C_BG_MID,
    C_BG_PANEL,
    C_BG_PANEL2,
    C_BG_CARD,
    C_BG_CARD2,
    C_ACCENT,
    C_ACCENT2,
    C_ACCENT_GLOW,
    C_RED,
    C_RED_GLOW,
    C_TEXT,
    C_TEXT_DIM,
    C_BORDER,
)
from frontend.core.frontend_controller import FrontendController
from frontend.core.main_window import ZooMainWindow

# ── Full QSS Dark Theme (~100 lines) ─────────────────────────────────────


def _get_qss() -> str:
    """Return the full QSS Dark Theme stylesheet.

    Covers: QMainWindow, QToolBar, QStatusBar, QPushButton, QComboBox,
    QSpinBox, QSlider, QProgressBar, QGroupBox, QTabWidget/QTabBar,
    QTextEdit, QScrollBar, QMenuBar/QMenu, QCheckBox, QLabel.

    Returns:
        A str of CSS rules for the PyQt6 application.

    Tests:
        - test_qss_contains_dark_bg: Verify returned string contains
          C_BG_DEEP (#0d1117) for QMainWindow background.
        - test_qss_contains_accent: Verify returned string contains
          C_ACCENT (#3fb950) for accent button styling.
    """
    return f"""
    /* ── Window & Bars (Tier 1 — gradient backgrounds) ── */
    QMainWindow {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
            stop:0 {C_BG_DEEP}, stop:0.5 {C_BG_MID}, stop:1 {C_BG_DEEP});
        color: {C_TEXT};
    }}
    QToolBar {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 {C_BG_PANEL2}, stop:0.3 {C_BG_PANEL}, stop:1 {C_BG_PANEL});
        border-bottom: 1px solid {C_BORDER};
        spacing: 4px;
        padding: 4px;
    }}
    QStatusBar {{
        background: {C_BG_PANEL};
        color: {C_TEXT_DIM};
        border-top: 1px solid {C_BORDER};
    }}

    /* ── Buttons (Tier 1 — glow + gradient) ──────────── */
    QPushButton {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 {C_BG_CARD2}, stop:1 {C_BG_CARD});
        border: 1px solid {C_BORDER};
        color: {C_TEXT};
        border-radius: 6px;
        padding: 8px 14px;
        font-weight: 500;
    }}
    QPushButton:hover {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 #3a4a5e, stop:1 #2a3a4e);
        border: 1px solid {C_ACCENT_GLOW};
        color: #ffffff;
    }}
    QPushButton:pressed {{
        background: {C_ACCENT2};
        border: 2px solid {C_ACCENT};
        color: #ffffff;
    }}
    QPushButton:disabled {{
        color: #444;
        background: #111;
        border: 1px solid #1a1a1a;
    }}
    QPushButton[accent="true"] {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 {C_ACCENT_GLOW}, stop:1 {C_ACCENT});
        color: #fff;
        border: 1px solid {C_ACCENT_GLOW};
        font-weight: bold;
    }}
    QPushButton[accent="true"]:hover {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 {C_ACCENT}, stop:1 {C_ACCENT2});
        border: 1px solid #fff;
    }}
    QPushButton[danger="true"] {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 {C_RED_GLOW}, stop:1 {C_RED});
        color: #fff;
        border: 1px solid {C_RED_GLOW};
        font-weight: bold;
    }}
    QPushButton[danger="true"]:hover {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 {C_RED}, stop:1 #b22222);
        border: 1px solid #fff;
    }}

    /* ── Inputs (Tier 4 — visible dropdowns + hover) ──── */
    QComboBox {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 {C_BG_CARD2}, stop:1 {C_BG_CARD});
        border: 2px solid {C_ACCENT};
        color: {C_TEXT};
        border-radius: 6px;
        padding: 7px 10px;
        font-weight: bold;
    }}
    QComboBox:hover {{
        border: 2px solid {C_ACCENT_GLOW};
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 #2a3a4e, stop:1 {C_BG_CARD2});
    }}
    QComboBox::drop-down {{
        subcontrol-origin: padding;
        subcontrol-position: top right;
        width: 24px;
        border-left: 1px solid {C_ACCENT};
        border-top-right-radius: 6px;
        border-bottom-right-radius: 6px;
        background: {C_ACCENT};
    }}
    QComboBox::down-arrow {{
        width: 10px;
        height: 10px;
        background: white;
    }}
    QComboBox QAbstractItemView {{
        background: {C_BG_PANEL};
        border: 2px solid {C_ACCENT};
        border-radius: 4px;
        color: {C_TEXT};
        selection-background-color: {C_ACCENT};
        padding: 4px;
        outline: none;
    }}
    QSpinBox {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 {C_BG_CARD2}, stop:1 {C_BG_CARD});
        border: 1px solid {C_BORDER};
        color: {C_TEXT};
        border-radius: 4px;
        padding: 5px 6px;
    }}
    QSpinBox:hover {{
        border: 1px solid {C_ACCENT_GLOW};
    }}
    QSlider::groove:horizontal {{
        background: {C_BORDER};
        height: 4px;
        border-radius: 2px;
    }}
    QSlider::handle:horizontal {{
        background: {C_ACCENT};
        width: 12px;
        height: 12px;
        margin: -4px 0;
        border-radius: 6px;
    }}

    /* ── Progress Bars ────────────────────────────────── */
    QProgressBar {{
        background: {C_BG_CARD};
        border: 1px solid {C_BORDER};
        border-radius: 4px;
        text-align: center;
        color: {C_TEXT};
        height: 18px;
        font-size: 10px;
    }}
    QProgressBar::chunk {{
        border-radius: 3px;
    }}

    /* ── Group Box ────────────────────────────────────── */
    QGroupBox {{
        border: 1px solid {C_BORDER};
        border-radius: 8px;
        margin-top: 14px;
        padding: 14px;
        color: {C_TEXT};
        font-weight: bold;
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 {C_BG_PANEL2}, stop:1 {C_BG_PANEL});
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        subcontrol-position: top left;
        padding: 0 6px;
    }}

    /* ── Tabs ─────────────────────────────────────────── */
    QTabWidget::pane {{
        border: 1px solid {C_BORDER};
        background: {C_BG_PANEL};
        border-radius: 4px;
    }}
    QTabBar::tab {{
        background: {C_BG_CARD};
        padding: 8px 16px;
        border: 1px solid {C_BORDER};
        border-bottom: none;
        border-top-left-radius: 4px;
        border-top-right-radius: 4px;
        color: {C_TEXT_DIM};
    }}
    QTabBar::tab:selected {{
        background: {C_BG_PANEL};
        color: {C_TEXT};
        border-bottom: 2px solid {C_ACCENT};
    }}

    /* ── Text Area ────────────────────────────────────── */
    QTextEdit {{
        background: {C_BG_CARD};
        color: {C_TEXT};
        border: 1px solid {C_BORDER};
        border-radius: 4px;
        padding: 4px;
    }}

    /* ── Scroll Bar ───────────────────────────────────── */
    QScrollBar:vertical {{
        background: {C_BG_DEEP};
        width: 8px;
        border-radius: 4px;
    }}
    QScrollBar::handle:vertical {{
        background: {C_BORDER};
        border-radius: 4px;
        min-height: 20px;
    }}
    QScrollBar::add-line:vertical,
    QScrollBar::sub-line:vertical {{
        height: 0;
    }}

    /* ── Menu ─────────────────────────────────────────── */
    QMenuBar {{
        background: {C_BG_PANEL};
        color: {C_TEXT};
        border-bottom: 1px solid {C_BORDER};
    }}
    QMenuBar::item:selected {{
        background: {C_BG_CARD};
    }}
    QMenu {{
        background: {C_BG_PANEL};
        border: 1px solid {C_BORDER};
        color: {C_TEXT};
    }}
    QMenu::item:selected {{
        background: {C_ACCENT};
    }}

    /* ── Misc ─────────────────────────────────────────── */
    QCheckBox {{
        color: {C_TEXT};
    }}
    QLabel {{
        color: {C_TEXT};
        background: transparent;
    }}
    """


# ── Engine Factory ────────────────────────────────────────────────────────


def _create_demo_engine() -> object | None:
    """Try to import and create a demo SimulationEngine with a pre-seeded zoo.

    Falls back to None silently if the backend module is not importable
    or if construction fails — the frontend then runs in empty mode.

    Returns:
        A SimulationEngine instance, or None.

    Tests:
        - test_returns_none_when_backend_unavailable: Run without
          sqlalchemy installed; verify None returned gracefully.
        - test_returns_engine_on_success: Run in environment with full
          backend dependencies; verify a non-None engine returned.
    """
    try:
        from backend.core.zoo import Zoo
        from backend.core.engine import SimulationEngine
        from backend.core.message_logger import MessageLogger

        MessageLogger.reset_to_fresh()
        logger = MessageLogger.instance()
        zoo = Zoo(name="vivizoo Demo", logger=logger)

        # Create enclosures matching the hardcoded frontend positions
        savanna = zoo.add_enclosure("Savanne 1", "savanna", capacity=5)
        ice = zoo.add_enclosure("Eiswelt 1", "ice", capacity=4)
        water = zoo.add_enclosure("Aquarium 1", "water", capacity=3)

        # Add starter animals
        zoo.add_animal("lion", "Simba", savanna)
        zoo.add_animal("giraffe", "Melman", savanna)
        zoo.add_animal("penguin", "Pingu", ice)
        zoo.add_animal("penguin", "Kowalski", water)

        return SimulationEngine(zoo, persistence=None, logger=logger)
    except Exception:  # pylint: disable=broad-exception-caught
        return None


# ── Launch ─────────────────────────────────────────────────────────────────


def launch_frontend(engine: object | None = None) -> int:
    """Create QApplication, apply QSS, show ZooMainWindow, and exec loop.

    Args:
        engine: Optional SimulationEngine instance. If None, the function
            attempts to create one via _create_demo_engine(). Pass an
            explicit engine to use a different configuration.

    Returns:
        The exit code from app.exec().

    Tests:
        - test_launch_with_none_engine_does_not_crash: Pass engine=None
          with QT_QPA_PLATFORM=offscreen; verify window opens and
          ZooMainWindow is displayed without RuntimeError.
        - test_launch_with_no_engine_flag: Simulate --no-engine flag;
          verify FrontendController receives None engine and degrades
          gracefully.
    """
    app = QApplication(sys.argv)
    app.setStyleSheet(_get_qss())

    # Auto-create engine if none provided
    if engine is None and "--no-engine" not in sys.argv:
        engine = _create_demo_engine()

    controller = FrontendController(engine)
    window = ZooMainWindow(controller)
    window.show()

    return app.exec()


# ── CLI Entry Point ───────────────────────────────────────────────────────

if __name__ == "__main__":
    sys.exit(launch_frontend())
