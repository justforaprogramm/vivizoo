"""The simulation loop -- the "heartbeat" the frontend observes.

:class:`SimulationEngine` owns the tick loop. It advances the whole zoo one
logical step at a time and exposes the read/write API the frontend uses:
snapshots, entity hover data, the chat feed and player actions. It is the
only object the frontend depends on (see ``backend/docs/api.md``).

A real play session runs the tick loop on a background thread; the demo
drives ``tick()`` manually, which keeps the module testable and dependency
free at the core level.
"""

from __future__ import annotations

import threading
import time
from typing import TYPE_CHECKING, Any

from db.interface.enums import TimeOfDay
from backend.core.action_handler import ActionHandler
from backend.core.message_logger import MessageLogger

if TYPE_CHECKING:  # type checkers only, avoids a runtime cycle
    from backend.core.zoo import Zoo
    from backend.persistence.db_gateway import DbGateway

# One full simulation day spans these many ticks, split into four phases.
TICKS_PER_DAY = 480
TICKS_PER_PHASE = TICKS_PER_DAY // 4


class SimulationEngine:
    """Advances the zoo and serves the frontend-facing read/write API.

    Args:
        zoo (Zoo): The zoo to simulate. Its lifecycle is owned by the caller.
        persistence (DbGateway | None): Optional adapter that persists day
            summaries and the chat log at each day boundary. Without it the
            engine runs purely in memory.
        logger (MessageLogger | None): The shared chat feed. Defaults to the
            singleton.
    """

    def __init__(
        self,
        zoo: "Zoo",
        persistence: "DbGateway | None" = None,
        logger: MessageLogger | None = None,
    ) -> None:
        """Create the engine bound to a zoo.

        Args:
            zoo (Zoo): The zoo to simulate.
            persistence (DbGateway | None): Optional persistence adapter.
            logger (MessageLogger | None): Chat feed; defaults to the shared
                singleton.

        Returns:
            None (constructor).

        Tests:
            1. A fresh engine starts at tick 0 and is not paused.
            2. Without a persistence adapter the engine still ticks.
        """
        self._zoo = zoo
        self._persistence = persistence
        self._logger = logger if logger is not None else MessageLogger.instance()
        self._tick_count = 0
        self._paused = False
        self._speed = 1.0
        self._thread: threading.Thread | None = None
        self._stop = False

    def _phase_of(self, tick: int) -> TimeOfDay:
        """Map a tick number to its time-of-day phase.

        Args:
            tick (int): The global tick count.

        Returns:
            TimeOfDay: The phase the tick falls into.

        Tests:
            1. Ticks 0 and 120 map to ``MORNING`` and ``NOON``.
            2. The mapping wraps seamlessly across day boundaries.
        """
        slot = (tick % TICKS_PER_DAY) // TICKS_PER_PHASE
        return [
            TimeOfDay.MORNING,
            TimeOfDay.NOON,
            TimeOfDay.EVENING,
            TimeOfDay.NIGHT,
        ][slot]

    # ------------------------------------------------------------------
    # Lifecycle / threading
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Begin ticking on a background thread.

        Args:
            None.

        Returns:
            None.

        Tests:
            1. Starting twice does not spawn a second thread.
            2. A paused engine keeps ticking until paused again later.
        """
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop = False
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self) -> None:
        """The background tick loop body.

        Args:
            None.

        Returns:
            None.
        """
        while not self._stop:
            if not self._paused:
                self.tick()
            time.sleep(1.0 / (10.0 * self._speed))

    def pause(self) -> None:
        """Freeze the tick loop.

        Args:
            None.

        Returns:
            None.
        """
        self._paused = True

    def resume(self) -> None:
        """Unfreeze the tick loop.

        Args:
            None.

        Returns:
            None.
        """
        self._paused = False

    def set_speed(self, multiplier: float) -> None:
        """Change how many ticks per second the loop produces.

        Args:
            multiplier (float): A positive factor; ``1.0`` is normal.

        Returns:
            None.

        Raises:
            ValueError: If ``multiplier`` is not positive.

        Tests:
            1. Setting ``2.0`` is accepted.
            2. Setting ``0`` or a negative value raises ``ValueError``.
        """
        if multiplier <= 0:
            raise ValueError(f"multiplier must be positive, got {multiplier}.")
        self._speed = multiplier

    # ------------------------------------------------------------------
    # The tick
    # ------------------------------------------------------------------

    def tick(self) -> None:
        """Advance the whole simulation by exactly one structural step.

        Args:
            None.

        Returns:
            None.

        Tests:
            1. ``tick()`` increments the internal tick counter by one.
            2. At a day boundary the engine closes and persists the day.
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

    def _close_day(self) -> None:
        """Wrap up the finished day: capture stats and persist if possible.

        Args:
            None.

        Returns:
            None.

        Tests:
            1. With a persistence adapter, a day summary is written.
            2. Without one, the day still advances (in-memory only).
        """
        self._zoo.begin_new_day()
        if self._persistence is not None:
            self._persistence.save_daily_summary(self._zoo)
        self._zoo.current_day += 1

    # ------------------------------------------------------------------
    # Read API for the frontend
    # ------------------------------------------------------------------

    def get_game_state(self) -> dict:
        """Return a full snapshot of the simulation for one render frame.

        Args:
            None.

        Returns:
            dict: With ``system``, ``finances``, ``inventory``,
            ``animals_on_map`` and ``visitors_on_map``.
        """
        phase = self._phase_of(self._tick_count).value
        return self._zoo.to_game_state(self._tick_count, phase)

    def get_entity_info(self, entity_id: str) -> dict:
        """Return hover/tooltip data for one entity.

        Args:
            entity_id (str): The entity's id (animal or enclosure).

        Returns:
            dict: Tooltip data, or ``{}`` if unknown.
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
        """Return any new chat messages and clear the buffer.

        Args:
            None.

        Returns:
            list[dict]: New log entries in the order they were produced.
        """
        return [entry.to_dict() for entry in self._logger.drain()]

    def execute_action(self, action_name: str, **kwargs: Any) -> dict:
        """Run a named player action against the zoo.

        Args:
            action_name (str): One of the supported action names.
            **kwargs: Action-specific arguments.

        Returns:
            dict: The action result (``success``, ``message``,
            ``chat_entries``).

        Raises:
            ValueError: If ``action_name`` is unknown.
        """
        return ActionHandler(self._zoo).execute_action(action_name, **kwargs).to_dict()

    def get_stats(self, days_back: int = 30) -> list[dict]:
        """Fetch recent daily summaries for charts.

        Args:
            days_back (int): How many days to read back.

        Returns:
            list[dict]: Daily summaries, oldest first; ``[]`` without a
            persistence adapter.
        """
        if self._persistence is None:
            return []
        return self._persistence.fetch_stats(days_back)

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        """Return a short readable representation.

        Args:
            None.

        Returns:
            str: Named debug string.
        """
        return (
            f"<SimulationEngine tick={self._tick_count} "
            f"phase={self._phase_of(self._tick_count).value}>"
        )
