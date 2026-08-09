"""The player's "God mode" -- actions the frontend can trigger.

:class:`ActionHandler` implements the single entry point
``execute_action(action_name, **kwargs)`` from the planning. Every action
returns an :class:`ActionResult` describing success, a human message and any
chat entries produced -- exactly the contract the frontend consumes.

Actions implemented in the current phase:

* ``feed_all`` / ``feed_one``   -- feed every/one animal.
* ``heal``                      -- a veterinarian heals one animal.
* ``buy_food``                  -- spend budget to add to the inventory.
* ``buy_animal``                -- spend budget to add an animal.
* ``clean``                     -- reset an enclosure's cleanliness.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable

from db.interface.enums import FoodType
from backend.core.animal import Animal, create_animal, known_species

if TYPE_CHECKING:  # type checkers only, avoids a runtime cycle
    from backend.core.zoo import Zoo


@dataclass
class ActionResult:
    """The structured outcome of a player action.

    Attributes:
        success (bool): Whether the action applied.
        message (str): Human-readable summary.
        chat_entries (list[dict]): Optional events appended to the feed.
    """

    success: bool
    message: str
    chat_entries: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Render the result for the frontend.

        Args:
            None.

        Returns:
            dict: With ``success``, ``message`` and ``chat_entries``.
        """
        return {
            "success": self.success,
            "message": self.message,
            "chat_entries": self.chat_entries,
        }


class ActionHandler:
    """Dispatches named actions to concrete private methods.

    Args:
        zoo (Zoo): The zoo the actions operate on.
    """

    def __init__(self, zoo: "Zoo") -> None:
        """Create a handler bound to a zoo.

        Args:
            zoo (Zoo): The zoo to mutate.

        Returns:
            None (constructor).
        """
        self._zoo = zoo

    def execute_action(self, action_name: str, **kwargs: Any) -> ActionResult:
        """Run a named player action with keyword arguments.

        Args:
            action_name (str): One of the supported action names.
            **kwargs: Extra arguments (``animal_id``, ``species``,
                ``food``, ``amount``, ``type``, ``enclosure_id``).

        Returns:
            ActionResult: The result of the action.

        Raises:
            ValueError: If ``action_name`` is not recognised.

        Tests:
            1. ``buy_food`` with a valid type and money returns success.
            2. An unknown action name raises ``ValueError``.
        """
        actions: dict[str, Callable[..., ActionResult]] = {
            "feed_all": self._action_feed_all,
            "feed_one": self._action_feed_one,
            "heal": self._action_heal,
            "buy_food": self._action_buy_food,
            "buy_animal": self._action_buy_animal,
            "clean": self._action_clean,
        }
        handler = actions.get(action_name)
        if handler is None:
            raise ValueError(
                f"Unknown action {action_name!r}. "
                f"Valid: {', '.join(sorted(actions))}."
            )
        return handler(**kwargs)

    # ------------------------------------------------------------------
    # Concrete actions
    # ------------------------------------------------------------------

    def _action_feed_all(self, **_: Any) -> ActionResult:
        """Feed every hungry living animal using matching stock.

        Args:
            **_: Unused.

        Returns:
            ActionResult: Summary of animals fed and food used.
        """
        fed = 0
        food_used: dict[str, int] = {}
        for animal in self._zoo.all_animals():
            if animal.is_dead or animal.hunger < animal.get_feed_threshold():
                continue
            used = self._zoo.inventory.consume(animal.PREFERRED_FOOD, 1)
            if used:
                animal.feed(animal._FEED_HUNGER_GAIN)
                fed += 1
                key = animal.PREFERRED_FOOD.value
                food_used[key] = food_used.get(key, 0) + 1
        detail = ", ".join(f"{v}x {k}" for k, v in food_used.items()) or "none"
        return ActionResult(
            success=True,
            message=f"Fed {fed} animal(s). Food used: {detail}.",
            chat_entries=[{"type": "SUCCESS", "text": f"{fed} animals fed."}],
        )

    def _action_feed_one(self, animal_id: str | None = None, **_: Any) -> ActionResult:
        """Feed a single animal.

        Args:
            animal_id (str | None): Identifier of the animal to feed.

        Returns:
            ActionResult: Outcome of the single feed.
        """
        animal = self._zoo.find_animal(animal_id or "")
        if animal is None:
            return ActionResult(False, f"No animal with id {animal_id}.")
        if animal.is_dead:
            return ActionResult(False, f"{animal.name} is dead.")
        used = self._zoo.inventory.consume(animal.PREFERRED_FOOD, 1)
        if not used:
            return ActionResult(
                False, f"No {animal.PREFERRED_FOOD.value} left in stock."
            )
        animal.feed(animal._FEED_HUNGER_GAIN)
        return ActionResult(
            True,
            f"Fed {animal.name}.",
            chat_entries=[{"type": "SUCCESS", "text": f"{animal.name} fed."}],
        )

    def _action_heal(self, animal_id: str | None = None, **_: Any) -> ActionResult:
        """Heal a single animal via the veterinarian.

        Args:
            animal_id (str | None): Identifier of the animal to heal.

        Returns:
            ActionResult: Outcome of the healing.
        """
        animal = self._zoo.find_animal(animal_id or "")
        if animal is None:
            return ActionResult(False, f"No animal with id {animal_id}.")
        if animal.is_dead:
            return ActionResult(False, f"{animal.name} is dead.")
        animal._hp = max(0.0, min(100.0, animal._hp + 25.0))
        cleared = bool(animal.status_effects and animal.status_effects.pop())
        return ActionResult(
            True,
            f"Healed {animal.name}." + (" Status effect cleared." if cleared else ""),
            chat_entries=[{"type": "SUCCESS", "text": f"{animal.name} healed."}],
        )

    def _action_buy_food(self, amount: int = 1, **kw: Any) -> ActionResult:
        """Purchase food and add it to the inventory.

        Args:
            amount (int): Units to buy.
            **kw: Accepts ``food`` or the legacy ``type`` key, e.g.
                ``food="MEAT"``.

        Returns:
            ActionResult: Outcome of the purchase.
        """
        food_key = kw.pop("type", kw.pop("food", None))
        try:
            food_type = FoodType(food_key) if food_key else FoodType.MEAT
        except ValueError:
            return ActionResult(False, f"Unknown food type {food_key!r}.")
        if amount <= 0:
            return ActionResult(False, "amount must be positive.")
        total = self._zoo.inventory.price_of(food_type) * amount
        if not self._zoo.finances.spend(total):
            return ActionResult(False, "Not enough money.")
        self._zoo.inventory.add(food_type, amount)
        return ActionResult(
            True,
            f"Bought {amount}x {food_type.value} for {total:.2f}.",
            chat_entries=[
                {"type": "SUCCESS", "text": f"{amount}x {food_type.value} added."}
            ],
        )

    def _action_buy_animal(
        self,
        species: str | None = None,
        name: str | None = None,
        enclosure_id: str | None = None,
        **_: Any,
    ) -> ActionResult:
        """Buy and place a new animal.

        Args:
            species (str | None): Species key.
            name (str | None): Display name.
            enclosure_id (str | None): Target enclosure.

        Returns:
            ActionResult: Outcome of the purchase.
        """
        if species not in known_species():
            return ActionResult(False, f"Unknown species {species!r}.")
        animal_cls = create_animal(
            species,
            animal_id="tmp",
            name="tmp",
            x=Animal.FALLBACK_X,
            y=Animal.FALLBACK_Y,
        )
        price = animal_cls.BUY_PRICE
        if not self._zoo.finances.spend(price):
            return ActionResult(False, "Not enough money.")
        enclosure = self._zoo.find_enclosure(enclosure_id or "")
        if enclosure is None:
            if not self._zoo.enclosures:
                return ActionResult(False, "No enclosure exists yet.")
            enclosure = self._zoo.enclosures[0]
        if enclosure.is_full():
            return ActionResult(False, f"{enclosure.name} is full.")
        animal = self._zoo.add_animal(species, name or f"New {species}", enclosure)
        return ActionResult(
            True,
            f"Bought {animal.name} for {price:.2f} into {enclosure.name}.",
            chat_entries=[{"type": "SUCCESS", "text": f"{animal.name} arrived."}],
        )

    def _action_clean(self, enclosure_id: str | None = None, **_: Any) -> ActionResult:
        """Reset an enclosure's cleanliness to full.

        Args:
            enclosure_id (str | None): Identifier of the enclosure to clean.

        Returns:
            ActionResult: Outcome of the cleaning.
        """
        enclosure = self._zoo.find_enclosure(enclosure_id or "")
        if enclosure is None:
            return ActionResult(False, f"No enclosure with id {enclosure_id}.")
        enclosure.clean()
        return ActionResult(
            True,
            f"Cleaned {enclosure.name}.",
            chat_entries=[{"type": "SUCCESS", "text": f"{enclosure.name} cleaned."}],
        )
