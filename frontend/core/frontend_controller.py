"""
FrontendController — thin bridge between the PyQt6 UI and the backend
SimulationEngine.

Provides dependency injection: the UI never imports backend.* directly.
The controller receives an engine instance at construction and exposes
methods that the ZooMainWindow uses for polling state, dispatching
God-mode actions, and draining chat messages.

The controller gracefully degrades when no engine is connected
(standalone UI testing mode) by returning empty/error payloads.

Tests:
    - test_returns_empty_dict_when_engine_is_none: Create
      FrontendController(None); verify get_state() returns {}.
    - test_delegates_to_engine_correctly: Mock an engine with a known
      state dict; verify get_state() returns the mock data.
    - test_get_chat_drains_messages: Mock engine that returns 2 messages
      then []; verify first call returns 2, second returns 0.
"""

from __future__ import annotations

from typing import Any


class FrontendController:
    """Translates UI signals into SimulationEngine method calls.

    Tests:
        - test_returns_empty_dict_when_engine_is_none: Create
          FrontendController(None); verify get_state() returns {}.
        - test_delegates_to_engine_correctly: Mock an engine with a known
          state dict; verify get_state() returns the mock data.
    """
    def __init__(self, engine: Any = None) -> None:
        """Wrap a SimulationEngine instance.

        Args:
            engine: A backend.core.engine.SimulationEngine instance,
                or None for headless / standalone UI testing.
        """
        self._engine = engine
        self._paused = False

    # ── Engine control ───────────────────────────────────────────────────

    def advance_tick(self) -> None:
        """Advance one simulation step.

        Calls engine.tick() if an engine is connected and not paused.
        If the backend uses its own internal timer thread
        (engine.start()), this method is a no-op — the frontend
        purely polls.

        Tests:
            - test_advance_tick_none_engine_does_not_crash: Call with
              no engine; verify no exception.
        """
        if self._engine is not None and not self._paused:
            try:
                self._engine.tick()
            except AttributeError:
                pass  # engine may not have a manual tick() method

    @property
    def paused(self) -> bool:
        """Return whether the simulation is paused.

        Tests:
            - test_initial_paused_is_false: Verify a newly constructed
              controller has paused == False.
            - test_toggle_pause_flips_state: Call toggle_pause twice;
              verify paused goes True → False.
        """
        return self._paused

    def toggle_pause(self) -> bool:
        """Toggle the pause state and return the new value.

        Tests:
            - test_toggle_pause_flips_state: Call twice; verify
              initial is False, then True, then False.
        """
        self._paused = not self._paused
        return self._paused

    # ── State polling (read-only) ────────────────────────────────────────

    def get_state(self) -> dict:
        """Return the full game-state snapshot from the engine.

        Returns:
            The dict from engine.get_game_state(), or an empty dict
            if no engine is connected.

        Tests:
            - test_get_state_returns_empty_when_none: Engine is None;
              verify {} returned.
            - test_get_state_delegates: Mock engine.get_game_state()
              returns {"system": {}}; verify same dict returned.
        """
        if self._engine is None:
            return {}
        try:
            return self._engine.get_game_state()
        except AttributeError:
            return {}

    def get_entity_info(self, entity_id: str) -> dict | None:
        """Return detailed hover info for one animal.

        Args:
            entity_id: Backend entity id (e.g. "a_01").

        Returns:
            A dict with name, species, hp, hunger, welfare, etc.,
            or None if the engine is unavailable.

        Tests:
            - test_get_entity_info_returns_none_for_none_engine: Engine is
              None; verify None returned.
            - test_get_entity_info_returns_empty_dict_for_unknown_id: Mock
              engine returns {} for unknown id; verify {} returned.
        """
        if self._engine is None:
            return None
        try:
            return self._engine.get_entity_info(entity_id)
        except AttributeError:
            return None

    def get_chat_messages(self) -> list[dict]:
        """Drain the backend message queue.

        Returns:
            A list of dicts with keys "time", "type", "text".
            Empty list if no engine or no new messages.

        Tests:
            - test_get_chat_returns_empty_for_none_engine: Verify [].
            - test_get_chat_drains_queue: Mock engine returns 2 messages
              on first call, then 0 on second; verify correct counts.
        """
        if self._engine is None:
            return []
        try:
            return self._engine.get_chat_messages()
        except AttributeError:
            return []

    # ── God-mode actions (write) ─────────────────────────────────────────

    def execute_action(self, action: str, **kwargs: object) -> dict:
        """Execute a God-mode action on the backend.

        Args:
            action: Action name (e.g. "feed_all", "buy_food", "heal").
            **kwargs: Action-specific parameters (e.g. animal_id,
                food_type, amount, species, enclosure_id, price).

        Returns:
            A dict with keys "success", "message", "chat_entries".
            On error or missing engine, returns a failure dict.

        Tests:
            - test_execute_action_returns_failure_for_none_engine:
              Verify success=False when engine is None.
            - test_execute_action_forwards_kwargs: Mock engine; call
              execute_action("buy_food", food_type="MEAT", amount=5);
              verify engine.execute_action called with correct kwargs.
        """
        if self._engine is None:
            return {
                "success": False,
                "message": "Keine Verbindung zur Simulations-Engine.",
                "chat_entries": [],
            }
        try:
            return self._engine.execute_action(action, **kwargs)
        except AttributeError:
            return {
                "success": False,
                "message": f"Unbekannte Aktion: {action}",
                "chat_entries": [],
            }
        except Exception:
            return {
                "success": False,
                "message": f"Fehler bei Aktion '{action}'.",
                "chat_entries": [],
            }