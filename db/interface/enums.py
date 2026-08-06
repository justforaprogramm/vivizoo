"""Enumerations that are part of the database interface contract.

These enums define which values may appear in the corresponding columns.
They replace "magic strings" in the code and form part of the module's
public vocabulary.

All enums also inherit from :class:`str`, which means::

    EventType.WARNING == "WARNING"   # -> True

Callers may therefore pass either the enum member or the matching plain
string; both are accepted by the models (see the ``@validates`` hooks in
:mod:`db.models`).

Extending:
    A new value is a single new line. Because the enums are stored as
    ``VARCHAR`` plus a ``CHECK`` constraint (``native_enum=False``), an
    existing database file must be recreated after extending an enum -- see
    ``db/docs/architecture.md``, section "Schema changes".

Part of the vivizoo project. Module owner: Jannes (database).
"""

from __future__ import annotations

from enum import Enum

__all__ = ["EventType", "TimeOfDay", "FoodType"]


class EventType(str, Enum):
    """Kind of message stored in the ``events`` table.

    A UI uses this value to pick the colour of a chat line.

    Members:
        INFO: Ordinary status message ("Zoo has opened").
        WARNING: Something is going badly but is still recoverable
            ("Animal is hungry").
        ERROR: An action failed ("Not enough money").
        SUCCESS: An action succeeded ("All animals fed").
    """

    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    SUCCESS = "SUCCESS"


class TimeOfDay(str, Enum):
    """Phase of the simulated day, column ``zoo_state.time_of_day``.

    The day-end write into ``daily_stats`` happens at the end of
    :attr:`NIGHT`.

    Members:
        MORNING: Zoo opens, first visitors arrive.
        NOON: Peak visitor hours.
        EVENING: Visitor numbers drop, zoo closes.
        NIGHT: No visitors; the day is persisted at the end of this phase.
    """

    MORNING = "MORNING"
    NOON = "NOON"
    EVENING = "EVENING"
    NIGHT = "NIGHT"


class FoodType(str, Enum):
    """Resource kind held in stock, column ``inventory.food_type``.

    ``MEDICINE`` only becomes relevant in phase 2 (for the ``heal`` action),
    but it is already part of the enum so the schema does not have to change
    later.

    Members:
        MEAT: For carnivores (e.g. lion).
        PLANTS: For herbivores (e.g. giraffe).
        FISH: For piscivores (e.g. penguin).
        MEDICINE: Consumable used by the veterinarian (phase 2).
    """

    MEAT = "MEAT"
    PLANTS = "PLANTS"
    FISH = "FISH"
    MEDICINE = "MEDICINE"
