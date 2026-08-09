"""
NumericTableItem — a table cell that sorts by value instead of by text.

``QTableWidgetItem`` compares its display string, so clicking a column header
would order 100 before 9 and put a nearly dead animal above a healthy one.
This subclass keeps the number it was built from and overrides ``__lt__``, so
the roster sorts the way a keeper reads it.

The displayed text stays free-form: the roster prefixes critical values with
a marker (``"!! 12"``), which must not affect the ordering. Sorting therefore
uses the stored number, never the label.

Lives in its own module because the project rule is one class per file — see
``docs/IMPLEMENTATION_PLAN.md`` §0.

Tests:
    - test_sorts_by_value_not_text: Compare items for 9 and 100; verify the
      9 sorts first although "100" < "9" as text.
    - test_marker_does_not_affect_order: Compare "!! 12" (value 12) with
      "95" (value 95); verify the 12 still sorts first.

Module owner: Erik (frontend).
"""

from __future__ import annotations

from PyQt6.QtWidgets import QTableWidgetItem


class NumericTableItem(QTableWidgetItem):
    """Table cell that remembers its numeric value for sorting.

    Tests:
        - test_value_is_kept: Build with 81.7; verify the value property
          returns 81.7 regardless of the shown text.
        - test_comparison_with_plain_item_is_safe: Compare against a plain
          QTableWidgetItem; verify no exception and a defined result.
    """

    def __init__(self, text: str, value: float) -> None:
        """Create a cell showing ``text`` but ordering by ``value``.

        Args:
            text: What the user sees, marker prefix included.
            value: The number the ordering is based on.

        Returns:
            None (constructor).

        Tests:
            - test_text_is_displayed: Build with ("! 45", 45.0); verify the
              cell text is "! 45".
            - test_value_is_stored: Build with ("! 45", 45.0); verify the
              value property returns 45.0.
        """
        super().__init__(text)
        self._value = float(value)

    @property
    def value(self) -> float:
        """Return the number this cell sorts by.

        Returns:
            float: The value passed to the constructor.

        Tests:
            - test_returns_constructor_value: Build with 12.5; verify 12.5.
            - test_is_read_only: Verify the property exposes no setter.
        """
        return self._value

    def set_value(self, text: str, value: float) -> None:
        """Update both the shown text and the sorting value.

        Reusing the item instead of replacing it keeps the user's selection
        alive across the roster's periodic refresh.

        Args:
            text: The new display text.
            value: The new sorting value.

        Returns:
            None.

        Tests:
            - test_updates_text_and_value: Call with ("!! 5", 5.0); verify
              both the text and the value changed.
            - test_selection_survives_update: Select the cell, update it;
              verify it is still the selected item.
        """
        self.setText(text)
        self._value = float(value)

    def __lt__(self, other: QTableWidgetItem) -> bool:
        """Order by the stored number, falling back to Qt's text order.

        Args:
            other: The cell Qt is comparing this one against.

        Returns:
            bool: True when this cell sorts before ``other``.

        Tests:
            - test_numeric_order: Verify item(9) < item(100) is True.
            - test_falls_back_for_plain_items: Compare against a plain
              QTableWidgetItem; verify the text comparison is used instead
              of raising AttributeError.
        """
        if isinstance(other, NumericTableItem):
            return self._value < other.value
        return super().__lt__(other)
