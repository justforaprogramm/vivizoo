# vivizoo — Frontend (`frontend/`)

The **frontend** is the graphical user interface of the zoo simulation, built with **PyQt6**. It
sits at the top of the three-tier architecture:

```
┌─────────────┐   API calls    ┌─────────────┐   domain→models   ┌─────────────┐
│   Frontend  │ ─────────────▶ │   Backend   │ ───────────────▶ │  Database   │
│   (PyQt6)   │ ◀───────────── │   (this)    │ ◀─────────────── │   (db/)     │
└─────────────┘   snapshots    └─────────────┘   models          └─────────────┘
```

It renders the zoo state, provides interactive controls for the player (God mode actions),
and displays real-time simulation feedback such as animal status, staff activities,
financial charts, and chat messages.

Module owner: **Erik (frontend)**.

---

## Scope and responsibilities

| Concern | Where it lives |
| --- | --- |
| Main window & layout | `frontend/core/main_window.py` |
| UI connection to `SimulationEngine` | `frontend/core/frontend_controller.py` |
| Reusable PyQt widgets (charts, stats, …) | `frontend/ui/` |
| Architecture and API documentation | `frontend/docs/` |

The frontend talks to exactly one object: a `SimulationEngine` (from `backend.core.engine`).
It receives snapshots via `engine.get_game_state()` and sends God-mode actions via
`engine.execute_action("feed_all")`. No direct database access — everything flows through
the backend API.

---

## Installation & running

From the repository root (inside the devcontainer):

```bash
pip install -r frontend/requirements.txt
```

Run the application:

```bash
python -m frontend.main
```

---

## Architecture

```
frontend/
├── __init__.py
├── main.py                  # Application entry point
├── README.md
├── requirements.txt
├── core/
│   ├── __init__.py
│   ├── main_window.py       # Main PyQt window
│   └── frontend_controller.py # Bridge to SimulationEngine
├── ui/
│   ├── __init__.py
│   ├── zoo_view.py          # Zoo map / enclosure overview
│   ├── animal_panel.py      # Animal detail & status
│   ├── staff_panel.py       # Employee overview
│   ├── finance_view.py      # Budget & charts
│   ├── inventory_view.py    # Stock overview
│   └── chat_view.py         # Message logger feed
└── docs/
    └── (Mermaid diagrams, API docs)
```

---

## How to extend

* Add new widgets in `frontend/ui/` — each widget receives a game-state snapshot and
  renders its portion of the data.
* The `FrontendController` in `frontend/core/` polls the engine on a timer, dispatches
  state to widgets, and translates button clicks into `execute_action` calls.
* Keep the UI layer stateless — all authoritative data lives in the backend.