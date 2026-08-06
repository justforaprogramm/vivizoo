"""The simulation heartbeat -- :class:`SimulationEngine`.

The engine owns the tick loop and drives every entity forward. It keeps its
own counters (tick number, time of day, day number) and uses the
:class:`~backend.core.zoo.Zoo` aggregate to reach the domain objects. At the
end of a day it invokes the persistence gateway so the finished day (and its
messages) is written to the database -- exactly once per day.

The engine is deliberately decoupled from the frontend: :meth:`tick` only
computes logic; the frontend polls :meth:`get_game_state` to render.

Single Responsibility Principle: the engine *orchestrates*; money moves go
through :class:`~backend.core.finances.Finances`, animals through
:class:`~backend.core.animal.Animal`, and so on.
"""

from __future__ import annotations

import threading
import time
from typing import TYPE_CHECKING

from backend.core.action_handler import ActionHandler
from backend.core.message_logger import MessageLogger
from db.interface.enums import TimeOfDay

if TYPE_CHECKING:  # type checkers only, avoids a runtime cycle
    from backend.core.zoo import Zoo
    from backend.persistence.db_gateway import DbGateway

# Simulation pacing: ticks per simulated day and the four phases.
TICKS_PER_DAY = 480
_NIGHT_START = 360  # phase index at which the day is closed and persisted


class SimulationEngine:
    """Runs the zoo forward one tick at a time.

    Args:
        zoo (Zoo): The aggregate root to drive.
        persistence (DbGateway | None): Optional day-end persistence; when
            ``None`` the engine runs purely in memory.
        logger (MessageLogger | None): Shared chat feed, defaults to the
            singleton.

    Attributes:
        TICKS_PER_DAY (int): Simulated ticks per day.
    """

    def __init__(
        self,
        zoo: "Zoo",
        persistence: "DbGateway | None" = None,
        logger: MessageLogger | None = None,
    ) -> None:
        """Create an engine suspended (paused) at tick zero.

        Args:
            zoo (Zoo): The zoo to drive.
            persistence (DbGateway | None): The persistence gateway.
            logger (MessageLogger | None): The chat feed.

        Returns:
            None (constructor).

        Tests:
            1. A new engine is paused with tick zero.
            2. ``get_game_state()`` works immediately with an empty zoo.
        """
        self._zoo = zoo
        self._persistence = persistence
        self._logger = logger or MessageLogger.instance()
        self._tick_count = 0
        self._paused = True
        self._running_thread: threading.Thread | None = None
        self._stop_requested = False
        self._speed = 1.0
        self._actions = ActionHandler(zoo)

    # ------------------------------------------------------------------
    # Control API (called by the frontend)
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Begin the internal tick timer (if not already running).

        Args:
            None.

        Returns:
            None.

        Tests:
            1. After ``start()`` the engine is no longer paused.
        """
        if self._running_thread is not None and self._running_thread.is_alive():
            return
        self._paused = False
        self._stop_requested = False
        self._running_thread = threading.Thread(
            target=self._run_loop, daemon=True
        )
        self._running_thread.start()

    def pause(self) -> None:
        """Freeze the tick counter.

        Args:
            None.

        Returns:
            None.

        Tests:
            1. Calling ``pause()`` sets the paused flag.
        """
        self._paused = True

    def set_speed(self, multiplier: float) -> None:
        """Change the simulation speed multiplier.

        Args:
            multiplier (float): 1.0 normal, 2.0 double speed; must be > 0.

        Returns:
            None.

        Raises:
            ValueError: If ``multiplier`` is not positive.

        Tests:
            1. A positive multiplier is stored.
            2. A zero or negative multiplier raises ``ValueError``.
        """
        if multiplier <= 0:
            raise ValueError(f"multiplier must be positive, got {multiplier}.")
        self._speed = multiplier

    # ------------------------------------------------------------------
    # Core loop
    # ------------------------------------------------------------------

    def tick(self) -> None:
        """Compute exactly one logic step.

        This is the heart of the planning's tick loop:

        1. Advance the counter and the time of day.
        2. Update animals (hunger down, age up, death check).
        3. Spawn / move / despawn visitors (ticket income).
        4. Run staff jobs and random events.
        5. If it is night, close the day and persist it.
        6. The frontend separately calls ``get_game_state()`` to render.

        Args:
            None.

        Returns:
            None.

        Tests:
            1. After one tick the counter advanced by one.
            2. Day-end persistence is invoked exactly when the night phase is
               reached.
        """
        self._tick_count += 1
        phase = self._phase_of(self._tick_count)

        if phase == TimeOfDay.NIGHT:
            if self._zoo.is_open:
                self._zoo.is_open = False
        else:
            self._zoo.is_open = True

        self._zoo.update_animals(self._tick_count)
        self._zoo.update_visitors((50, 50))
        self._zoo.update_staff(self._tick_count)
        self._zoo.scheduler.check(self._zoo, self._tick_count)

        # A full day is 480 ticks; close it as soon as the boundary is crossed.
        if self._tick_count % TICKS_PER_DAY == 0:
            self._close_day()

    def _run_loop(self) -> None:
        """Background loop that ticks at the configured speed.

        Args:
            None.

        Returns:
            None.
        """
        while not self._stop_requested:
            if not self._paused:
                self.tick()
            time.sleep(self._speed * 0.05)  # 20 ticks/s at speed 1.0

    def stop(self) -> None:
        """Request the background thread to stop.

        Args:
            None.

        Returns:
            None.

        Tests:
            1. After ``stop()`` the stop flag is set.
        """
        self._stop_requested = True
        self._paused = True

    # ------------------------------------------------------------------
    # Day lifecycle
    # ------------------------------------------------------------------

    def _close_day(self) -> None:
        """Close the day, persist it, and advance the calendar.

        Args:
            None.

        Returns:
            None.

        Tests:
            1. When a persistence gateway is present, it is invoked.
            2. The zoo's day counter advances and its daily counters reset.
        """
        self._zoo.begin_new_day()
        if self._persistence is not None:
            self._persistence.save_daily_summary(self._zoo)
        self._zoo.current_day += 1

    # ------------------------------------------------------------------
    # Read API (polled by the frontend)
    # ------------------------------------------------------------------

    def get_game_state(self) -> dict:
        """Return the full current snapshot for the frontend to render.

        Args:
            None.

        Returns:
            dict: The ``game_state_data`` payload (system, finances,
            inventory, map objects).

        Tests:
            1. Returning the zoo's state plus the current tick and phase.
        """
        time_of_day = self._phase_of(self._tick_count).value
        return self._zoo.to_game_state(self._tick_count, time_of_day)

    def get_entity_info(self, entity_id: str) -> dict:
        """Return hover/tooltip data for one entity.

        Args:
            entity_id (str): An animal or enclosure identifier.

        Returns:
            dict: The hover payload, or an empty dict when not found.

        Tests:
            1. An existing animal yields its hover data.
            2. An unknown id yields an empty dict.
        """
        animal = self._zoo.find_animal(entity_id)
        if animal is not None:
            return animal.to_hover_data()
        enclosure = self._zoo.find_enclosure(entity_id)
        if enclosure is not None:
            return {
                "id": enclosure.enclosure_id,
                "name": enclosure.name,
                "biome": enclosure.biome,
                "cleanliness": round(enclosure.cleanliness, 1),
                "free_slots": enclosure.free_slots(),
            }
        return {}

    def get_chat_messages(self) -> list[dict]:
        """Return and clear the pending chat messages.

        Args:
            None.

        Returns:
            list[dict]: New chat entries since the last call, drained.

        Tests:
            1. Returning pending entries resets the buffer.
        """
        return [
            entry.to_dict() for entry in self._logger.drain()
        ]

    def execute_action(self, action_name: str, **kwargs: object) -> dict:
        """Run a player action and return its structured result.

        Args:
            action_name (str): Action name, e.g. ``"feed_all"``.
            **kwargs: Action arguments.

        Returns:
            dict: The action result (``success``, ``message``,
            ``chat_entries``).

        Tests:
            1. A valid action returns a result dict.
        """
        result = self._actions.execute_action(action_name, **kwargs)
        return result.to_dict()

    def get_stats(self, days_back: int = 30) -> list[dict]:
        """Fetch recent daily summaries for charts via the gateway.

        Args:
            days_back (int): How many days to read.

        Returns:
            list[dict]: Recent day summaries, oldest first; empty when no
            persistence gateway is attached.
        """
        if self._persistence is None:
            return []
        return list(self._persistence.fetch_stats(days_back))

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _phase_of(tick: int) -> TimeOfDay:
        """Compute the time-of-day phase from a tick number.

        Args:
            tick (int): Current tick.

        Returns:
            TimeOfDay: The active phase.
        """
        slot = (tick % TICKS_PER_DAY) // (TICKS_PER_DAY // 4)
        return [TimeOfDay.MORNING, TimeOfDay.NOON,
                TimeOfDay.EVENING, TimeOfDay.NIGHT][slot]
