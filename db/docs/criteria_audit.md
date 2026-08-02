# Assessment Criteria — Audit of the Database Module

An honest mapping of every requirement in the project brief to the evidence
in this module. Gaps are listed as gaps, not glossed over.

Scope: the **database focus area**. Criteria that belong to other focus
areas are marked as out of scope and named anyway, so nothing silently
disappears.

---

## Summary

| Criterion | Points | Status |
|---|---|---|
| Class structure & modelling | 12 | Covered |
| Inheritance & polymorphism | 10 | Covered |
| Encapsulation & data integrity | 8 | Covered |
| Modularity & extensibility | 10 | Covered |
| Core functionality | 8 | Covered |
| Simulation logic & realism | 7 | Out of scope (backend) |
| Test plan & test cases | 10 | Covered |
| Test coverage & edge cases | 5 | Covered |
| Code documentation | 15 | Covered |
| Design visualisation (Mermaid) | 10 | Covered |
| Reflection & AI use | 5 | **Needs your own text** — see section 12 |

Deduction-relevant requirements are audited separately in section 11.

---

## 1. Class structure & modelling (12 pts)

**Required:** a comprehensive, focus-specific class diagram; clean modelling
with attributes, methods and relationships.

| Evidence | Where |
|---|---|
| 17 classes across 18 modules, one responsibility per file | `db/` |
| 5 class diagrams (overview, interface, domain model, animal hierarchy, enums) | `docs/uml_class_diagram.md` |
| ER diagram with every column and type | `docs/uml_er_diagram.md` |
| 5 sequence diagrams for the real interactions | `docs/uml_sequence_diagrams.md` |
| All four relationship kinds explicitly modelled and drawn | see below |

**All four required relationship kinds are present and distinguished:**

| Kind | Example | Realised as |
|---|---|---|
| Inheritance | `Animal` → `Lion` / `Giraffe` / `Penguin` | `class Lion(Animal)` |
| Composition | `ZooState` owns `Enclosure` | `cascade="all, delete-orphan"` |
| Aggregation | `Enclosure` houses `Animal` | relationship, drawn as `o--` |
| Association | `Event` references `DailyStats` | `ForeignKey` + `relationship` |

---

## 2. Inheritance & polymorphism (10 pts)

**Required:** a clear inheritance hierarchy; polymorphic methods that behave
differently per subclass.

Polymorphism appears at **two independent levels**, which is the strongest
part of this module:

**Level 1 — the domain model.** The `species` column is a discriminator:

```python
class Animal(Base):
    __mapper_args__ = {"polymorphic_on": "species", "polymorphic_identity": "animal"}

class Lion(Animal):
    PREFERRED_FOOD = FoodType.MEAT
    __mapper_args__ = {"polymorphic_identity": "lion"}
```

Reading animals back returns `Lion`, `Giraffe` and `Penguin` instances, not
generic `Animal` objects. `PREFERRED_FOOD` resolves per subclass without a
single `if species == ...` anywhere.

*Verified:* `load_game()` returns objects for which `isinstance(x, Lion)` and
`isinstance(x, Penguin)` hold.

**Level 2 — the architecture.** `AbstractPersistence` is an abstract base
class with 11 abstract methods and no implementation. The demo and every
test are typed against it, never against the concrete class:

```python
def run_scenario(storage: AbstractPersistence) -> None: ...
```

The abstraction is load-bearing rather than decorative: Python refuses to
instantiate a subclass that misses a method, so a broken implementation
fails at start-up instead of mid-session. Because SQLAlchemy sits
underneath, the database engine itself is a configuration value —
`"sqlite:///…"` becomes `"postgresql://…"` without touching another line.

*Verified:* a subclass omitting one method raises `TypeError` on
instantiation; `issubclass(ZooDatabase, AbstractPersistence)`
holds; the same object serves both a file-backed and an in-memory database.

**Multiple inheritance:** `TimestampMixin` contributes a column to two tables
without forcing them to share a parent table
(`class DailyStats(TimestampMixin, Base)`).

---

## 3. Encapsulation & data integrity (8 pts)

**Required:** internal state protected, manipulated only through defined
interfaces.

**Two independent layers of validation, deliberately:**

```python
@validates("hp", "hunger", "welfare")            # 1. Python
def _check_percentage(self, field, value): ...

CheckConstraint("hp BETWEEN 0 AND 100")          # 2. schema
```

They guard different threats. The validator catches bugs in our own code at
the moment of assignment, with a readable message. The constraint protects
the **file** — it still holds if someone edits a row in a SQLite browser.

| Mechanism | Where |
|---|---|
| 9 `@validates` hooks across 7 models | `models/*.py` |
| Duplicate-identifier guard before a savegame is written | `_assert_unique_ids` |
| Repeated-day guard before figures are replaced | `_assert_day_is_free` |
| 15 `CHECK` constraints in the schema | `__table_args__` |
| Enum coercion with clear errors on invalid input | `_coerce_type`, `_coerce_food_type`, `_coerce_time_of_day` |
| Generated column makes `profit_loss` structurally unable to drift, and assigning it raises | `daily_stats.profit_loss` |
| Private attributes (`_engine`, `_session_factory`, `_closed`) | `ZooDatabase` |
| Transactions: a failed write changes nothing | `session.begin()` |
| Foreign keys actually enforced | `PRAGMA foreign_keys=ON` |

*Verified:* 13 rejection tests (out-of-range percentages, negative amounts,
invalid enum values, unknown species, writing a computed column) all raise;
boundary values `0` and `100` are accepted.

---

## 4. Modularity & extensibility (10 pts)

**Required:** easy to extend with new species, enclosure types or functions.

| Extension | Cost | Ripple effect |
|---|---|---|
| New animal species | 3 lines | None. No migration, no new table. |
| New storage implementation | 1 class implementing the interface | None. One line changes at the entry point. |
| New event kind | 0 lines | The `details` JSON column absorbs it. |
| New biome | 0 lines | `biome` is free text on purpose. |
| Different database engine | 1 string | `"sqlite:///..."` → `"postgresql://..."` |
| New table | inherits `as_dict()` / `from_dict()` | Serialisation is written once in `Base`. |

The layering rule is machine-checkable — both commands must print nothing:

```bash
grep -rnE "^\s*(from|import) backend" db/ --include="*.py"
```

```bash
grep -rnE "^\s*(from|import) db\.persistence" backend/ --include="*.py"
```

*Verified:* both return 0 hits.

---

## 5. Core functionality (8 pts)

| Function | Status |
|---|---|
| Write day summaries | Implemented, transactional |
| Persist message log | Implemented, batched |
| Read chart data | Implemented, chronological |
| Weekly aggregation | Implemented via SQL view |
| Full savegame | Implemented, one call for the whole graph |
| Load savegame | Implemented, polymorphic |
| Manage slots | `list_saves`, `delete_save` |

*Verified:* 120 assertions against real SQLite databases, all passing.
`python -m db.demo` exercises every path end to end.

**Measured performance:**

| Operation | Cost |
|---|---|
| `save_day()` with 50 messages | ~3 ms |
| `get_stats(30)` | ~0.5 ms |
| `get_events(100)` | ~0.7 ms |
| `get_weekly_summary()` | ~0.4 ms |

At 20 ticks/s a tick has 50 ms. The database uses none of it — nothing is
written per tick.

---

## 6. Simulation logic & realism (7 pts) — out of scope

Belongs to another focus area. This module supports it by storing the
figures the simulation produces.

---

## 7. Test plan & test cases (10 pts) + coverage & edge cases (5 pts)

**Required:** at least two tests **described, not implemented**, per function.

| Measure | Value |
|---|---|
| Functions/methods in the module | 67 |
| Functions without a `Tests:` section | **0** |
| Functions with fewer than 2 cases | **0** |
| Described test cases in docstrings | **134** |
| Consolidated test plan | `docs/test_plan.md` |

The cases live in **two** places on purpose: in the docstring right next to
the function it covers, and consolidated in `test_plan.md` with IDs and
categories.

Every case is tagged: **H** happy path, **B** boundary, **E** error,
**I** idempotence, **C** contract parity. Every function has at least one
**B** or **E** case — boundary and error coverage is the explicit target, not
a by-product.

*Verified:* an AST-based audit over all 18 modules reports zero gaps in
`Tests:`, `Args:` and `Returns:` sections.

---

## 8. Code documentation (15 pts)

**Required:** full documentation as taught — docstrings and inline docs.

| Measure | Value |
|---|---|
| Modules without a docstring | **0** of 18 |
| Classes without a docstring | **0** of 17 |
| Functions without a docstring | **0** of 67 |
| Functions with parameters but no `Args:` | **0** |
| Functions without `Returns:` | **0** |

Every docstring follows the same structure: summary, explanation, `Args:`
(what goes in), `Returns:` (what comes out), `Raises:` where applicable, and
`Tests:`. Inline comments explain *why*, not *what*.

---

## 9. Design visualisation — Mermaid (10 pts)

| Diagram | Count | File |
|---|---|---|
| Class diagrams | 5 | `docs/uml_class_diagram.md` |
| ER diagrams | 3 | `docs/uml_er_diagram.md` |
| Sequence diagrams | 5 | `docs/uml_sequence_diagrams.md` |
| **Total** | **13** | |

The brief asks for at least one comprehensive focus-specific class diagram
(present) and allows sequence diagrams as an addition (five present, covering
day-end write, chart read, save, load and startup).

---

## 10. Reflection & AI use (5 pts)

**Status: needs your own text.** See section 12 — this one cannot be
outsourced, and the criterion explicitly rewards understanding rather than
volume of AI output.

---

## 11. Deduction-relevant requirements

These cost points if missing, regardless of quality elsewhere.

| Requirement | Status | Evidence |
|---|---|---|
| Who does what visible **in the README** | Met | the root `README.md` assigns each focus area |
| Who does what visible **in the code** | Met | every module docstring carries an owner line — all 18 |
| Interface and database visibly separated by folder structure | Met | `db/interface/`, `db/models/`, `db/persistence/`; the dependency rule is grep-checkable |
| One responsibility per file, not everything in one Python file | Met | 18 modules, one class or one concern each |
| `requirements.txt` present | Met | `db/requirements.txt` |
| README with test instructions | Met for this module | `db/README.md`; **the root README still lacks whole-app run instructions** |
| Virtual environment excluded from the submission | Met | `.venv` is in `.gitignore`; database artefacts added too |
| Runs on a plain Python 3.14 kernel | Met | Python 3.14.6 verified; only dependency is SQLAlchemy |
| Planning matches implementation | Met | `planning/db_planning/db_requirements.md` matches the schema exactly |
| Basic console interaction | Met for this module | `python -m db.demo` is a runnable console program covering every operation |

### Open items outside this module

1. **Root `README.md` has no run instructions.** The brief requires that the
   examiner can start the application on a 3.14 kernel. Needs an install and
   run section once the application exists.
2. **The application has to call `save_day()`.** Until something does, this
   module contributes nothing observable to a running program.
3. **`planning/general/` is empty.**

---

## 12. What is still yours to write

The reflection (5 pts) has to be in your own words. Use
`docs/reflection.md` as the scaffold — the factual parts are filled in;
the judgement parts are marked `[YOUR TEXT]`.

The criterion is explicit: *"decisive is not the extent of AI use, but the
ability to understand the generated code, question it critically, adapt it
and reflect on your own learning process."*

Concrete material you can draw on, all of it real:

* **A performance bug found by measuring, not guessing.** `get_stats(30)`
  eagerly loaded every message of every day — data charts never use. Measured
  at 15.6 ms; after suppressing that load, 0.51 ms. A 30× improvement that
  only surfaced because the assumption was tested.
* **A usability bug in the ORM defaults.** SQLAlchemy applies `default=`
  values on insert, not on construction, so a freshly built
  `Lion(animal_id="a_01")` carried `hp = None` and `is_critical()` crashed on
  it. Fixed with an `init` event listener so defaults apply immediately.
* **A rejected first proposal.** The initial design was hand-written
  repositories and mappers with no ORM. That was dropped after the examiner's
  guidance that no large custom effort was expected — and the SQLAlchemy
  version turned out to demonstrate *more* object orientation, not less,
  because polymorphic loading and cascades are domain modelling rather than
  plumbing.
* **A trade-off consciously accepted.** `profit_loss` as a generated column
  cannot drift from `revenue - expenses`, at the cost of being `None` on
  objects that have not been through the database.
* **A limitation stated rather than hidden.** One save slot only; the fix
  (composite primary key) is documented in `architecture.md`.
