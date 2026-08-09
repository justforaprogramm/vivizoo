"""
ShopPanel — buy food and animals from the zoo shop.

Mirrors exactly the two purchase actions the backend exposes:

* ``buy_food(type, amount)`` — MEAT, PLANTS and FISH at the prices from
  ``backend.core.inventory.Inventory.FOOD_PRICES``;
* ``buy_animal(species, name, enclosure_id)`` — all three kwargs are sent so
  the animal gets a real name and lands in the chosen enclosure instead of
  the backend's fallback.

MEDICINE is part of the backend inventory and is therefore *displayed*, but
it is not offered for sale: Phase 1 heals in God mode without consuming it,
so buying it would be a dead feature (IMPLEMENTATION_PLAN §2.1, §7).

Tests:
    - test_food_price_updates_on_type_change: Select MEAT (8 €) with
      amount 5; verify the total label shows "40 €".
    - test_buy_disabled_when_budget_too_low: Pass money=1; verify both buy
      buttons are disabled.
    - test_inventory_display_shows_all_keys: Pass a full inventory dict;
      verify MEAT, PLANTS, FISH and MEDICINE all appear.

Module owner: Erik (frontend).
"""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QComboBox,
    QSpinBox,
    QGroupBox,
    QHBoxLayout,
    QLineEdit,
)
from PyQt6.QtCore import pyqtSignal

from frontend.ui.styled_widgets import panel_layout, styled_button, styled_label
from frontend.core.constants import (
    ANIMAL_PRICES,
    ENCLOSURE_DEFS,
    FOOD_LABELS,
    FOOD_PRICES,
    INVENTORY_KEYS,
    SHOP_FOOD_TYPES,
    SPECIES_LABELS,
)


# Twelve fields, pylint allows seven: one control per widget of the two
# purchase sections plus the budget and the enclosure list. A QWidget simply
# holds one attribute per child widget it has to touch again later.
# too-few-public-methods is a knock-on effect of ignored-modules=PyQt6 (see
# .pylintrc): pylint counts inherited methods, and without a resolvable Qt
# base it sees only update_state.
# pylint: disable-next=too-many-instance-attributes, too-few-public-methods
class ShopPanel(QWidget):
    """Shop interface for buying food and animals.

    Emits ``buy_food(type, amount)`` and
    ``buy_animal(species, name, enclosure_id)``; the main window forwards
    both straight to ``engine.execute_action``.

    Tests:
        - test_buy_food_emits_correct_signal: Select FISH with amount 3,
          click Kaufen; verify buy_food is emitted with ("FISH", 3).
        - test_buy_animal_emits_all_kwargs: Select Giraffe, type a name,
          pick a enclosure, click Kaufen; verify buy_animal carries all
          three values.
    """

    buy_food = pyqtSignal(str, int)
    buy_animal = pyqtSignal(str, str, str)

    def __init__(self, parent: QWidget | None = None) -> None:
        """Build the food section and the animal section.

        Args:
            parent: Optional parent widget.

        Returns:
            None (constructor).

        Tests:
            - test_food_combo_has_three_options: Verify the combo holds
              exactly MEAT, PLANTS and FISH.
            - test_both_sections_are_added: Verify the panel holds the food
              group and the animal group in that order.
        """
        super().__init__(parent)
        layout = panel_layout(self)

        self._money = 0.0
        self._enclosures: list[dict] = []

        layout.addWidget(self._build_food_section())
        layout.addWidget(self._build_animal_section())
        layout.addStretch()

        self._update_food_total()

    def _build_food_section(self) -> QGroupBox:
        """Assemble the food type, amount, price preview and stock line.

        Returns:
            QGroupBox: The ready-made section, wired to its handlers.

        Tests:
            - test_food_combo_lists_every_type: Call it; verify the combo
              holds one entry per SHOP_FOOD_TYPES value.
            - test_amount_starts_at_ten: Call it; verify the spin box opens
              at 10 within the range 1–100.
        """
        food_group = QGroupBox("🍖 Futter kaufen")
        food_layout = QVBoxLayout(food_group)

        self._food_combo = QComboBox()
        for food_type in SHOP_FOOD_TYPES:
            self._food_combo.addItem(
                f"{FOOD_LABELS[food_type]} ({food_type}) · "
                f"{FOOD_PRICES[food_type]:.0f} €/Stk",
                food_type,
            )
        food_layout.addWidget(self._food_combo)

        row = QHBoxLayout()
        self._food_spin = QSpinBox()
        self._food_spin.setRange(1, 100)
        self._food_spin.setValue(10)
        row.addWidget(self._food_spin)
        self._food_total = styled_label("", dim=True)
        row.addWidget(self._food_total)
        food_layout.addLayout(row)

        self._btn_buy_food = styled_button("Kaufen", accent=True)
        self._btn_buy_food.clicked.connect(self._on_buy_food)
        food_layout.addWidget(self._btn_buy_food)

        self._food_inv_label = styled_label("Im Lager: —", dim=True)
        self._food_inv_label.setWordWrap(True)
        food_layout.addWidget(self._food_inv_label)

        self._food_combo.currentIndexChanged.connect(self._update_food_total)
        self._food_spin.valueChanged.connect(self._update_food_total)
        return food_group

    def _build_animal_section(self) -> QGroupBox:
        """Assemble species, name, target enclosure and the buy button.

        Returns:
            QGroupBox: The ready-made section, wired to its handlers.

        Tests:
            - test_species_combo_matches_prices: Call it; verify the combo
              holds one entry per ANIMAL_PRICES key.
            - test_enclosure_combo_matches_defs: Call it; verify the target
              combo holds one entry per ENCLOSURE_DEFS entry.
        """
        animal_group = QGroupBox("🦁 Tiere kaufen")
        animal_layout = QVBoxLayout(animal_group)

        self._animal_combo = QComboBox()
        for species, price in ANIMAL_PRICES.items():
            self._animal_combo.addItem(
                f"{SPECIES_LABELS[species]} · {price:,.0f} €".replace(",", "."),
                species,
            )
        animal_layout.addWidget(self._animal_combo)

        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("Name (optional)")
        self._name_edit.setMaxLength(24)
        animal_layout.addWidget(self._name_edit)

        self._enclosure_combo = QComboBox()
        for edef in ENCLOSURE_DEFS:
            self._enclosure_combo.addItem(edef["name"], edef["id"])
        animal_layout.addWidget(self._enclosure_combo)

        self._enclosure_info = styled_label("—", dim=True)
        animal_layout.addWidget(self._enclosure_info)

        self._btn_buy_animal = styled_button("Kaufen")
        self._btn_buy_animal.clicked.connect(self._on_buy_animal)
        animal_layout.addWidget(self._btn_buy_animal)

        self._animal_combo.currentIndexChanged.connect(self._refresh_buttons)
        self._enclosure_combo.currentIndexChanged.connect(self._refresh_enclosure_info)
        return animal_group

    # ── Public interface ──────────────────────────────────────────────────

    def update_state(self, game_state: dict) -> None:
        """Refresh inventory, enclosure occupancy and budget gating.

        Args:
            game_state: The enriched snapshot — uses "inventory",
                "finances" and "enclosures_on_map".

        Returns:
            None.

        Tests:
            - test_inventory_shows_all_four_keys: Pass MEAT=10, PLANTS=5,
              FISH=3, MEDICINE=0; verify all four appear in the label.
            - test_buy_animal_disabled_when_broke: Pass money=10; verify the
              animal buy button is disabled.
            - test_enclosure_info_shows_occupancy: Pass an enclosure with
              capacity 5 and free_slots 2; verify the label reads "3 / 5".
        """
        inventory = game_state.get("inventory") or {}
        self._food_inv_label.setText(
            "Im Lager:  "
            + "  |  ".join(
                f"{FOOD_LABELS[key]}: {inventory.get(key, 0)}" for key in INVENTORY_KEYS
            )
        )

        self._money = float((game_state.get("finances") or {}).get("money", 0.0))
        self._enclosures = game_state.get("enclosures_on_map") or []
        self._refresh_enclosure_info()
        self._refresh_buttons()

    # ── Internal helpers ──────────────────────────────────────────────────

    def _refresh_enclosure_info(self) -> None:
        """Show occupancy and cleanliness of the selected target enclosure.

        Returns:
            None.

        Tests:
            - test_shows_occupancy: Pass an enclosure with capacity 5 and 3
              occupied; verify the label reads "3 / 5".
            - test_unknown_enclosure_shows_dash: Select an id the snapshot does
              not contain; verify the label reads "—".
        """
        target_id = self._enclosure_combo.currentData()
        entry = next((e for e in self._enclosures if e.get("id") == target_id), None)
        if entry is None:
            self._enclosure_info.setText("—")
            return

        capacity = int(entry.get("capacity", 0))
        # Prefer the pre-computed value, but fall back to the raw backend
        # field so a plain get_entity_info payload also renders correctly.
        if entry.get("occupied") is not None:
            occupied = int(entry["occupied"])
        elif entry.get("free_slots") is not None:
            occupied = max(0, capacity - int(entry["free_slots"]))
        else:
            occupied = 0
        text = f"Belegung: {occupied} / {capacity}"
        cleanliness = entry.get("cleanliness")
        if cleanliness is not None:
            text += f"  ·  Sauberkeit: {float(cleanliness):.0f}%"
        self._enclosure_info.setText(text)

    def _refresh_buttons(self) -> None:
        """Enable or disable the buy buttons based on the current budget.

        Returns:
            None.

        Tests:
            - test_food_button_disabled_when_broke: Set money below the total;
              verify the food button is disabled.
            - test_animal_button_enabled_with_budget: Set money above the species
              price; verify the animal button is enabled.
        """
        food_type = self._food_combo.currentData()
        food_total = FOOD_PRICES.get(food_type, 0.0) * self._food_spin.value()
        self._btn_buy_food.setEnabled(self._money >= food_total)

        species = self._animal_combo.currentData()
        self._btn_buy_animal.setEnabled(self._money >= ANIMAL_PRICES.get(species, 0.0))

    def _update_food_total(self) -> None:
        """Recompute the food price preview after a type or amount change.

        Returns:
            None.

        Tests:
            - test_total_is_price_times_amount: Select MEAT (8 €) with amount 5;
              verify the label reads "Gesamt: 40 €".
            - test_total_updates_on_type_change: Switch to PLANTS; verify the
              total drops accordingly.
        """
        food_type = self._food_combo.currentData()
        total = FOOD_PRICES.get(food_type, 0.0) * self._food_spin.value()
        self._food_total.setText(f"Gesamt: {total:,.0f} €".replace(",", "."))
        self._refresh_buttons()

    def _on_buy_food(self) -> None:
        """Emit buy_food with the selected type and amount.

        Returns:
            None.

        Tests:
            - test_emits_selected_type: Select FISH, call it; verify buy_food
              carried "FISH".
            - test_emits_selected_amount: Set the spin box to 7, call it; verify
              buy_food carried 7.
        """
        self.buy_food.emit(self._food_combo.currentData(), self._food_spin.value())

    def _on_buy_animal(self) -> None:
        """Emit buy_animal with species, typed name and target enclosure.

        Returns:
            None.

        Tests:
            - test_emits_all_three_kwargs: Pick a species, a name and a target;
              verify all three reach the signal.
            - test_name_field_is_cleared: Type a name, call it; verify the input
              is empty afterwards.
        """
        self.buy_animal.emit(
            self._animal_combo.currentData(),
            self._name_edit.text().strip(),
            self._enclosure_combo.currentData() or "",
        )
        self._name_edit.clear()
