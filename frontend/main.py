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

from PyQt6.QtWidgets import QApplication, QMessageBox

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
    C_TEXT,
    C_TEXT_DIM,
    C_BORDER,
)
from frontend.core.frontend_controller import FrontendController
from frontend.core.main_window import ZooMainWindow

# ── Full QSS Dark Theme (~100 lines) ─────────────────────────────────────


def _get_qss() -> str:
    """Return the full QSS Dark Theme stylesheet.

    Covers every widget class the frontend actually instantiates and nothing
    else: QMainWindow, QPushButton, QComboBox, QSpinBox, QLineEdit,
    QProgressBar, QGroupBox, QTabWidget/QTabBar, QTextEdit,
    QTableWidget/QHeaderView, QScrollBar, QMenuBar/QMenu, QDialog, QToolTip
    and QLabel.

    Deliberately absent: the top and bottom bars are custom QFrames with
    their own object-name rules, so no QToolBar/QStatusBar block is needed,
    and the button variants are applied inline by ``ui/styled_widgets.py``
    rather than through ``[accent="true"]`` property selectors — a global
    rule that nothing sets the property for is a rule that silently does
    nothing.

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

    /* ── Line Edit (animal name input) ────────────────── */
    QLineEdit {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 {C_BG_CARD2}, stop:1 {C_BG_CARD});
        border: 1px solid {C_BORDER};
        color: {C_TEXT};
        border-radius: 4px;
        padding: 6px 8px;
        selection-background-color: {C_ACCENT};
    }}
    QLineEdit:focus {{
        border: 1px solid {C_ACCENT_GLOW};
    }}

    /* ── Tables (statistics + animal roster) ──────────── */
    QTableWidget {{
        background: {C_BG_CARD};
        color: {C_TEXT};
        border: 1px solid {C_BORDER};
        border-radius: 4px;
        gridline-color: {C_BORDER};
    }}
    QTableWidget::item:selected {{
        background: {C_ACCENT2};
        color: #ffffff;
    }}
    QHeaderView::section {{
        background: {C_BG_PANEL};
        color: {C_TEXT_DIM};
        border: none;
        border-bottom: 1px solid {C_BORDER};
        padding: 4px;
        font-weight: bold;
    }}

    /* ── Dialogs (help / shortcuts) ───────────────────── */
    QDialog {{
        background: {C_BG_PANEL};
        color: {C_TEXT};
    }}

    /* ── Tooltips ─────────────────────────────────────── */
    QToolTip {{
        background: {C_BG_PANEL};
        color: {C_TEXT};
        border: 1px solid {C_BORDER};
        padding: 4px 6px;
    }}

    /* ── Labels ───────────────────────────────────────── */
    QLabel {{
        color: {C_TEXT};
        background: transparent;
    }}
    """


# ── Engine Factory ────────────────────────────────────────────────────────


def _create_persistence() -> object | None:
    """Try to build the optional day-end persistence gateway.

    The backend only records day summaries — and therefore only answers
    ``get_stats()`` — when a gateway is attached. The gateway is optional:
    when the database module or its driver is unavailable the simulation
    still runs, the statistics tab simply stays empty.

    Returns:
        object | None: A DbGateway backed by an in-memory database, or
        None when persistence cannot be set up.

    Tests:
        - test_returns_gateway_when_db_available: Run with sqlalchemy
          installed; verify a non-None gateway is returned.
        - test_returns_none_without_db: Simulate an ImportError; verify
          None is returned instead of raising.
    """
    try:
        # Local rather than at module level: the frontend must start without a
        # backend and without a database (--no-engine, and tests/test_layering.py
        # asserts that main.py is the only place that knows these packages at
        # all). A module-level import would tie every start to them — exactly
        # what the layering is meant to prevent.
        # pylint: disable=import-outside-toplevel
        from backend.persistence.db_gateway import DbGateway
        from db import ZooDatabase

        return DbGateway(ZooDatabase(":memory:"))
    except Exception:  # pylint: disable=broad-exception-caught
        return None


def _create_demo_engine() -> tuple[object | None, str]:
    """Import the backend and build a demo SimulationEngine.

    Creates three enclosures whose ids and capacities match
    ``constants.ENCLOSURE_DEFS`` plus four starter animals, and attaches
    the optional persistence gateway so the statistics tab has data.

    Returns the failure reason instead of only logging it: whoever starts
    the app by double-clicking never sees stderr, and an empty window with
    no explanation is the worst possible first impression.

    Returns:
        tuple[object | None, str]: The engine and an empty string on
        success; ``(None, reason)`` when the backend could not be loaded.

    Tests:
        - test_returns_none_when_backend_unavailable: Run without the
          backend package importable; verify (None, reason) comes back and
          the reason is not empty.
        - test_enclosure_ids_match_frontend_defs: Build the engine; verify
          get_entity_info("e_01") resolves to the savanna enclosure.
        - test_success_has_no_message: Build the engine normally; verify the
          second element is an empty string.
    """
    try:
        # Local rather than at module level — see _create_persistence: if the
        # backend is missing, the except branch catches it and the interface
        # still starts, with an explanation in the error dialog.
        # pylint: disable=import-outside-toplevel
        from backend.core.zoo import Zoo
        from backend.core.engine import SimulationEngine
        from backend.core.message_logger import MessageLogger

        MessageLogger.reset_to_fresh()
        logger = MessageLogger.instance()
        zoo = Zoo(name="vivizoo Demo", logger=logger)

        # Order matters: the backend numbers enclosures e_01, e_02, e_03 in
        # creation order, which is what ENCLOSURE_DEFS expects.
        savanna = zoo.add_enclosure("Savanne 1", "savanna", capacity=5)
        ice = zoo.add_enclosure("Eiswelt 1", "ice", capacity=4)
        water = zoo.add_enclosure("Aquarium 1", "water", capacity=3)

        zoo.add_animal("lion", "Simba", savanna)
        zoo.add_animal("giraffe", "Melman", savanna)
        zoo.add_animal("penguin", "Pingu", ice)
        zoo.add_animal("penguin", "Kowalski", water)

        engine = SimulationEngine(
            zoo,
            persistence=_create_persistence(),  # type: ignore[arg-type]
            logger=logger,
        )
        return engine, ""
    except Exception as exc:  # pylint: disable=broad-exception-caught
        # Do not fail silently: an empty window with no explanation is the
        # worst possible outcome for whoever runs the app for the first time.
        reason = (
            f"Das Backend konnte nicht geladen werden:\n\n{exc!r}\n\n"
            "Die Oberfläche startet ohne Simulation — die Karte bleibt leer.\n"
            "Prüfe die Abhängigkeiten:  pip install -r db/requirements.txt"
        )
        print(f"[vivizoo] {reason}", file=sys.stderr)
        return None, reason


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
        - test_failure_opens_a_dialog: Make the engine factory fail; verify
          a QMessageBox is shown before the window appears.
    """
    app = QApplication(sys.argv)
    app.setStyleSheet(_get_qss())

    standalone = "--no-engine" in sys.argv
    reason = ""
    if engine is None and not standalone:
        engine, reason = _create_demo_engine()

    controller = FrontendController(engine)
    window = ZooMainWindow(controller)
    window.show()

    if reason:
        # A dialog, not only stderr: started from a file manager or a
        # desktop shortcut, stderr goes nowhere and the user is left with an
        # empty map and no idea why.
        QMessageBox.warning(window, "vivizoo — Backend nicht verfügbar", reason)

    return app.exec()


# ── CLI Entry Point ───────────────────────────────────────────────────────

if __name__ == "__main__":
    sys.exit(launch_frontend())
