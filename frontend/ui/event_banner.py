"""EventBanner — stub for Phase 1. Always hidden. Phase 2+ will show seasonal events.

Tests:
    - test_banner_hidden_by_default: Create EventBanner; verify isVisible() is False.
    - test_show_event_sets_text_and_visible: Call show_event("Lichterfest", 5);
      verify label text contains "Lichterfest" and banner is visible.
    - test_hide_event_makes_invisible: Call show_event then hide_event;
      verify isVisible() returns False.
"""

from PyQt6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget


class EventBanner(QFrame):
    """Frame displayed at the bottom of the right column during special events.

    Phase 1: permanently hidden.
    Phase 2+: shows event name and remaining days with gold border.

    Tests:
        - test_banner_starts_hidden: Verify isVisible() is False after init.
        - test_show_event_populates_label: Call show_event("Test", 3); verify
          label shows "Test" and "3 Tage".
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setVisible(False)  # hidden in Phase 1
        layout = QVBoxLayout(self)
        self._label = QLabel("")
        layout.addWidget(self._label)

    def show_event(self, name: str, days_remaining: int) -> None:
        """Display an event banner. (Phase 2+)

        Args:
            name: Event name (e.g. "Lichterfest").
            days_remaining: Days left in the event.

        Tests:
            - test_show_event_makes_visible: Call show_event; verify banner
              becomes visible and label contains the event name.
            - test_show_event_updates_days: Call show_event("A", 7); verify
              label shows all information correctly.
        """
        self._label.setText(f"🎉 {name} — noch {days_remaining} Tage!")
        self.setVisible(True)

    def hide_event(self) -> None:
        """Hide the banner.

        Tests:
            - test_hide_event_makes_invisible: Show an event then call
              hide_event; verify banner is no longer visible.
        """
        self.setVisible(False)