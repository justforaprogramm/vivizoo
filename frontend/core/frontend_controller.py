"""
FrontendController — thin bridge between the PyQt6 UI and the backend
SimulationEngine.

Provides dependency injection: the UI never imports ``backend.*`` directly.
The controller receives an engine instance at construction and exposes
methods that the ZooMainWindow uses for polling state, dispatching
God-mode actions, and draining chat messages.

Besides plain delegation the controller performs the *marshalling* the UI
needs, because the backend snapshot is deliberately lean:

* ``animals_on_map`` carries no ``name`` — the controller resolves each
  name once via ``engine.get_entity_info(id)`` and caches it.
* the snapshot carries no enclosure list — the controller assembles
  ``enclosures_on_map`` from the static map geometry in ``constants`` plus
  the live ``cleanliness`` / ``free_slots`` the backend reports per
  enclosure id.

Pacing note: the engine also offers ``start()`` / ``pause()`` /
``set_speed()`` for its own background thread. The frontend deliberately
does **not** use that thread — it drives ``tick()`` from the Qt timer so
rendering and simulation stay in step. Pause and speed are therefore
frontend-side gates over ``tick()``; see IMPLEMENTATION_PLAN §2.7.

The controller gracefully degrades when no engine is connected
(standalone UI testing mode) by returning empty/error payloads.

Tests:
    - test_returns_empty_dict_when_engine_is_none: Create
      FrontendController(None); verify get_state() returns {}.
    - test_delegates_to_engine_correctly: Mock an engine with a known
      state dict; verify get_state() returns the mock data.
    - test_get_chat_drains_messages: Mock engine that returns 2 messages
      then []; verify first call returns 2, second returns 0.

Module owner: Erik (frontend).
"""

from __future__ import annotations

from typing import Any

from frontend.core.constants import ENCLOSURE_DEFS, SPEED_STEPS


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

        Returns:
            None (constructor).

        Tests:
            - test_accepts_none_engine: Construct with None; verify no
              exception and paused == False.
            - test_stores_engine: Construct with a mock; verify get_state()
              delegates to that mock.
        """
        self._engine = engine
        self._paused = False
        self._speed = 1.0
        self._tick_budget = 0.0
        self._name_cache: dict[str, str] = {}
        self._pending_chat: list[dict] = []

    # ── Engine control ───────────────────────────────────────────────────

    def advance_tick(self) -> int:
        """Advance the simulation by the number of ticks the speed allows.

        Called once per Qt timer frame. At speed 1.0 exactly one tick is
        computed; at 2.0 two ticks; at 0.5 one tick every second frame
        (a fractional budget is carried over between frames).

        Args:
            None.

        Returns:
            int: How many ticks were actually computed this frame.

        Tests:
            - test_advance_tick_none_engine_does_not_crash: Call with no
              engine; verify it returns 0 and raises nothing.
            - test_speed_two_ticks_twice: Set speed 2.0, call once; verify
              engine.tick() was called twice.
            - test_half_speed_ticks_every_second_frame: Set speed 0.5, call
              twice; verify engine.tick() was called exactly once.
        """
        if self._engine is None or self._paused:
            return 0

        if not hasattr(self._engine, "tick"):
            return 0  # engine without a manual step — nothing to drive

        self._tick_budget += self._speed
        steps = int(self._tick_budget)
        self._tick_budget -= steps

        for _ in range(steps):
            self._engine.tick()
            # Drain after every step, not once per frame: the backend closes
            # a day inside tick() and its persistence gateway drains the very
            # same logger, so at speed >= 2 messages from earlier steps of
            # this frame would be swallowed before the UI ever sees them.
            self._pending_chat.extend(self._drain_engine_chat())
        return steps

    @property
    def paused(self) -> bool:
        """Return whether the simulation is paused.

        Returns:
            bool: True while the tick loop is gated off.

        Tests:
            - test_initial_paused_is_false: Verify a newly constructed
              controller has paused == False.
            - test_property_follows_toggle: Call toggle_pause twice;
              verify paused goes True then False.
        """
        return self._paused

    def toggle_pause(self) -> bool:
        """Toggle the pause state and return the new value.

        Returns:
            bool: True if the simulation is now paused.

        Tests:
            - test_toggle_pause_flips_state: Call twice; verify the result
              is True, then False.
            - test_paused_blocks_ticks: Pause, call advance_tick(); verify
              it returns 0 and engine.tick() was not called.
        """
        self._paused = not self._paused
        return self._paused

    @property
    def speed(self) -> float:
        """Return the current speed multiplier.

        Returns:
            float: One of SPEED_STEPS, 1.0 by default.

        Tests:
            - test_default_speed_is_one: Verify a new controller reports 1.0.
            - test_cycle_speed_changes_value: Call cycle_speed(); verify the
              speed property no longer equals 1.0.
        """
        return self._speed

    def cycle_speed(self) -> float:
        """Advance to the next speed multiplier in SPEED_STEPS and return it.

        Returns:
            float: The newly selected multiplier.

        Tests:
            - test_cycle_wraps_around: Call len(SPEED_STEPS) times; verify
              the speed is back at SPEED_STEPS[0].
            - test_cycle_returns_new_value: Call once; verify the return
              value equals SPEED_STEPS[1].
        """
        try:
            idx = SPEED_STEPS.index(self._speed)
        except ValueError:
            idx = 0
        self._speed = SPEED_STEPS[(idx + 1) % len(SPEED_STEPS)]
        return self._speed

    # ── State polling (read-only) ────────────────────────────────────────

    def get_state(self) -> dict:
        """Return the game-state snapshot, enriched for the UI.

        On top of the raw backend payload this adds:

        * ``name`` on every entry of ``animals_on_map`` (resolved once per
          animal id via get_entity_info and cached).
        * ``enclosures_on_map``: one dict per entry in ENCLOSURE_DEFS with
          the static geometry plus the live ``cleanliness``, ``free_slots``
          and derived ``occupied`` reported by the backend.

        Returns:
            dict: The enriched snapshot, or an empty dict when no engine
            is connected.

        Tests:
            - test_get_state_returns_empty_when_none: Engine is None;
              verify {} is returned.
            - test_animals_get_names: Mock an engine whose animals_on_map
              lacks "name"; verify every animal in the result has one.
            - test_enclosures_on_map_added: Verify the result contains one
              enclosures_on_map entry per ENCLOSURE_DEFS entry.
        """
        if self._engine is None:
            return {}
        try:
            state = self._engine.get_game_state()
        except AttributeError:
            return {}
        if not isinstance(state, dict):
            return {}

        self._attach_animal_names(state)
        state["enclosures_on_map"] = self._collect_enclosures()
        return state

    def get_entity_info(self, entity_id: str) -> dict | None:
        """Return detailed hover info for one animal or enclosure.

        Args:
            entity_id: Backend entity id (e.g. "a_01" or "e_01").

        Returns:
            dict | None: For an animal: name, species, age_days, hp, hunger,
            welfare, is_dead, status_effects. For an enclosure: name, biome,
            cleanliness, free_slots. ``{}`` for an unknown id and ``None``
            when the engine is unavailable.

        Tests:
            - test_get_entity_info_returns_none_for_none_engine: Engine is
              None; verify None is returned.
            - test_get_entity_info_returns_empty_dict_for_unknown_id: Mock
              engine returns {} for an unknown id; verify {} is returned.
        """
        if self._engine is None:
            return None
        try:
            return self._engine.get_entity_info(entity_id)
        except AttributeError:
            return None

    def get_animal_details(self, state: dict | None = None) -> list[dict]:
        """Return the full hover payload of every animal on the map.

        The map snapshot only carries id, species, position and life state;
        the values a keeper actually needs — hp, hunger, welfare, status
        effects — live behind ``get_entity_info``. This method joins both so
        the animal roster can show one complete row per animal without the
        UI ever touching the engine itself.

        Args:
            state: An already-polled snapshot to reuse. When omitted a fresh
                one is fetched, which makes the method usable on its own.

        Returns:
            list[dict]: One merged dict per living or dead animal, sorted by
            display name. Empty when no engine is connected or the snapshot
            holds no animals.

        Tests:
            - test_empty_without_engine: Engine is None; verify [].
            - test_merges_map_and_hover_data: Mock an engine whose hover
              payload carries hp=80; verify the entry has both "x" (from the
              map) and "hp" (from the hover payload).
            - test_sorted_by_name: Mock three animals named C, A, B; verify
              the result order is A, B, C.
            - test_unknown_id_keeps_map_entry: Mock get_entity_info returning
              {}; verify the animal still appears, with its id as the name.
        """
        if self._engine is None:
            return []
        snapshot = self.get_state() if state is None else state
        details: list[dict] = []
        for animal in snapshot.get("animals_on_map") or []:
            animal_id = str(animal.get("id", ""))
            info = self.get_entity_info(animal_id) or {}
            merged = {**animal, **info}
            merged.setdefault("name", self.get_animal_name(animal_id))
            details.append(merged)
        return sorted(details, key=lambda entry: str(entry.get("name", "")))

    def get_animal_name(self, animal_id: str) -> str:
        """Return an animal's display name, resolving and caching it once.

        The map snapshot carries no names, so the name is fetched from the
        hover payload the first time an animal id is seen.

        Args:
            animal_id: Backend animal id (e.g. "a_01").

        Returns:
            str: The animal's name, or the raw id when it cannot be
            resolved.

        Tests:
            - test_name_is_cached: Call twice for the same id; verify
              engine.get_entity_info was called only once.
            - test_unknown_id_falls_back_to_id: Mock engine returns {};
              verify the id itself is returned.
        """
        cached = self._name_cache.get(animal_id)
        if cached is not None:
            return cached
        info = self.get_entity_info(animal_id) or {}
        name = str(info.get("name") or animal_id)
        self._name_cache[animal_id] = name
        return name

    def get_chat_messages(self) -> list[dict]:
        """Drain the backend message queue.

        Returns:
            list[dict]: Entries with keys "tick_count", "type", "text" and
            optionally "entity_id" / "details". Empty when no engine is
            connected or no new messages exist.

        Tests:
            - test_get_chat_returns_empty_for_none_engine: Verify [].
            - test_get_chat_drains_queue: Mock engine returns 2 messages on
              the first call and 0 on the second; verify both counts.
        """
        buffered, self._pending_chat = self._pending_chat, []
        return buffered + self._drain_engine_chat()

    def _drain_engine_chat(self) -> list[dict]:
        """Read and clear the engine's message queue once.

        Returns:
            list[dict]: The pending entries, or [] when unavailable.

        Tests:
            - test_returns_empty_without_engine: Engine is None; verify [].
            - test_drains_once: Mock engine returning 2 entries then 0;
              verify the second call yields an empty list.
        """
        if self._engine is None:
            return []
        try:
            return list(self._engine.get_chat_messages())
        except AttributeError:
            return []

    def get_stats(self, days_back: int = 30) -> list[dict]:
        """Return recent day-end summaries for the statistics panel.

        The backend only records these when a persistence gateway is
        attached; without one it returns an empty list.

        Args:
            days_back: How many finished days to read, newest last.

        Returns:
            list[dict]: Entries with day_id, total_visitors, revenue,
            expenses, profit_loss, avg_animal_welfare, avg_happiness,
            reputation_end_of_day and animals_died. Empty when unavailable.

        Tests:
            - test_stats_empty_without_engine: Engine is None; verify [].
            - test_stats_empty_without_persistence: Engine without a
              gateway; verify [] and no exception.
            - test_stats_delegates_days_back: Mock engine; call with 7;
              verify get_stats(7) was called.
        """
        if self._engine is None:
            return []
        try:
            return list(self._engine.get_stats(days_back))
        except (AttributeError, TypeError):
            return []

    # ── God-mode actions (write) ─────────────────────────────────────────

    def execute_action(self, action: str, **kwargs: object) -> dict:
        """Execute a God-mode action on the backend.

        Args:
            action: One of "feed_all", "feed_one", "heal", "buy_food",
                "buy_animal", "clean".
            **kwargs: Action-specific parameters (animal_id, type, amount,
                species, name, enclosure_id).

        Returns:
            dict: With keys "success", "message", "chat_entries". On error
            or missing engine a failure dict is returned instead.

        Tests:
            - test_execute_action_returns_failure_for_none_engine: Verify
              success is False when the engine is None.
            - test_execute_action_forwards_kwargs: Mock engine; call
              execute_action("buy_food", type="MEAT", amount=5); verify the
              engine received exactly those kwargs.
            - test_unknown_action_returns_failure: Backend raises
              ValueError; verify a failure dict instead of a crash.
        """
        if self._engine is None:
            return {
                "success": False,
                "message": "Keine Verbindung zur Simulations-Engine.",
                "chat_entries": [],
            }
        if not hasattr(self._engine, "execute_action"):
            return {
                "success": False,
                "message": "Engine unterstützt keine Aktionen.",
                "chat_entries": [],
            }
        try:
            result = self._engine.execute_action(action, **kwargs)
        except ValueError as exc:
            return {
                "success": False,
                "message": f"Aktion '{action}' abgelehnt: {exc}",
                "chat_entries": [],
            }
        except Exception as exc:  # pylint: disable=broad-exception-caught
            # Surface the backend's own error text instead of swallowing it —
            # a silent generic failure is impossible to diagnose during
            # integration (see CHANGELOG: buy_animal is currently broken in
            # backend.core.action_handler).
            return {
                "success": False,
                "message": f"Backend-Fehler bei '{action}': {exc}",
                "chat_entries": [],
            }

        return result

    # ── Internal marshalling helpers ─────────────────────────────────────

    def _attach_animal_names(self, state: dict) -> None:
        """Add a cached ``name`` to every animal in the snapshot in place.

        Args:
            state: The raw snapshot dict from engine.get_game_state().

        Returns:
            None.
        
        Tests:
            - test_adds_missing_names: Pass a snapshot whose animals carry no
              "name"; verify each one has a resolved name afterwards.
            - test_keeps_existing_names: Pass an animal that already has a name;
              verify it is left untouched.
            - test_prunes_cache_for_gone_animals: Resolve a name, then pass a
              snapshot without that animal; verify the cache entry is dropped.
        """
        animals = state.get("animals_on_map") or []
        live_ids = set()
        for animal in animals:
            animal_id = animal.get("id", "")
            live_ids.add(animal_id)
            if not animal.get("name"):
                animal["name"] = self.get_animal_name(animal_id)
        for gone in set(self._name_cache) - live_ids:
            del self._name_cache[gone]

    def _collect_enclosures(self) -> list[dict]:
        """Merge the static map geometry with live backend enclosure data.

        Returns:
            list[dict]: One entry per ENCLOSURE_DEFS entry with the keys
            id, name, biome, x, y, w, h, capacity, cleanliness, free_slots
            and occupied. ``cleanliness`` is None when the backend does not
            know the id.
        
        Tests:
            - test_one_entry_per_definition: Verify the result length equals
              len(ENCLOSURE_DEFS).
            - test_occupied_derived_from_free_slots: Mock free_slots=2 for a
              capacity of 5; verify occupied is 3.
            - test_unknown_id_keeps_static_values: Mock an engine that returns {};
              verify cleanliness is None and the static name survives.
        """
        result: list[dict] = []
        for edef in ENCLOSURE_DEFS:
            info = self.get_entity_info(edef["id"]) or {}
            capacity = int(edef["capacity"])
            free = info.get("free_slots")
            occupied = 0 if free is None else max(0, capacity - int(free))
            result.append(
                {
                    **edef,
                    "name": info.get("name", edef["name"]),
                    "biome": info.get("biome", edef["biome"]),
                    "cleanliness": info.get("cleanliness"),
                    "free_slots": free,
                    "occupied": occupied,
                }
            )
        return result
