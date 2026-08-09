"""Runnable end-to-end demonstration of the backend core logic.

Run it from the repository root (the ``db`` package must be importable)::

    python -m backend.demo

What it does:

1. Build a small zoo with one enclosure, a keeper, and a couple of animals.
2. Run the :class:`SimulationEngine` manually for a number of ticks.
3. Poll ``get_game_state()`` and print the snapshot.
4. Trigger a few God-mode actions (``buy_food``, ``feed_all``).
5. If a persistence gateway is attached, show that a finished day is written
   to the database and can be read back for charts.

By default the demo runs purely in memory. Pass a flag to also demo database
persistence::

    python -m backend.demo --with-db

Part of the vivizoo project. Module owner: Benjamin (backend).
"""

from __future__ import annotations

import sys

from backend.core.employee import Keeper
from backend.core.engine import SimulationEngine, TICKS_PER_DAY
from backend.core.message_logger import MessageLogger
from backend.core.zoo import Zoo


def build_demo_zoo(logger: MessageLogger) -> Zoo:
    """Assemble a small, self-contained zoo for the demo.

    Args:
        logger (MessageLogger): The shared chat feed to bind.

    Returns:
        Zoo: A zoo with one enclosure, a keeper and two animals.

    Tests:
        1. The zoo has exactly one enclosure.
        2. It contains at least two animals and one employee.
    """
    from db.interface.enums import FoodType

    zoo = Zoo(name="Demo Zoo", logger=logger)
    savanna = zoo.add_enclosure("Savanna 1", "savanna", capacity=8)
    # Start the lion fairly hungry so the feed action demonstrates something.
    lion = zoo.add_animal("lion", "Hungry Harry", savanna)
    lion._hunger = 70.0
    zoo.add_animal("giraffe", "Long Neck", savanna)
    zoo.add_employee(Keeper("st_01", "Kurt"))
    # Give the demo some meat so the lion can be fed in the action section.
    zoo.inventory.add(FoodType.MEAT, 10)
    return zoo


def run_demo(use_db: bool) -> int:
    """Run the demo and report success.

    Args:
        use_db (bool): Whether to attach a real persistence gateway.

    Returns:
        int: Process exit code -- ``0`` on success.

    Tests:
        1. ``run_demo(False)`` returns ``0`` and leaves ``persistence`` unset,
           so the ``[5]`` database section is skipped entirely.
        2. ``run_demo(True)`` also returns ``0``, ticking on until
           ``_tick_count`` is a multiple of ``TICKS_PER_DAY`` so a day
           closes, then reporting ``get_stats(7)`` and closing the
           ``":memory:"`` database.
    """
    logger = MessageLogger.instance()
    logger.clear()
    zoo = build_demo_zoo(logger)

    persistence = None
    if use_db:
        from backend.persistence.db_gateway import DbGateway
        from db import ZooDatabase

        storage = ZooDatabase(":memory:")
        persistence = DbGateway(storage)

    engine = SimulationEngine(zoo, persistence=persistence, logger=logger)

    print("=" * 66)
    print("  vivizoo backend core (demo)")
    print("=" * 66)

    # --- 1. Run a few ticks manually --------------------------------
    print("\n[1] Feeding the zoo is turned into player actions later;")
    print("    first we run the engine for some ticks, then inspect state.")
    for _ in range(30):
        engine.tick()

    state = engine.get_game_state()
    print(
        f"\n    tick={state['system']['tick_count']} "
        f"phase={state['system']['time_of_day']}"
    )

    # --- 2. God-mode actions ---------------------------------------
    print("\n[2] Player buys food and feeds all animals:")
    bought = engine.execute_action("buy_food", type="MEAT", amount=6)
    print(f"    {bought['success']}: {bought['message']}")
    fed = engine.execute_action("feed_all")
    print(f"    {fed['success']}: {fed['message']}")

    # --- 3. Inspect an animal's hover data --------------------------
    animal_id = zoo.all_animals()[0].animal_id
    info = engine.get_entity_info(animal_id)
    print(f"\n[3] Hover info for {animal_id}:")
    print(
        f"    {info['name']} (hp={info['hp']}, hunger={info['hunger']}, "
        f"welfare={info['welfare']})"
    )

    # --- 4. Inventory + money ---------------------------------------
    final = engine.get_game_state()
    print("\n[4] Inventory:", final["inventory"])
    print(
        "    Money:",
        final["finances"]["money"],
        "| Animals on map:",
        len(final["animals_on_map"]),
    )

    # --- 5. Persistence (optional) ----------------------------------
    if persistence is not None:
        # Advance until the night phase closes the day.
        steps = 0
        while engine._tick_count % TICKS_PER_DAY != 0 and steps < TICKS_PER_DAY:
            engine.tick()
            steps += 1
        stats = engine.get_stats(7)
        print(f"\n[5] Wrote a day summary; chart rows now: {len(stats)}")
        if stats:
            row = stats[0]
            print(
                f"    day {row['day_id']}: visitors={row['total_visitors']}, "
                f"profit={row['profit_loss']}, welfare={row['avg_animal_welfare']}"
            )
        storage.close()

    print("\n" + "=" * 66)
    print("  Backend core loop complete.")
    print("=" * 66)
    return 0


def main() -> int:
    """Entry point: read the --with-db flag and run the demo.

    Args:
        Reads ``sys.argv`` for ``"--with-db"``.

    Returns:
        int: Exit code -- ``0`` on success.

    Tests:
        1. ``python -m backend.demo`` returns 0.
        2. ``python -m backend.demo --with-db`` returns 0.
    """
    use_db = "--with-db" in sys.argv
    return run_demo(use_db)


if __name__ == "__main__":
    raise SystemExit(main())
