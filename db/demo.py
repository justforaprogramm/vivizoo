"""Runnable end-to-end demonstration of the database module.

Run it from the repository root::

    python -m db.demo

It walks through every operation this module offers, in order, and prints
what happens at each step:

1. Open storage and write three simulation days including their messages.
2. Read the days back for charts.
3. Read the message log.
4. Read the weekly aggregation (computed by an SQL view).
5. Save a complete zoo, load it back, and show that animals return as their
   correct species subclass.

The demo uses an in-memory database by default and therefore leaves nothing
behind. Pass a path to write a real file::

    python -m db.demo data/demo.sqlite

Part of the vivizoo project. Module owner: Jannes (database).
"""

from __future__ import annotations

import sys

from db import (
    AbstractPersistence,
    AnimalStatusEffect,
    DailyStats,
    Enclosure,
    Event,
    EventType,
    FoodType,
    InventoryItem,
    ZooDatabase,
    TimeOfDay,
    ZooState,
    create_animal,
)


def build_sample_days() -> list[tuple[DailyStats, list[Event]]]:
    """Create three days of example data with matching messages.

    Kept separate from the storage calls so the data is easy to read and to
    change without touching the demonstration logic.

    Args:
        None.

    Returns:
        list[tuple[DailyStats, list[Event]]]: Three pairs of a day summary
        and the messages belonging to that day. Day 2 deliberately runs at a
        loss so the profit calculation shows a negative number somewhere.

    Tests:
        1. The result has length ``3`` and the ``day_id`` values are
           ``[1, 2, 3]`` in order.
        2. Day 2 has ``expenses > revenue``, so ``is_profitable()`` returns
           ``False`` for it and ``True`` for days 1 and 3.
    """
    return [
        (
            DailyStats(
                day_id=1,
                total_visitors=120,
                revenue=840.0,
                expenses=300.0,
                avg_animal_welfare=88.5,
                avg_happiness=91.0,
                reputation_end_of_day=85,
                animals_died=0,
            ),
            [
                Event(
                    tick_count=100,
                    type=EventType.INFO,
                    text="Zoo has opened.",
                ),
                Event(
                    tick_count=450,
                    type=EventType.SUCCESS,
                    text="All animals fed.",
                ),
            ],
        ),
        (
            DailyStats(
                day_id=2,
                total_visitors=95,
                revenue=665.0,
                expenses=810.0,
                avg_animal_welfare=71.0,
                avg_happiness=64.5,
                reputation_end_of_day=79,
                animals_died=1,
            ),
            [
                Event(
                    tick_count=1300,
                    type=EventType.WARNING,
                    text="Lion 'Hungry Harry' is starving!",
                    entity_id="a_01",
                ),
                Event(
                    tick_count=1480,
                    type=EventType.ERROR,
                    text="Giraffe 'Long Neck' has died.",
                    entity_id="a_02",
                    details={"cause": "starvation", "days_without_food": 3},
                ),
            ],
        ),
        (
            DailyStats(
                day_id=3,
                total_visitors=180,
                revenue=1260.0,
                expenses=420.0,
                avg_animal_welfare=94.0,
                avg_happiness=96.5,
                reputation_end_of_day=92,
                animals_died=0,
            ),
            [
                Event(
                    tick_count=2200,
                    type=EventType.SUCCESS,
                    text="Record attendance!",
                ),
            ],
        ),
    ]


def build_sample_zoo() -> ZooState:
    """Create a small but complete zoo for the savegame demonstration.

    Contains everything a savegame has to survive: global state, stock
    levels, two enclosures, three animals of three different species, and a
    status effect on one of them.

    Args:
        None.

    Returns:
        ZooState: A fully populated, not yet persisted object graph.

    Tests:
        1. ``build_sample_zoo().total_animals()`` returns ``3``.
        2. The three animals are instances of three different classes, and
           exactly one of them carries a status effect.
    """
    savanna = Enclosure(
        enclosure_id="e_01",
        name="Savanna 1",
        biome="savanna",
        capacity=8,
        cleanliness=95.0,
    )
    savanna.animals = [
        create_animal(
            "lion",
            animal_id="a_01",
            name="Hungry Harry",
            age_days=14,
            hp=85.0,
            hunger=20.0,
            welfare=90.0,
            pos_x=150,
            pos_y=300,
        ),
        create_animal(
            "giraffe",
            animal_id="a_02",
            name="Long Neck",
            age_days=9,
            hp=95.0,
            hunger=10.0,
            welfare=97.0,
            pos_x=210,
            pos_y=280,
        ),
    ]

    arctic = Enclosure(
        enclosure_id="e_02",
        name="Arctic Zone",
        biome="arctic",
        capacity=12,
        cleanliness=78.0,
    )
    penguin = create_animal(
        "penguin",
        animal_id="a_03",
        name="Pingu",
        age_days=4,
        hp=60.0,
        hunger=80.0,
        welfare=55.0,
        pos_x=400,
        pos_y=120,
    )
    penguin.status_effects = [
        AnimalStatusEffect(effect_name="Stressed", remaining_ticks=40)
    ]
    arctic.animals = [penguin]

    zoo = ZooState(
        id=1,
        tick_count=4500,
        game_day=3,
        time_of_day=TimeOfDay.NIGHT,
        zoo_open=False,
        money=15400.50,
        reputation=85,
        ticket_price=12.50,
    )
    zoo.inventory = [
        InventoryItem(food_type=FoodType.MEAT, amount=15),
        InventoryItem(food_type=FoodType.PLANTS, amount=0),
        InventoryItem(food_type=FoodType.FISH, amount=3),
    ]
    zoo.enclosures = [savanna, arctic]
    return zoo


def run_scenario(storage: AbstractPersistence) -> None:
    """Run the full read/write scenario against a storage implementation.

    The parameter is typed as :class:`AbstractPersistence`, not as a concrete
    class. This function therefore has no idea which implementation it is
    talking to -- exactly how the application is written.

    Args:
        storage (AbstractPersistence): The storage object to exercise. Its
            contents are wiped at the start via ``reset()``.

    Returns:
        None. All results are printed to stdout.

    Tests:
        1. Called with ``ZooDatabase(":memory:")`` the function
           completes without raising and prints three day lines.
        2. Called twice in a row on the same object it prints identical
           output, because ``reset()`` clears the previous run.
    """
    storage.reset()

    # --- 1. Write days -------------------------------------------------
    for stats, events in build_sample_days():
        storage.save_day(stats, events)
    print("\n[1] Wrote 3 days including messages.")

    # --- 2. Read days back --------------------------------------------
    print("\n[2] get_stats(7) -- data for charts:")
    print(f"    {'day':>4} {'visitors':>9} {'revenue':>9} {'expenses':>9} "
          f"{'profit':>9}  profitable")
    for day in storage.get_stats(7):
        print(
            f"    {day.day_id:>4} {day.total_visitors:>9} {day.revenue:>9.2f} "
            f"{day.expenses:>9.2f} {day.profit_loss:>9.2f}  "
            f"{'yes' if day.is_profitable() else 'no'}"
        )

    # --- 3. Messages ---------------------------------------------------
    print("\n[3] get_events(day_id=2) -- the message feed of day 2:")
    for entry in storage.get_events(day_id=2):
        marker = "!" if entry.is_problem() else " "
        print(f"  {marker} [{entry.type.value:<7}] tick {entry.tick_count:>5}: "
              f"{entry.text}")
        if entry.details:
            print(f"      details: {entry.details}")

    # --- 4. Weekly aggregation ----------------------------------------
    print("\n[4] get_weekly_summary() -- aggregated by an SQL view:")
    for week in storage.get_weekly_summary():
        print(
            f"    week {week['week']}: {week['days_recorded']} days, "
            f"revenue {week['revenue']:.2f}, profit {week['profit_loss']:.2f}, "
            f"welfare {week['avg_animal_welfare']:.1f}%"
        )

    # --- 5. Savegame ---------------------------------------------------
    slot = storage.save_game(build_sample_zoo())
    print(f"\n[5] save_game() -- complete zoo written to slot {slot}.")

    loaded = storage.load_game(slot)
    assert loaded is not None, "savegame must be loadable"
    print(f"    load_game({slot}) -> day {loaded.game_day}, "
          f"money {loaded.money:.2f}, {loaded.total_animals()} animals")

    print("\n    Animals return as their species subclass:")
    for enclosure in loaded.enclosures:
        print(f"      {enclosure.name} ({enclosure.biome}), "
              f"{enclosure.free_slots()} slots free:")
        for animal in enclosure.animals:
            effects = ", ".join(
                effect.effect_name for effect in animal.status_effects
            ) or "-"
            print(
                f"        {animal.name:<14} class={type(animal).__name__:<8} "
                f"food={animal.PREFERRED_FOOD.value:<7} "
                f"critical={'yes' if animal.is_critical() else 'no':<3} "
                f"effects={effects}"
            )

    print("\n[6] list_saves():")
    for entry in storage.list_saves():
        print(f"    slot {entry['id']}: day {entry['game_day']}, "
              f"money {entry['money']:.2f}, saved {entry['created_at']}")


def main() -> int:
    """Entry point: run the scenario and report success.

    Args:
        None. Reads ``sys.argv[1]`` as an optional database path; without it
        an in-memory database is used.

    Returns:
        int: Process exit code -- ``0`` on success. Suitable for
        ``sys.exit(main())``.

    Tests:
        1. Running ``python -m db.demo`` returns exit code ``0`` and prints
           all six numbered steps.
        2. Running ``python -m db.demo <path>`` creates a database file at
           that path and still returns ``0``.
    """
    database = sys.argv[1] if len(sys.argv) > 1 else ":memory:"

    print("=" * 70)
    print(f"  vivizoo database module  (database={database})")
    print("=" * 70)

    with ZooDatabase(database) as storage:
        run_scenario(storage)

    print()
    print("=" * 70)
    print("  Everything above went through AbstractPersistence.")
    print("  The application calls exactly these methods and never sees SQL.")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
