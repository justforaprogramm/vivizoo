"""ShopPanel — buy food and animals from the zoo shop.

Phase 1: Food (MEAT/PLANTS/FISH) and Animals (Lion/Giraffe/Penguin).
Ticket section removed (not in backend Phase 1 API).

Tests:
    - test_food_price_updates_on_type_change: Select MEAT (50€), amount=5;
      verify total label shows "250€".
    - test_animal_buy_disabled_when_budget_too_low: Set budget to 100€;
      verify animal purchase should fail via backend.
    - test_inventory_display_updates: Call update_state with inventory
      dict; verify label shows MEAT/PLANTS/FISH counts.
"""

from __future__ import annotations
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QComboBox, QSpinBox,
    QGroupBox, QHBoxLayout,
)
from PyQt6.QtCore import pyqtSignal, Qt
from frontend.ui.styled_widgets import styled_button, styled_label
from frontend.core.constants import (
    C_TEXT, C_TEXT_DIM, FOOD_PRICES, ANIMAL_PRICES,
)


class ShopPanel(QWidget):
    """Shop interface for buying food and animals.

    Two sections: Food purchase (type selector, quantity spinner, price
    preview, inventory display) and Animal purchase (species selector
    with price label).

    Emits buy_food(type, amount) and buy_animal(species) signals.

    Tests:
        - test_buy_food_emits_correct_signal: Select FISH, amount 3,
          click Kaufen; verify buy_food emitted with ("FISH", 3).
        - test_buy_animal_emits_species: Select Giraffe, click Kaufen;
          verify buy_animal emitted with "giraffe".
        - test_food_combo_has_three_options: Verify combo has exactly
          MEAT, PLANTS, FISH entries.
    """

    buy_food = pyqtSignal(str, int)
    buy_animal = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # ── Section 1: Food ──────────────────────────────────────────
        food_group = QGroupBox("🍖 Futter kaufen")
        fl = QVBoxLayout(food_group)
        self._food_combo = QComboBox()
        for ftype, label in [("MEAT","Fleisch"), ("PLANTS","Pflanzen"), ("FISH","Fisch")]:
            self._food_combo.addItem(f"{label} ({ftype}) · {FOOD_PRICES[ftype]}€/Stk", ftype)
        fl.addWidget(self._food_combo)
        row = QHBoxLayout()
        self._food_spin = QSpinBox()
        self._food_spin.setRange(1, 100)
        self._food_spin.setValue(1)
        row.addWidget(self._food_spin)
        self._food_total = styled_label("Gesamt: 50€", dim=True)
        row.addWidget(self._food_total)
        fl.addLayout(row)
        btn_buy_food = styled_button("Kaufen", accent=True)
        btn_buy_food.clicked.connect(self._on_buy_food)
        fl.addWidget(btn_buy_food)
        self._food_inv_label = styled_label("Im Lager: —", dim=True)
        fl.addWidget(self._food_inv_label)
        self._food_combo.currentIndexChanged.connect(self._update_food_total)
        self._food_spin.valueChanged.connect(self._update_food_total)
        layout.addWidget(food_group)

        # ── Section 2: Animals ───────────────────────────────────────
        animal_group = QGroupBox("🦁 Tiere kaufen")
        al = QVBoxLayout(animal_group)
        self._animal_combo = QComboBox()
        for sp, label in [("lion","Löwe"), ("giraffe","Giraffe"), ("penguin","Pinguin")]:
            self._animal_combo.addItem(f"{label} · {ANIMAL_PRICES[sp]:,}€", sp)
        al.addWidget(self._animal_combo)
        btn_buy_animal = styled_button("Kaufen")
        btn_buy_animal.clicked.connect(self._on_buy_animal)
        al.addWidget(btn_buy_animal)
        layout.addWidget(animal_group)

        layout.addStretch()

    def update_state(self, game_state: dict) -> None:
        """Refresh inventory display from the latest game state.

        Args:
            game_state: Full state dict, uses "inventory" key.

        Tests:
            - test_inventory_shows_meat_plants_fish: Pass inventory with
              MEAT=10, PLANTS=5, FISH=3; verify label contains all three.
            - test_inventory_empty_shows_zeros: Pass inventory with all
              zero values; verify label shows 0 for all types.
        """
        inv = game_state.get("inventory", {})
        self._food_inv_label.setText(
            f'Im Lager:  MEAT: {inv.get("MEAT",0)}  |  '
            f'PLANTS: {inv.get("PLANTS",0)}  |  FISH: {inv.get("FISH",0)}'
        )

    def _update_food_total(self) -> None:
        ftype = self._food_combo.currentData()
        amount = self._food_spin.value()
        price = FOOD_PRICES.get(ftype, 0)
        self._food_total.setText(f"Gesamt: {price * amount}€")

    def _on_buy_food(self) -> None:
        ftype = self._food_combo.currentData()
        self.buy_food.emit(ftype, self._food_spin.value())

    def _on_buy_animal(self) -> None:
        self.buy_animal.emit(self._animal_combo.currentData())