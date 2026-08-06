"""ActionPanel — God-mode action buttons.

Phase 1: 4 uniformly styled buttons matching backend Phase 1 API.
Phase 2+: adds "Leichen entsorgen" (start_cremation) and "Tier umbenennen" (rename_animal).

Tests:
    - test_feed_all_disabled_when_inventory_empty
    - test_heal_enabled_when_animal_selected
    - test_heal_disabled_when_animal_dead
"""

from __future__ import annotations
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QSizePolicy
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QFont
from frontend.ui.styled_widgets import styled_button
from frontend.core.constants import C_TEXT, SPECIES_FOOD


class ActionPanel(QWidget):
    """God-mode action buttons panel.

    Provides 4 action buttons (feed_all, feed_one, heal, clean) that emit
    action_triggered when clicked. Button enable states are dynamically
    updated based on inventory, selected animal, and selected enclosure.

    Tests:
        - test_feed_all_disabled_when_inventory_empty: Pass state with zero
          inventory; verify feed_all button is disabled.
        - test_heal_enabled_when_animal_selected: Pass state with selected
          animal that is alive; verify heal button is enabled.
    """

    action_triggered = pyqtSignal(str, dict)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(4, 4, 4, 4)

        header = QLabel("🎮 Aktionen")
        header.setStyleSheet(
            f"color: {C_TEXT}; font-size: 13px; font-weight: bold; padding: 2px 0;"
        )
        layout.addWidget(header)

        # All action buttons use neutral style for visual consistency.
        # The primary action ("Alle Tiere füttern") is listed first.
        self._btn_feed_all = styled_button("Alle Tiere füttern")
        self._btn_feed_one = styled_button("Ausgewähltes füttern")
        self._btn_heal = styled_button("Tier heilen")
        self._btn_clean = styled_button("Gehege reinigen")

        self._btn_feed_all.clicked.connect(lambda: self.action_triggered.emit("feed_all", {}))
        self._btn_feed_one.clicked.connect(lambda: self._emit_selected("feed_one"))
        self._btn_heal.clicked.connect(lambda: self._emit_selected("heal"))
        self._btn_clean.clicked.connect(lambda: self._emit_enclosure("clean"))

        # Size policy — let buttons expand to fill width
        for btn in [self._btn_feed_all, self._btn_feed_one, self._btn_heal, self._btn_clean]:
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            layout.addWidget(btn)

        layout.addStretch()

        self._selected_animal_id: str | None = None
        self._selected_enclosure_id: str | None = None

    def update_state(self, game_state: dict, selected_animal_id: str | None,
                     selected_enclosure_id: str | None) -> None:
        """Enable or disable buttons based on current game state and selection.

        Args:
            game_state: Full game state dict (inventory, animals_on_map).
            selected_animal_id: Currently selected animal id, or None.
            selected_enclosure_id: Currently selected enclosure id, or None.

        Tests:
            - test_feed_one_disabled_when_no_species_food: Select a lion but
              MEAT inventory is 0; verify feed_one button is disabled.
            - test_clean_disabled_when_no_enclosure_selected: Pass
              selected_enclosure_id=None; verify clean button is disabled.
        """
        self._selected_animal_id = selected_animal_id
        self._selected_enclosure_id = selected_enclosure_id
        inv: dict = game_state.get("inventory", {})
        animals: list = game_state.get("animals_on_map", [])
        any_food = inv.get("MEAT", 0) > 0 or inv.get("PLANTS", 0) > 0 or inv.get("FISH", 0) > 0
        self._btn_feed_all.setEnabled(any_food)

        sel_animal = next((a for a in animals if a["id"] == selected_animal_id), None)
        feed_one_ok = False
        if sel_animal and not sel_animal.get("is_dead"):
            food_type = SPECIES_FOOD.get(sel_animal["species"], "")
            feed_one_ok = inv.get(food_type, 0) > 0
        self._btn_feed_one.setEnabled(feed_one_ok)
        self._btn_heal.setEnabled(sel_animal is not None and not sel_animal.get("is_dead", False))
        self._btn_clean.setEnabled(selected_enclosure_id is not None)

    def _emit_selected(self, action: str) -> None:
        if self._selected_animal_id:
            self.action_triggered.emit(action, {"animal_id": self._selected_animal_id})

    def _emit_enclosure(self, action: str) -> None:
        if self._selected_enclosure_id:
            self.action_triggered.emit(action, {"enclosure_id": self._selected_enclosure_id})