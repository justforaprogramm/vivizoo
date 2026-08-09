"""The staff hierarchy -- chapter 1 ("Zoo-Verwaltung").

:class:`Employee` is an abstract base describing a staff member's shared
attributes (``employee_id``, ``name``) and its core task. Three subclasses
implement the three roles the assignment names:

* :class:`Keeper`        -- feeds and cleans.
* :class:`Veterinarian`  -- heals animals and removes status effects.
* :class:`AdminStaff`    -- manages the budget and ticket price.

Polymorphism: the caller calls :meth:`Employee.perform_job`, and each role
carries out its own work against the zoo. In the current phase the staff
perform their jobs as part of the engine's tick loop (or can be triggered
directly through God mode).

Part of the vivizoo project. Module owner: Benjamin (backend).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from db.interface.enums import FoodType

if TYPE_CHECKING:  # type checkers only, avoids a runtime cycle
    from backend.core.zoo import Zoo


class Employee(ABC):
    """Base of every staff member.

    Args:
        employee_id (str): Unique identifier, e.g. ``"st_01"``.
        name (str): Display name.
        salary (float): Daily wage drawn from the budget.
    """

    def __init__(self, employee_id: str, name: str, salary: float) -> None:
        """Create a staff member.

        Args:
            employee_id (str): Unique identifier.
            name (str): Display name.
            salary (float): Daily wage; must be non-negative.

        Returns:
            None (constructor).

        Tests:
            1. A staff member stores its id, name and salary.
            2. A negative salary raises ``ValueError``.
        """
        if salary < 0:
            raise ValueError(f"salary must not be negative, got {salary}.")
        self.employee_id = employee_id
        self.name = name
        self.salary = salary

    @abstractmethod
    def perform_job(self, zoo: "Zoo") -> None:
        """Carry out this employee's task against the given zoo.

        Args:
            zoo (Zoo): The zoo this employee works for.

        Returns:
            None.
        """

    @property
    def role(self) -> str:
        """Return the human-readable role name.

        Returns:
            str: Lower-case class name (e.g. ``"keeper"``).
        """
        return self.__class__.__name__.lower()

    def __repr__(self) -> str:  # pragma: no cover - debugging
        """Return a short readable representation.

        Args:
            None.

        Returns:
            str: Named debug string.
        """
        return f"<{self.__class__.__name__} {self.employee_id} ({self.name})>"


class Keeper(Employee):
    """Feeds hungry animals and cleans enclosures.

    The keeper walks the zoo once per job: it feeds any living animal whose
    hunger has dropped below its feeding threshold (consuming the species'
    preferred food from the inventory) and resets the cleanliness of every
    enclosure.
    """

    SALARY = 60.0

    def __init__(self, employee_id: str, name: str) -> None:
        """Create a keeper.

        Args:
            employee_id (str): Unique identifier.
            name (str): Display name.

        Returns:
            None (constructor).
        """
        super().__init__(employee_id, name, self.SALARY)

    def perform_job(self, zoo: "Zoo") -> None:
        """Feed hungry animals and clean all enclosures.

        Args:
            zoo (Zoo): The zoo to maintain.

        Returns:
            None.

        Tests:
            1. After a job, every hungry animal was fed (if food was in
               stock).
            2. After a job, every enclosure is ``100.0`` clean.
        """
        for enclosure in zoo.enclosures:
            enclosure.clean()
            for animal in enclosure.animals:
                self._feed_if_needed(zoo, animal)
        zoo.logger.log(
            "INFO",
            f"Keeper {self.name} cleaned the enclosures and fed the animals.",
            entity_id=self.employee_id,
        )

    def _feed_if_needed(self, zoo: "Zoo", animal: "object") -> None:
        """Feed one animal if it wants food and the stock allows it.

        Args:
            zoo (Zoo): The zoo whose inventory is drawn from.
            animal (Animal): The animal to consider.

        Returns:
            None.

        Tests:
            1. A hungry animal with matching food in stock is fed.
            2. If stock is empty the animal is not fed.
        """
        if animal.is_dead:
            return
        if animal.hunger > animal.get_feed_threshold():
            return
        food_type = animal.PREFERRED_FOOD
        used = zoo.inventory.consume(food_type, 1)
        if used:
            animal.feed(animal._FEED_HUNGER_GAIN)


class Veterinarian(Employee):
    """Heals animals and clears their status effects.

    The veterinarian spends medicine per treatment. If no medicine is in
    stock it still restores a little health but the status effect stays.
    """

    SALARY = 90.0

    def __init__(self, employee_id: str, name: str) -> None:
        """Create a veterinarian.

        Args:
            employee_id (str): Unique identifier.
            name (str): Display name.

        Returns:
            None (constructor).
        """
        super().__init__(employee_id, name, self.SALARY)

    def heal(self, zoo: "Zoo", animal: "object") -> bool:
        """Treat a single animal, restoring health and clearing an effect.

        Args:
            zoo (Zoo): The zoo whose inventory provides medicine.
            animal (Animal): The animal to heal.

        Returns:
            bool: ``True`` if the animal was treated, ``False`` if it is
            dead.

        Tests:
            1. A living animal is healed and loses one status effect.
            2. A dead animal is left untouched and ``False`` is returned.
        """
        if animal.is_dead:
            return False
        # Medicine is consumed per treatment; healing health works even
        # without medicine, but the status effect is only cleared when
        # medicine was available.
        used_medicine = zoo.inventory.consume(FoodType.MEDICINE, 1)
        animal._hp = max(0.0, min(100.0, animal._hp + 20.0))
        if used_medicine and animal.status_effects:
            animal.status_effects.pop()
        zoo.logger.log(
            "SUCCESS",
            f"Veterinarian {self.name} healed {animal.name}.",
            entity_id=animal.animal_id,
        )
        return True

    def perform_job(self, zoo: "Zoo") -> None:
        """Heal the first critical animal, if any.

        Args:
            zoo (Zoo): The zoo to care for.

        Returns:
            None.
        """
        for enclosure in zoo.enclosures:
            for animal in enclosure.animals:
                if not animal.is_dead and animal.is_critical():
                    self.heal(zoo, animal)
                    return


class AdminStaff(Employee):
    """Manages the budget and ticket price.

    The admin adjusts the ticket price around the zoo's reputation: a well
    regarded zoo can charge more without scaring visitors away.
    """

    SALARY = 80.0

    def __init__(self, employee_id: str, name: str) -> None:
        """Create an admin staff member.

        Args:
            employee_id (str): Unique identifier.
            name (str): Display name.

        Returns:
            None (constructor).
        """
        super().__init__(employee_id, name, self.SALARY)

    def perform_job(self, zoo: "Zoo") -> None:
        """Tune the ticket price from the current reputation.

        Args:
            zoo (Zoo): The zoo whose finances are adjusted.

        Returns:
            None.

        Tests:
            1. Higher reputation raises the ticket price.
        """
        base = 10.0 + zoo.reputation * 0.05
        zoo.finances.set_ticket_price(round(base, 2))
        zoo.logger.log(
            "INFO",
            f"Admin {self.name} set the ticket price to "
            f"{zoo.finances.ticket_price:.2f}.",
            entity_id=self.employee_id,
        )
