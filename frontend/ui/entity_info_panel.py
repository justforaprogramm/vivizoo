"""EntityInfoPanel — detail view for a hovered/selected animal."""

from __future__ import annotations
from PyQt6.QtWidgets import QGroupBox, QFormLayout, QLabel, QProgressBar, QWidget
from frontend.core.constants import C_TEXT, C_TEXT_DIM, C_ACCENT, C_GOLD, C_RED


class EntityInfoPanel(QGroupBox):
    """Shows name, species, HP, hunger, welfare, and status effects."""

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
        bg = "#1c2333"
        border = "#30363d"
        return (
            f"QProgressBar {{"
            f" background: {bg}; border: 1px solid {border};"
            f" border-radius: 3px; text-align: center; color: {C_TEXT};"
            f"}}"
            f"QProgressBar::chunk {{"
            f" background: {accent}; border-radius: 2px;"
            f"}}"
        )

    def show_entity(self, data: dict | None) -> None:
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
        if hunger >= 70:
            colour = C_RED
        elif hunger >= 30:
            colour = C_GOLD
        else:
            colour = C_ACCENT
        self._hunger_bar.setStyleSheet(self._bar_qss(colour))
        self._welfare_bar.setValue(int(data.get("welfare", 0)))
        effects = data.get("status_effects", [])
        self._lbl_effects.setText(", ".join(effects) if effects else "Keine")
