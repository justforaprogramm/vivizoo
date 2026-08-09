# vivizoo — A Digital Twin of a Zoo Simulation

**vivizoo** is an object-oriented zoo simulation combining the administrative and economic aspects of a zoo (enclosures, staff, finances, inventory) with the biological processes of its animals (hunger, health, welfare, behaviour, weather) — connected, as required by the assignment, through a shared simulation engine that advances both worlds with every simulation step.

The project is a **runable application**: an interactive PyQt6 frontend (map, animals, visitors, controls), an object-oriented simulation backend, and a persistent database (daily statistics, chat log, complete savegames) — clearly separated into three modules.

---

## Project Layout & Assignment of Work

The project is split into three functional areas (frontend, backend, database). Each area has **one responsible person**, identifiable through the owner line in every module docstring as well as in the module READMEs.

| Area | Responsible | Module | README |
| --- | --- | --- | --- |
| **Frontend** (PyQt6 UI) | Erik | `frontend/` | [`frontend/README.md`](frontend/README.md) |
| **Backend** (OOP simulation) | Benjamin | `backend/` | [`backend/README.md`](backend/README.md) |
| **Database** (persistence) | Jannes | `db/` | [`db/README.md`](db/README.md) |

> Each person planned and implemented their area individually; the database planning lives under [`planning/`](planning/). The detailed READMEs of the three modules contain the installation, architecture, API and test information and are linked in detail below.

---

## Architecture at a Glance

```
┌─────────────┐   API calls         ┌─────────────┐   domain→models  ┌─────────────┐
│   Frontend  │  ───────────────▶   │   Backend   │  ──────────────▶ │  Database    │
│    PyQt6    │  ◀───────────────   │  SimEngine  │  ◀────────────── │   (SQLite)   │
└─────────────┘   snapshots /       └─────────────┘   DailyStats +   └─────────────┘
                     action results                    Savegame
```

- The **frontend** talks to *exactly one* object, the `SimulationEngine` (API contract in `backend/docs/api.md`).
- The **backend** holds all of the object-oriented simulation logic (animal hierarchy, staff, enclosures, finances, inventory, weather, tick loop) and writes **no SQL**.
- The **database** persists daily statistics, the chat log, and complete savegames behind an abstract interface (`db.interface.AbstractPersistence`).

The three OOP areas of the assignment are implemented as follows:

| Assignment area | Implementation |
| --- | --- |
| **1. Zoo management** | `Zoo`, `Employee` (+ `Keeper`, `Veterinarian`, `AdminStaff`), `Enclosure`, `Finances`, `Inventory` |
| **2. Animal simulation** | `Animal` (+ `Lion`, `Giraffe`, `Penguin`), `Behaviour` (+ `FeedingBehaviour`, `RestingBehaviour`), `EnvironmentFactor`, `StatusEffect` |
| **3. Simulation core** | `SimulationEngine` (tick loop), `EventScheduler`, `ActionHandler` |

---

## Quickstart (in the Devcontainer)

The project is developed and run **exclusively in a Devcontainer** (see [Why a Devcontainer made sense](#why-a-devcontainer-made-sense)). The container provides a **Python-3.14 kernel**, a pre-installed virtual environment under `/opt/venv`, and the required Qt system libraries, so the GUI starts out of the box. There is therefore **no manual setup on the host** — you work and run everything inside the container.

### 1. Open the Devcontainer

Open the repository in a container-capable IDE (e.g. VS Code with "Reopen in Container") or with DevPod. The configuration lives in [`.devcontainer/`](.devcontainer/) with `.devcontainer/Dockerfile` and `.devcontainer/devcontainer.json`; on first open the image is built and the virtual environment is set up and activated automatically. `SQLAlchemy` and `PyQt6` are pre-installed.

Only if the dependencies are ever missing inside the container can they be installed with:

```bash
pip install -r db/requirements.txt          # SQLAlchemy
pip install -r frontend/requirements.txt    # PyQt6
```

> **Note:** the backend needs the same dependencies as the database (SQLAlchemy) because it builds on the persistence interface. For this reason there is **no separate** `backend/requirements.txt` — the required packages come from `db/requirements.txt` and `frontend/requirements.txt`.

### 2. Start the frontend (GUI app)

```bash
python -m frontend.main
```

This opens the window with the zoo map, animals, visitors, enclosures and the control panels (feed, heal, buy, clean). If no display is available in the container (headless environment), the frontend can be started without a backend engine:

```bash
python -m frontend.main --no-engine
```

---

## Demos (run per module)

All three modules provide a self-contained console demo. Each one demonstrates its scope end-to-end and can be run directly.

| Command | What it demonstrates |
| --- | --- |
| `python -m backend.demo` | Backend core: build a zoo, run engine ticks, trigger God-mode actions (buy food, feed all), query hover data, inventory & money. With `--with-db` a finished day is additionally written to the database and read back as a chart row. |
| `python -m db.demo` | Database: write 3 daily statistics + chat log, read them back, weekly aggregation (SQL view), save/load a complete savegame with polymorphic loading of the species. The default is in-memory; with `python -m db.demo data/demo.sqlite` a real file is written. |
| `python -m frontend.main` | Frontend: starts the full GUI with an auto-generated demo simulation (lion, giraffe, penguins in three enclosures). |

> All demos run persistence **in-memory by default** (`:memory:`), so no files are left behind. A real database file is only created when a path is passed.

---

## How to Start the Application — Step by Step

You start the full application (database + backend + frontend) like this:

```bash
# 1. Run the database demo to verify persistence works
python -m db.demo

# 2. Verify the backend core
python -m backend.demo

# 3. Start the GUI (the frontend builds the demo simulation itself)
python -m frontend.main
```

The frontend automatically creates a demo simulation (lion "Simba", giraffe "Melman", penguins "Pingu" & "Kowalski") and connects to the backend through a `SimulationEngine`. Persistence in the frontend default is purely in-memory (no files land on disk). If you want to store real savegames / daily histories, connect a `DbGateway` from `backend.persistence` (see `backend/docs/api.md`, section *Bootstrap*).

---

## The Three Modules in Detail

The following README files describe each module completely — installation, architecture, the OOP concepts used, tests and (where present) the API.

### 🔵 Backend — `backend/README.md`
The **simulation engine** at the core of the application. It contains the animal hierarchy (`Animal` → `Lion`/`Giraffe`/`Penguin`), the staff hierarchy (`Employee` → `Keeper`/`Veterinarian`/`AdminStaff`), enclosures, finances, inventory, weather, behaviour (strategy pattern) and the tick loop. It is strictly decoupled from the frontend and the database: **it renders no UI and writes no SQL**.

📄 [`backend/README.md`](backend/README.md) includes:
- Installation and demo instructions
- Responsibility table (where each piece of logic lives)
- Dependency rule (`backend.core → backend.persistence → db`)
- How to connect the frontend
- Test strategy & fixture templates
- AI use & reflection

Documents under [`backend/docs/`](backend/docs/): [`api.md`](backend/docs/api.md) (API contract), [`class_diagram.md`](backend/docs/class_diagram.md) (Mermaid UML), [`sequence_diagrams.md`](backend/docs/sequence_diagrams.md) (Mermaid sequences), [`test_plan.md`](backend/docs/test_plan.md).

### 🟢 Database — `db/README.md`
The **persistence layer**. It stores daily statistics, chat log and complete savegames in SQLite (via SQLAlchemy) behind the abstract interface `AbstractPersistence`. Callers never see SQL — they create objects and call methods.

📄 [`db/README.md`](db/README.md) includes:
- Quickstart & complete API examples
- Table overview (7 tables) and layout (`interface/`, `models/`, `persistence/`)
- A grep-checkable dependency rule
- Performance measurements
- An index of the documentation files

Documents under [`db/docs/`](db/docs/): [`architecture.md`](db/docs/architecture.md), [`usage.md`](db/docs/usage.md), [`uml_class_diagram.md`](db/docs/uml_class_diagram.md), [`uml_er_diagram.md`](db/docs/uml_er_diagram.md), [`uml_sequence_diagrams.md`](db/docs/uml_sequence_diagrams.md), [`test_plan.md`](db/docs/test_plan.md), [`criteria_audit.md`](db/docs/criteria_audit.md), [`reflection.md`](db/docs/reflection.md).

### 🟠 Frontend — `frontend/README.md`
The **Graphical User Interface** in PyQt6. It renders the zoo map, animals and visitors as sprites, shows status panels, finance/inventory views and a chat feed, and translates clicks into backend actions. It works *always* through the `SimulationEngine` — no direct database access.

📄 [`frontend/README.md`](frontend/README.md) includes:
- Installation & start
- Architecture of the GUI components
- An extension guide
- A pointer to the frontend docs under [`frontend/docs/`](frontend/docs/)

Under [`frontend/docs/`](frontend/docs/): [`frontend_class_diagram.md`](frontend/docs/frontend_class_diagram.md) (Mermaid class diagram), [`FRONTEND_ARCHITECTURE.md`](frontend/FRONTEND_ARCHITECTURE.md), [`IMPLEMENTATION_PLAN.md`](frontend/docs/IMPLEMENTATION_PLAN.md), [`CHANGELOG.md`](frontend/docs/CHANGELOG.md), [`KI_REFLEXION.md`](frontend/docs/KI_REFLEXION.md).

---

## Why a Devcontainer Made Sense

The project is a **Qt GUI application** plus a SQLite database. Exactly for this a reproducible development container setup pays off — the Devcontainer in [`.devcontainer/`](.devcontainer/) (`.devcontainer/Dockerfile` + [`devcontainer.json`](.devcontainer/devcontainer.json)) solves three concrete problems:

**1. Qt system libraries.** PyQt6 requires a set of native `.so` libraries on Linux (`libGL`, `libEGL`, `libxcb-*`, `libxkbcommon`, …). Without them the frontend immediately fails with "could not load Qt platform plugin". The Dockerfile installs exactly these packages (`libgl1`, `libegl1`, `libxcb-*`, …) up front — so the GUI **starts out of the box in the container**, without every team member having to install the right packages individually on their own machine.

**2. A guaranteed Python 3.14 kernel.** The assignment requires the application to run "with a 3.14 Python kernel". The image is based on `mcr.microsoft.com/devcontainers/python:3.14` — so the whole team develops, tests and checks on **the same Python version**, and there are no "works on my machine" discrepancies between machines.

**3. A consistent virtual environment.** The Dockerfile creates a central venv under `/opt/venv`, activates it automatically (via `bash.bashrc`/`.bashrc`) and installs the dependencies (`pandas`, `sqlalchemy`, `PyQt6`) directly into it. `devcontainer.json` additionally sets `VIRTUAL_ENV` and the `PATH` so that both VS Code/Pylance and the terminal use the correct environment. New team members clone the repo, open it in the Devcontainer and immediately have a runable environment — without manual venv setup or configuration pitfalls.

> **Note on the submission:** the virtual environment (`.venv`) and the database artefacts (`data/*.sqlite*`) are excluded from version control via [`.gitignore`](.gitignore) and do **not** belong in the submission. The examiner can run the application entirely through the Devcontainer (see [Quickstart](#quickstart-in-the-devcontainer)); the `.devcontainer/` folder is part of the repository so the container can be rebuilt by anyone.

---

## Tests

The assignment requires **at least two tests per function to be described, but not implemented**. These test descriptions are extensively present:

- **In the code:** every method carries a `Tests:` block in its docstring describing at least two cases (happy path, edge case, error case).
- **Consolidated:** the test plans [`backend/docs/test_plan.md`](backend/docs/test_plan.md) and [`db/docs/test_plan.md`](db/docs/test_plan.md) bring together all described cases per module (in `db` with the ID categories *H/B/E/I/C*).

The module READMEs describe how concrete pytest fixtures and test files can be derived from these descriptions.

---

## Planning

The planning phase is documented per area. The database planning lives under [`planning/db_planning/`](planning/db_planning/) (`backend_core_plan.md`, `db_requirements.md`). The Mermaid designs (class diagrams showing inheritance, composition, aggregation, association, as well as sequence diagrams) are located in the `*_diagram.md` files of the three module documentation folders (see above).

---

## License

See [LICENSE](LICENSE).
