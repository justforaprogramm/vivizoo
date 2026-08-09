"""The enclosure -- a container that aggregates animals.

An :class:`Enclosure` belongs to a zoo and holds zero or more animals. It is
an **aggregation** in the assignment's sense: the same animal could in
principle be moved elsewhere. The enclosure tracks capacity, cleanliness and
the biome, and performs its own upkeep within the tick loop.

The field names (``enclosure_id``, ``biome``, ``capacity``, ``cleanliness``)
mirror the ``enclosures`` table of the database module, so a savegame adapter
can map between them without transforms.

Part of the vivizoo project. Module owner: Benjamin (backend).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # imported for type checkers only, avoids a runtime cycle
    from backend.core.animal import Animal


class Enclosure:
    """A container holding animals, with its own cleanliness upkeep.

    Args:
        enclosure_id (str): Unique identifier, e.g. ``"e_01"``.
        name (str): Display name, e.g. ``"Savanna 1"``.
        biome (str): Landscape type, e.g. ``"savanna"`` or ``"arctic"``.
        capacity (int): Maximum number of animals that fit in.
        cleanliness (float): Starting cleanliness in percent (0--100).

    Class attributes:
        CLEAN_DECAY (float): Cleanliness lost per cleanliness-update tick.
        TICKS_PER_CLEAN_UPDATE (int): Interval for the decay.
    """

    CLEAN_DECAY = 0.1
    TICKS_PER_CLEAN_UPDATE = 20

    def __init__(
        self,
        enclosure_id: str,
        name: str,
        biome: str,
        capacity: int,
        cleanliness: float = 100.0,
    ) -> None:
        """Create an empty enclosure.

        Args:
            enclosure_id (str): Unique identifier.
            name (str): Display name.
            biome (str): Landscape type.
            capacity (int): Capacity; must be non-negative.
            cleanliness (float): Starting cleanliness in 0--100.

        Returns:
            None (constructor).

        Tests:
            1. ``Enclosure("e_01", "Savanna 1", "savanna", 8)`` holds no
               animals and has ``free_slots() == 8``.
            2. ``capacity=-1`` raises ``ValueError``.
        """
        if capacity < 0:
            raise ValueError(f"capacity must not be negative, got {capacity}.")
        self.enclosure_id = enclosure_id
        self.name = name
        self.biome = biome
        self.capacity = capacity
        self.cleanliness = self._clamp_clean(cleanliness)
        self.animals: list["Animal"] = []
        self._update_offset = 0

    def _clamp_clean(self, value: float) -> float:
        """Keep the cleanliness percentage inside 0--100.

        Args:
            value (float): The value to clamp/validate.

        Returns:
            float: The clamped value.

        Raises:
            ValueError: If ``value`` is not a number or far out of range.

        Tests:
            1. A value in range passes through unchanged.
            2. A tiny overshoot is clamped to ``100.0``.
        """
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValueError(f"cleanliness must be a number, got {value!r}.")
        if value < -0.01 or value > 100.01:
            raise ValueError(f"cleanliness must be 0--100, got {value}.")
        return max(0.0, min(100.0, float(value)))

    # ------------------------------------------------------------------
    # Capacity
    # ------------------------------------------------------------------

    def add_animal(self, animal: "Animal") -> None:
        """Place an animal into this enclosure.

        Args:
            animal (Animal): The animal to add. Its ``enclosure_id`` is set
                to this enclosure's id.

        Returns:
            None.

        Tests:
            1. Adding an animal increments ``len(animals)`` and sets its
               ``enclosure_id``.
            2. Adding a dead animal is allowed but it still occupies a slot.
        """
        animal.enclosure_id = self.enclosure_id
        self.animals.append(animal)

    def remove_animal(self, animal: "Animal") -> None:
        """Take an animal out of this enclosure, if it is present.

        Args:
            animal (Animal): The animal to remove. Missing animals are a
                no-op.

        Returns:
            None.

        Tests:
            1. Removing a present animal reduces ``len(animals)``.
            2. Removing an absent animal does nothing and does not raise.
        """
        if animal in self.animals:
            self.animals.remove(animal)
            animal.enclosure_id = None

    def free_slots(self) -> int:
        """Return how many more animals fit into this enclosure.

        Dead animals still occupy a slot until removed, so the count is based
        on all rows.

        Args:
            None.

        Returns:
            int: ``capacity - len(animals)``, clamped at ``0``.

        Tests:
            1. An enclosure with ``capacity=8`` holding 3 returns ``5``.
            2. An over-full enclosure returns ``0``, never negative.
        """
        return max(0, self.capacity - len(self.animals))

    def is_full(self) -> bool:
        """Report whether no further animal fits in.

        Args:
            None.

        Returns:
            bool: ``True`` when ``free_slots() == 0``.

        Tests:
            1. An enclosure with ``capacity=2`` holding two animals returns
               ``True``, and ``False`` again after one is removed.
            2. An enclosure built with ``capacity=0`` is full from the start.
        """
        return self.free_slots() == 0

    # ------------------------------------------------------------------
    # Tick loop
    # ------------------------------------------------------------------

    def tick_update(self, tick_counter: int) -> None:
        """Advance the enclosure's own upkeep (cleanliness decay).

        Throttled and staggered so enclosures do not all decay on the same
        tick.

        Args:
            tick_counter (int): Current simulation tick.

        Returns:
            None.

        Tests:
            1. After enough ticks, ``cleanliness`` drops by ``CLEAN_DECAY``.
            2. Decaying a filthy enclosure bottoms out at ``0.0`` and never
               goes negative, however many ticks are run.
        """
        if (tick_counter + self._update_offset) % self.TICKS_PER_CLEAN_UPDATE != 0:
            return
        # Clamp here rather than via _clamp_clean: that validator guards
        # *caller-supplied* values and raises out of range, while the decay is
        # an internal computation that simply bottoms out at zero.
        self.cleanliness = max(0.0, self.cleanliness - self.CLEAN_DECAY)

    def clean(self) -> None:
        """Restore the enclosure to full cleanliness.

        Args:
            None.

        Returns:
            None.

        Tests:
            1. After ``clean()``, ``cleanliness == 100.0``.
            2. Calling ``clean()`` on an already spotless enclosure leaves
               ``cleanliness`` at ``100.0``.
        """
        self.cleanliness = 100.0

    def average_welfare(self) -> float:
        """Return the mean welfare of the living animals here.

        Args:
            None.

        Returns:
            float: Mean welfare (0--100); ``0.0`` if there are no animals or
            all are dead.

        Tests:
            1. Two living animals with welfare ``100.0`` and ``50.0`` give
               ``75.0``.
            2. An empty enclosure -- and one whose animals all have
               ``is_dead`` set -- returns ``0.0``.
        """
        live = [a.welfare for a in self.animals if not a.is_dead]
        if not live:
            return 0.0
        return sum(live) / len(live)

    def __repr__(self) -> str:  # pragma: no cover - debugging
        """Return a short readable representation.

        Args:
            None.

        Returns:
            str: Named debug string.

        Tests:
            1. The string contains the ``enclosure_id``, the ``name`` and the
               ``len(animals)``/``capacity`` occupancy.
            2. It is stable across calls on an unchanged enclosure.
        """
        return f"<Enclosure {self.enclosure_id} ({self.name}) {len(self.animals)}/{self.capacity}>"
