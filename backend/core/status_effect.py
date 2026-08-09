"""Temporary modifiers applied to an animal.

:class:`StatusEffect` captures a short-lived state that changes an animal's
behaviour or drains its health -- e.g. ``Poisoned`` or ``Stressed``. The
modelling mirrors the database table ``animal_status_effects`` (see
``db/models/animal_status_effect.py``), so the field names line up for
persistence.

Phase note: the effects exist in the domain from the start, but the healing
mechanic that removes them is wired in phase 2 of the planning. The core
loop already applies them and counts them down each tick.
"""

from __future__ import annotations


class StatusEffect:
    """A short-lived modifier that affects one animal per tick.

    Args:
        name (str): Display name, e.g. ``"Poisoned"`` or ``"Stressed"``.
        tick_interval (int): How often the effect acts (every N ticks).
        hp_drain (float): Health points drained each time the effect acts.
        remaining_ticks (int): How many more ticks the effect lasts.

    Attributes:
        name (str): Display name of the effect.
        tick_interval (int): Interval in ticks between two activations.
        hp_drain (float): Health drained per activation.
        remaining_ticks (int): Life left in ticks; ``0`` means expired.
        _offset (int): Phase offset so multiple effects do not all fire on
            the same tick.
    """

    def __init__(
        self,
        name: str,
        tick_interval: int,
        hp_drain: float,
        remaining_ticks: int,
    ) -> None:
        """Create a status effect with the given parameters.

        Args:
            name (str): Display name.
            tick_interval (int): Activation interval in ticks; must be positive.
            hp_drain (float): Health drained per activation.
            remaining_ticks (int): Lifespan in ticks; may be zero.

        Returns:
            None (constructor).

        Tests:
            1. ``StatusEffect("Hungry", 5, 2.0, 40)`` stores the values and
               is not expired.
            2. ``StatusEffect("Hungry", 5, 2.0, 0)`` is already expired.
        """
        if tick_interval < 1:
            raise ValueError(f"tick_interval must be positive, got {tick_interval}.")
        self.name = name
        self.tick_interval = tick_interval
        self.hp_drain = hp_drain
        self.remaining_ticks = remaining_ticks
        self._offset = 0

    def tick(self) -> float:
        """Advance the effect by one tick.

        The remaining duration always decreases by one. The health drain is
        only "paid out" when the effect is due according to its interval; on
        other ticks ``0.0`` is returned.

        Args:
            None.

        Returns:
            float: The health points to drain this tick (``hp_drain`` if the
            effect acted, otherwise ``0.0``).

        Tests:
            1. With ``tick_interval=1`` every ``tick()`` returns ``hp_drain``
               and decrements ``remaining_ticks`` by one.
            2. With ``tick_interval=3`` and an offset of one, only every
               third ``tick()`` returns ``hp_drain``; the others return
               ``0.0``.
        """
        if self.remaining_ticks > 0:
            self.remaining_ticks -= 1
        drain = 0.0
        # _offset lets the engine stagger effects so they never all fire at once.
        if (self._offset + self.remaining_ticks) % self.tick_interval == 0:
            drain = self.hp_drain
        return drain

    def is_expired(self) -> bool:
        """Report whether the effect has run out of time.

        Args:
            None.

        Returns:
            bool: ``True`` when ``remaining_ticks`` reached zero.

        Tests:
            1. An effect with ``remaining_ticks=0`` returns ``True``.
            2. An effect with ``remaining_ticks=1`` returns ``False``.
        """
        return self.remaining_ticks == 0

    def __repr__(self) -> str:  # pragma: no cover - trivial convenience
        """Provide a human-readable representation for debugging.

        Args:
            None.

        Returns:
            str: A short string naming the effect and its remaining time.
        """
        return f"<StatusEffect {self.name} remaining={self.remaining_ticks}>"
