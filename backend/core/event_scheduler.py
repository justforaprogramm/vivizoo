"""Random and timed events that shake up the simulation.

:class:`EventScheduler` checks each tick for a small chance of a random event
(staff accident, animal illness, weather change) and hands resulting messages
to the message logger. In the current phase the event content is light -- an
occasional weather change and a rare animal "illness" status effect -- which
is enough to make the loop lively without unbalancing the core economy loop.
"""

from __future__ import annotations

import random

from backend.core.status_effect import StatusEffect


class EventScheduler:
    """Produces occasional random events during the tick.

    Args:
        event_chance (float): Probability of an event per tick (0.0--1.0).
            Defaults to a small value so the zombie of randomness stays rare.

    Attributes:
        event_chance (float): Probability of an event per tick.
    """

    DEFAULT_CHANCE = 0.01

    def __init__(self, event_chance: float | None = None) -> None:
        """Create a scheduler with a per-tick event probability.

        Args:
            event_chance (float | None): probability per tick; ``None`` uses
                :attr:`DEFAULT_CHANCE`.

        Returns:
            None (constructor).

        Tests:
            1. ``EventScheduler(None).event_chance`` equals ``DEFAULT_CHANCE``.
            2. ``EventScheduler(0.0)`` never fires an event.
        """
        self.event_chance = (
            self.DEFAULT_CHANCE if event_chance is None else float(event_chance)
        )
        if not 0.0 <= self.event_chance <= 1.0:
            raise ValueError(
                f"event_chance must be 0.0..1.0, got {event_chance}."
            )

    def check(self, zoo: "object", tick: int) -> None:
        """Roll for an event and apply it if triggered.

        Args:
            zoo (Zoo): The zoo to mutate.
            tick (int): The current simulation tick.

        Returns:
            None.

        Tests:
            1. With ``event_chance=0.0`` nothing ever happens.
            2. With ``event_chance=1.0`` an event fires every check.
        """
        if random.random() >= self.event_chance:
            return
        roll = random.random()
        if roll < 0.5:
            # Weather change.
            zoo.environment.randomize()
            zoo.logger.log(
                "INFO",
                f"The weather changed to {zoo.environment.weather}.",
            )
        elif roll < 0.8:
            # Animal illness -> apply a temporary stress effect.
            animal = self._random_living_animal(zoo)
            if animal is not None:
                animal.apply_status_effect(
                    StatusEffect(name="Stressed", tick_interval=5,
                                 hp_drain=1.0, remaining_ticks=40)
                )
                zoo.logger.log(
                    "WARNING",
                    f"{animal.name} seems stressed.",
                    entity_id=animal.animal_id,
                )
        else:
            # Rain spell.
            zoo.environment.weather = "rain"
            zoo.logger.log("WARNING", "It started raining in the zoo.")

    @staticmethod
    def _random_living_animal(zoo: "object"):
        """Pick a random living animal across all enclosures.

        Args:
            zoo (Zoo): The zoo to search.

        Returns:
            Animal | None: A random living animal, or ``None`` if none exist.

        Tests:
            1. A zoo with one living animal returns that animal.
            2. An empty zoo returns ``None``.
        """
        living = [
            a
            for enclosure in zoo.enclosures
            for a in enclosure.animals
            if not a.is_dead
        ]
        return random.choice(living) if living else None
