"""The chat feed of the simulation.

:class:`MessageLogger` collects every message produced by the simulation and
hands them to the frontend. It is implemented as a **singleton** because the
planning document states it explicitly: every corner of the simulation logs
to the same feed, so a single shared instance is the natural fit.

The logger distinguishes between *provisional* messages (produced during the
day, flushed on demand) and *persisted* messages. In the current phase the
persistence boundary only writes messages together with a finished day -- see
``backend/docs/api.md`` and the database module.

Module owner: Benjamin (backend).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class LogEntry:
    """A single chat message described by its fields.

    Attributes:
        tick_count (int): Simulation tick at which the message was produced.
        message_type (str): Severity -- one of ``INFO``, ``WARNING``,
            ``ERROR``, ``SUCCESS``. Matches :class:`db.interface.EventType`.
        text (str): The human-readable message body.
        entity_id (str | None): Optional identifier of the affected object.
        details (dict[str, Any] | None): Optional structured payload.
    """

    tick_count: int
    message_type: str
    text: str
    entity_id: str | None = None
    details: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Render the entry as a plain dictionary for the frontend.

        Args:
            None (instance method, only ``self``).

        Returns:
            dict[str, Any]: A shallow copy with the keys ``tick_count``,
            ``type``, ``text`` and optionally ``entity_id`` / ``details``.

        Tests:
            1. For an entry without ``entity_id`` the dict has exactly the
               keys ``tick_count``, ``type`` and ``text``.
            2. For an entry with all fields set, ``to_dict()`` contains the
               matching ``entity_id`` and ``details`` and the ``type`` equals
               the original ``message_type``.
        """
        result: dict[str, Any] = {
            "tick_count": self.tick_count,
            "type": self.message_type,
            "text": self.text,
        }
        if self.entity_id is not None:
            result["entity_id"] = self.entity_id
        if self.details is not None:
            result["details"] = self.details
        return result


class MessageLogger:
    """Singleton that collects and serves the simulation's chat feed.

    The singleton guarantees that all producers share one buffer; the
    frontend reads and drains it in one call (``drain()``).

    Args:
        None. Access the shared instance through :attr:`instance` (created
        lazily) or by calling :meth:`Logger.instance = MessageLogger()` to
        inject a fresh one in tests.

    Attributes:
        MAX_BUFFER (int): Hard cap on buffered messages, protecting memory
            when nobody drains between ticks.
    """

    MAX_BUFFER = 500

    _own_instance: "MessageLogger | None" = None

    @classmethod
    def instance(cls) -> "MessageLogger":
        """Return the shared singleton, creating it on first use.

        Args:
            None.

        Returns:
            MessageLogger: The process-wide shared instance.

        Tests:
            1. Two calls return the identical object (singleton identity).
            2. After :meth:`reset_to_fresh`, a later call returns a different
               instance with an empty history.
        """
        if cls._own_instance is None:
            cls._own_instance = cls()
        return cls._own_instance

    @classmethod
    def reset_to_fresh(cls) -> None:
        """Drop the shared instance so the next call builds a new one.

        Intended for tests that need an empty logger without sharing state.

        Args:
            None.

        Returns:
            None.

        Tests:
            1. After a reset, ``instance().drain()`` returns ``[]`` even if
               the previous instance held messages.
            2. The reset does not raise when no instance exists yet.
        """
        cls._own_instance = None

    def __init__(self) -> None:
        """Create an empty logger.

        A logger created through ``MessageLogger()`` directly is independent;
        use :meth:`instance` for the shared feed.

        Args:
            None.

        Returns:
            None (constructor).

        Tests:
            1. A fresh logger reports ``has_unread()`` as ``False``.
            2. A fresh logger accepts entries without error.
        """
        self._pending: list[LogEntry] = []

    def log(
        self,
        message_type: str,
        text: str,
        entity_id: str | None = None,
        details: dict[str, Any] | None = None,
        tick_count: int = 0,
    ) -> None:
        """Append one message to the feed.

        Args:
            message_type (str): One of ``INFO``, ``WARNING``, ``ERROR``,
                ``SUCCESS``.
            text (str): The message body.
            entity_id (str | None): Identifier of the affected object.
            details (dict[str, Any] | None): Optional structured payload.
            tick_count (int): Tick at which the message was produced.

        Returns:
            None.

        Tests:
            1. ``log("INFO", "hello")`` makes a following ``drain()`` return
               one entry whose ``type`` is ``INFO``.
            2. Logging beyond :attr:`MAX_BUFFER` discards the oldest entries
               so the buffer never exceeds the cap.
        """
        self._pending.append(
            LogEntry(
                tick_count=tick_count,
                message_type=message_type,
                text=text,
                entity_id=entity_id,
                details=details,
            )
        )
        if len(self._pending) > self.MAX_BUFFER:
            del self._pending[: len(self._pending) - self.MAX_BUFFER]

    def drain(self) -> list[LogEntry]:
        """Return all pending messages and clear the buffer.

        The frontend polls this repeatedly; once a message is returned it is
        no longer held, so it is delivered exactly once.

        Args:
            None.

        Returns:
            list[LogEntry]: The buffered messages in the order they were
            logged. Empty list when nothing is pending.

        Tests:
            1. After two logs, ``drain()`` returns two entries and a second
               ``drain()`` returns ``[]`` (drained at least once).
            2. ``drain()`` on a fresh logger returns ``[]`` without raising.
        """
        result = self._pending
        self._pending = []
        return result

    def has_unread(self) -> bool:
        """Report whether the feed holds messages the frontend has not read.

        Args:
            None.

        Returns:
            bool: ``True`` if the buffer is non-empty.

        Tests:
            1. A fresh logger returns ``False``; after ``log(...)`` it
               returns ``True``.
            2. After ``drain()`` the logger again returns ``False``.
        """
        return bool(self._pending)

    def clear(self) -> None:
        """Remove every buffered message without returning them.

        Used by tests and by :meth:`SimulationEngine` when a new call starts.

        Args:
            None.

        Returns:
            None.

        Tests:
            1. After ``clear()``, ``has_unread()`` is ``False``.
            2. Calling ``clear()`` on an already empty logger does not raise.
        """
        self._pending = []

    def __len__(self) -> int:
        """Return the number of buffered messages.

        Args:
            None.

        Returns:
            int: Number of currently pending messages.

        Tests:
            1. A fresh logger has length ``0``; after two logs it is ``2``.
        """
        return len(self._pending)
