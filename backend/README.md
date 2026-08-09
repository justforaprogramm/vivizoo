# vivizoo — Backend (`backend/`)

The **backend** is the core logic ("the heartbeat") of the zoo simulation. It
sits in the middle of the three-tier architecture:

```
┌─────────────┐   API calls    ┌─────────────┐   domain→models   ┌─────────────┐
│   Frontend  │ ─────────────▶ │   Backend   │ ───────────────▶ │  Database   │
│   (PyQt)    │ ◀───────────── │   (this)    │ ◀─────────────── │   (db/)     │
└─────────────┘   snapshots    └─────────────┘   models          └─────────────┘
```

It owns the **object-oriented simulation logic**: the tick loop, the animal
hierarchy, behaviours, visitors, finances, inventory, staff, environmental
factors and the player's "God mode". It neither renders the UI nor writes
SQL — those are the frontend's and database module's jobs.

Module owner: **Benjamin (backend)**.

---

## Scope and responsibilities

| Concern | Where it lives |
| --- | --- |
| Tick engine, game state, entity info, actions | `backend/core/engine.py` |
| `execute_action` God mode (feed, heal, buy, clean, …) | `backend/core/action_handler.py` |
| Animal hierarchy + behaviour (chapter 2) | `backend/core/animal.py`, `behaviour.py` |
| Zoo aggregate root (composition) | `backend/core/zoo.py` |
| Staff roles (chapter 1) | `backend/core/employee.py` |
| Visitors / budget / stock / weather / effects / chat | `backend/core/visitor.py`, `finances.py`, `inventory.py`, `environment.py`, `status_effect.py`, `message_logger.py` |
| Persistence *adapter* to the database contract | `backend/persistence/db_gateway.py` |
| Architecture and API documentation | `backend/docs/` |

The backend follows a strict dependency rule:

```
backend.core  ->  backend.persistence  ->  db.interface + db.models   (imports)
```

Only `backend/persistence/db_gateway.py` may import from `db`. The core
domain stays database-ignorant, which keeps the simulation testable in
isolation.

---

## Installation & running

The backend is standard library, but it imports the database module, which
needs SQLAlchemy. From the repository root (inside the devcontainer):

```bash
pip install -r backend/requirements.txt
```

Run the self-contained demonstration of the core logic:

```bash
python -m backend.demo                  # in-memory only
python -m backend.demo --with-db        # also writes a day to the database
```

---

## How to plug the frontend in

The frontend talks to exactly one object: a `SimulationEngine`. The public
methods are (details in `docs/api.md`):

```python
engine = SimulationEngine(zoo, persistence=gateway, logger=MessageLogger.instance())

engine.start()                       # begin ticking in a background thread
engine.pause() / engine.set_speed(2.0)

state  = engine.get_game_state()     # snapshot each render frame
info   = engine.get_entity_info("a_01")   # tooltip data
msgs   = engine.get_chat_messages()  # chat feed (drained)
result = engine.execute_action("feed_all")   # God mode
rows   = engine.get_stats(7)         # chart data (optional gateway)
```

The `persistence` argument is optional: without it the backend runs purely in
memory (handy for demos), with it, day summaries and chat messages are stored
through `db.interface.AbstractPersistence`.

---

## Code-Qualität (Pylint)

Die Pylint-Konfiguration liegt auf der **Projektwurzel** (`.pylintrc`), damit
Pylint sie beim Aufruf von dort automatisch findet. Sie lockert gezielt die
Prüfungen, die der OOP-Entwurf (Kapselung, schlanke Strategie-/Handler-Klassen,
`db`-Imports in der Demo als dritte "Partei") konzeptionell vorsieht -- ohne
die Überladungs- oder snake_case-Schutzprüfungen grundsätzlich abzuschalten.
Da nur gelockert wird, hat die Datei für andere Module (z. B. `db/`) nie eine
senkende Wirkung.

```bash
cd /workspaces/vivizoo            # Projektwurzel
pylint backend/                   # => 10.00/10
```

---

## KI-Einsatz & Reflexion
> **Note:** benutzt wurden `deepseek flash` von plattform.deepseek.com und `gemini flash` von gemini.google.com

Dieses Backend wurde mit Unterstützung durch einen KI-Assistenten entwickelt.
Die KI wurde gezielt für folgende Zwecke eingesetzt:

* **Code schreiben:** Funktionen und Klassen wurden einzeln von der KI
  generieren lassen (beispielsweise die Tick-Logik, die `Behaviour`-Strategien
  oder die `ActionHandler`-Dispatcher), statt ganze Module auf einmal zu
  erzeugen.
* **Gedankenanstöße:** Die KI diente als Sparringspartner für Designfragen
  (z. B. wie die Tages-/Phasenlogik getaktet wird, wie Besucher-Wahrscheinlichkeit
  sinnvoll vom Wetter abhängen sollte oder wie die Persistenz sauber hinter einem
  Adapter versteckt wird).
* **Gezielte Umstrukturierung:** Schwer lesbarer oder „nicht guter" Code wurde
  gezielt refaktorisiert — auf Basis konkreter KI-Vorschläge wurde die Struktur
  umgebaut, ohne das bestehende Verhalten zu verändern.
* **Pylint-Bereinigung:** Die KI half dabei, Pylint-Warnungen zu beheben und
  die Konfiguration (`.pylintrc`) so anzupassen, dass sie die vom OOP-Entwurf
  beabsichtigten Muster (Kapselung, schlanke Strategie-Klassen, `db`-Import der
  Demo als dritte Partei) ohne die allgemeinen Qualitätsregeln
  abzuschalten.

**Eigenverantwortung / Qualitätssicherung:** Die KI wurde ausschließlich als
Werkzeug eingesetzt. Jede einzelne erzeugte Funktion wurde **logisch selbst
geprüft** (die `Tests:`-Blöcke in den Docstrings sind ein Ergebnis dieser
manuellen Verifikation), sodass die KI-generierten Bausteine nur nach
menschlicher Kontrolle übernommen wurden.

---

## Tests

Dieses Modul liefert keine fertigen Tests, sondern den Rahmen. Die Erwartungen an
jede öffentliche Methode sind bereits als kurze `Tests:`-Blöcke in den
Docstrings hinterlegt — sie sind die Grundlage für Unit-Tests.


### Struktur des Testordners

Der Ordner `backend/tests/` wird sinnvollerweise **spiegelbildlich zum
Produktivcode** aufgebaut — je Produktivmodul eine Testdatei, mit einem
gemeinsamen Fixture-Modul für die wiederkehrende Setup-Logik:

```
backend/tests/
├── __init__.py           # macht den Ordner zum Package (Imports von backend.*)
├── conftest.py           # gemeinsame pytest-Fixtures (z. B. eine frische Zoo-Instanz)
├── test_animal.py        # tests für backend/core/animal.py (Kapitel 2: Tiersimulation)
├── test_employee.py      # tests für backend/core/employee.py (Kapitel 1: Personal)
├── test_enclosure.py     # tests für backend/core/enclosure.py
├── test_zoo.py           # tests für das Aggregat backend/core/zoo.py
├── test_engine.py        # tests für den Tick-Loop und den ActionHandler
├── test_finances.py      # tests für backend/core/finances.py (Budgets)
├── test_inventory.py     # tests für backend/core/inventory.py (Lager)
├── test_environment.py   # tests für backend/core/environment.py (Wetter)
├── test_status_effect.py # tests für backend/core/status_effect.py
└── test_persistence.py   # tests für backend/persistence/db_gateway.py (Datenbank-Anschluss)
```

Richtlinien für die Struktur:

* **Ein Produktivmodul, eine Testdatei** — so bleibt die Zuordnung eindeutig
  und es ist sofort sichtbar, welche Realität ein Test abdeckt.
* **`conftest.py`** hält den Setup-Code (Zoo bauen, Logger frisch setzen,
  Engine erstellen) als Fixtures, statt ihn je Testdatei zu duplizieren.
  Beispiele dafür stehen weiter unten.
* **Testnamen sprechen das *Verhalten* aus**, nicht die Implementierung:
  `test_feed_reduces_hunger` statt `test_feed`.
* Jede Testdatei beginnt mit einem kurzen Docstring, der das Kapitel/den
  Bereich nennt (z. B. "Kapitel 2: Tiersimulation").

### Was wird getestet

Das Backend deckt die drei OOP-Säulen der Aufgabe ab — daran orientieren sich
die Tests:

| Bereich | Beispielfall |
| --- | --- |
| **Kapselung** | Statistik kann nicht außerhalb 0–100 geraten; `spend()` darf das Budget nicht negativ machen; `finances._balance` ist privat. |
| **Polymorphismus** | `Lion`/`Giraffe`/`Penguin` erben `Animal`, unterscheiden sich aber in `PREFERRED_FOOD`, `DIGESTION_RATE`, `move()`; `create_animal("penguin", …)` liefert die richtige Subklasse. |
| **Komposition** | `Zoo` enthält Enclosures/Finanzen/Inventar; `Enclosure` hält Tiere; ein „Zoo-Verwaltung"-Test prüft Hinzufügen/Entfernen und Kapazität. |

Konkret pro Modul:

* **animal.py** — Art-Diskriminator, `feed`/`rest`/`age_one_day`/`move`, der
  Hunger-Anstieg über Ticks, Tod nach 3 verhungerten Tagen, Werte-Klemmung.
* **employee.py** — jede Rolle übernimmt ihre Kernaufgabe im Zoo
  (Keeper füttert/putzt, Tierarzt heilt, Admin setzt Ticketpreis).
* **enclosure.py** — `free_slots`, `is_full`, `clean`, `average_welfare`,
  Verschmutzungsabnahme.
* **zoo.py** — Enclosures/Tiere/Personal anlegen und finden, Tages-Snapshot,
  `to_game_state`-Form, Besucher zahlen Ticket.
* **engine.py** — Tick zählt hoch; `execute_action` mutiert den Zoo;
  unbekannte Aktion wirft `ValueError`; `get_entity_info` liefert `{}` bei
  unbekannter ID.
* **persistence.py** — über einen **in-memory** `ZooDatabase(":memory:")`:
  nach einem abgeschlossenen Tag ist genau ein `DailyStats`-Eintrag lesbar;
  die Events teilen sich die `day_id`.

### Wichtige Randbedingungen für einzelne Tests

* **Isolation des Loggers.** `MessageLogger` ist ein Singleton. Vor einem
  Test, der Chat-Einträge erwartet, muss er frisch gesetzt werden, sonst
  schleppen Tests Nachrichten aus vorherigen Tests mit:
  ```python
  MessageLogger.reset_to_fresh()
  zoo = Zoo(name="T", logger=MessageLogger.instance())
  ```
* **Determinismus des Zufalls.** Bewegungen, Wetter und Besucher-Spawns sind
  zufällig. Tests dafür dürfen **keine Festwerte** auf Koordinaten prüfen,
  sondern nur Invarianten („in einem Bereich", „ein gültiges Wetter"). Wo
  möglich mit `random.seed(...)` arbeiten oder die Zufallskomponente (etwa
  `_update_offset`) gezielt auf `0` setzen, damit der throttled Update sofort
  feuert.
* **Tick-Grenzen.** Viele Abläufe sind getaktet (Hunger alle N Ticks,
  Tierarzt ab ~20, Tag wird bei `tick % 480 == 0` geschlossen). Ein Test des
  Tagesabschlusses muss die Engine exakt **einmal eine volle Runde laufen
  lassen** (`for _ in range(TICKS_PER_DAY): engine.tick()`), sonst wird nie ein
  Tag geschlossen und die Persistenz liefert 0 Zeilen.
* **Hunger-Semantik.** Hunger ist `0 = satt` / `100 = verhungernd`. Ein
  „füttern"-Test startet ein Tier deshalb hungrig (z. B. `_hunger = 70.0`),
  sonst wird es nicht gefüttert, weil `hunger < threshold` gilt.
* **Keine Seiteneffekte auf echte Daten.** Budget-, Inventar- und
  Zufalls-Tests bauen ihre Objekte frisch auf. Die Persistenz-Tests nutzen
  `ZooDatabase(":memory:")` und schließen sie am Ende (`storage.close()`).
* **Kapselung respektieren.** Nach Möglichkeit keine privaten Attribute
  (`_hp` etc.) in Tests schreiben; wo es (z. B. beim Vorsetzen des Hungers)
  nicht zu umgehen ist, dies im Kommentar kenntlich machen.
* **Jeder Test prüft eine Sache.** Ein Fehlschlag soll eine einzige Ursache
  haben; deshalb pro Test eine Behauptung bzw. ein zusammenhängendes Szenario.

### Hilfreiche Fixture-Vorlagen (für `conftest.py`)

```python
import pytest
from backend.core.message_logger import MessageLogger
from backend.core.zoo import Zoo

@pytest.fixture
def zoo():
    MessageLogger.reset_to_fresh()
    z = Zoo(name="Test Zoo", logger=MessageLogger.instance())
    savanna = z.add_enclosure("Savanna 1", "savanna", capacity=8)
    return z, savanna

@pytest.fixture
def hungry_lion(zoo):
    z, savanna = zoo
    lion = z.add_animal("lion", "Simba", savanna)
    lion._hunger = 80.0  # hungrig -> wird von feed_all gefüttert
    return z, lion
```

---

## Database relationship ("nichts zur Datenbank dazu")

This module **adds no tables and no schema**. It consumes the database
module's public contract exactly as the planning requires:

* It holds a reference to an `AbstractPersistence` (e.g. `ZooDatabase`).
* At the end of each day it builds the `DailyStats` and `Event` model objects
  the database module already knows and calls `persistence.save_day(...)`.
* The mapping happens in `backend/persistence/db_gateway.py`.

Field names (species keys `"lion"`/`"giraffe"`/`"penguin"`, `FoodType`
resources, `enclosure_id`, …) intentionally mirror the database module, so the
adapter needs no transformation logic.

---

## Documentation

* `docs/class_diagram.md` — Mermaid UML class diagram of the domain.
* `docs/sequence_diagrams.md` — Mermaid sequence diagrams (tick loop, action,
  persistence).
* `docs/api.md` — the frontend-facing API contract and data shapes.
* `docs/test_plan.md` — distributed test expectations (each method's `Tests:`
  docstring) and how to turn them into unit tests (see the **Tests** section
  above for the concrete structure and boundary conditions).
