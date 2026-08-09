"""The zoo's budget -- income versus expenses.

:class:`Finances` encapsulates all money movements so nothing can change the
balance except through its methods. It tracks revenue and expenses per day,
so the day-end summary can be built from the same object that owns the money.

Applied OOP principle: **encapsulation** -- the balance is private and only
reached via :meth:`spend`, :meth:`earn` and the read-only :attr:`balance`.

Part of the vivizoo project. Module owner: Benjamin (backend).
"""

from __future__ import annotations


class Finances:
    """Budget manager that owns revenue, expenses and the running total.

    Args:
        starting_balance (float): Initial money. Defaults to ``5000.0`` so a
            fresh zoo can afford its first purchases.

    Attributes:
        ticket_price (float): Current admission price.

    Class attributes:
        DEFAULT_BALANCE (float): Starting balance for a new zoo.
    """

    DEFAULT_BALANCE = 5000.0

    def __init__(self, starting_balance: float | None = None) -> None:
        """Create the budget with the given (or default) starting balance.

        Args:
            starting_balance (float | None): Initial money; ``None`` uses
                :attr:`DEFAULT_BALANCE`.

        Returns:
            None (constructor).

        Tests:
            1. ``Finances()`` starts with ``DEFAULT_BALANCE``.
            2. ``Finances(100.0).balance == 100.0``.
        """
        self._balance = (
            float(starting_balance)
            if starting_balance is not None
            else self.DEFAULT_BALANCE
        )
        self._revenue_today = 0.0
        self._expenses_today = 0.0
        self.ticket_price = 12.5

    @property
    def balance(self) -> float:
        """The current account balance (read-only).

        Returns:
            float: Money currently available.

        Tests:
            1. A fresh ``Finances()`` reports ``balance == 5000.0``.
            2. Assigning to ``balance`` raises ``AttributeError`` because the
               property has no setter.
        """
        return self._balance

    @property
    def revenue_today(self) -> float:
        """Income accumulated so far today.

        Returns:
            float: Today's revenue.

        Tests:
            1. A fresh budget reports ``revenue_today == 0.0``.
            2. After ``earn(20.0)`` it is ``20.0``; a later ``spend`` leaves it
               unchanged.
        """
        return self._revenue_today

    @property
    def expenses_today(self) -> float:
        """Spending accumulated so far today.

        Returns:
            float: Today's expenses.

        Tests:
            1. A fresh budget reports ``expenses_today == 0.0``.
            2. A ``spend`` that returns ``False`` (insufficient balance) leaves
               ``expenses_today`` unchanged.
        """
        return self._expenses_today

    def earn(self, amount: float) -> None:
        """Add income (e.g. ticket sales).

        Args:
            amount (float): A non-negative amount to add.

        Returns:
            None.

        Tests:
            1. A positive amount increases ``balance`` and ``revenue_today``.
            2. A negative amount raises ``ValueError``.
        """
        if amount < 0:
            raise ValueError(f"amount must not be negative, got {amount}.")
        self._balance += amount
        self._revenue_today += amount

    def spend(self, amount: float) -> bool:
        """Spend money if the budget can cover it.

        Args:
            amount (float): A non-negative amount to withdraw.

        Returns:
            bool: ``True`` if the money was spent, ``False`` if the balance
            is insufficient (nothing is withdrawn, and ``expenses_today`` is
            unchanged).

        Tests:
            1. With enough money, spending succeeds and reduces the balance.
            2. With insufficient money, spending returns ``False`` and leaves
               the balance unchanged.
        """
        if amount < 0:
            raise ValueError(f"amount must not be negative, got {amount}.")
        if self._balance < amount:
            return False
        self._balance -= amount
        self._expenses_today += amount
        return True

    def pay_ticket(self) -> float:
        """Process one visitor paying the current ticket price.

        Args:
            None.

        Returns:
            float: The amount earned (``ticket_price``).

        Tests:
            1. After a ticket payment, ``revenue_today`` grew by the price.
            2. The return value equals ``ticket_price``, so after
               ``set_ticket_price(0.0)`` it returns ``0.0`` and the balance is
               unchanged.
        """
        self.earn(self.ticket_price)
        return self.ticket_price

    def start_new_day(self) -> None:
        """Reset today's revenue and expense counters.

        Called by the engine at each day boundary; the previous day's figures
        must have been captured (persisted) before this call.

        Args:
            None.

        Returns:
            None.

        Tests:
            1. After a call both ``revenue_today`` and ``expenses_today`` are
               zero.
            2. ``balance`` and ``ticket_price`` are untouched by the reset.
        """
        self._revenue_today = 0.0
        self._expenses_today = 0.0

    def set_ticket_price(self, price: float) -> None:
        """Change the admission price.

        Args:
            price (float): New ticket price; must be non-negative.

        Returns:
            None.

        Tests:
            1. A non-negative price is stored.
            2. A negative price raises ``ValueError``.
        """
        if price < 0:
            raise ValueError(f"price must not be negative, got {price}.")
        self.ticket_price = price

    def to_dict(self) -> dict:
        """Render the financial snapshot for the frontend.

        Args:
            None.

        Returns:
            dict: With ``money``, ``revenue``, ``expenses`` and
            ``ticket_price``.

        Tests:
            1. A fresh budget renders ``money`` as ``5000.0`` with ``revenue``
               and ``expenses`` at ``0.0`` and ``ticket_price`` at ``12.5``.
            2. ``money`` follows the balance, so after ``spend(500.0)`` the
               dict reports ``4500.0``.
        """
        return {
            "money": round(self._balance, 2),
            "revenue": round(self._revenue_today, 2),
            "expenses": round(self._expenses_today, 2),
            "ticket_price": self.ticket_price,
        }

    def __repr__(self) -> str:  # pragma: no cover - debugging
        """Return a short readable representation.

        Args:
            None.

        Returns:
            str: Named debug string.

        Tests:
            1. The string contains the balance with two decimals, e.g.
               ``<Finances balance=5000.00>``.
            2. It is stable across calls on an unchanged object.
        """
        return f"<Finances balance={self._balance:.2f}>"
