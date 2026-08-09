"""
ActionPanel — God-mode action buttons.

Exposes exactly the four actions ``backend.core.action_handler`` accepts
without a purchase: ``feed_all``, ``feed_one``, ``heal`` and ``clean``.
A button is enabled when the snapshot shows the action's preconditions met
— selection, stock, life state — and its tooltip explains the current state
so a greyed-out button is never a mystery. One limit is worth naming: the
backend additionally skips animals below their individual feeding
threshold, which the snapshot does not expose, so a well-fed zoo can still
answer "Fed 0 animal(s)" to an enabled feed button.

Tests:
    - test_feed_all_disabled_when_inventory_empty: Pass a state with an
      empty inventory; verify the feed_all button is disabled.
    - test_feed_all_disabled_on_mismatched_stock: Pass FISH stock with only
      a living lion; verify the button stays disabled because the backend
      feeds each animal from its own PREFERRED_FOOD only.
    - test_heal_enabled_when_animal_selected: Pass a state with a living
      selected animal; verify the heal button is enabled.
    - test_heal_disabled_when_animal_dead: Pass a state whose selected
      animal has is_dead=True; verify the heal button is disabled.

Module owner: Erik (frontend).
"""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QLabel,
    QPushButton,
    QSizePolicy,
    QWidget,
)
from PyQt6.QtCore import pyqtSignal

from frontend.ui.styled_widgets import panel_layout, styled_button
from frontend.core.constants import C_TEXT, FOOD_LABELS, SPECIES_FOOD


# Eight fields instead of seven: four buttons, the hint line, the shortcut
# mapping and the two selection ids every button is gated against.
# too-few-public-methods is a knock-on effect of ignored-modules=PyQt6 (see
# .pylintrc): without a resolvable Qt base, pylint counts only update_state
# instead of the inherited QWidget methods.
# pylint: disable-next=too-many-instance-attributes, too-few-public-methods
class ActionPanel(QWidget):
    """God-mode action buttons panel.

    Emits ``action_triggered(action_name, kwargs)``; the main window passes
    both straight into ``engine.execute_action``.

    Tests:
        - test_feed_all_disabled_when_inventory_empty: Pass a state with
          zero stock; verify the feed_all button is disabled.
        - test_clean_enabled_only_with_selection: Pass
          selected_enclosure_id=None then "e_01"; verify the clean button
          flips from disabled to enabled.
    """

    action_triggered = pyqtSignal(str, dict)

    def __init__(self, parent: QWidget | None = None) -> None:
        """Build the four action buttons and wire their click handlers.

        Args:
            parent: Optional parent widget.

        Returns:
            None (constructor).

        Tests:
            - test_all_buttons_start_disabled: Verify all four buttons,
              feed_all included, are disabled before the first update_state
              call.
            - test_buttons_expand_horizontally: Verify each button uses an
              expanding horizontal size policy.
        """
        super().__init__(parent)
        layout = panel_layout(self)

        header = QLabel("🎮 Aktionen")
        header.setStyleSheet(
            f"color: {C_TEXT}; font-size: 13px; font-weight: bold; padding: 2px 0;"
        )
        layout.addWidget(header)

        self._btn_feed_all = styled_button("Alle Tiere füttern")
        self._btn_feed_one = styled_button("Ausgewähltes füttern")
        self._btn_heal = styled_button("Tier heilen")
        self._btn_clean = styled_button("Gehege reinigen")

        self._btn_feed_all.clicked.connect(
            lambda: self.action_triggered.emit("feed_all", {})
        )
        self._btn_feed_one.clicked.connect(lambda: self._emit_selected("feed_one"))
        self._btn_heal.clicked.connect(lambda: self._emit_selected("heal"))
        self._btn_clean.clicked.connect(lambda: self._emit_enclosure("clean"))

        for button in (
            self._btn_feed_all,
            self._btn_feed_one,
            self._btn_heal,
            self._btn_clean,
        ):
            button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            button.setEnabled(False)
            # The label is the accessible name by default; the shortcut is
            # not, and a disabled button's reason lives in its tooltip. Both
            # belong in what a screen reader announces.
            button.setAccessibleName(button.text())
            layout.addWidget(button)

        self._keys = {
            self._btn_feed_all: "F",
            self._btn_feed_one: "E",
            self._btn_heal: "H",
            self._btn_clean: "R",
        }

        self._hint = QLabel("Tier anfahren oder Gehege anklicken.")
        self._hint.setWordWrap(True)
        self._hint.setStyleSheet("color: #8b949e; font-size: 10px;")
        layout.addWidget(self._hint)

        layout.addStretch()

        self._selected_animal_id: str | None = None
        self._selected_enclosure_id: str | None = None

    # ── Public interface ──────────────────────────────────────────────────

    def update_state(
        self,
        game_state: dict,
        selected_animal_id: str | None,
        selected_enclosure_id: str | None,
    ) -> None:
        """Enable or disable each button from the snapshot and the selection.

        Args:
            game_state: The enriched snapshot — uses "inventory",
                "animals_on_map" and "enclosures_on_map".
            selected_animal_id: Currently hovered/selected animal id, or None.
            selected_enclosure_id: Currently selected enclosure id, or None.

        Returns:
            None.

        Tests:
            - test_feed_one_disabled_when_no_species_food: Select a lion
              while MEAT is 0; verify the feed_one button is disabled.
            - test_clean_disabled_without_enclosure: Pass
              selected_enclosure_id=None; verify the clean button is
              disabled.
            - test_tooltip_names_missing_food: Select a lion with no MEAT;
              verify the feed_one tooltip mentions "Fleisch".
        """
        self._selected_animal_id = selected_animal_id
        self._selected_enclosure_id = selected_enclosure_id

        inventory: dict = game_state.get("inventory") or {}
        animals: list = game_state.get("animals_on_map") or []

        # The backend feeds each animal only from its own PREFERRED_FOOD, so
        # "some food in stock" is not enough — a full fish tank cannot feed a
        # lion. Hunger itself is not in the snapshot, so this is a necessary
        # but not sufficient condition: an enabled button can still report
        # "Fed 0 animal(s)" when every animal is already satiated.
        species_in_stock = sorted(
            {
                SPECIES_FOOD[a["species"]]
                for a in animals
                if not a.get("is_dead")
                and a.get("species") in SPECIES_FOOD
                and inventory.get(SPECIES_FOOD[a["species"]], 0) > 0
            }
        )
        has_any_stock = any(
            inventory.get(key, 0) > 0 for key in ("MEAT", "PLANTS", "FISH")
        )
        self._btn_feed_all.setEnabled(bool(species_in_stock))
        if species_in_stock:
            self._set_hint(
                self._btn_feed_all,
                "Füttert jedes ausreichend hungrige Tier. Passendes Futter "
                "vorrätig: "
                + ", ".join(FOOD_LABELS.get(k, k) for k in species_in_stock)
                + ".",
            )
        elif has_any_stock:
            self._set_hint(
                self._btn_feed_all,
                "Das Lager passt zu keinem lebenden Tier — jede Art frisst "
                "nur ihr eigenes Futter.",
            )
        else:
            self._set_hint(
                self._btn_feed_all, "Kein Futter im Lager — erst im Shop kaufen."
            )

        animal = next((a for a in animals if a.get("id") == selected_animal_id), None)
        self._update_feed_one(animal, inventory)
        self._update_heal(animal)
        self._update_clean(game_state.get("enclosures_on_map") or [])

    # ── Internal helpers ──────────────────────────────────────────────────

    def _set_hint(self, button: QPushButton, text: str) -> None:
        """Give a button its explanation as tooltip *and* accessible text.

        A greyed-out button whose reason only lives in a tooltip is a dead
        end for anyone who does not hover — keyboard users included. The
        same sentence therefore goes into the accessible description, with
        the keyboard shortcut appended.

        Args:
            button: The button to annotate.
            text: The explanation, e.g. "Kein Futter im Lager".

        Returns:
            None.

        Tests:
            - test_tooltip_and_description_match: Call it; verify both carry
              the same explanation.
            - test_shortcut_is_appended: Call it for the heal button; verify
              the description ends with the key H.
        """
        button.setToolTip(text)
        key = self._keys.get(button)
        button.setAccessibleDescription(f"{text} Tastenkürzel {key}." if key else text)

    def _update_feed_one(self, animal: dict | None, inventory: dict) -> None:
        """Set state and tooltip of the single-feed button.

        Args:
            animal: The selected animal entry, or None.
            inventory: The snapshot's inventory dict.

        Returns:
            None.

        Tests:
            - test_disabled_without_selection: Call with animal=None; verify the
              button is disabled.
            - test_disabled_when_stock_empty: Pass a lion with MEAT=0; verify the
              button is disabled and the tooltip names Fleisch.
            - test_enabled_with_stock: Pass a lion with MEAT=5; verify the button
              is enabled.
        """
        if animal is None:
            self._btn_feed_one.setEnabled(False)
            self._set_hint(self._btn_feed_one, "Kein Tier ausgewählt.")
            return
        if animal.get("is_dead"):
            self._btn_feed_one.setEnabled(False)
            self._set_hint(self._btn_feed_one, "Das Tier ist verstorben.")
            return

        food_type = SPECIES_FOOD.get(animal.get("species", ""), "")
        stock = inventory.get(food_type, 0)
        self._btn_feed_one.setEnabled(stock > 0)
        label = FOOD_LABELS.get(food_type, food_type or "Futter")
        self._set_hint(
            self._btn_feed_one,
            (
                f"Füttert {animal.get('name', 'das Tier')} mit {label} "
                f"(Lager: {stock})."
                if stock > 0
                else f"Kein {label} im Lager."
            ),
        )

    def _update_heal(self, animal: dict | None) -> None:
        """Set state and tooltip of the heal button.

        Args:
            animal: The selected animal entry, or None.

        Returns:
            None.

        Tests:
            - test_heal_disabled_without_selection: Call with animal=None;
              verify the button is disabled.
            - test_disabled_for_dead_animal: Pass an animal with is_dead=True;
              verify the button is disabled.
        """
        if animal is None:
            self._btn_heal.setEnabled(False)
            self._set_hint(self._btn_heal, "Kein Tier ausgewählt.")
            return
        alive = not animal.get("is_dead", False)
        self._btn_heal.setEnabled(alive)
        self._set_hint(
            self._btn_heal,
            (
                f"Heilt {animal.get('name', 'das Tier')} und entfernt einen "
                "Statuseffekt."
                if alive
                else "Das Tier ist verstorben."
            ),
        )

    def _update_clean(self, enclosures: list[dict]) -> None:
        """Set state and tooltip of the clean button.

        Args:
            enclosures: The snapshot's enclosures_on_map list.

        Returns:
            None.

        Tests:
            - test_disabled_without_enclosure: Clear the selection; verify the
              button is disabled.
            - test_tooltip_shows_cleanliness: Select an enclosure at 45%; verify
              the tooltip mentions 45%.
        """
        selected = self._selected_enclosure_id
        self._btn_clean.setEnabled(selected is not None)
        if selected is None:
            self._set_hint(self._btn_clean, "Kein Gehege ausgewählt.")
            self._hint.setText("Tier anfahren oder Gehege anklicken.")
            return

        entry = next((e for e in enclosures if e.get("id") == selected), None)
        name = entry.get("name", selected) if entry else selected
        cleanliness = entry.get("cleanliness") if entry else None
        suffix = (
            f" (aktuell {float(cleanliness):.0f}%)" if cleanliness is not None else ""
        )
        self._set_hint(
            self._btn_clean,
            f"Setzt die Sauberkeit von {name} auf 100%{suffix}.",
        )
        self._hint.setText(f"Gehege ausgewählt: {name}")

    def _emit_selected(self, action: str) -> None:
        """Emit an action that operates on the selected animal.

        Args:
            action: "feed_one" or "heal".

        Returns:
            None.

        Tests:
            - test_emits_with_animal_id: Select an animal, call it; verify the
              signal carried that animal_id.
            - test_silent_without_selection: Call with no selection; verify no
              signal is emitted.
        """
        if self._selected_animal_id:
            self.action_triggered.emit(action, {"animal_id": self._selected_animal_id})

    def _emit_enclosure(self, action: str) -> None:
        """Emit an action that operates on the selected enclosure.

        Args:
            action: "clean".

        Returns:
            None.

        Tests:
            - test_emits_with_enclosure_id: Select an enclosure, call it; verify
              the signal carried that enclosure_id.
            - test_enclosure_action_silent_without_selection: Call with no
              enclosure selected; verify no signal is emitted.
        """
        if self._selected_enclosure_id:
            self.action_triggered.emit(
                action, {"enclosure_id": self._selected_enclosure_id}
            )
