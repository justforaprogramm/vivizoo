"""Shared foundation for every ORM model (every table blueprint).

Three building blocks live here:

* :class:`Base` -- the declarative base class. Every model inherits from it;
  SQLAlchemy collects all tables in ``Base.metadata`` and can create them
  with a single call.
* :class:`TimestampMixin` -- a mixin contributing a timestamp column. Mixins
  are pulled in via multiple inheritance and are the clean way to reuse the
  same column across tables without forcing them to share a parent table.
* Two helper functions converting between Python values and JSON-friendly
  primitives.

Why do ``as_dict()`` / ``from_dict()`` live here instead of in each model?
    Both read the column list from the mapper at runtime, so they work for
    *every* model automatically -- including ones added later. A new table
    inherits serialisation and deserialisation without a single extra line
    of code.

Part of the vivizoo project. Module owner: Jannes (database).

Authorship:
    Drafted with AI assistance and completed under a human-in-the-loop
    process: every declaration in this file was read, executed and reconciled
    with ``planning/db_planning/db_requirements.md`` before it was committed.
    ``db/docs/ai_usage.md`` records what that review covered and the ten
    defects it caught.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from sqlalchemy import DateTime, Enum as SAEnum, event, inspect as sa_inspect
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import TypeEngine

__all__ = ["Base", "TimestampMixin"]


def _to_primitive(value: Any) -> Any:
    """Convert a Python value into a JSON-friendly primitive.

    Used by :meth:`Base.as_dict` so the returned dictionaries can be handed
    straight to a UI or written into a JSON file.

    Args:
        value (Any): Any model attribute value. Typically ``int``, ``float``,
            ``str``, ``bool``, ``None``, an :class:`~enum.Enum` or a
            :class:`~datetime.datetime`.

    Returns:
        Any: ``Enum`` -> its ``.value`` (str); ``datetime`` -> ISO-8601 string
        (e.g. ``"2026-08-02T21:15:00"``). Every other value is returned
        unchanged.

    Tests:
        1. ``_to_primitive(EventType.WARNING)`` returns exactly the string
           ``"WARNING"`` and *not* an enum member.
        2. ``_to_primitive(datetime(2026, 8, 2, 21, 15))`` returns
           ``"2026-08-02T21:15:00"``, while ``_to_primitive(42)`` returns
           ``42`` unchanged (pass-through case).
    """
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def _from_primitive(column_type: TypeEngine, value: Any) -> Any:
    """Convert a JSON primitive back into the column's Python type.

    Counterpart of :func:`_to_primitive`; used by :meth:`Base.from_dict` to
    rebuild real objects from a parsed dictionary.

    Args:
        column_type (TypeEngine): SQLAlchemy type of the target column, e.g.
            ``DateTime()`` or ``Enum(EventType)``. Determines which Python
            type the value has to be converted into.
        value (Any): The raw value taken from the dictionary (usually ``str``,
            ``int``, ``float``, ``bool`` or ``None``).

    Returns:
        Any: A :class:`~datetime.datetime` for ``DateTime`` columns, the
        matching enum member for ``Enum`` columns, otherwise the unchanged
        value. ``None`` is always passed through untouched.

    Tests:
        1. With ``column_type=DateTime()`` and ``value="2026-08-02T21:15:00"``
           a ``datetime`` with year 2026 is returned.
        2. With ``column_type=Enum(EventType)`` and ``value="WARNING"`` the
           member ``EventType.WARNING`` is returned; with ``value=None`` the
           result is ``None`` and no exception is raised.
    """
    if value is None:
        return None
    if isinstance(column_type, DateTime) and isinstance(value, str):
        return datetime.fromisoformat(value)
    if isinstance(column_type, SAEnum):
        return column_type.python_type(value)
    return value


class Base(DeclarativeBase):
    """Declarative base class for every table model.

    Every model class (``DailyStats``, ``Event``, ``Animal`` ...) inherits
    from this class. SQLAlchemy automatically registers the table in
    ``Base.metadata``, so ``Base.metadata.create_all(engine)`` creates *all*
    tables at once -- no handwritten ``CREATE TABLE`` anywhere.

    On top of that the class provides serialisation for all subclasses
    (:meth:`as_dict` / :meth:`from_dict`) and a readable :meth:`__repr__` for
    debugging and console output.
    """

    def as_dict(self) -> dict[str, Any]:
        """Return every column value of this object as a JSON-friendly dict.

        Relationships to other tables (e.g. ``Enclosure.animals``) are *not*
        included -- only real columns. That way the method can never recurse
        infinitely and never triggers a lazy database load.

        Args:
            None (instance method, only ``self``).

        Returns:
            dict[str, Any]: Mapping ``column name -> value``. Enums are turned
            into strings and ``datetime`` into ISO strings. Example::

                {"day_id": 1, "total_visitors": 120, "revenue": 840.0, ...}

        Tests:
            1. For ``DailyStats(day_id=1, total_visitors=120)`` the result
               contains the key ``"day_id"`` with value ``1`` and *no* key
               ``"events"`` (that is a relationship, not a column).
            2. For ``Event(type=EventType.INFO)`` the entry ``result["type"]``
               is of type ``str`` and not ``EventType``, making the result
               directly usable with ``json.dumps``.
        """
        mapper = sa_inspect(type(self)).mapper
        return {
            attribute.key: _to_primitive(getattr(self, attribute.key))
            for attribute in mapper.column_attrs
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Any:
        """Rebuild a model object from a dictionary.

        Counterpart of :meth:`as_dict`. Unknown keys are ignored so an older
        JSON backup does not break when a column is renamed later.

        **Computed columns are skipped.** ``daily_stats.profit_loss`` is
        calculated by the database itself; setting it would make SQLAlchemy
        reject the INSERT.

        Args:
            data (dict[str, Any]): Dictionary in the format produced by
                :meth:`as_dict`. Missing keys simply leave the corresponding
                column at its default value.

        Returns:
            Any: A new, **not yet persisted** instance of ``cls``. The object
            is not attached to any session; only a ``save_*`` call writes it
            to the database.

        Tests:
            1. ``DailyStats.from_dict({"day_id": 5, "revenue": 100.0})``
               returns an object with ``day_id == 5`` while the omitted
               column ``expenses`` keeps its default ``0.0``.
            2. A dictionary that additionally contains ``"profit_loss": 999.0``
               and ``"does_not_exist": 1`` still produces a valid object --
               both keys are silently ignored.
        """
        mapper = sa_inspect(cls).mapper
        fields: dict[str, Any] = {}
        for attribute in mapper.column_attrs:
            column = attribute.columns[0]
            if column.computed is not None:
                continue  # calculated by the database -> not settable
            if attribute.key not in data:
                continue
            fields[attribute.key] = _from_primitive(column.type, data[attribute.key])
        return cls(**fields)

    def __repr__(self) -> str:
        """Return a compact, readable text representation of the object.

        Only primary key columns are shown so the output stays short even for
        tables with many columns.

        Args:
            None (instance method, only ``self``).

        Returns:
            str: Text of the form ``<DailyStats day_id=3>``, or for composite
            keys ``<InventoryItem zoo_id=1, food_type=<FoodType.MEAT: 'MEAT'>>``
            -- values are rendered with ``!r``, so an enum shows its full
            repr rather than just its value.

        Tests:
            1. ``repr(DailyStats(day_id=3))`` contains both the class name
               ``"DailyStats"`` and ``"day_id=3"``.
            2. ``repr(InventoryItem(zoo_id=1, food_type=FoodType.MEAT))``
               contains both key columns separated by a comma.
        """
        mapper = sa_inspect(type(self)).mapper
        keys = ", ".join(
            f"{column.key}={getattr(self, column.key)!r}"
            for column in mapper.primary_key
        )
        return f"<{type(self).__name__} {keys}>"


class TimestampMixin:  # pylint: disable=too-few-public-methods
    """Mixin contributing the ``created_at`` column.

    The suppression above is deliberate: a mixin whose entire job is to
    contribute one column *should* have no methods. Adding one to satisfy a
    linter would be the actual design smell.

    A mixin does **not** inherit from :class:`Base` and is not a table
    itself. It is pulled in through multiple inheritance::

        class DailyStats(TimestampMixin, Base):
            ...

    SQLAlchemy then copies the column declared here into every table using
    the mixin. The definition exists exactly once in the code but ends up in
    several tables -- without forcing them to share a parent table.

    Attributes:
        created_at (datetime): Wall-clock time the row was created (*not*
            simulation time). Set automatically on instantiation.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now,
        nullable=False,
        doc="Real-world creation time of this row (not simulation time).",
    )


@event.listens_for(Base, "init", propagate=True)
def _apply_column_defaults(target: Any, _args: tuple, kwargs: dict) -> None:
    """Apply column defaults immediately when an object is constructed.

    By default SQLAlchemy only fills ``default=`` values while writing a row,
    so a freshly built ``Lion(animal_id="a_01")`` would carry ``hp = None``
    until it had been through the database. Any helper reading those
    attributes -- ``is_critical()``, ``free_slots()`` -- would then crash on
    ``None``.

    This listener closes that gap: SQLAlchemy fires the ``init`` event for
    every model instance, and ``propagate=True`` makes it apply to every
    subclass too, so the behaviour holds for all seven tables and every
    animal species.

    Values passed to the constructor always win; only unset columns are
    filled. Assigning through ``setattr`` also means the ``@validates`` hooks
    run on the defaults, so a default can never be an invalid value.

    Args:
        target (Any): The model instance being constructed.
        _args (tuple): Positional constructor arguments. Unused -- the
            declarative constructor is keyword-only.
        kwargs (dict): Keyword arguments passed to the constructor. Keys
            listed here are skipped, so explicit values are never overwritten.

    Returns:
        None. Attributes are set on ``target`` as a side effect.

    Tests:
        1. ``Lion(animal_id="a_01").hp`` equals ``100.0`` right after
           construction, without any database contact.
        2. ``Lion(animal_id="a_01", hp=42.0).hp`` equals ``42.0`` -- an
           explicit argument beats the default; and
           ``DailyStats(day_id=1).profit_loss`` stays ``None`` because
           computed columns are skipped.
    """
    mapper = sa_inspect(type(target)).mapper
    for attribute in mapper.column_attrs:
        if attribute.key in kwargs:
            continue
        column = attribute.columns[0]
        if column.computed is not None:
            continue
        default = column.default
        if default is None:
            continue
        if getattr(default, "is_scalar", False):
            setattr(target, attribute.key, default.arg)
        elif getattr(default, "is_callable", False):
            setattr(target, attribute.key, default.arg(None))
