"""Environmental influence on the simulation.

:class:`EnvironmentFactor` models the weather and temperature. It is part of
the area "Umweltfaktor" in the assignment. In the current phase the factor is
mostly ambient -- it influences welfare and visitor spawn slightly -- but it
is fully wired so that altering the weather has an observable effect without
any structural change.

The possible weathers are the values in :attr:`EnvironmentFactor.WEATHERS`.
"""

from __future__ import annotations

import random


class EnvironmentFactor:
    """Drives the weather and reports its effect on welfare.

    Args:
        weather (str | None): Starting weather; ``None`` picks a random one.
        temperature (float): Starting temperature in Celsius.

    Attributes:
        WEATHERS (tuple[str, ...]): Valid weather values.
    """

    WEATHERS: tuple[str, ...] = ("sun", "rain", "cloudy")

    def __init__(
        self, weather: str | None = None, temperature: float = 20.0
    ) -> None:
        """Create an environment factor with a starting weather.

        Args:
            weather (str | None): Initial weather; ``None`` selects one at
                random.
            temperature (float): Initial temperature in Celsius.

        Returns:
            None (constructor).

        Tests:
            1. ``EnvironmentFactor("sun", 22.0)`` reports weather ``"sun"``.
            2. ``EnvironmentFactor(None)`` picks one of :attr:`WEATHERS`.
        """
        if weather is None:
            weather = random.choice(self.WEATHERS)
        if weather not in self.WEATHERS:
            raise ValueError(
                f"Unknown weather {weather!r}. Valid: {self.WEATHERS}."
            )
        self.weather = weather
        self.temperature = temperature

    def welfare_modifier(self) -> float:
        """Return a welfare adjustment from the current weather.

        Args:
            None.

        Returns:
            float: ``0.0`` in sunshine, ``-3.0`` in rain, ``-1.0`` when
            cloudy.

        Tests:
            1. ``"sun"`` gives ``0.0`` and ``"rain"`` gives a negative value.
        """
        return {"sun": 0.0, "rain": -3.0, "cloudy": -1.0}[self.weather]

    def visitor_multiplier(self) -> float:
        """Return a factor on visitor spawn rate from the weather.

        Args:
            None.

        Returns:
            float: ``1.0`` for sun/cloudy, ``0.6`` for rain.

        Tests:
            1. Rain lowers the visitor spawn factor below ``1.0``.
        """
        return 0.6 if self.weather == "rain" else 1.0

    def randomize(self) -> None:
        """Pick a new random weather and a slightly varied temperature.

        Args:
            None.

        Returns:
            None.

        Tests:
            1. After the call the weather is one of :attr:`WEATHERS`.
        """
        self.weather = random.choice(self.WEATHERS)
        self.temperature += random.uniform(-2.0, 2.0)

    def to_dict(self) -> dict:
        """Render the current weather for the frontend.

        Args:
            None.

        Returns:
            dict: With ``weather`` and ``temperature``.
        """
        return {
            "weather": self.weather,
            "temperature": round(self.temperature, 1),
        }
