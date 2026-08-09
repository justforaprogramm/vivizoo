"""Model for the ``animals`` table -- including the species hierarchy.

This module is the centrepiece of the persistence layer's object-oriented
design. The ``species`` column doubles as a **discriminator**: SQLAlchemy
reads it to decide which Python class an loaded row becomes.

    class Animal(Base):
        __mapper_args__ = {"polymorphic_on": "species", ...}

    class Lion(Animal):
        __mapper_args__ = {"polymorphic_identity": "lion"}

Because of that, ``session.scalars(select(Animal))`` does **not** return a
list of ``Animal`` objects -- it returns ``Lion``, ``Giraffe`` and ``Penguin``
instances, each with its own class attributes and its own behaviour. The
database resolves the inheritance itself; no ``if species == ...`` chain is
needed anywhere.

All species share one table (single-table inheritance). This costs no extra
columns and no joins, which is exactly right here because the species differ
in *behaviour*, not in *stored fields*.

Adding a new species:
    Three lines -- see :class:`Lion` as the template. Nothing else changes:
    no migration, no new table, no change in the persistence layer.

Part of the vivizoo project. Module owner: Jannes (database).

Authorship:
    Drafted with AI assistance and completed under a human-in-the-loop
    process: every declaration in this file was read, executed and reconciled
    with ``planning/db_planning/db_requirements.md`` before it was committed.
    ``db/docs/ai_usage.md`` records what that review covered and the ten
    defects it caught.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Float,
    ForeignKey,
    Integer,
    String,
    inspect as sa_inspect,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from db.interface.enums import FoodType
from db.models.base import Base

if TYPE_CHECKING:  # imported for type checkers only, not at runtime
    from db.models.animal_status_effect import AnimalStatusEffect
    from db.models.enclosure import Enclosure

__all__ = [
    "Animal",
    "Lion",
    "Giraffe",
    "Penguin",
    "create_animal",
    "known_species",
]


class Animal(Base):
    """Base class of every animal and the mapping of the ``animals`` table.

    Do **not** instantiate this class directly for a real species -- use the
    subclass (``Lion(...)``) or the factory :func:`create_animal`. Two ways it
    goes wrong:

    * ``Animal(animal_id="a_01", ...)`` with the species omitted stores the
      base discriminator ``"animal"``, and the row loads back as a plain
      ``Animal`` whose ``PREFERRED_FOOD`` is the default ``MEAT`` -- whatever
      the animal was meant to be.
    * ``Animal(species="lyon")`` stores the typo verbatim. Nothing rejects it,
      and on load SQLAlchemy finds no class for that identity.

    Passing a *correct* species string does work -- ``Animal(species="lion")``
    really does store ``"lion"`` -- but it silently produces an ``Animal``
    instance rather than a ``Lion``, so the object in memory lacks the
    subclass behaviour until it has been round-tripped through the database.
    :func:`create_animal` avoids all three traps.

    Attributes:
        animal_id (str): Identifier such as ``"a_01"``. Primary key, assigned
            by the application.
        enclosure_id (str): Enclosure the animal lives in (foreign key to
            ``enclosures.enclosure_id``).
        name (str): The animal's given name, e.g. ``"Hungry Harry"``.
        species (str): Discriminator column. Set automatically from the
            class -- never assign it by hand.
        age_days (int): Age in simulation days.
        hp (float): Current health in percent (0--100).
        hunger (float): Current hunger level in percent (0--100), where 100
            means starving.
        welfare (float): Current well-being in percent (0--100).
        is_dead (bool): Whether the animal has died.
        pos_x (int): X position on the map.
        pos_y (int): Y position on the map.
        enclosure (Enclosure): The enclosure this animal lives in.
        status_effects (list[AnimalStatusEffect]): Active status effects;
            deleted together with the animal.

    Class attributes:
        PREFERRED_FOOD (FoodType): Which resource this species eats.
            Overridden by every subclass -- this is the polymorphic part that
            the application can read without knowing the concrete class.
    """

    __tablename__ = "animals"
    __table_args__ = (
        CheckConstraint("hp BETWEEN 0 AND 100", name="ck_animal_hp"),
        CheckConstraint("hunger BETWEEN 0 AND 100", name="ck_animal_hunger"),
        CheckConstraint("welfare BETWEEN 0 AND 100", name="ck_animal_welfare"),
        CheckConstraint("age_days >= 0", name="ck_animal_age"),
    )

    PREFERRED_FOOD: FoodType = FoodType.MEAT

    animal_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    enclosure_id: Mapped[str] = mapped_column(
        ForeignKey("enclosures.enclosure_id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    species: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        doc="Discriminator column -- set automatically from the class.",
    )
    age_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    hp: Mapped[float] = mapped_column(Float, default=100.0, nullable=False)
    hunger: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    welfare: Mapped[float] = mapped_column(Float, default=100.0, nullable=False)
    is_dead: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    pos_x: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    pos_y: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    enclosure: Mapped["Enclosure"] = relationship(back_populates="animals")
    status_effects: Mapped[list["AnimalStatusEffect"]] = relationship(
        back_populates="animal",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="AnimalStatusEffect.id",
    )

    __mapper_args__ = {
        "polymorphic_on": "species",
        "polymorphic_identity": "animal",
    }

    @validates("hp", "hunger", "welfare")
    def _check_percentage(self, field: str, value: float) -> float:
        """Keep all three percentage attributes inside 0--100.

        One validator covers three columns, which is why the ``field``
        argument matters -- it names which attribute is currently being set
        and makes the error message specific.

        Args:
            field (str): Name of the attribute being set: ``"hp"``,
                ``"hunger"`` or ``"welfare"``. Supplied by SQLAlchemy.
            value (float): The value about to be assigned.

        Returns:
            float: The unchanged value if it is valid.

        Raises:
            ValueError: If ``value`` is below 0 or above 100.

        Tests:
            1. Assigning ``hp = 0.0`` succeeds and the error message of a
               later invalid assignment mentions the correct field name.
            2. Assigning ``hunger = 100.1`` raises ``ValueError``, and so does
               ``welfare = -0.1`` -- confirming the validator really is
               attached to all three columns.
        """
        if not 0 <= value <= 100:
            raise ValueError(f"{field} must be between 0 and 100, got {value}.")
        return value

    def is_critical(self) -> bool:
        """Report whether the animal needs attention right now.

        Lets a caller highlight animals that need help, or decide which one
        to treat first.

        Args:
            None (instance method, only ``self``).

        Returns:
            bool: ``True`` if the animal is alive and either its health has
            dropped to 25 % or below, or its hunger has risen to 75 % or
            above. Dead animals always return ``False`` -- they no longer
            need help.

        Tests:
            1. An animal with ``hp=20.0, hunger=0.0, is_dead=False`` returns
               ``True``; one with ``hp=100.0, hunger=80.0`` also returns
               ``True`` (either condition suffices).
            2. An animal with ``hp=10.0, is_dead=True`` returns ``False``
               despite the critical health, and a healthy animal
               (``hp=100.0, hunger=0.0``) returns ``False``.
        """
        if self.is_dead:
            return False
        return self.hp <= 25.0 or self.hunger >= 75.0


class Lion(Animal):
    """Carnivore. Template for adding further species.

    Adding a species requires exactly this much code: a class, a
    ``polymorphic_identity`` matching the value stored in ``species``, and the
    preferred food.

    Attributes:
        PREFERRED_FOOD (FoodType): :attr:`~db.interface.enums.FoodType.MEAT`.
    """

    PREFERRED_FOOD = FoodType.MEAT
    __mapper_args__ = {"polymorphic_identity": "lion"}


class Giraffe(Animal):
    """Herbivore.

    Attributes:
        PREFERRED_FOOD (FoodType): :attr:`~db.interface.enums.FoodType.PLANTS`.
    """

    PREFERRED_FOOD = FoodType.PLANTS
    __mapper_args__ = {"polymorphic_identity": "giraffe"}


class Penguin(Animal):
    """Piscivore.

    Attributes:
        PREFERRED_FOOD (FoodType): :attr:`~db.interface.enums.FoodType.FISH`.
    """

    PREFERRED_FOOD = FoodType.FISH
    __mapper_args__ = {"polymorphic_identity": "penguin"}


def known_species() -> dict[str, type[Animal]]:
    """List every registered species and the class implementing it.

    Reads SQLAlchemy's polymorphic map at runtime, so a newly added subclass
    shows up here automatically -- there is no second list to keep in sync.

    Args:
        None.

    Returns:
        dict[str, type[Animal]]: Mapping ``species value -> class``, for
        example ``{"lion": Lion, "giraffe": Giraffe, "penguin": Penguin}``.
        The abstract base identity ``"animal"`` is excluded.

    Tests:
        1. The result contains the key ``"lion"`` mapped to the class
           :class:`Lion`, and its length equals the number of concrete
           subclasses (3 at present).
        2. The result does *not* contain the key ``"animal"``, confirming the
           abstract base identity is filtered out.
    """
    mapper = sa_inspect(Animal).mapper
    return {
        identity: sub_mapper.class_
        for identity, sub_mapper in mapper.polymorphic_map.items()
        if identity != "animal"
    }


def create_animal(species: str, **fields: Any) -> Animal:
    """Create an animal of the right class from a species string.

    This is the safe way for the application to build an animal when the species
    only exists as a string (e.g. coming from ``execute_action("buy_animal",
    species="penguin")``). It removes the trap of instantiating
    :class:`Animal` directly and ending up with the wrong discriminator.

    Args:
        species (str): Species identifier, e.g. ``"lion"``. Case-insensitive.
            Must match one of the keys returned by :func:`known_species`.
        **fields (Any): Any further column values forwarded to the
            constructor, e.g. ``animal_id="a_01"``, ``name="Harry"``,
            ``enclosure_id="e_01"``.

    Returns:
        Animal: A new instance of the matching subclass (e.g. :class:`Lion`),
        not yet persisted.

    Raises:
        ValueError: If ``species`` matches no registered class. The message
            lists all valid species.

    Tests:
        1. ``create_animal("penguin", animal_id="a_02", name="Pingu",
           enclosure_id="e_01")`` returns an object that
           ``isinstance(result, Penguin)`` confirms, and whose
           ``PREFERRED_FOOD`` is ``FoodType.FISH``.
        2. ``create_animal("LION", ...)`` works too (case-insensitive), while
           ``create_animal("dragon")`` raises ``ValueError`` whose message
           contains the word ``"lion"`` among the valid options.
    """
    registry = known_species()
    animal_class = registry.get(species.lower())
    if animal_class is None:
        allowed = ", ".join(sorted(registry))
        raise ValueError(f"Unknown species {species!r}. Registered species: {allowed}.")
    return animal_class(**fields)
