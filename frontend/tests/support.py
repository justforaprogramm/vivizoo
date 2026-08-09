"""
Shared test scaffolding: the QApplication singleton and a fake engine.

Two preconditions from ``docs/test_plan.md`` §4 are implemented here:

1. **Exactly one QApplication per test run.** Qt widgets cannot be built
   without one, and a second instance crashes the process. :func:`app`
   returns the existing one or creates it.
2. **No real backend.** The controller takes its engine by injection, so the
   tests hand it a :class:`FakeEngine` that answers the documented contract
   from ``backend/docs/api.md`` and records what it was asked to do.

``frontend/tests/__init__.py`` sets ``QT_QPA_PLATFORM=offscreen`` before this
module is imported, so the suite runs in a container without a display.

Module owner: Erik (frontend).
"""

from __future__ import annotations

from PyQt6.QtWidgets import QApplication

# The list is the point, not the container: a QApplication that only lives in
# a local variable is garbage-collected the moment the caller returns, and Qt
# then reports "Must construct a QApplication before a QWidget" on the next
# widget. Appending to a module-level list keeps the reference alive without a
# ``global`` statement.
_KEEP_ALIVE: list[QApplication] = []


def app() -> QApplication:
    """Return the process-wide QApplication, creating it on first use.

    Returns:
        QApplication: The singleton instance every widget test needs.
    """
    existing = QApplication.instance()
    if not isinstance(existing, QApplication):
        existing = QApplication([])
    if existing not in _KEEP_ALIVE:
        _KEEP_ALIVE.append(existing)
    return existing


class FakeEngine:
    """Stand-in for ``backend.core.engine.SimulationEngine``.

    Implements exactly the six methods the frontend contract names and
    records every call, so a test can assert what reached the backend
    without running the simulation.

    Attributes:
        calls: Every ``tick`` and ``(action, kwargs)`` in order.
    """

    def __init__(
        self,
        state: dict | None = None,
        info: dict | None = None,
        messages: list[dict] | None = None,
        stats: list[dict] | None = None,
    ) -> None:
        """Create a fake engine with canned answers.

        Args:
            state: What ``get_game_state()`` returns.
            info: Mapping of entity id to hover payload.
            messages: Entries handed out by the first ``get_chat_messages()``.
            stats: What ``get_stats()`` returns.
        """
        self.state = state if state is not None else EMPTY_STATE
        self.info = info or {}
        self.messages = list(messages or [])
        self.stats = list(stats or [])
        self.calls: list[object] = []
        self.info_queries: list[str] = []

    def tick(self) -> None:
        """Record one simulation step."""
        self.calls.append("tick")

    def get_game_state(self) -> dict:
        """Return a copy of the canned snapshot."""
        return {
            key: ([dict(item) for item in value] if isinstance(value, list)
                  else dict(value) if isinstance(value, dict) else value)
            for key, value in self.state.items()
        }

    def get_entity_info(self, entity_id: str) -> dict:
        """Return the canned hover payload for one id, or {}."""
        self.info_queries.append(entity_id)
        return dict(self.info.get(entity_id, {}))

    def get_chat_messages(self) -> list[dict]:
        """Hand out the pending messages once, draining the buffer."""
        pending, self.messages = self.messages, []
        return pending

    def get_stats(self, days_back: int = 30) -> list[dict]:
        """Return the canned day summaries."""
        self.calls.append(("get_stats", days_back))
        return list(self.stats)

    def execute_action(self, action: str, **kwargs: object) -> dict:
        """Record an action and report success."""
        self.calls.append((action, kwargs))
        return {"success": True, "message": f"ok:{action}", "chat_entries": []}


EMPTY_STATE: dict = {
    "system": {"tick_count": 0, "time_of_day": "MORNING", "zoo_open": True},
    "finances": {"money": 10000.0, "revenue": 0.0, "expenses": 0.0,
                 "ticket_price": 12.5},
    "inventory": {"MEAT": 0, "PLANTS": 0, "FISH": 0, "MEDICINE": 0},
    "animals_on_map": [],
    "visitors_on_map": [],
}


def state_with_animals(*animals: dict) -> dict:
    """Build a snapshot carrying the given animals.

    Args:
        *animals: Partial animal dicts; missing keys are filled with
            defaults so a test only states what it cares about.

    Returns:
        dict: A complete snapshot in the backend's documented shape.
    """
    filled = []
    for index, animal in enumerate(animals, start=1):
        entry = {
            "id": f"a_{index:02d}",
            "species": "lion",
            "x": 300.0,
            "y": 200.0,
            "is_dead": False,
        }
        entry.update(animal)
        filled.append(entry)
    snapshot = {key: (dict(value) if isinstance(value, dict) else list(value))
                for key, value in EMPTY_STATE.items()}
    snapshot["animals_on_map"] = filled
    return snapshot
