# Backend — UML Class Diagram (Mermaid)

This diagram covers the backend core domain. Arrows point from the *using*
class to the *used* class.

```mermaid
classDiagram
    direction TB

    class SimulationEngine {
        -_tick_count: int
        -_paused: bool
        -_speed: float
        +start() void
        +pause() void
        +tick() void
        +get_game_state() dict
        +get_entity_info(id) dict
        +get_chat_messages() list
        +execute_action(name, **kw) dict
    }

    class Zoo {
        +enclosures: list~Enclosure~
        +employees: list~Employee~
        +visitors: list~Visitor~
        +finances: Finances
        +inventory: Inventory
        +environment: EnvironmentFactor
        -_visitors_today: int
        +add_enclosure() Enclosure
        +add_animal(species, name, enc) Animal
        +update_animals(tick) void
        +update_visitors(gate) void
        +daily_snapshot() dict
        +to_game_state(tick, phase) dict
    }

    class Animal {
        <<abstract>>
        +animal_id: str
        +name: str
        +x, y: int
        #_hp, _hunger, _welfare: float
        -_days_starved: int
        +PREFERRED_FOOD: FoodType
        +feed(amount) void
        +rest() void
        +age_one_day() void
        +move() void*
        +tick_update(tick) void
    }

    class Lion {
        +PREFERRED_FOOD = MEAT
        +move() void
    }
    class Giraffe {
        +PREFERRED_FOOD = PLANTS
        +move() void
    }
    class Penguin {
        +PREFERRED_FOOD = FISH
        +move() void
    }

    class Behaviour {
        <<interface>>
        +perform(animal, tick, is_night) str
    }
    class FeedingBehaviour
    class RestingBehaviour
    class StatefulBehaviour

    class StatusEffect {
        +name: str
        +remaining_ticks: int
        +tick() float
    }

    class Enclosure {
        +enclosure_id: str
        +biome: str
        +capacity: int
        +cleanliness: float
        +animals: list~Animal~
        +add_animal(a) void
        +average_welfare() float
    }

    class Visitor {
        +visitor_id: str
        +x, y: int
        +remaining_ticks: int
        +tick() void
    }

    class Finances {
        -_balance: float
        +earn(amount) void
        +spend(amount) bool
        +pay_ticket() float
        +start_new_day() void
    }

    class Inventory {
        -_stock: dict~FoodType,int~
        +add(type, amount) void
        +consume(type, amount) int
        +price_of(type) float
    }

    class Food {
        +food_type: FoodType
        +purchase_tick: int
    }

    class Employee {
        <<abstract>>
        +employee_id: str
        +salary: float
        +perform_job(zoo) void*
    }
    class Keeper
    class Veterinarian
    class AdminStaff

    class EnvironmentFactor {
        +weather: str
        +temperature: float
        +welfare_modifier() float
    }

    class EventScheduler {
        +check(zoo, tick) void
    }

    class MessageLogger {
        <<singleton>>
        +log(...) void
        +drain() list~LogEntry~
    }

    class ActionHandler {
        +execute_action(name, **kw) ActionResult
    }
    class ActionResult

    SimulationEngine --> Zoo : drives
    SimulationEngine --> ActionHandler
    SimulationEngine --> MessageLogger
    Zoo *-- Enclosure
    Zoo *-- Finances
    Zoo *-- Inventory
    Zoo *-- EnvironmentFactor
    Zoo *-- EventScheduler
    Zoo o-- Employee
    Zoo o-- Visitor
    Animal <|-- Lion
    Animal <|-- Giraffe
    Animal <|-- Penguin
    Animal --> "many" StatusEffect
    Animal --> "0..n" Behaviour : composes
    Behaviour <|-- FeedingBehaviour
    Behaviour <|-- RestingBehaviour
    Behaviour <|-- StatefulBehaviour
    Enclosure o-- "0..n" Animal
    Employee <|-- Keeper
    Employee <|-- Veterinarian
    Employee <|-- AdminStaff
    Inventory o-- Food
    ActionHandler --> Zoo
    ActionHandler --> Animal
```

**Legend**

* `#` private, `+` public, `<<abstract>>` abstract class, `*--` composition
  (strong ownership), `o--` aggregation (looser), `<|--` inheritance.
* `Animal` is polymorphic: the OOP course chapter 2 requirement
  (fressen / schlafen / bewegen / altern) maps to `feed`, `rest`, `move`,
  `age_one_day`.
* `Behaviour` is the strategy pattern; `StatusEffect` is a plain value object.
* `Zoo` is the aggregate root (composition per chapter 1).
