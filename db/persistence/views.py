"""SQL views -- pre-aggregated read shortcuts.

A view is a stored ``SELECT`` that behaves like a read-only table. Putting
aggregation here rather than in Python has two benefits: a UI can ask
for a weekly summary in one round trip, and the aggregation rule lives in
exactly one place instead of being reimplemented in every caller.

The views are registered on ``Base.metadata`` and created automatically right
after ``create_all()`` -- there is no separate step to remember.

Part of the vivizoo project. Module owner: Jannes (database).

Authorship:
    Drafted with AI assistance and completed under a human-in-the-loop
    process: every declaration in this file was read, executed and reconciled
    with ``planning/db_planning/db_requirements.md`` before it was committed.
    ``db/docs/ai_usage.md`` records what that review covered and the ten
    defects it caught.
"""

from __future__ import annotations

from sqlalchemy import DDL, MetaData, event

__all__ = ["WEEKLY_SUMMARY_VIEW", "EVENT_SUMMARY_VIEW", "register_views"]

#: Metadata objects the views have already been attached to.
#:
#: SQLAlchemy's ``event.listen`` appends -- it does not replace. Without this
#: set, constructing :class:`~db.persistence.zoo_database.ZooDatabase` twice in
#: one process would attach the two DDL statements twice, three times for a
#: third instance, and so on. Every ``create_all()`` would then re-issue them
#: all. A test suite that builds one in-memory database per test case hits
#: exactly that.
_REGISTERED: set[int] = set()

#: Aggregates ``daily_stats`` into calendar weeks of seven days.
#: Week 1 covers days 1--7, week 2 days 8--14, and so on.
WEEKLY_SUMMARY_VIEW = """
CREATE VIEW IF NOT EXISTS v_weekly_summary AS
SELECT
    (day_id - 1) / 7 + 1        AS week,
    COUNT(*)                    AS days_recorded,
    SUM(total_visitors)         AS total_visitors,
    SUM(revenue)                AS revenue,
    SUM(expenses)               AS expenses,
    SUM(revenue) - SUM(expenses) AS profit_loss,
    AVG(avg_animal_welfare)     AS avg_animal_welfare,
    AVG(avg_happiness)          AS avg_happiness,
    SUM(animals_died)           AS animals_died
FROM daily_stats
GROUP BY (day_id - 1) / 7
"""

#: Counts how many messages of each type occurred on each day.
#: Lets a UI show "3 warnings, 1 error" without loading the messages.
EVENT_SUMMARY_VIEW = """
CREATE VIEW IF NOT EXISTS v_event_summary AS
SELECT
    day_id,
    type,
    COUNT(*) AS occurrences
FROM events
GROUP BY day_id, type
"""


def register_views(metadata: MetaData) -> None:
    """Attach the view definitions to a metadata object.

    After this call, every ``metadata.create_all(engine)`` also creates the
    views. The statements use ``CREATE VIEW IF NOT EXISTS``, so running it
    against an existing database is harmless.

    Called from :meth:`~db.persistence.zoo_database.ZooDatabase.__init__`;
    application code does not need to call it.

    **Attaching happens once per metadata object.** ``event.listen`` appends
    rather than replaces, so calling this function repeatedly -- which every
    additional ``ZooDatabase`` instance does -- would otherwise pile up
    duplicate listeners and re-issue both statements once per instance on
    every ``create_all()``. The guard makes repeated calls free instead of
    merely harmless.

    Args:
        metadata (MetaData): The metadata object the views should be bound
            to -- in practice always ``Base.metadata``.

    Returns:
        None.

    Tests:
        1. After ``register_views(Base.metadata)`` and ``create_all(engine)``,
           querying ``SELECT * FROM v_weekly_summary`` succeeds instead of
           raising "no such table".
        2. Calling ``register_views`` twice leaves exactly two ``after_create``
           listeners on the metadata, not four -- repeated registration is a
           no-op rather than an accumulation (idempotence).
    """
    if id(metadata) in _REGISTERED:
        return
    _REGISTERED.add(id(metadata))

    for statement in (WEEKLY_SUMMARY_VIEW, EVENT_SUMMARY_VIEW):
        event.listen(
            metadata,
            "after_create",
            DDL(statement).execute_if(dialect="sqlite"),
        )
