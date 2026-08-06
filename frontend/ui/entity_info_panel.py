"""EntityInfoPanel — detail view for a hovered/selected animal."""

from __future__ import annotations
from typing import Optional
from PyQt6.QtWidgets import QGroupBox, QFormLayout, QLabel, QProgressBar, QWidget
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from frontend.core.constants import C_TEXT, C_TEXT_DIM, C_ACCENT, C_GOLD, C_RED


class EntityInfoPanel(QGroupBox):
    """Shows name, species, HP, hunger, welfare, and status effects.

    Populated via show_entity() when the user hovers over an animal
    sprite. Displays a placeholder when no animal is selected.

    Tests:
        - test_clear_shows_placeholder: Call show_entity(None); verify
          the placeholder text "Kein Tier ausgewählt" is displayed.
        - test_valid_data_populates_fields: Pass dict with name, species,
          hp=85, hunger=40, welfare=90; verify all labels and progress
          bars reflect the data.
        - test_empty_dict_shows_placeholder: Pass {}; verify placeholder
          displayed (unknown entity behaviour).
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("🔍 Tier-Info", parent)
        layout = QFormLayout(self)
        layout.setSpacing(6)

        self._lbl_name = QLabel("Kein Tier ausgewählt")
        self._lbl_name.setStyleSheet(f"color: {C_TEXT}; font-weight: bold;")
        self._lbl_age = QLabel("—")
        self._lbl_age.setStyleSheet(f"color: {C_TEXT_DIM};")

        self._hp_bar = QProgressBar()
        self._hp_bar.setRange(0, 100)
        self._hp_bar.setValue(0)
        self._hp_bar.setFormat("HP %v")
        self._hp_bar.setStyleSheet(self._bar_qss(C_ACCENT))

        self._hunger_bar = QProgressBar()
        self._hunger_bar.setRange(0, 100)
        self._hunger_bar.setValue(0)
        self._hunger_bar.setFormat("Hunger %v")
        self._hunger_bar.setStyleSheet(self._bar_qss(C_GOLD))

        self._welfare_bar = QProgressBar()
        self._welfare_bar.setRange(0, 100)
        self._welfare_bar.setValue(0)
        self._welfare_bar.setFormat("Wohlbefinden %v")
        self._welfare_bar.setStyleSheet(self._bar_qss(C_ACCENT))

        self._lbl_effects = QLabel("—")
        self._lbl_effects.setStyleSheet(f"color: {C_RED}; font-size: 10px;")
        self._lbl_effects.setWordWrap(True)

        layout.addRow("Name:", self._lbl_name)
        layout.addRow("Alter · Stadium:", self._lbl_age)
        layout.addRow(self._hp_bar)
        layout.addRow(self._hunger_bar)
        layout.addRow(self._welfare_bar)
        layout.addRow("Effekte:", self._lbl_effects)

    @staticmethod
    def _bar_qss(accent: str) -> str:
        return (
            f"QProgressBar {{ background: #1c2333; border: 1px solid #30363d; border-radius: 3px; text-align: center; color: {C_TEXT}; }}"
            f"QProgressBar::chunk {{ background: {accent}; border-radius: 2px; }}"
        )

    def show_entity(self, data: dict | None) -> None:
        """Populate or clear the panel with animal hover data.

        Args:
            data: Dict from get_entity_info(), or None to reset.

        Tests:
            - test_show_entity_none_clears_to_placeholder: Call with
              None; verify all bars at 0 and placeholder text shown.
            - test_show_entity_hunger_changes_progress_bar_color: Pass
              hunger=90; verify hunger bar QSS uses C_RED accent.
            - test_show_entity_status_effects_rendered: Pass
              status_effects=["Hungry", "Sick"]; verify lbl_effects
              shows "Hungry, Sick".
        """
        if not data:
            self._lbl_name.setText("Kein Tier ausgewählt")
            self._lbl_age.setText("—")
            self._hp_bar.setValue(0)
            self._hunger_bar.setValue(0)
            self._welfare_bar.setValue(0)
            self._lbl_effects.setText("—")
            return

        self._lbl_name.setText(f'{data.get("name", "?")} · {data.get("species", "?")}')
        self._lbl_age.setText(f'{data.get("age_days", 0)} Tage · Erwachsen')
        self._hp_bar.setValue(int(data.get("hp", 0)))
        hunger = int(data.get("hunger", 0))
        self._hunger_bar.setValue(hunger)
        self._hunger_bar.setStyleSheet(
            self._bar_qss(C_RED if hunger >= 70 else C_GOLD if hunger >= 30 else C_ACCENT)
        )
        self._welfare_bar.setValue(int(data.get("welfare", 0)))
        effects = data.get("status_effects", [])
        self._lbl_effects.setText(", ".join(effects) if effects else "Keine")