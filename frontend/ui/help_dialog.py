"""
HelpDialog — keyboard shortcuts and map legend in one modal window.

Every control the window offers is reachable with the mouse, but the
simulation runs on: pausing, changing speed and feeding are things a keeper
does *while watching*, and reaching for a button costs the moment. The
shortcut list therefore lives next to the shortcuts themselves — the dialog
is built from :data:`SHORTCUTS`, the same tuple ``ZooMainWindow`` registers
its ``QShortcut`` objects from, so a shortcut that exists is documented and a
documented shortcut exists.

Opened with F1 or via the "Hilfe" menu.

Tests:
    - test_dialog_lists_every_shortcut: Create the dialog; verify the text
      mentions every key in SHORTCUTS.
    - test_dialog_is_modal: Create it; verify isModal() is True so the
      simulation is not clicked by accident behind it.

Module owner: Erik (frontend).
"""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QDialog,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from PyQt6.QtCore import Qt

from frontend.core.constants import C_ACCENT_GLOW, C_TEXT, C_TEXT_DIM

# (key sequence, action name, human description). ZooMainWindow binds the
# first field, this dialog prints all three — one source, no drift.
SHORTCUTS: tuple[tuple[str, str, str], ...] = (
    ("Space", "pause", "Simulation anhalten / fortsetzen"),
    ("S", "speed", "Nächste Geschwindigkeitsstufe (1× → 2× → 5× → 0,5×)"),
    ("F", "feed_all", "Alle Tiere füttern"),
    ("E", "feed_one", "Ausgewähltes Tier füttern"),
    ("H", "heal", "Ausgewähltes Tier heilen"),
    ("R", "clean", "Ausgewähltes Gehege reinigen"),
    ("Esc", "deselect", "Auswahl aufheben"),
    ("1 – 4", "tabs", "Tab wechseln: Aktionen, Tiere, Shop, Statistik"),
    ("F1", "help", "Diese Hilfe anzeigen"),
)

_LEGEND: tuple[tuple[str, str], ...] = (
    ("🦁 🦒 🐧", "Tiere — Klick wählt aus, Hover zeigt eine Vorschau"),
    ("✝ rot", "verstorbenes Tier; Füttern und Heilen sind gesperrt"),
    ("Gestrichelter Rahmen", "Gehege — gold ab 60 % Sauberkeit, rot ab 30 %"),
    ("Kleine Punkte", "Besucher; jeder zahlt beim Eintritt den Ticketpreis"),
    ("Mausrad", "Zoom 0,3× – 3,0× · Ziehen verschiebt die Karte"),
)


class HelpDialog(QDialog):
    """Modal cheat sheet listing shortcuts and map symbols.

    Tests:
        - test_has_close_button: Create the dialog; verify a button labelled
          "Schließen" exists.
        - test_legend_mentions_dead_marker: Verify the legend text explains
          the red cross marker.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        """Build the shortcut table, the legend and the close button.

        Args:
            parent: The window the dialog is modal to.

        Returns:
            None (constructor).

        Tests:
            - test_title_is_set: Verify the window title mentions "Hilfe".
            - test_every_shortcut_row_rendered: Verify the rendered text
              contains as many rows as SHORTCUTS has entries.
        """
        super().__init__(parent)
        self.setWindowTitle("Hilfe — Tastenkürzel & Legende")
        self.setModal(True)
        self.setMinimumWidth(460)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(16, 16, 16, 16)

        layout.addWidget(self._section("⌨️  Tastenkürzel"))
        layout.addWidget(self._body(self.shortcut_lines()))

        layout.addWidget(self._section("🗺️  Legende"))
        layout.addWidget(self._body(self.legend_lines()))

        close = QPushButton("Schließen")
        close.clicked.connect(self.accept)
        layout.addWidget(close)

    # ── Content ───────────────────────────────────────────────────────────

    @staticmethod
    def shortcut_lines() -> list[str]:
        """Return one aligned "key — description" line per shortcut.

        Returns:
            list[str]: One entry per SHORTCUTS row, key column padded so the
            descriptions line up in the monospace body.

        Tests:
            - test_one_line_per_shortcut: Verify the list length equals
              len(SHORTCUTS).
            - test_line_contains_key_and_text: Verify the Space line mentions
              both "Space" and "anhalten".
        """
        width = max(len(key) for key, _, _ in SHORTCUTS)
        return [f"{key:<{width}}   {text}" for key, _, text in SHORTCUTS]

    @staticmethod
    def legend_lines() -> list[str]:
        """Return one "symbol — meaning" line per legend entry.

        Returns:
            list[str]: One entry per _LEGEND row.

        Tests:
            - test_one_line_per_symbol: Verify the list length equals
              len(_LEGEND).
            - test_mentions_zoom_range: Verify one line names the 3,0× zoom
              limit.
        """
        return [f"{symbol}   {meaning}" for symbol, meaning in _LEGEND]

    # ── Construction helpers ──────────────────────────────────────────────

    @staticmethod
    def _section(title: str) -> QLabel:
        """Create a section heading label.

        Args:
            title: The heading text.

        Returns:
            QLabel: The styled heading.

        Tests:
            - test_heading_is_bold: Create one; verify the stylesheet asks
              for a bold font.
            - test_heading_uses_accent: Verify the stylesheet contains the
              accent colour.
        """
        label = QLabel(title)
        label.setStyleSheet(
            f"color: {C_ACCENT_GLOW}; font-size: 12px; font-weight: bold;"
        )
        return label

    @staticmethod
    def _body(lines: list[str]) -> QLabel:
        """Create a monospace block label from a list of lines.

        Args:
            lines: The already-formatted text lines.

        Returns:
            QLabel: A selectable, word-wrapping monospace label.

        Tests:
            - test_lines_are_joined: Pass two lines; verify the label text
              contains both.
            - test_text_is_selectable: Verify the label allows text
              selection so a key can be copied.
        """
        label = QLabel("\n".join(lines))
        label.setWordWrap(True)
        label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        label.setStyleSheet(
            f"color: {C_TEXT}; font-family: 'Courier New', monospace;"
            f" font-size: 11px; border: none;"
        )
        label.setToolTip(f"Insgesamt {len(lines)} Einträge")
        # Dim the block a touch so the headings stay dominant.
        label.setStyleSheet(label.styleSheet() + f" selection-color: {C_TEXT_DIM};")
        return label
