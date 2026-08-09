"""
AnimalListPanel — the zoo's roster as a sortable, filterable table.

This panel exists for a concrete reason. ``backend.core.zoo.add_animal()``
places every animal on the same fixed coordinate and the snapshot exposes no
enclosure membership, so all four demo animals stand on exactly the same
spot until they wander apart. Picking one of them with the mouse is a matter
of luck, and the two selection-bound actions ("Ausgewähltes füttern", "Tier
heilen") are only as usable as the selection is reliable.

The roster gives every animal an unambiguous, always-hittable row. Clicking
one selects that animal exactly like clicking its sprite does, and the table
doubles as a keeper's overview:

* **Sortieren** — a click on "Hunger" orders the zoo by urgency. Numeric
  columns use :class:`~frontend.ui.numeric_table_item.NumericTableItem`, so
  9 sorts before 100 instead of after it.
* **Filtern** — "Braucht Aufmerksamkeit" hides every animal that is fine,
  which is the whole list on a good day and exactly the interesting rows on
  a bad one.
* **Lesbar ohne Farbe** — a low value is not only red but also marked
  ``!`` / ``!!``. Roughly one man in twelve cannot tell the red cells from
  the green ones.

Everything shown here comes from ``FrontendController.get_animal_details()``,
which merges the map snapshot with the backend's own hover payload. No value
is invented, and no backend change was needed.

Rows are updated in place rather than rebuilt: recreating them would drop
the user's selection, reset the sort order and make the scroll position
jump. Each row carries its animal id in ``Qt.ItemDataRole.UserRole``, so a
re-sorted table still knows which row is which animal.

Tests:
    - test_row_per_animal: Refresh with three animals; verify the table has
      three rows.
    - test_click_emits_animal_id: Click the second row; verify
      animal_selected carried that animal's id.
    - test_selection_survives_refresh: Select a row, refresh with the same
      animals; verify the row is still selected.
    - test_sorting_is_numeric: Sort by HP with values 9 and 100; verify 9
      comes first.

Module owner: Erik (frontend).
"""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QWidget,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor

from frontend.core.constants import (
    C_ACCENT,
    C_GOLD,
    C_RED,
    C_TEXT,
    C_TEXT_DIM,
    ROSTER_COLUMNS,
    ROSTER_FILTERS,
    SPECIES_LABELS,
    VALUE_CRITICAL,
    VALUE_MARKERS,
    VALUE_WARN,
)
from frontend.ui.numeric_table_item import NumericTableItem
from frontend.ui.styled_widgets import panel_layout

_ID_ROLE = Qt.ItemDataRole.UserRole


# too-few-public-methods is a knock-on effect of ignored-modules=PyQt6 (see
# .pylintrc): without a resolvable Qt base, pylint counts only refresh()
# instead of the inherited QWidget methods.
# pylint: disable-next=too-few-public-methods
class AnimalListPanel(QWidget):
    """Sortable overview of every animal, with click-to-select.

    Emits ``animal_selected(animal_id)``; the main window treats it exactly
    like a click on the animal's sprite, so both paths end in the same
    selection state.

    Tests:
        - test_dead_animal_row_is_red: Refresh with a dead animal; verify its
          name cell uses the red colour.
        - test_empty_list_shows_hint: Refresh with []; verify the hint is
          visible and the table hidden.
    """

    animal_selected = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        """Build the header row, the filter, the hint and the roster table.

        Args:
            parent: Optional parent widget.

        Returns:
            None (constructor).

        Tests:
            - test_column_count_matches_constant: Verify the table has one
              column per ROSTER_COLUMNS entry.
            - test_table_is_read_only: Verify no edit triggers are enabled so
              a double click cannot start editing a cell.
            - test_sorting_is_enabled: Verify the header is clickable for
              sorting right after construction.
        """
        super().__init__(parent)
        layout = panel_layout(self, spacing=6)

        header_row = QHBoxLayout()
        header_row.setSpacing(6)

        header = QLabel("🐾 Tierbestand")
        header.setStyleSheet(
            f"color: {C_TEXT}; font-size: 13px; font-weight: bold; padding: 2px 0;"
        )
        header_row.addWidget(header)
        header_row.addStretch()

        self._filter_combo = QComboBox()
        self._filter_combo.addItems(list(ROSTER_FILTERS))
        self._filter_combo.setAccessibleName("Filter für die Tierliste")
        self._filter_combo.setToolTip(
            "„Braucht Aufmerksamkeit“ zeigt nur Tiere mit niedriger HP, "
            "hohem Hunger oder schlechtem Wohlbefinden."
        )
        self._filter_combo.setStyleSheet(
            f"QComboBox {{ border: 1px solid {C_TEXT_DIM}; padding: 1px 6px;"
            f" font-size: 10px; font-weight: normal; }}"
        )
        self._filter_combo.currentIndexChanged.connect(self._apply_filter)
        header_row.addWidget(self._filter_combo)

        layout.addLayout(header_row)

        self._hint = QLabel(
            "Keine Tiere im Zoo.\nIm Shop-Tab lassen sich neue Tiere kaufen."
        )
        self._hint.setWordWrap(True)
        self._hint.setStyleSheet(f"color: {C_TEXT_DIM}; font-size: 11px;")
        layout.addWidget(self._hint)

        self._table = QTableWidget(0, len(ROSTER_COLUMNS))
        self._table.setHorizontalHeaderLabels(list(ROSTER_COLUMNS))
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table.setMinimumHeight(120)
        self._table.setVisible(False)
        self._table.setSortingEnabled(True)
        self._table.setAccessibleName("Tierbestand")
        self._table.setAccessibleDescription(
            "Eine Zeile je Tier mit HP, Hunger und Wohlbefinden. "
            "Zeile anklicken wählt das Tier aus."
        )
        head = self._table.horizontalHeader()
        if head is not None:
            head.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
            head.setSortIndicatorShown(True)
            head.setToolTip("Spaltenkopf anklicken sortiert die Liste.")
        self._table.sortByColumn(0, Qt.SortOrder.AscendingOrder)
        self._table.cellClicked.connect(self._on_cell_clicked)
        layout.addWidget(self._table, stretch=1)

        self._legend = QLabel(
            "Zeile anklicken wählt das Tier aus — dieselbe Auswahl wie ein "
            "Klick auf die Karte. Hunger: 0 = satt, 100 = verhungernd. "
            "„!“ = auffällig, „!!“ = kritisch."
        )
        self._legend.setWordWrap(True)
        self._legend.setStyleSheet(f"color: {C_TEXT_DIM}; font-size: 10px;")
        layout.addWidget(self._legend)

        self._row_ids: list[str] = []

    # ── Public interface ──────────────────────────────────────────────────

    def refresh(self, animals: list[dict], selected_id: str | None = None) -> None:
        """Update every row from the merged animal payloads.

        Args:
            animals: The list from
                ``FrontendController.get_animal_details()`` — each entry
                carries id, name, species, hp, hunger, welfare and is_dead.
            selected_id: The animal currently pinned by the window, so the
                table can mirror a selection made on the map.

        Returns:
            None.

        Tests:
            - test_rows_match_input_length: Refresh with four animals; verify
              four rows.
            - test_values_are_rounded: Refresh with hp=81.7; verify the cell
              reads "82".
            - test_mirrors_map_selection: Refresh with selected_id set to the
              second animal; verify that row is the selected one.
            - test_shrinking_list_removes_rows: Refresh with three, then two
              animals; verify the table has two rows.
            - test_sort_order_survives_a_value_update: Sort by HP, refresh
              with changed values; verify the rows did not jump.
        """
        if not animals:
            self._row_ids = []
            self._table.setRowCount(0)
            self._table.setVisible(False)
            self._hint.setVisible(True)
            return

        self._hint.setVisible(False)
        self._table.setVisible(True)

        ids = [str(a.get("id", "")) for a in animals]
        if sorted(ids) != sorted(self._row_ids):
            self._rebuild(animals)
        else:
            rows = self._rows_by_id()
            for animal in animals:
                row = rows.get(str(animal.get("id", "")))
                if row is not None:
                    self._fill_row(row, animal)
        self._row_ids = ids

        self._apply_filter()
        self._apply_selection(selected_id)

    # ── Internal helpers ──────────────────────────────────────────────────

    def _rebuild(self, animals: list[dict]) -> None:
        """Recreate every row, keeping the active sort order.

        Sorting is switched off while the rows are written: with it on, Qt
        re-sorts after every single ``setItem`` and the half-filled rows end
        up interleaved.

        Args:
            animals: The animal payloads to write.

        Returns:
            None.

        Tests:
            - test_row_count_matches: Rebuild with three animals; verify
              three rows.
            - test_sorting_is_restored: Rebuild while sorting is on; verify
              the table still sorts afterwards.
        """
        self._table.setSortingEnabled(False)
        self._table.setRowCount(len(animals))
        for row, animal in enumerate(animals):
            self._fill_row(row, animal)
        self._table.setSortingEnabled(True)

    def _rows_by_id(self) -> dict[str, int]:
        """Map each animal id to the row it currently occupies.

        The row index changes whenever the user sorts, so it cannot be
        cached — it is read back from the cells that carry the id.

        Returns:
            dict[str, int]: One entry per row with a readable id.

        Tests:
            - test_maps_every_row: Fill three rows; verify the map has three
              entries.
            - test_reflects_sort_order: Sort descending, call it; verify the
              first animal is no longer at row 0.
        """
        rows: dict[str, int] = {}
        for row in range(self._table.rowCount()):
            item = self._table.item(row, 0)
            if item is not None:
                animal_id = item.data(_ID_ROLE)
                if animal_id:
                    rows[str(animal_id)] = row
        return rows

    def _fill_row(self, row: int, animal: dict) -> None:
        """Write one animal into the given table row.

        Args:
            row: Zero-based row index.
            animal: One merged animal payload.

        Returns:
            None.

        Tests:
            - test_species_is_translated: Pass species "lion"; verify the
              cell reads "Löwe".
            - test_dead_animal_is_marked: Pass is_dead=True; verify the name
              cell carries the cross marker and the red colour.
            - test_id_is_stored_on_the_row: Fill a row; verify the name cell
              carries the animal id in its user role.
        """
        is_dead = bool(animal.get("is_dead"))
        species_key = str(animal.get("species", ""))
        animal_id = str(animal.get("id", ""))
        name = str(animal.get("name") or animal_id or "?")

        name_item = self._text_cell(row, 0)
        # The cross goes *after* the name: as a prefix it would sort every
        # dead animal to one end of the alphabet, which is not what a reader
        # clicking "Name" expects.
        name_item.setText(f"{name} ✝" if is_dead else name)
        name_item.setForeground(QColor(C_RED if is_dead else C_TEXT))
        name_item.setData(_ID_ROLE, animal_id)

        species_item = self._text_cell(row, 1)
        species_item.setText(
            SPECIES_LABELS.get(species_key, species_key.title() or "?")
        )
        species_item.setForeground(QColor(C_TEXT))

        hp = self._as_float(animal.get("hp"))
        hunger = self._as_float(animal.get("hunger"))
        welfare = self._as_float(animal.get("welfare"))

        self._value_cell(row, 2, hp, hp)
        # Hunger is inverted in the backend: 0 = full, 100 = starving. The
        # cell shows the raw value but is graded and sorted by urgency.
        self._value_cell(row, 3, hunger, 100.0 - hunger)
        self._value_cell(row, 4, welfare, welfare)

        tooltip = (
            f"{name} · {SPECIES_LABELS.get(species_key, species_key)}\n"
            f"HP {hp:.0f} · Hunger {hunger:.0f} · Wohlbefinden {welfare:.0f}"
            + ("\nverstorben" if is_dead else "")
        )
        for column in range(len(ROSTER_COLUMNS)):
            cell = self._table.item(row, column)
            if cell is not None:
                cell.setToolTip(tooltip)

    def _text_cell(self, row: int, column: int) -> QTableWidgetItem:
        """Return the plain cell at the position, creating it once.

        Args:
            row: Zero-based row index.
            column: Zero-based column index.

        Returns:
            QTableWidgetItem: The existing or freshly created cell.

        Tests:
            - test_creates_missing_cell: Call on an empty row; verify an item
              exists afterwards.
            - test_reuses_existing_cell: Call twice; verify the same object
              comes back so the selection survives.
        """
        item = self._table.item(row, column)
        if item is None:
            item = QTableWidgetItem()
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._table.setItem(row, column, item)
        return item

    def _value_cell(self, row: int, column: int, shown: float, graded: float) -> None:
        """Write a numeric cell with its marker, colour and sort value.

        Args:
            row: Zero-based row index.
            column: Zero-based column index.
            shown: The number the user reads.
            graded: The number the traffic-light grading uses — for hunger
                this is the inverted value, because a high hunger is bad.

        Returns:
            None.

        Tests:
            - test_critical_value_gets_double_marker: Pass graded=10; verify
              the text starts with "!!".
            - test_sorting_uses_the_shown_number: Pass shown=9 and 100;
              verify the cell for 9 sorts first despite the marker.
        """
        colour, marker = self._grade(graded)
        item = self._table.item(row, column)
        text = f"{marker}{shown:.0f}"
        if isinstance(item, NumericTableItem):
            item.set_value(text, shown)
        else:
            item = NumericTableItem(text, shown)
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._table.setItem(row, column, item)
        item.setForeground(QColor(colour))

    def _apply_filter(self) -> None:
        """Hide the rows the active filter is not interested in.

        Returns:
            None.

        Tests:
            - test_all_filter_shows_everything: With filter 0 active; verify
              no row is hidden.
            - test_attention_filter_hides_healthy_animals: With the attention
              filter active and one healthy animal; verify its row is hidden.
        """
        attention_only = self._filter_combo.currentIndex() == 1
        for row in range(self._table.rowCount()):
            self._table.setRowHidden(
                row, attention_only and not self._row_needs_attention(row)
            )

    def _row_needs_attention(self, row: int) -> bool:
        """Return whether one row carries at least one graded warning.

        The marker written by :meth:`_value_cell` is the single source of
        this decision — what the user sees and what the filter acts on can
        therefore not disagree.

        Args:
            row: Zero-based row index.

        Returns:
            bool: True when any value cell is marked, or the animal is dead.

        Tests:
            - test_healthy_row_is_calm: Fill a row with 100/0/100; verify
              False.
            - test_starving_row_needs_attention: Fill a row with hunger 95;
              verify True.
            - test_dead_row_needs_attention: Fill a dead animal; verify True.
        """
        name_item = self._table.item(row, 0)
        if name_item is not None and name_item.text().endswith("✝"):
            return True
        for column in range(2, len(ROSTER_COLUMNS)):
            item = self._table.item(row, column)
            if item is not None and item.text().startswith("!"):
                return True
        return False

    def _apply_selection(self, selected_id: str | None) -> None:
        """Mirror the window's current selection in the table.

        Args:
            selected_id: The pinned animal id, or None to clear the
                highlight.

        Returns:
            None.

        Tests:
            - test_none_clears_selection: Select a row, call with None;
              verify no row is selected afterwards.
            - test_unknown_id_clears_selection: Call with an id that is not
              in the table; verify the selection is cleared instead of
              raising.
            - test_finds_the_row_after_sorting: Sort descending, then select
              the first animal; verify its actual row is highlighted.
        """
        row = None if selected_id is None else self._rows_by_id().get(selected_id)
        if row is None:
            self._table.clearSelection()
            return
        if self._table.currentRow() != row:
            self._table.selectRow(row)

    def _on_cell_clicked(self, row: int, _column: int) -> None:
        """Announce the animal in the clicked row.

        The id is read from the row itself, not from a cached index: after
        the user sorts a column, row 1 is a different animal than before.

        Args:
            row: The clicked row index.
            _column: The clicked column — unused, the whole row is one
                animal.

        Returns:
            None.

        Tests:
            - test_emits_row_id: Click row 1; verify the signal carried the
              second animal's id.
            - test_emits_the_right_id_after_sorting: Sort descending, click
              row 0; verify the id of the animal now shown there.
            - test_stale_row_is_ignored: Call with a row index beyond the
              table; verify no signal and no exception.
        """
        item = self._table.item(row, 0)
        if item is None:
            return
        animal_id = item.data(_ID_ROLE)
        if animal_id:
            self.animal_selected.emit(str(animal_id))

    @staticmethod
    def _as_float(value: object) -> float:
        """Convert a backend value to float, tolerating None and text.

        Args:
            value: The raw payload value.

        Returns:
            float: The parsed number, or 0.0 when it cannot be read.

        Tests:
            - test_parses_number: Pass 81.7; verify 81.7 is returned.
            - test_none_becomes_zero: Pass None; verify 0.0 instead of a
              TypeError.
        """
        try:
            return float(value)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _grade(value: float) -> tuple[str, str]:
        """Map a 0–100 value onto a colour **and** a text marker.

        Colour alone would exclude anyone who cannot distinguish red from
        green, so every warning is redundantly encoded.

        Args:
            value: The measured value, already inverted where the backend
                counts downwards (hunger).

        Returns:
            tuple[str, str]: The hex colour and the marker prefix — red and
            "!! " below VALUE_CRITICAL, gold and "! " below VALUE_WARN,
            green and "" otherwise.

        Tests:
            - test_high_value_is_green_and_unmarked: _grade(90) returns the
              accent colour and an empty marker.
            - test_critical_value_is_red_and_double_marked: _grade(10)
              returns the red colour and "!! ".
        """
        if value < VALUE_CRITICAL:
            return C_RED, VALUE_MARKERS["critical"]
        if value < VALUE_WARN:
            return C_GOLD, VALUE_MARKERS["warn"]
        return C_ACCENT, VALUE_MARKERS["ok"]
