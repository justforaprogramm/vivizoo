"""Food storage -- the world's resource buffer.

:class:`Inventory` holds the amount of each resource type (``MEAT``,
``PLANTS``, ``FISH`` and, later, ``MEDICINE``) and enforces that the amounts
never drop below zero. :class:`Food` models a single purchased/consumed unit
and already carries the fields that the phase-2 spoilage system needs
(``purchase_tick``, ``is_spoiled()``).

The resource keys reuse :class:`db.interface.FoodType`, so the stock can be
mapped to the ``inventory`` table without string juggling.

Part of the vivizoo project. Module owner: Benjamin (backend).
"""

from __future__ import annotations

from db.interface.enums import FoodType


class Food:
    """A single consumable item of a given food type.

    Phase note: in the current phase items never spoil (``is_spoiled()``
    returns ``False``). The purchase timestamp is recorded now so the spoilage
    and poisoned-feed logic can be switched on in phase 2 without schema or
    interface changes.

    Args:
        food_type (FoodType): Which resource this is.
        amount (int): Units in this item, usually ``1``.
        purchase_tick (int): Tick at which it was bought.
    """

    def __init__(self, food_type: FoodType, amount: int, purchase_tick: int) -> None:
        """Create a food item.

        Args:
            food_type (FoodType): Which resource.
            amount (int): Units; must be non-negative.
            purchase_tick (int): Purchase timestamp.

        Returns:
            None (constructor).

        Tests:
            1. A fresh item never spoils in the current phase.
        """
        if amount < 0:
            raise ValueError(f"amount must not be negative, got {amount}.")
        self.food_type = food_type
        self.amount = amount
        self.purchase_tick = purchase_tick

    def is_spoiled(self, current_tick: int) -> bool:
        """Report whether the item has gone bad.

        Args:
            current_tick (int): The current simulation tick.

        Returns:
            bool: ``False`` in the current phase (spoilage disabled).

        Tests:
            1. Always returns ``False`` regardless of age for now.
        """
        # Spoilage is a phase-2 feature; the field exists to keep the shape.
        return False

    def __repr__(self) -> str:  # pragma: no cover - debugging
        """Return a short readable representation.

        Args:
            None.

        Returns:
            str: Named debug string.
        """
        return f"<Food {self.food_type.value} x{self.amount}>"


class Inventory:
    """A dictionary-backed store of resource amounts, never negative.

    Args:
        None.

    Attributes:
        FOOD_PRICES (dict[FoodType, float]): Purchase price per resource in
            budget units.
    """

    FOOD_PRICES: dict[FoodType, float] = {
        FoodType.MEAT: 8.0,
        FoodType.PLANTS: 5.0,
        FoodType.FISH: 6.0,
        FoodType.MEDICINE: 25.0,
    }

    def __init__(self) -> None:
        """Create an empty inventory.

        Args:
            None.

        Returns:
            None (constructor).

        Tests:
            1. A fresh inventory has zero for every food type.
        """
        self._stock: dict[FoodType, int] = {food_type: 0 for food_type in FoodType}

    def stock_of(self, food_type: FoodType) -> int:
        """Return the current amount of one resource.

        Args:
            food_type (FoodType): The resource to query.

        Returns:
            int: Units in stock, never negative.
        """
        return self._stock[food_type]

    def add(self, food_type: FoodType, amount: int) -> None:
        """Add units of a resource to the store.

        Args:
            food_type (FoodType): Which resource.
            amount (int): Units to add; must be non-negative.

        Returns:
            None.

        Tests:
            1. Adding units increases the stock by that amount.
            2. Adding a negative amount raises ``ValueError``.
        """
        if amount < 0:
            raise ValueError(f"amount must not be negative, got {amount}.")
        self._stock[food_type] += amount

    def consume(self, food_type: FoodType, amount: int) -> int:
        """Remove units of a resource, capped at what is in stock.

        Args:
            food_type (FoodType): Which resource.
            amount (int): Units requested; must be non-negative.

        Returns:
            int: The units actually removed (0 if there was none of that
            type).

        Tests:
            1. With enough stock, the full amount is removed.
            2. With too little stock, only what is available is removed and
               the balance never goes negative.
        """
        if amount < 0:
            raise ValueError(f"amount must not be negative, got {amount}.")
        removed = min(self._stock[food_type], amount)
        self._stock[food_type] -= removed
        return removed

    def price_of(self, food_type: FoodType) -> float:
        """Return the budget cost of one unit of a resource.

        Args:
            food_type (FoodType): The resource.

        Returns:
            float: Price per unit.
        """
        return self.FOOD_PRICES.get(food_type, 0.0)

    def to_dict(self) -> dict[str, int]:
        """Render the stock as a plain dict keyed by food-type value.

        The frontend uses this to grey out buttons, so the keys are the
        string forms (``"MEAT"`` etc.).

        Args:
            None.

        Returns:
            dict[str, int]: Mapping like ``{"MEAT": 15, "PLANTS": 0, ...}``.

        Tests:
            1. Keys match ``FoodType`` values.
        """
        return {food_type.value: amount for food_type, amount in self._stock.items()}

    def __repr__(self) -> str:  # pragma: no cover - debugging
        """Return a short readable representation.

        Args:
            None.

        Returns:
            str: Named debug string.
        """
        return f"<Inventory {self.to_dict()}>"
