"""Composable behaviours for animals (Strategy Pattern).

A :class:`Behaviour` encapsulates *how* an animal does something, so an
animal can be composed from different behaviours without changing its class.
The base class defines the common interface; concrete strategies implement
species-specific rules.

This is the chapter-2 part of the assignment ("Teilbereich 2: Tiersimulation,
Verhalten"). The engine calls ``perform()`` during a tick; the animal passes
itself so the behaviour can read the current hunger, time of day and so on.

In the current phase the two shipped behaviours cover feeding and resting;
new behaviours (social, mating, foraging) can be added by subclassing
:class:`Behaviour` and returning an action tag.

Part of the vivizoo project. Module owner: Benjamin (backend).
"""

from __future__ import annotations

from abc import ABC, abstractmethod

# Action tags returned by behaviours -- the engine interprets them.
ACT_FEED = "feed"
ACT_REST = "rest"
ACT_IDLE = "idle"


class Behaviour(ABC):
    """Strategy interface every concrete behaviour implements.

    A behaviour is stateless by design -- all inputs arrive through
    :meth:`perform`, so one instance can be shared. If a strategy needs
    internal state, subclass :class:`StatefulBehaviour` instead.
    """

    @abstractmethod
    def perform(self, animal: "object", tick_counter: int, is_night: bool) -> str:
        """Decide what the animal should do this tick.

        Args:
            animal (object): The animal performing the behaviour. It exposes
                attributes the strategy may read (``hunger``, ``hp``).
            tick_counter (int): Current global simulation tick.
            is_night (bool): Whether it is currently night.

        Returns:
            str: An action tag from this module (``feed``, ``rest``,
            ``idle``) that the engine interprets for the animal type.

        Tests:
            1. A behaviour always returns one of the module-level tags.
            2. Two calls with the same inputs produce the same tag
               (determinism) for a stateless behaviour.
        """


class StatefulBehaviour(Behaviour):
    """Base for behaviours that keep internal state between ticks.

    Subclasses that need memory (a feeding cooldown, a walking timer) extend
    this class and normally override :meth:`reset` for snapshots/restores.

    Attributes:
        _state (dict): Arbitrary key-value state, empty by default.
    """

    def __init__(self) -> None:
        """Create a behaviour with empty internal state.

        Args:
            None.

        Returns:
            None (constructor).

        Tests:
            1. A fresh behaviour has empty ``_state``.
        """
        self._state: dict = {}

    def reset(self) -> None:
        """Clear the behaviour's internal state.

        Used when an animal is resurrected or a savegame snapshot is restored.

        Args:
            None.

        Returns:
            None.

        Tests:
            1. After storing state and calling ``reset()`` the state is empty.
        """
        self._state.clear()


class FeedingBehaviour(Behaviour):
    """Default feeding strategy: feed when the animal is hungry enough.

    The animal decides to feed when its hunger has risen to the species
    threshold (hunger grows over time; 100 = starving) and it is not night.
    """

    def perform(self, animal: "object", tick_counter: int, is_night: bool) -> str:
        """Return ``feed`` when the animal is hungry and it is daytime.

        Args:
            animal (object): The animal; reads ``hunger`` and the feeding
                threshold via ``get_feed_threshold()``.
            tick_counter (int): Current tick (unused by this strategy).
            is_night (bool): If ``True`` most animals do not feed.

        Returns:
            str: ``feed`` if the animal is hungry enough during the day,
            otherwise ``idle``.

        Tests:
            1. A hungry animal (``hunger >= threshold``) during the day
               returns ``feed``.
            2. A well-fed animal, or any animal at night, returns ``idle``.
        """
        if is_night:
            return ACT_IDLE
        threshold = getattr(animal, "get_feed_threshold", lambda: 40.0)()
        if animal.hunger >= threshold:
            return ACT_FEED
        return ACT_IDLE


class RestingBehaviour(Behaviour):
    """Default resting strategy: sleep at night, rest when tired.

    The animal rests during the night unconditionally, and additionally when
    its health is low during the day.
    """

    def perform(self, animal: "object", tick_counter: int, is_night: bool) -> str:
        """Return ``rest`` at night or when the animal is badly hurt.

        Args:
            animal (object): The animal; reads ``hp``.
            tick_counter (int): Current tick (unused).
            is_night (bool): Whether it is night.

        Returns:
            str: ``rest`` at night or when ``hp`` dropped below 30 %,
            otherwise ``idle``.

        Tests:
            1. At night the strategy returns ``rest`` regardless of health.
            2. During the day a healthy animal returns ``idle`` while a
               critically wounded one returns ``rest``.
        """
        if is_night or getattr(animal, "hp", 100.0) < 30.0:
            return ACT_REST
        return ACT_IDLE
