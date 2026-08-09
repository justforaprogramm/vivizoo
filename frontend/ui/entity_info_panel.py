"""
EntityInfoPanel — detail view for the hovered animal or selected enclosure.

The backend answers ``get_entity_info(id)`` for both entity kinds, so the
panel renders two different forms and shows whichever matches the current
selection:

* animal — name, species, age, HP, hunger, welfare, status effects and
  whether it is dead;
* enclosure — name, biome, occupancy and cleanliness.

Hunger follows the backend semantics: 0 means full, 100 means starving, so
the bar turns from green to red as it fills.

Tests:
    - test_placeholder_when_nothing_selected: Call show_entity(None); verify
      the placeholder label is visible and both forms are hidden.
    - test_animal_payload_fills_all_rows: Call show_entity with a full hover
      dict; verify every label and progress bar carries the value.
    - test_enclosure_payload_switches_form: Call show_enclosure with an
      enclosure dict; verify the enclosure form is visible instead.

Module owner: Erik (frontend).
"""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QGroupBox,
    QFormLayout,
    QLabel,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)

from frontend.core.constants import (
    BIOME_LABELS,
    SPECIES_LABELS,
    CLEAN_CRITICAL,
    CLEAN_WARN,
    C_TEXT,
    C_TEXT_DIM,
    C_ACCENT,
    C_GOLD,
    C_RED,
)


# Fourteen fields instead of seven: the panel keeps two complete forms
# (animal and enclosure) plus the placeholder alive at once and switches
# between them, rather than rebuilding them on every change of selection.
# pylint: disable-next=too-many-instance-attributes
class EntityInfoPanel(QGroupBox):
    """Detail card for one animal or one enclosure.

    Holds two mutually exclusive forms plus a placeholder label. Only the
    form matching the last ``show_*`` call is visible.

    Tests:
        - test_starts_with_placeholder: Create the panel; verify the
          placeholder is visible and no form is shown.
        - test_dead_animal_marks_status: Call show_entity with
          is_dead=True; verify the status label reads "verstorben".
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        """Build the placeholder, the animal form and the enclosure form.

        Args:
            parent: Optional parent widget.

        Returns:
            None (constructor).

        Tests:
            - test_bars_are_zero_initially: Verify HP, hunger and welfare
              bars all start at 0.
            - test_enclosure_form_hidden_initially: Verify the enclosure
              form is not visible after construction.
        """
        super().__init__("🔍 Info", parent)
        root = QVBoxLayout(self)
        root.setSpacing(6)

        self._placeholder = QLabel("Kein Tier oder Gehege ausgewählt")
        self._placeholder.setStyleSheet(f"color: {C_TEXT_DIM};")
        root.addWidget(self._placeholder)

        # ── Animal form ──────────────────────────────────────────────────
        self._animal_box = QWidget()
        animal_form = QFormLayout(self._animal_box)
        animal_form.setContentsMargins(0, 0, 0, 0)
        animal_form.setSpacing(6)

        self._lbl_name = QLabel("—")
        self._lbl_name.setStyleSheet(f"color: {C_TEXT}; font-weight: bold;")
        self._lbl_age = QLabel("—")
        self._lbl_age.setStyleSheet(f"color: {C_TEXT_DIM};")
        self._lbl_status = QLabel("—")
        self._lbl_status.setStyleSheet(f"color: {C_ACCENT};")

        self._hp_bar = self._make_bar("HP %v / 100", C_ACCENT)
        self._hunger_bar = self._make_bar("Hunger %v / 100", C_ACCENT)
        self._welfare_bar = self._make_bar("Wohlbefinden %v / 100", C_ACCENT)

        self._lbl_effects = QLabel("—")
        self._lbl_effects.setStyleSheet(f"color: {C_GOLD}; font-size: 10px;")
        self._lbl_effects.setWordWrap(True)

        animal_form.addRow("Name:", self._lbl_name)
        animal_form.addRow("Alter:", self._lbl_age)
        animal_form.addRow("Status:", self._lbl_status)
        animal_form.addRow(self._hp_bar)
        animal_form.addRow(self._hunger_bar)
        animal_form.addRow(self._welfare_bar)
        animal_form.addRow("Effekte:", self._lbl_effects)
        root.addWidget(self._animal_box)

        # ── Enclosure form ───────────────────────────────────────────────
        self._enclosure_box = QWidget()
        enclosure_form = QFormLayout(self._enclosure_box)
        enclosure_form.setContentsMargins(0, 0, 0, 0)
        enclosure_form.setSpacing(6)

        self._lbl_enc_name = QLabel("—")
        self._lbl_enc_name.setStyleSheet(f"color: {C_TEXT}; font-weight: bold;")
        self._lbl_enc_biome = QLabel("—")
        self._lbl_enc_biome.setStyleSheet(f"color: {C_TEXT_DIM};")
        self._lbl_enc_slots = QLabel("—")
        self._lbl_enc_slots.setStyleSheet(f"color: {C_TEXT_DIM};")
        self._clean_bar = self._make_bar("Sauberkeit %v / 100", C_ACCENT)

        enclosure_form.addRow("Gehege:", self._lbl_enc_name)
        enclosure_form.addRow("Biom:", self._lbl_enc_biome)
        enclosure_form.addRow("Belegung:", self._lbl_enc_slots)
        enclosure_form.addRow(self._clean_bar)
        root.addWidget(self._enclosure_box)

        self._animal_box.setVisible(False)
        self._enclosure_box.setVisible(False)

    # ── Construction helpers ──────────────────────────────────────────────

    @staticmethod
    def _make_bar(fmt: str, accent: str) -> QProgressBar:
        """Create a 0–100 progress bar with the given format and colour.

        Args:
            fmt: Qt format string, e.g. ``"HP %v / 100"``.
            accent: Hex colour of the filled chunk.

        Returns:
            QProgressBar: A configured, zeroed bar.

        Tests:
            - test_range_is_zero_to_hundred: Create a bar; verify minimum 0 and
              maximum 100.
            - test_format_is_applied: Create with "HP %v / 100"; verify the bar
              reports that format.
        """
        progress = QProgressBar()
        progress.setRange(0, 100)
        progress.setValue(0)
        progress.setFormat(fmt)
        progress.setStyleSheet(EntityInfoPanel._bar_qss(accent))
        return progress

    @staticmethod
    def _bar_qss(accent: str) -> str:
        """Return the stylesheet for a progress bar with the given accent.

        Args:
            accent: Hex colour used for the filled chunk.

        Returns:
            str: A QSS snippet for QProgressBar and QProgressBar::chunk.

        Tests:
            - test_contains_accent_colour: Call with the green accent; verify the
              snippet contains it.
            - test_styles_both_selectors: Verify the snippet covers QProgressBar
              and QProgressBar::chunk.
        """
        return (
            f"QProgressBar {{"
            f" background: #1c2333; border: 1px solid #30363d;"
            f" border-radius: 3px; text-align: center; color: {C_TEXT};"
            f"}}"
            f"QProgressBar::chunk {{"
            f" background: {accent}; border-radius: 2px;"
            f"}}"
        )

    @staticmethod
    def _grade(value: float, warn: float, critical: float) -> str:
        """Map a 0–100 value onto a traffic-light colour.

        Args:
            value: The measured value.
            warn: Below this the colour is gold.
            critical: Below this the colour is red.

        Returns:
            str: One of C_ACCENT, C_GOLD or C_RED.

        Tests:
            - test_high_value_is_green: _grade(90, 60, 30) returns C_ACCENT.
            - test_critical_value_is_red: _grade(10, 60, 30) returns C_RED.
        """
        if value < critical:
            return C_RED
        if value < warn:
            return C_GOLD
        return C_ACCENT

    # ── Public interface ──────────────────────────────────────────────────

    def show_entity(self, data: dict | None) -> None:
        """Render an animal hover payload, or the placeholder when empty.

        Args:
            data: The dict from ``get_entity_info(animal_id)`` with the keys
                name, species, age_days, hp, hunger, welfare, is_dead and
                status_effects. ``None`` or ``{}`` clears the panel.

        Returns:
            None.

        Tests:
            - test_none_shows_placeholder: Call with None; verify the
              placeholder is visible and the animal form is hidden.
            - test_empty_dict_shows_placeholder: Call with {} (unknown id);
              verify the placeholder is shown.
            - test_hunger_colour_turns_red: Call with hunger=90; verify the
              hunger bar stylesheet contains the red colour.
        """
        if not data:
            self.clear()
            return

        species_key = str(data.get("species", ""))
        species = SPECIES_LABELS.get(species_key, species_key.title() or "?")
        self._lbl_name.setText(f'{data.get("name", "?")} · {species}')
        self._lbl_age.setText(f'{int(data.get("age_days", 0))} Tage')

        is_dead = bool(data.get("is_dead", False))
        self._lbl_status.setText("verstorben" if is_dead else "lebt")
        self._lbl_status.setStyleSheet(f"color: {C_RED if is_dead else C_ACCENT};")

        hp = float(data.get("hp", 0))
        self._hp_bar.setValue(int(hp))
        self._hp_bar.setStyleSheet(self._bar_qss(self._grade(hp, 50, 25)))

        # Backend semantics: 0 = full, 100 = starving — invert the grading.
        hunger = float(data.get("hunger", 0))
        self._hunger_bar.setValue(int(hunger))
        self._hunger_bar.setStyleSheet(self._bar_qss(self._grade(100 - hunger, 70, 30)))

        welfare = float(data.get("welfare", 0))
        self._welfare_bar.setValue(int(welfare))
        self._welfare_bar.setStyleSheet(self._bar_qss(self._grade(welfare, 50, 25)))

        effects = data.get("status_effects") or []
        self._lbl_effects.setText(", ".join(effects) if effects else "Keine")

        self._placeholder.setVisible(False)
        self._enclosure_box.setVisible(False)
        self._animal_box.setVisible(True)

    def show_enclosure(self, data: dict | None) -> None:
        """Render an enclosure payload, or the placeholder when empty.

        Args:
            data: Either the raw dict from ``get_entity_info(enclosure_id)``
                (name, biome, cleanliness, free_slots) or an enriched entry
                from ``enclosures_on_map`` that also carries capacity and
                occupied. ``None`` or ``{}`` clears the panel.

        Returns:
            None.

        Tests:
            - test_none_enclosure_shows_placeholder: Call with None; verify
              the placeholder is visible.
            - test_occupancy_uses_free_slots: Call with capacity=5 and
              free_slots=2; verify the label reads "3 / 5".
            - test_dirty_enclosure_turns_red: Call with cleanliness=10;
              verify the bar stylesheet contains the red colour.
        """
        if not data:
            self.clear()
            return

        biome_key = str(data.get("biome", ""))
        self._lbl_enc_name.setText(str(data.get("name", "?")))
        self._lbl_enc_biome.setText(
            BIOME_LABELS.get(biome_key, biome_key.title() or "?")
        )

        capacity = data.get("capacity")
        free = data.get("free_slots")
        if capacity is not None and free is not None:
            occupied = max(0, int(capacity) - int(free))
            self._lbl_enc_slots.setText(
                f"{occupied} / {int(capacity)} ({int(free)} frei)"
            )
        elif free is not None:
            self._lbl_enc_slots.setText(f"{int(free)} Plätze frei")
        else:
            self._lbl_enc_slots.setText("—")

        cleanliness = data.get("cleanliness")
        value = 0.0 if cleanliness is None else float(cleanliness)
        self._clean_bar.setValue(int(value))
        self._clean_bar.setStyleSheet(
            self._bar_qss(self._grade(value, CLEAN_WARN, CLEAN_CRITICAL))
        )

        self._placeholder.setVisible(False)
        self._animal_box.setVisible(False)
        self._enclosure_box.setVisible(True)

    def clear(self) -> None:
        """Hide both forms and show the placeholder text.

        Returns:
            None.

        Tests:
            - test_clear_hides_forms: Show an animal, call clear(); verify
              both forms are hidden.
            - test_clear_shows_placeholder: Call clear(); verify the
              placeholder label is visible.
        """
        self._placeholder.setVisible(True)
        self._animal_box.setVisible(False)
        self._enclosure_box.setVisible(False)
