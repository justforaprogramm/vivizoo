"""The animal hierarchy -- chapter 2 of the assignment.

:class:`Animal` is an abstract base class defining the shared structure and
the four abstract operations requested for the "Tiersimulation" area:
feeding, resting, moving and aging. Three concrete species -- :class:`Lion`,
:class:`Giraffe`, :class:`Penguin` -- inherit from it and differ in behaviour
(``PREFERRED_FOOD``, ``DIGESTION_RATE``, feeding threshold), which is classic
polymorphism.

The species identifiers (``"lion"``, ``"giraffe"``, ``"penguin"``) deliberately
match the discriminator column of ``db/models/animal.py``, so a future savegame
adapter can map backend animals to persisted rows losslessly.

Encapsulation: the mutable simulation state (``_hunger``, ``_hp``, ...) is
private and only reachable through documented properties and methods, so no
caller can push a value outside 0--100.
"""

from __future__ import annotations

import random
from abc import ABC, abstractmethod

from backend.core.behaviour import (
    ACT_FEED,
    ACT_IDLE,
    ACT_REST,
    Behaviour,
    FeedingBehaviour,
    RestingBehaviour,
)
from backend.core.status_effect import StatusEffect
from db.interface.enums import FoodType

MAX_STAT = 100.0
"""Highest valid value for percentage stats (hunger, hp, welfare)."""


class Animal(ABC):
    """Abstract base of every animal.

    Shared by all species: identifiers, position, the percentage stats, the
    composed :class:`Behaviour` strategies and the tick-advance machine.

    Args:
        animal_id (str): Unique identifier, e.g. ``"a_01"``.
        name (str): Given name, e.g. ``"Hungry Harry"``.
        x (int), y (int): Position on the map.
        behaviour (Behaviour | None): The composed behaviour; defaults to a
            :class:`FeedingBehaviour` / :class:`RestingBehaviour` pair.
        age_days (int): Age in simulation days.
        hp (float): Current health (0--100).
        hunger (float): Current hunger (0--100, 0 = full).
        welfare (float): Current well-being (0--100).

    Class attributes (overridden by subclasses):
        PREFERRED_FOOD (FoodType): Which resource this species eats.
        DIGESTION_RATE (float): Hunger dropped per hunger-update tick.
        TICKS_PER_HUNGER_UPDATE (int): How often hunger is recomputed.
        FEED_THRESHOLD (float): Hunger value below which the animal feeds.
        BUY_PRICE (float): Cost in budget to buy this species.
        FALLBACK_X, FALLBACK_Y (int): Spawn position for new animals.
    """

    PREFERRED_FOOD: FoodType = FoodType.MEAT
    DIGESTION_RATE: float = 1.5
    TICKS_PER_HUNGER_UPDATE: int = 10
    FEED_THRESHOLD: float = 40.0
    BUY_PRICE: float = 500.0
    FALLBACK_X: int = 300
    FALLBACK_Y: int = 200
    _FEED_HUNGER_GAIN: float = 35.0

    def __init__(
        self,
        animal_id: str,
        name: str,
        x: int,
        y: int,
        behaviour: Behaviour | None = None,
        age_days: int = 0,
        hp: float = 100.0,
        hunger: float = 0.0,
        welfare: float = 100.0,
    ) -> None:
        """Build an animal with defaults that subclasses can refine.

        Args:
            animal_id (str): Unique identifier.
            name (str): Display name.
            x (int), y (int): Initial map position.
            behaviour (Behaviour | None): Composed behaviour; ``None`` gives
                the default pair.
            age_days (int): Initial age in days; must be non-negative.
            hp, hunger, welfare (float): Initial stats.

        Returns:
            None (constructor).

        Tests:
            1. ``Lion("a_01", "Simba", 0, 0)`` has ``PREFERRED_FOOD ==
               FoodType.MEAT`` and stats inside 0--100.
            2. Passing ``hp=150.0`` raises ``ValueError`` (out of range).
        """
        if age_days < 0:
            raise ValueError(f"age_days must not be negative, got {age_days}.")
        # Construction-time range validation is strict; later incremental
        # operations clamp via _clamp instead.
        for field, value in (("hp", hp), ("hunger", hunger),
                             ("welfare", welfare)):
            if not 0.0 <= float(value) <= MAX_STAT:
                raise ValueError(
                    f"{field} must be between 0 and {MAX_STAT}, got {value}."
                )
        self.animal_id = animal_id
        self.name = name
        self.x = x
        self.y = y
        self.age_days = age_days
        self.enclosure_id: str | None = None
        self._hp = self._clamp("hp", hp)
        self._hunger = self._clamp("hunger", hunger)
        self._welfare = self._clamp("welfare", welfare)
        self.is_dead = False
        self._days_starved = 0
        self._update_offset = random.randint(0, self.TICKS_PER_HUNGER_UPDATE - 1)
        # Compose behaviour strategies (strategy pattern).
        self._behaviours: list[Behaviour] = behaviour is not None and [behaviour] or [
            FeedingBehaviour(),
            RestingBehaviour(),
        ]
        self._status_effects: list[StatusEffect] = []

    # ------------------------------------------------------------------
    # Public read access (encapsulation)
    # ------------------------------------------------------------------

    @property
    def hp(self) -> float:
        """Current health as a float in 0--100.

        Returns:
            float: Current health value.
        """
        return self._hp

    @property
    def hunger(self) -> float:
        """Current hunger as a float; 0 = fully fed, 100 = starving.

        Returns:
            float: Current hunger value.
        """
        return self._hunger

    @property
    def welfare(self) -> float:
        """Current well-being as a float in 0--100.

        Returns:
            float: Current welfare value.
        """
        return self._welfare

    @property
    def days_starved(self) -> int:
        """Number of consecutive days the animal went without food.

        Returns:
            int: Count of starvation days.
        """
        return self._days_starved

    @property
    def status_effects(self) -> list[StatusEffect]:
        """The list of active status effects.

        Returns:
            list[StatusEffect]: Active effects; the caller may read the list.
        """
        return self._status_effects

    def get_feed_threshold(self) -> float:
        """Return the hunger threshold below which this animal wants to feed.

        Returns:
            float: The species' feeding threshold.
        """
        return self.FEED_THRESHOLD

    # ------------------------------------------------------------------
    # Tick loop
    # ------------------------------------------------------------------

    def tick_update(self, tick_counter: int) -> None:
        """Advance this animal by one simulation tick.

        Movement happens every tick; hunger, welfare and status effects are
        throttled (only the species' base updates on its own interval) and
        staggered by :attr:`_update_offset` so hundreds of animals never all
        update on the same tick.

        Args:
            tick_counter (int): Current global simulation tick.

        Returns:
            None.

        Tests:
            1. After enough ticks, ``hunger`` rises by ``DIGESTION_RATE`` for
               the species.
            2. While the throttled update is skipped, ``hunger`` stays put.
        """
        self.move()
        due = (tick_counter + self._update_offset) % self.TICKS_PER_HUNGER_UPDATE == 0
        if not due:
            return
        if not self.is_dead:
            self._update_hunger()
            self._apply_status_effects()
            self._recompute_welfare()
            self._check_starvation()

    def _update_hunger(self) -> None:
        """Raise hunger by the species' digestion rate and track starvation.

        Hunger grows over time (0 = full, 100 = starving). Once it reaches
        the ceiling the animal cannot get hungrier; instead
        ``days_starved`` climbs.

        Args:
            None.

        Returns:
            None.

        Tests:
            1. Hunger never rises above ``100.0``.
            2. An animal already at max hunger increments ``days_starved``.
        """
        if self._hunger >= MAX_STAT:
            if self._days_starved < 1_000_000:
                self._days_starved += 1
        else:
            self._hunger = self._clamp("hunger", self._hunger + self.DIGESTION_RATE)

    def _apply_status_effects(self) -> None:
        """Tick all active status effects and collect their health drains.

        Expired effects are removed; the summed drain reduces health.

        Args:
            None.

        Returns:
            None.

        Tests:
            1. A poisoned animal loses ``hp_drain`` health over the effect's
               active period.
            2. An expired effect is removed from ``status_effects``.
        """
        total_drain = 0.0
        survivors: list[StatusEffect] = []
        for effect in self._status_effects:
            total_drain += effect.tick()
            if not effect.is_expired():
                survivors.append(effect)
        self._status_effects = survivors
        if total_drain:
            self._hp = self._clamp("hp", self._hp - total_drain)

    def _recompute_welfare(self) -> None:
        """Recalculate welfare from hunger and health.

        A healthy, well-fed animal has high welfare; hunger and low health
        drag it down.

        Args:
            None.

        Returns:
            None.

        Tests:
            1. A full, healthy animal keeps welfare close to ``100.0``.
            2. An animal at high hunger sees its welfare drop.
        """
        target = 100.0 - (self._hunger * 0.5) - ((100.0 - self._hp) * 0.3)
        self._welfare = self._clamp("welfare", target)

    def _check_starvation(self) -> None:
        """Kill the animal after three consecutive starvation days.

        Args:
            None.

        Returns:
            None.

        Tests:
            1. After three starved days, ``is_dead`` becomes ``True``.
            2. A fed animal (``days_starved < 3``) never dies from this.
        """
        if self._days_starved >= 3 and not self.is_dead:
            self._hp = 0.0
            self.is_dead = True

    # ------------------------------------------------------------------
    # Abstract operations mandated by the assignment
    # ------------------------------------------------------------------

    @abstractmethod
    def move(self) -> None:
        """Move the animal by one step.

        Concrete species override this with their own locomotion rules,
        though most simply change ``x``/``y`` modestly.

        Args:
            None.

        Returns:
            None.
        """

    def feed(self, amount: float) -> None:
        """Feed the animal, reducing hunger and recovering a little health.

        Args:
            amount (float): How much food was consumed. After feeding, the
                starvation counter resets.

        Returns:
            None.

        Tests:
            1. After ``feed(35.0)`` hunger drops and ``days_starved`` resets
               to zero.
            2. Feeding keeps hunger clamped at ``0.0`` (fully fed).
        """
        if self.is_dead:
            return
        self._hunger = self._clamp("hunger", self._hunger - amount)
        self._days_starved = 0
        self._hp = self._clamp("hp", self._hp + 2.0)

    def rest(self) -> None:
        """Recover a little health while resting.

        Args:
            None.

        Returns:
            None.

        Tests:
            1. ``rest()`` raises a wounded animal's health by a fixed small
               amount, kept within 0--100.
        """
        if not self.is_dead:
            self._hp = self._clamp("hp", self._hp + 5.0)

    def age_one_day(self) -> None:
        """Grow the animal one simulation day older.

        Args:
            None.

        Returns:
            None.

        Tests:
            1. ``age_days`` increases by exactly one.
            2. Calling it does not alter hunger or health.
        """
        self.age_days += 1

    def act(self, tick_counter: int, is_night: bool) -> str:
        """Let the composed behaviours decide the animal's action this tick.

        The first behaviour that produces a non-idle action wins; otherwise
        the animal idles. The engine may interpret the returned tag.

        Args:
            tick_counter (int): Current simulation tick.
            is_night (bool): Whether it is night.

        Returns:
            str: The decided action tag (``feed``, ``rest`` or ``idle``).

        Tests:
            1. A hungry animal during the day returns ``feed`` from its
               feeding behaviour.
            2. At night the animal returns ``rest`` via its resting behaviour.
        """
        for behaviour in self._behaviours:
            action = behaviour.perform(self, tick_counter, is_night)
            if action in (ACT_FEED, ACT_REST):
                return action
        return ACT_IDLE

    # ------------------------------------------------------------------
    # Actions / helpers
    # ------------------------------------------------------------------

    def apply_status_effect(self, effect: StatusEffect) -> None:
        """Attach a new status effect to the animal.

        Args:
            effect (StatusEffect): The effect to attach; must not be None.

        Returns:
            None.

        Tests:
            1. Adding an effect puts it at the end of ``status_effects``.
        """
        if effect is None:
            raise ValueError("effect must not be None.")
        self._status_effects.append(effect)

    def is_critical(self) -> bool:
        """Report whether the animal needs attention right now.

        Args:
            None.

        Returns:
            bool: ``True`` if alive and health at/below 25 % or hunger
            at/above 75 %.

        Tests:
            1. ``hp=20`` or ``hunger=85`` returns ``True``.
            2. Dead animals return ``False`` regardless of stats.
        """
        if self.is_dead:
            return False
        return self._hp <= 25.0 or self._hunger >= 75.0

    def to_hover_data(self) -> dict:
        """Build the tooltip payload the frontend requests per entity.

        Args:
            None.

        Returns:
            dict: The ``animal_hover_data`` shape from the planning --
            name, species, age, hp, hunger, welfare, status effects and
            whether it is dead.

        Tests:
            1. The dict contains all keys the frontend uses.
            2. ``status_effects`` lists the names of active effects only.
        """
        return {
            "id": self.animal_id,
            "name": self.name,
            "species": self.species_key(),
            "age_days": self.age_days,
            "hp": round(self._hp, 1),
            "hunger": round(self._hunger, 1),
            "welfare": round(self._welfare, 1),
            "is_dead": self.is_dead,
            "status_effects": [e.name for e in self._status_effects],
        }

    def species_key(self) -> str:
        """Return the species discriminator used by the database.

        Args:
            None.

        Returns:
            str: Lower-case species identifier (``"lion"``, ``"giraffe"``,
            ``"penguin"``).

        Tests:
            1. ``Lion(...).species_key()`` returns ``"lion"``.
        """
        return self.__class__.__name__.lower()

    @staticmethod
    def _clamp(field: str, value: float) -> float:
        """Keep a percentage stat inside 0--100.

        Incremental simulation operations legitimately overshoot -- feeding a
        full animal adds a small amount of health, so the value is quietly
        clamped to 0..MAX_STAT rather than raising. Grossly invalid numeric
        (non-number) input is still rejected.

        Args:
            field (str): Name of the stat, used in error messages.
            value (float): The value to clamp.

        Returns:
            float: The clamped value in 0..MAX_STAT.

        Raises:
            ValueError: If ``value`` is not a number.

        Tests:
            1. In-range values are returned unchanged.
            2. A tiny over-shoot (e.g. ``100.0001``) is clamped to ``100.0``.
        """
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValueError(f"{field} must be a number, got {value!r}.")
        return max(0.0, min(MAX_STAT, float(value)))

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        """Return a short readable representation.

        Args:
            None.

        Returns:
            str: Named debug string.
        """
        return f"<{self.__class__.__name__} {self.animal_id} ({self.name})>"

    def __eq__(self, other: object) -> bool:
        """Compare animals by their unique identifier.

        Args:
            other (object): Another object.

        Returns:
            bool: ``True`` if ``other`` is an :class:`Animal` with the same
            ``animal_id``.
        """
        return isinstance(other, Animal) and other.animal_id == self.animal_id

    def __hash__(self) -> int:
        """Hash an animal by its identifier for use in sets.

        Returns:
            int: Hash of ``animal_id``.
        """
        return hash(self.animal_id)


class Lion(Animal):
    """Carnivore: eats meat, digests slowly, costs the most.

    Overrides only the polymorphic constants; all behaviour comes from
    :class:`Animal`.
    """

    PREFERRED_FOOD = FoodType.MEAT
    DIGESTION_RATE = 2.0
    FEED_THRESHOLD = 35.0
    BUY_PRICE = 900.0

    def move(self) -> None:
        """Step the lion a short random distance.

        Args:
            None.

        Returns:
            None.
        """
        self.x += random.randint(-3, 3)
        self.y += random.randint(-3, 3)


class Giraffe(Animal):
    """Herbivore: eats plants, carries a high health pool.

    Overrides only the polymorphic constants.
    """

    PREFERRED_FOOD = FoodType.PLANTS
    DIGESTION_RATE = 1.2
    FEED_THRESHOLD = 50.0
    BUY_PRICE = 700.0

    def move(self) -> None:
        """Step the giraffe a short random distance.

        Args:
            None.

        Returns:
            None.
        """
        self.x += random.randint(-5, 5)
        self.y += random.randint(-2, 2)


class Penguin(Animal):
    """Piscivore: eats fish, digests quickly, cheapest to buy.

    Overrides only the polymorphic constants.
    """

    PREFERRED_FOOD = FoodType.FISH
    DIGESTION_RATE = 2.5
    FEED_THRESHOLD = 30.0
    BUY_PRICE = 400.0

    def move(self) -> None:
        """Step the penguin along mostly the x-axis (waddling).

        Args:
            None.

        Returns:
            None.
        """
        self.x += random.randint(-2, 4)
        self.y += 0


# ----------------------------------------------------------------------
# Factory
# ----------------------------------------------------------------------

_SPECIES: dict[str, type[Animal]] = {
    "lion": Lion,
    "giraffe": Giraffe,
    "penguin": Penguin,
}


def known_species() -> list[str]:
    """List every registered species name.

    Args:
        None.

    Returns:
        list[str]: Sorted species keys, e.g. ``["giraffe", "lion", "penguin"]``.
    """
    return sorted(_SPECIES)


def create_animal(species: str, **fields: object) -> Animal:
    """Create an animal of the right subclass from a species string.

    This is the safe way to build an animal when the species only exists as
    a string (e.g. from ``execute_action("buy_animal", species="penguin")``).
    Case-insensitive.

    Args:
        species (str): Species key, e.g. ``"lion"``.
        **fields: Extra constructor values, e.g. ``animal_id``, ``name``.

    Returns:
        Animal: A new instance of the matching subclass.

    Raises:
        ValueError: If ``species`` matches no registered class; the message
            lists the valid options.

    Tests:
        1. ``create_animal("penguin", animal_id="a_01", name="Pingu")``
           returns a :class:`Penguin` with the given id.
        2. ``create_animal("dragon")`` raises ``ValueError``.
    """
    animal_class = _SPECIES.get(species.lower())
    if animal_class is None:
        allowed = ", ".join(known_species())
        raise ValueError(f"Unknown species {species!r}. Valid: {allowed}.")
    return animal_class(**fields)
