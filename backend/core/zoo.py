"""The aggregate root of the simulation.

:class:`Zoo` is the top-most object that owns everything else: the
enclosures (and through them the animals), the employees, the finances, the
inventory, the active visitors, the environment and the message logger.
This satisfies the assignment's "Zoo als Kompositionsobjekt" requirement --
it is built by composition, it knows its parts, and it coordinates their
lifecycle.

The planning document describes this as the *aggregate root* that the
:class:`~backend.core.engine.SimulationEngine` drives forward.

Part of the vivizoo project. Module owner: Benjamin (backend).
"""

from __future__ import annotations

import itertools
import random

from backend.core.animal import Animal, create_animal
from backend.core.enclosure import Enclosure
from backend.core.environment import EnvironmentFactor
from backend.core.employee import Employee
from backend.core.event_scheduler import EventScheduler
from backend.core.finances import Finances
from backend.core.inventory import Inventory
from backend.core.message_logger import MessageLogger
from backend.core.visitor import Visitor


class Zoo:
    """The composable, top-level container of a zoo simulation.

    Args:
        name (str): Display name of the zoo.
        logger (MessageLogger): The shared chat feed.
    """

    def __init__(
        self, name: str = "My Zoo", logger: MessageLogger | None = None
    ) -> None:
        """Build an empty zoo ready for setup.

        Args:
            name (str): Display name.
            logger (MessageLogger | None): Shared logger; ``None`` falls back
                to :meth:`MessageLogger.instance`.

        Returns:
            None (constructor).

        Tests:
            1. A fresh zoo has no enclosures and no employees.
            2. Composition parts (finances, inventory, environment) are
               present and independent per zoo.
        """
        self.name = name
        self.logger = logger or MessageLogger.instance()
        self.finances = Finances()
        self.inventory = Inventory()
        self.environment = EnvironmentFactor()
        self.scheduler = EventScheduler()
        self.enclosures: list[Enclosure] = []
        self.employees: list[Employee] = []
        self.visitors: list[Visitor] = []
        self.is_open = True
        self.reputation = 80
        self.current_day = 1
        self._visitors_today = 0
        self._revenue_today = 0.0
        self._expenses_today = 0.0
        self._deaths_today = 0
        # Figures of the just-finished day, frozen by begin_new_day().
        self._visitors_snapshot = 0
        self._deaths_snapshot = 0
        self._animal_counter = itertools.count(1)
        self._enclosure_counter = itertools.count(1)
        self._visitor_counter = itertools.count(1)

    # ------------------------------------------------------------------
    # Builder helpers
    # ------------------------------------------------------------------

    def add_enclosure(
        self,
        name: str,
        biome: str,
        capacity: int,
        cleanliness: float = 100.0,
    ) -> Enclosure:
        """Create and register a new enclosure with a fresh identifier.

        Args:
            name (str): Display name.
            biome (str): Landscape type.
            capacity (int): Capacity.
            cleanliness (float): Starting cleanliness.

        Returns:
            Enclosure: The newly created enclosure, already registered.

        Tests:
            1. The returned enclosure has a unique ``e_`` identifier.
            2. The enclosure is appended to ``self.enclosures``.
        """
        identifier = f"e_{next(self._enclosure_counter):02d}"
        enclosure = Enclosure(identifier, name, biome, capacity, cleanliness)
        self.enclosures.append(enclosure)
        return enclosure

    def add_employee(self, employee: Employee) -> None:
        """Register a staff member.

        Args:
            employee (Employee): The employee to add.

        Returns:
            None.

        Tests:
            1. The employee is added to ``self.employees``.
            2. No de-duplication takes place, so adding the same employee
               object twice leaves two entries in ``self.employees``.
        """
        self.employees.append(employee)

    def add_animal(self, species: str, name: str, enclosure: Enclosure) -> Animal:
        """Create and place a new animal of the given species.

        Args:
            species (str): Species key (``"lion"``, ``"giraffe"``,
                ``"penguin"``).
            name (str): The animal's given name.
            enclosure (Enclosure): The enclosure to place it in.

        Returns:
            Animal: The new animal, already added to the enclosure.

        Tests:
            1. The animal has a fresh ``a_`` identifier and correct enclosure.
            2. An unknown species such as ``"dragon"`` propagates the
               ``ValueError`` raised by ``create_animal``.
        """
        identifier = f"a_{next(self._animal_counter):02d}"
        animal = create_animal(
            species,
            animal_id=identifier,
            name=name,
            x=Animal.FALLBACK_X,
            y=Animal.FALLBACK_Y,
        )
        enclosure.add_animal(animal)
        return animal

    def _spawn_visitor(self, x: int, y: int, lifetime: int) -> Visitor:
        """Create and register a visitor at the gate.

        Args:
            x (int), y (int): Spawn position.
            lifetime (int): Ticks the visitor stays.

        Returns:
            Visitor: The new visitor, appended to ``self.visitors``.

        Tests:
            1. The visitor gets a three-digit ``v_`` identifier and is
               appended to ``self.visitors``.
            2. Every spawn pays a ticket, so ``finances.revenue_today`` grows
               by the ticket price and ``_visitors_today`` by one.
        """
        identifier = f"v_{next(self._visitor_counter):03d}"
        visitor = Visitor(identifier, x, y, lifetime)
        self.visitors.append(visitor)
        self.finances.pay_ticket()
        self._visitors_today += 1
        return visitor

    # ------------------------------------------------------------------
    # Lookups
    # ------------------------------------------------------------------

    def find_animal(self, animal_id: str) -> Animal | None:
        """Find an animal by identifier across every enclosure.

        Args:
            animal_id (str): The identifier to look up.

        Returns:
            Animal | None: The matching animal, or ``None``.

        Tests:
            1. A present animal is returned.
            2. An unknown id returns ``None``.
        """
        for enclosure in self.enclosures:
            for animal in enclosure.animals:
                if animal.animal_id == animal_id:
                    return animal
        return None

    def find_enclosure(self, enclosure_id: str) -> Enclosure | None:
        """Find an enclosure by identifier.

        Args:
            enclosure_id (str): The identifier to look up.

        Returns:
            Enclosure | None: The matching enclosure, or ``None``.

        Tests:
            1. A registered enclosure is found by its ``e_`` identifier.
            2. An unknown id returns ``None``, and so does a lookup on a zoo
               without enclosures.
        """
        for enclosure in self.enclosures:
            if enclosure.enclosure_id == enclosure_id:
                return enclosure
        return None

    # ------------------------------------------------------------------
    # Aggregates (queried daily / by the frontend)
    # ------------------------------------------------------------------

    def living_animals(self) -> list[Animal]:
        """Return every living animal in the zoo.

        Args:
            None.

        Returns:
            list[Animal]: The living animals across all enclosures.

        Tests:
            1. Animals of every enclosure are collected into one flat list.
            2. Animals with ``is_dead`` set are filtered out, so a zoo without
               enclosures returns ``[]``.
        """
        return [
            animal
            for enclosure in self.enclosures
            for animal in enclosure.animals
            if not animal.is_dead
        ]

    def all_animals(self) -> list[Animal]:
        """Return every animal, dead or alive.

        Args:
            None.

        Returns:
            list[Animal]: All animals across all enclosures.

        Tests:
            1. Dead animals are included, so the result is never shorter than
               :meth:`living_animals`.
            2. A zoo without enclosures returns ``[]``.
        """
        return [a for enclosure in self.enclosures for a in enclosure.animals]

    def average_welfare(self) -> float:
        """Return the mean welfare of all living animals.

        Args:
            None.

        Returns:
            float: Mean welfare (0--100); ``0.0`` if none are alive.

        Tests:
            1. Two living animals with welfare ``100.0`` and ``50.0`` give
               ``75.0``.
            2. An empty zoo -- and one whose animals are all dead -- returns
               ``0.0`` instead of dividing by zero.
        """
        living = self.living_animals()
        if not living:
            return 0.0
        return sum(a.welfare for a in living) / len(living)

    def average_happiness(self) -> float:
        """Estimate visitor satisfaction from welfare and weather.

        Args:
            None.

        Returns:
            float: A happiness percentage in 0--100.

        Tests:
            1. With no living animals and weather ``"sun"`` the result is the
               base ``60.0``.
            2. Rain costs ``8.0`` points, so the same zoo reports ``52.0``.
        """
        welfare = self.average_welfare()
        base = 60.0 + welfare * 0.35
        rain = {"sun": 0.0, "cloudy": -2.0, "rain": -8.0}[self.environment.weather]
        return max(0.0, min(100.0, base + rain))

    # ------------------------------------------------------------------
    # Tick-level coordination
    # ------------------------------------------------------------------

    def update_animals(self, tick: int, is_night: bool = False) -> None:
        """Advance every animal and enclosure, removing the dead and counting them.

        Each enclosure first ages its own upkeep (cleanliness decay), then
        every living animal is ticked. ``is_night`` is handed down so the
        animal's composed :class:`Behaviour` strategies can decide between
        feeding and resting. Dead animals are removed from their enclosures so
        they free a slot; fresh deaths increment the daily counter.

        Args:
            tick (int): The current simulation tick.
            is_night (bool): Whether it is currently night, passed on to the
                animals' behaviour strategies. Defaults to ``False``.

        Returns:
            None.

        Tests:
            1. After a death, the animal is gone from its enclosure.
            2. Freshly dead animals are counted in ``_deaths_today``.
            3. Every enclosure's cleanliness decays over enough ticks,
               because ``update_animals`` also drives ``Enclosure.tick_update``.
        """
        for enclosure in self.enclosures:
            enclosure.tick_update(tick)
            survivors: list[Animal] = []
            for animal in enclosure.animals:
                if animal.is_dead:
                    continue
                animal.tick_update(tick, is_night)
                if animal.is_dead:
                    self._deaths_today += 1
                    self.logger.log(
                        "ERROR",
                        f"{animal.name} has died.",
                        entity_id=animal.animal_id,
                        details={
                            "cause": "starvation",
                            "days_without_food": animal.days_starved,
                        },
                    )
                    continue
                survivors.append(animal)
            enclosure.animals = survivors

    def update_visitors(self, spawn_gate: tuple[int, int]) -> None:
        """Advance visitors and spawn new ones while the zoo is open.

        The spawn chance is damped by the weather so rain keeps some people
        away.

        Args:
            spawn_gate (tuple[int, int]): The gate position for new spawns.

        Returns:
            None.

        Tests:
            1. A visitor whose ``remaining_ticks`` reached ``0`` is dropped
               from ``self.visitors``.
            2. A closed zoo (``is_open`` is ``False``) spawns nobody, while
               the visitors already inside still tick and can leave.
        """
        survivors: list[Visitor] = []
        for visitor in self.visitors:
            visitor.tick()
            if visitor.is_leaving():
                continue
            survivors.append(visitor)
        self.visitors = survivors
        if self.is_open:
            multiplier = self.environment.visitor_multiplier()
            if random.random() < 0.2 * multiplier:
                self._spawn_visitor(*spawn_gate, lifetime=24)

    def update_staff(self, tick: int) -> None:
        """Run staff jobs every few ticks.

        Args:
            tick (int): The current simulation tick; a modulo guard throttles
                the work.

        Returns:
            None.

        Tests:
            1. On a tick that is a multiple of ``20`` every employee's
               ``perform_job`` runs.
            2. On any other tick the method returns early and no employee
               works.
        """
        if tick % 20 != 0:
            return
        for employee in self.employees:
            employee.perform_job(self)

    # ------------------------------------------------------------------
    # Day lifecycle
    # ------------------------------------------------------------------

    def begin_new_day(self) -> None:
        """Start a new simulation day: capture yesterday's numbers and age the animals.

        Moves today's running totals into the daily snapshot fields used by
        the persistence adapter, resets the daily counters and grows every
        animal one day older -- this is the only place ``age_one_day()`` is
        driven from.

        Args:
            None.

        Returns:
            None.

        Tests:
            1. Yesterday's revenue is captured before the finances are reset.
            2. Every animal's ``age_days`` has grown by exactly one.
            3. Visitor and death counters start the new day at ``0``, so two
               consecutive days never report cumulative figures.
        """
        self._revenue_today = self.finances.revenue_today
        self._expenses_today = self.finances.expenses_today
        # Capture the running counters, then zero them for the new day --
        # daily_snapshot() reads the captured values, not the live ones.
        self._visitors_snapshot = self._visitors_today
        self._deaths_snapshot = self._deaths_today
        self.finances.start_new_day()
        self._visitors_today = 0
        self._deaths_today = 0
        for animal in self.all_animals():
            animal.age_one_day()

    def daily_snapshot(self) -> dict:
        """Return the persisted figures for the just-finished day.

        Args:
            None.

        Returns:
            dict: Keys ``day_id``, ``total_visitors``, ``revenue``,
            ``expenses``, ``avg_animal_welfare``, ``avg_happiness``,
            ``reputation_end_of_day``, ``animals_died``.

        Tests:
            1. The dict contains every key the persistence adapter needs.
            2. ``revenue`` and ``expenses`` report the figures captured by
               ``begin_new_day()``, i.e. yesterday's totals, not the running
               ones on ``self.finances``.
        """
        return {
            "day_id": self.current_day,
            "total_visitors": self._visitors_snapshot,
            "revenue": self._revenue_today,
            "expenses": self._expenses_today,
            "avg_animal_welfare": self.average_welfare(),
            "avg_happiness": self.average_happiness(),
            "reputation_end_of_day": self.reputation,
            "animals_died": self._deaths_snapshot,
        }

    # ------------------------------------------------------------------
    # Frontend snapshot
    # ------------------------------------------------------------------

    def to_game_state(self, tick: int, time_of_day: str) -> dict:
        """Build the full snapshot the frontend polls each render frame.

        Args:
            tick (int): The current tick count.
            time_of_day (str): Current phase, e.g. ``"MORNING"``.

        Returns:
            dict: The ``game_state_data`` payload described in
            ``docs/api.md`` -- system, finances, inventory, map objects.

        Tests:
            1. The dict exposes ``system``, ``finances`` and ``inventory``.
            2. The map lists handle the empty case with ``[]``.
        """
        animals_on_map = [
            {
                "id": a.animal_id,
                "species": a.species_key(),
                "x": a.x,
                "y": a.y,
                "is_dead": a.is_dead,
            }
            for a in self.all_animals()
        ]
        visitors_on_map = [v.to_dict() for v in self.visitors]
        return {
            "system": {
                "tick_count": tick,
                "time_of_day": time_of_day,
                "zoo_open": self.is_open,
            },
            "finances": self.finances.to_dict(),
            "inventory": self.inventory.to_dict(),
            "animals_on_map": animals_on_map,
            "visitors_on_map": visitors_on_map,
        }
