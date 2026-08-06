# 🤖 Frontend Implementation Plan — vivizoo

> **Audience:** AI coding agents implementing the frontend.
> **Read this FIRST** before writing any code.
> **Last updated:** 2026-08-06
>
> This document reconciles three sources:
> 1. `frontend/FRONTEND_ARCHITECTURE.md` — UI component specs (Erik's design)
> 2. `planning/db_planning/backend_core_plan.md` — what the backend actually provides
> 3. `frontend/README.md` — module structure & coding conventions
>
> Where these sources conflict, **this document is authoritative.** All conflicts have been resolved below with explicit decisions.

---

## ⚠️ GRADING REQUIREMENTS — READ BEFORE ANY CODE

> **These are the official Bewertungskriterien from the project specification.**
> Failure to meet these = point deductions. Every AI agent MUST verify these
> before marking any task complete.

### 🔴 OOP Principles (40 Punkte — direkte Auswirkung auf die Note)

| Kriterium | Punkte | Frontend-Umsetzung | MUSS erfüllt werden durch |
|-----------|--------|-------------------|--------------------------|
| **Klassenstruktur & Modellierung** | 12 | Jede UI-Komponente ist eine eigene Klasse in eigener Datei. Keine Monster-Files. | `ui/*.py` — eine Klasse pro Datei |
| **Vererbung & Polymorphie** | 10 | `AnimalSprite` als Basis, `AsciiLionSprite` erbt davon (oder beide von gemeinsamer abstrakter Basis `BaseEntitySprite`). Polymorphes `render()` pro Spezies. | `ui/animal_sprite.py`, `ui/lion_sprite.py`, `ui/visitor_sprite.py` |
| **Kapselung & Datenintegrität** | 8 | Alle internen Zustände der UI-Klassen sind `_privat`. Kein direktes Lesen/Schreiben von Backend-Daten — alles über `FrontendController`. | `_selected_animal_id`, `_controller`, private dicts in `ZooScene` |
| **Modularität & Erweiterbarkeit** | 10 | Neue Tierart hinzufügen = eine Konstante + eine Sprite-Klasse. Neue Aktion = ein Button. Architektur in `IMPLEMENTATION_PLAN.md` §0 dokumentiert. | Ordnerstruktur `core/` + `ui/` + `assets/` |

### 🔴 Funktionalität & Korrektheit (15 Punkte)

| Kriterium | Punkte | MUSS |
|-----------|--------|------|
| **Implementierung der Kernfunktionen** | 8 | Der Core-Prototyp muss LAUFFÄHIG sein. Map sichtbar, Tiere bewegen sich, Buttons lösen Aktionen aus, Chatlog zeigt Nachrichten. Kein Dummy-Code, der nichts tut. |
| **Simulationslogik & Realismus** | 7 | Die UI muss den Backend-Zustand KORREKT wiedergeben. Hunger-Balken muss dem Backend-Hunger entsprechen. Tote Tiere müssen grau sein. |

### 🔴 Testbeschreibung & Teststrategie (15 Punkte)

| Kriterium | Punkte | MUSS |
|-----------|--------|------|
| **Testplan & Testfälle** | 10 | JEDE öffentliche Funktion/Methode braucht MINDESTENS 2 Testbeschreibungen im Docstring. Format: `Tests:` Block. (Nicht implementieren — nur BESCHREIBEN.) |
| **Testabdeckung & Randfälle** | 5 | Randfälle abdecken: leeres `game_state`, `None`-Engine, Tier tot, Inventar leer, maximale Zoom-Stufe, 500+ Chat-Nachrichten. |

**Jede Datei MUSS Docstrings mit `Tests:`-Blöcken enthalten.** Siehe §8 für die vollständige Liste.

### 🔴 Dokumentation (15 Punkte)

| Kriterium | Punkte | MUSS |
|-----------|--------|------|
| **Code-Dokumentation** | 15 | **JEDE Klasse und JEDE öffentliche Methode** braucht einen vollständigen Docstring mit: Beschreibung, `Args:`, `Returns:`, `Raises:`, `Tests:`. Keine Ausnahmen. |

**Docstring-Template für jede Methode:**
```python
def update_state(self, x: float, y: float, is_dead: bool) -> None:
    """Update the sprite's visual state and position.
    
    Args:
        x: New X pixel coordinate on the map.
        y: New Y pixel coordinate on the map.
        is_dead: If True, render the sprite in grayscale with red border.
        
    Tests:
        - test_update_state_moves_sprite: Call with (100, 200, False), verify
          sceneBoundingRect().center() approx equals (100, 200).
        - test_update_state_dead_changes_color: Call with (x, y, True), verify
          brush color is gray (#30363d) and border is red (#f85149).
    """
```

### 🔴 Design-Visualisierung (10 Punkte — Mermaid-Diagramme)

| Kriterium | Punkte | MUSS |
|-----------|--------|------|
| **Mindestens ein schwerpunkt-spezifisches Klassendiagramm** | 10 | Ein **Mermaid-Klassendiagramm** das ALLE Frontend-Klassen zeigt: `ZooMainWindow`, `FrontendController`, `ZooScene`, `ZooGraphicsView`, `AnimalSprite`, `AsciiLionSprite`, `VisitorSprite`, `EnclosureItem`, `ActionPanel`, `ShopPanel`, `EntityInfoPanel`, `ChatlogWidget`. Mit Attributen, Methoden und Beziehungen (Vererbung, Aggregation, Assoziation). |
| **Sequenzdiagramme (optional, empfohlen)** | Bonus | Mindestens 2 Sequenzdiagramme: (1) "User klickt Feed-Button → ActionPanel → dispatch → engine.execute_action → UI Update", (2) "Hover über Tier → entity_hovered Signal → get_entity_info → EntityInfoPanel Update". |

> **Die Mermaid-Diagramme müssen in `frontend/docs/` abgelegt werden.**

### 🔴 Reflexion & KI-Einsatz (5 Punkte)

| Kriterium | Punkte | MUSS |
|-----------|--------|------|
| **KI-Einsatz dokumentiert** | 5 | Eine Datei `frontend/docs/KI_REFLEXION.md` die dokumentiert: Welche KI-Tools wurden verwendet, für welche Aufgaben, wie wurde der Output verifiziert ("human in the loop"), was wurde gelernt. |

### 🔴 Allgemeine Abgabe-Anforderungen (Abzugrelevant wenn nicht vorhanden!)

| Anforderung | Status |
|-------------|--------|
| `frontend/requirements.txt` mit allen Dependencies | ✅ Vorhanden (`PyQt6>=6.5.0`) |
| `frontend/README.md` mit Modulbesitzer (Erik) | ✅ Vorhanden |
| Python 3.14 Kompatibilität | ⚠️ MUSS getestet werden |
| `venv/` NICHT in Abgabe enthalten | ⚠️ Bei ZIP-Erstellung beachten |
| Sichtbare Trennung Frontend/Backend/DB | ✅ Ordnerstruktur existiert |
| Eine Klasse pro Datei | ⚠️ MUSS eingehalten werden (siehe §0) |
| KI-generierter Code via "human in the loop" verifiziert | ⚠️ MUSS in `KI_REFLEXION.md` dokumentiert werden |

---

## 0. Master Architecture Decision: Modular File Structure

The `FRONTEND_ARCHITECTURE.md` describes all components but implies a single `main_window.py`. For maintainability and parallel agent work, we use a **modular structure:**

```
frontend/
├── main.py                          # QApplication entry point + launch()
├── core/
│   ├── __init__.py
│   ├── main_window.py               # ZooMainWindow: top-level layout, signal routing, tick loop
│   ├── frontend_controller.py       # Lightweight bridge to SimulationEngine (dependency injection)
│   └── constants.py                 # All global constants (MAP_W, TICK_MS, colors, Z-order)
├── ui/
│   ├── __init__.py
│   ├── styled_widgets.py            # styled_button(), styled_label() factories (styled_card() deferred to Phase 3)
│   ├── zoo_scene.py                 # ZooScene: QGraphicsScene with entity dicts, lighting
│   ├── zoo_view.py                  # ZooGraphicsView: QGraphicsView with zoom/pan/hover/click
│   ├── animal_sprite.py             # AnimalSprite (Giraffe/Penguin circles)
│   ├── lion_sprite.py               # AsciiLionSprite (ASCII lion pixmap)
│   ├── visitor_sprite.py            # VisitorSprite (small colored dots)
│   ├── enclosure_item.py            # EnclosureItem (biome-colored rectangles)
│   ├── deco_sprite.py               # DecoSprite (emoji decorations — deferred Phase 3)
│   ├── action_panel.py              # ActionPanel: God-mode buttons
│   ├── shop_panel.py                # ShopPanel: Buy food, animals, ticket price
│   ├── entity_info_panel.py         # EntityInfoPanel: hover detail (HP bars, etc.)
│   ├── chat_view.py                 # ChatlogWidget: message feed
│   └── event_banner.py              # EventBanner (deferred — always hidden in Phase 1)
│   # deco_sprite.py NOT created in Phase 1 (Phase 3 feature)
├── assets/
│   ├── __init__.py
│   ├── ascii_lion.py                # ASCII_LION (40-line art for map pixmap)
│   └── ascii_lion_small.py          # ASCII_LION_SMALL (25-line art for info panel)
├── docs/
│   ├── FRONTEND_ARCHITECTURE.md     # Original design spec (reference only)
│   ├── IMPLEMENTATION_PLAN.md       # ← THIS FILE
│   ├── frontend_class_diagram.md    # Mermaid class diagram (grading requirement)
│   └── KI_REFLEXION.md              # AI usage reflection (grading requirement)
└── (__init__.py, README.md, requirements.txt)
```

**Why not a single `main_window.py`?** With 10+ UI classes, a monolithic file becomes unmaintainable and blocks parallel work. Each file has exactly one class with one responsibility (SRP). The `main_window.py` orchestrates but delegates all rendering to specialized files.

---

## 1. Phase Definitions (Aligned with Backend)

| Phase | Backend provides | Frontend renders |
|-------|-----------------|-----------------|
| **Phase 1 — Core Prototype** | `tick()`, `get_game_state()`, `execute_action()`, `get_entity_info()`, `get_chat_messages()` | Core map, animal sprites, visitor dots, action buttons, shop, chatlog, entity info tooltip, budget/rep toolbar |
| **Phase 2 — Biological Depth** | `time_of_day` 4-phase cycle, `stage` field, `StatusEffect` live, medicine inventory, `get_stats()` | Lighting overlay (real phases), staff panel, medicine in shop, age stage in info panel, charts |
| **Phase 3 — Tycoon Depth** | Upgrades, decorations, drag & drop, events, save/load | UpgradePanel, DecoSprite, drag & drop, EventBanner, SaveLoadDialog |

**Phase 1 is the only phase being implemented now.** Phase 2/3 features are listed to prevent premature implementation.

---

## 2. Conflict Resolutions (Decisions Made)

### 2.1 Food types: 3, not 5 ✅ RESOLVED
- **Backend Phase 1** provides only `MEAT`, `PLANTS`, `FISH`
- **FRONTEND_ARCHITECTURE.md** describes "5 Futtertypen"
- **Decision:** Use exactly 3 food types matching the backend. The ShopPanel QComboBox shows: "Fleisch (MEAT)", "Pflanzen (PLANTS)", "Fisch (FISH)" with prices. No 4th/5th type until Phase 2.

### 2.2 Day/Night lighting: simple toggle ✅ RESOLVED
- **Backend Phase 1** only provides `zoo_open: bool`. No `time_of_day` phases.
- **FRONTEND_ARCHITECTURE.md** assumes full 4-phase `PHASE_LIGHTING` table.
- **Decision:** Phase 1 `apply_lighting()` uses a simple 2-state approach: zoo open → bright (no overlay), zoo closed → dark (semi-transparent black overlay). The overlay widget exists and applies a single dark color when `zoo_open == False`. Phase 2 will expand to the full 4-phase table.

### 2.3 Animal stage: hardcoded "Erwachsen" ✅ RESOLVED
- **Backend Phase 1** sends no `stage` field (all animals are adults).
- **FRONTEND_ARCHITECTURE.md** shows "Alter · Stadium" row.
- **Decision:** The EntityInfoPanel shows "Alter · Stadium" row but the stage label is always "Erwachsen". Do NOT read a `stage` field from the backend — it doesn't exist in Phase 1.

### 2.4 Heal button: God-mode, no medicine gate ✅ RESOLVED
- **Backend Phase 1** implements `execute_action("heal", animal_id)` as pure God-mode (calls Veterinarian logic directly, no staff instance required, no medicine cost).
- **FRONTEND_ARCHITECTURE.md** gates the button on "Medikamente > 0".
- **Backend Phase 1 skip list** says "`MEDICINE` in inventory | Remove; no healing mechanic yet" — this refers to the medicine inventory item and staff auto-jobs, NOT the God-mode action.
- **Decision:** The heal button is **always enabled when an animal is selected** (no medicine check). The `Medicine` inventory field does not exist in Phase 1. If an animal is dead, the button disables. Phase 2 will add the medicine gate.

### 2.5 Enclosure data: hardcoded positions for Phase 1 ✅ RESOLVED
- **Backend `game_state_data`** has no `enclosures_on_map[]` field.
- **FRONTEND_ARCHITECTURE.md** assumes enclosures exist and can be rendered.
- **Decision:** Phase 1 uses **hardcoded enclosure definitions** in `constants.py` as a list of dicts (`ENCLOSURE_DEFS`). Animals map to enclosures via an `enclosure_id` field (must be added by backend team — see §7). If `enclosure_id` is not yet available, use the animal's position to determine which enclosure rectangle contains it (point-in-rect test).

### 2.6 All deferred features: SKIP in Phase 1 ✅ RESOLVED
- **UpgradePanel** → Not created. Deferred to Phase 3.
- **DecoSprite** → Not created. Deferred to Phase 3.
- **EventBanner** → Widget exists but `setVisible(False)` always. Deferred to Phase 2.
- **Drag & drop** → Not implemented. Deferred to Phase 3.
- **Staff panel** → Not created. All actions go through ActionPanel (God mode). Deferred to Phase 2.
- **Save/Load** → Not created. Deferred to Phase 3.
- **`styled_card()`** → Not needed in Phase 1 (UpgradePanel is the only consumer).

---

## 3. Data Contract with Backend

### 3.1 `game_state_data` (from `engine.get_game_state()`)

```python
# Exact shape the frontend MUST consume:
{
    "system": {
        "tick_count": int,        # Current tick number
        "time_of_day": str,       # Phase 1: always "DAY" (stub). Phase 2: "MORNING"/"NOON"/"EVENING"/"NIGHT"
        "zoo_open": bool          # Whether zoo is open to visitors
    },
    "finances": {
        "money": float,           # Current budget
        "reputation": int,        # 0-100
        "zoo_happiness": int      # 0-100 (Phase 1: stub → 100)
    },
    "inventory": {
        "MEAT": int,              # Amount in stock
        "PLANTS": int,            # Amount in stock
        "FISH": int               # Amount in stock
        # "MEDICINE" added in Phase 2
    },
    "animals_on_map": [
        {
            "id": str,            # e.g. "a_01"
            "species": str,       # "lion" / "giraffe" / "penguin"
            "name": str,          # Animal's display name
            "enclosure_id": str,  # e.g. "e_01" — ⚠️ MUST be added by backend (see §7)
            "x": float,           # Pixel X on the map
            "y": float,           # Pixel Y on the map
            "is_dead": bool       # True → render as grayscale
        }
    ],
    "visitors_on_map": [
        {
            "id": str,            # e.g. "v_99"
            "x": float,           # Pixel X on the map
            "y": float            # Pixel Y on the map
        }
    ]
    # "enclosures_on_map" not sent by backend in Phase 1 — hardcoded on frontend (see §2.5)
}
```

### 3.2 `animal_hover_data` (from `engine.get_entity_info(entity_id)`)

```python
{
    "name": str,                  # e.g. "Hungry Harry"
    "species": str,               # "Lion" / "Giraffe" / "Penguin" (capitalized)
    "age_days": int,              # Phase 1: always 0 (stub)
    "hp": int,                    # 0-100
    "hunger": int,                # 0-100, 0=full (satt), 100=starving (verhungernd) — matches backend spec
    "welfare": int,               # 0-100 (Phase 1: stub → 100)
    "status_effects": list[str]   # e.g. ["Slightly hungry"] (Phase 1: stub → [])
}
# Phase 2 adds: "stage": str, "biome": str
```

### 3.3 `chatlog_data` (from `engine.get_chat_messages()`)

```python
[
    {"time": str, "type": str, "text": str},
    # type ∈ {"INFO", "WARNING", "ERROR", "SUCCESS", "EVENT"}
]
```

### 3.4 `execute_action()` return value

```python
{
    "success": bool,
    "message": str,
    "chat_entries": list[dict]    # Same shape as chatlog_data entries
}
```

---

## 4. Implementation Order (Strict Dependency Chain)

Build in this exact order. Each file is fully testable after its dependencies are met.

### Stage A: Foundation (0 external dependencies)

| Order | File | Purpose | Depends On |
|-------|------|---------|-----------|
| A1 | `core/constants.py` | All global constants: colors, dimensions, z-order, enclosure positions, species→color mapping | Nothing |
| A2 | `ui/styled_widgets.py` | `styled_button()`, `styled_label()` factories | `constants.py` (colors) |
| A3 | `assets/ascii_lion.py` | ASCII_LION string constant (40 lines) | Nothing |
| A4 | `assets/ascii_lion_small.py` | ASCII_LION_SMALL string constant (25 lines) | Nothing |

### Stage B: Map sprites (depend on constants)

| Order | File | Purpose | Depends On |
|-------|------|---------|-----------|
| B1 | `ui/animal_sprite.py` | `AnimalSprite(QGraphicsEllipseItem)` — Giraffe & Penguin | `constants.py` |
| B2 | `ui/lion_sprite.py` | `AsciiLionSprite(QGraphicsPixmapItem)` + `_render_lion_pixmap()` + `_LION_CACHE` | `constants.py`, `ascii_lion.py` |
| B3 | `ui/visitor_sprite.py` | `VisitorSprite(QGraphicsEllipseItem)` | `constants.py` |
| B4 | `ui/enclosure_item.py` | `EnclosureItem(QGraphicsRectItem)` | `constants.py` |

### Stage C: Map container (depends on sprites)

| Order | File | Purpose | Depends On |
|-------|------|---------|-----------|
| C1 | `ui/zoo_scene.py` | `ZooScene(QGraphicsScene)` — entity dicts, `apply_lighting()`, `update_entities()` | B1-B4, `constants.py` |
| C2 | `ui/zoo_view.py` | `ZooGraphicsView(QGraphicsView)` — zoom, pan, hover/click signals | C1 |

### Stage D: Right-column panels (depend on styled_widgets, constants)

| Order | File | Purpose | Depends On |
|-------|------|---------|-----------|
| D1 | `ui/chat_view.py` | `ChatlogWidget` — message feed | `constants.py` |
| D2 | `ui/entity_info_panel.py` | `EntityInfoPanel` — hover details | `constants.py`, `styled_widgets.py`, (optional: `ascii_lion_small.py`) |
| D3 | `ui/action_panel.py` | `ActionPanel` — God-mode buttons | `constants.py`, `styled_widgets.py` |
| D4 | `ui/shop_panel.py` | `ShopPanel` — buy food/animals/ticket | `constants.py`, `styled_widgets.py` |
| D5 | `ui/event_banner.py` | `EventBanner` — always hidden in Phase 1 | `constants.py` |

### Stage E: Top-level wiring (depends on everything above)

| Order | File | Purpose | Depends On |
|-------|------|---------|-----------|
| E1 | `core/frontend_controller.py` | `FrontendController` — wraps SimulationEngine, provides `get_state()` → dict, `dispatch(action, **kwargs)` → ActionResult, `get_chat()` → list[dict] | Backend's `SimulationEngine` |
| E2 | `core/main_window.py` | `ZooMainWindow` — layout grid, toolbar, statusbar, `_tick()` loop, `_dispatch()` routing, `_update_sprites()`, `_update_labels()`, `_update_panels()` | C1, C2, D1-D5, E1, `constants.py`, `styled_widgets.py` |
| E3 | `main.py` | `launch_frontend()` — QApplication, QSS theme, instantiate engine+window, `app.exec()` | E2, `constants.py` |

---

## 5. Detailed Component Specifications

### 5.1 `core/constants.py`

```python
# Map & timing
MAP_W, MAP_H = 800, 600
TICK_MS = 100                         # 100ms polling = 10 FPS

# Z-order layers
Z_ENCLOSURES = 1
Z_DECORATIONS = 2                     # (unused in Phase 1)
Z_ANIMALS = 4
Z_VISITORS = 5
Z_DRAG = 10                           # (unused in Phase 1)
Z_OVERLAY = 9

# Dark Forest color palette (10 colors)
C_BG_DEEP  = "#0d1117"
C_BG_PANEL = "#161b22"
C_BG_CARD  = "#1c2333"               # (unused in Phase 1)
C_ACCENT   = "#3fb950"               # Green
C_ACCENT2  = "#2ea043"               # Darker green (hover)
C_GOLD     = "#d2991d"
C_RED      = "#f85149"
C_TEXT     = "#e6edf3"
C_TEXT_DIM = "#8b949e"
C_BORDER   = "#30363d"

# Species → color mapping (for sprites)
SPECIES_COLORS = {
    "giraffe": "#d4a44a",
    "penguin": "#7986cb",
    # Lion uses ASCII pixmap, but fallback color:
    "lion": "#e8a838"
}

# Species → food type mapping (for determining inventory key)
SPECIES_FOOD = {
    "lion":    "MEAT",
    "giraffe": "PLANTS",
    "penguin": "FISH"
}

# Food prices (€ per unit)
FOOD_PRICES = {
    "MEAT":   50,
    "PLANTS": 30,
    "FISH":   40
}

# Animal purchase prices
ANIMAL_PRICES = {
    "lion":    8000,
    "giraffe": 5000,
    "penguin": 3000
}

# Hardcoded enclosure positions (Phase 1 only — Phase 2 reads from backend)
ENCLOSURE_DEFS = [
    {"id": "e_01", "name": "Savanne 1", "biome": "savanna", "x": 30,  "y": 30,  "w": 340, "h": 250, "capacity": 5},
    {"id": "e_02", "name": "Eiswelt 1",  "biome": "ice",     "x": 400, "y": 30,  "w": 340, "h": 250, "capacity": 4},
    {"id": "e_03", "name": "Aquarium 1", "biome": "water",   "x": 30,  "y": 310, "w": 340, "h": 250, "capacity": 3},
]

# Biome → fill color
BIOME_COLORS = {
    "savanna": "#3d2b1f",
    "ice":     "#1b3b4d",
    "water":   "#1b2d3b"
}

# Phase 1 lighting (simple 2-state)
LIGHTING_DAY   = (0, 0, 0, 0)        # Fully transparent (zoo open)
LIGHTING_NIGHT = (0, 0, 0, 120)      # Semi-transparent black (zoo closed)

# Chat type → QColor
CHAT_COLORS = {
    "INFO":    "#8b949e",
    "WARNING": "#d2991d",
    "ERROR":   "#f85149",
    "SUCCESS": "#3fb950",
    "EVENT":   "#d2991d"
}

# Toolbar labels
WINDOW_TITLE = "🦁 vivizoo — Zoo Digital Twin"
WINDOW_W, WINDOW_H = 1400, 900
```

### 5.2 `ui/styled_widgets.py`

Two factory functions only in Phase 1:

```python
def styled_button(text: str, accent: bool = False, danger: bool = False, 
                  small: bool = False) -> QPushButton:
    """Create a consistently styled QPushButton."""
    # accent → green, danger → red, default → neutral dark
    # small → compact padding
    # All use setStyleSheet() with hover/disabled pseudo-states

def styled_label(text: str = "", dim: bool = False, large: bool = False,
                 bold: bool = False, color: str | None = None,
                 size: int | None = None) -> QLabel:
    """Create a consistently styled QLabel."""
    # dim → C_TEXT_DIM, default → C_TEXT
    # large → 18px, default → OS default
    # color/size → custom overrides
```

### 5.3 `ui/animal_sprite.py` — `AnimalSprite`

```python
class AnimalSprite(QGraphicsEllipseItem):
    """Circle + letter for Giraffe and Penguin."""
    
    entity_hovered = pyqtSignal(str)    # animal_id
    entity_unhovered = pyqtSignal()
    
    def __init__(self, animal_id: str, species: str, x: float, y: float, 
                 name: str, parent=None):
        # Ellipse: 18×18px centered at (x, y)
        # Fill: SPECIES_COLORS[species]
        # Label: first letter of name, white, bold, 9pt, centered
        # Hover: setAcceptHoverEvents(True) → emit signals
        
    def update_state(self, x: float, y: float, is_dead: bool):
        # If is_dead: gray fill (#30363d), red border, red letter
        # Update position
```

**Design decision for Phase 1:** All animals use `AnimalSprite`. The `AsciiLionSprite` for lions is a **separate, optional** sprite. The map rendering code checks `species == "lion"` and creates `AsciiLionSprite` instead of `AnimalSprite`. If the ASCII lion pixmap is not yet implemented, lions fall back to `AnimalSprite` with golden color.

### 5.4 `ui/lion_sprite.py` — `AsciiLionSprite`

```python
# Cache: only 2 renders ever (gold + dead-red)
_LION_CACHE: dict[str, QPixmap] = {}

def _render_lion_pixmap(color: str) -> QPixmap:
    """Render ASCII_LION text → QPixmap with SmoothTransformation."""
    if color in _LION_CACHE:
        return _LION_CACHE[color]
    # QImage(ARGB32, ~190×150 native)
    # QPainter + QFont("Courier New", 5pt)
    # Draw ASCII_LION lines
    # scaled(80, h, KeepAspectRatio, SmoothTransformation)
    # QPixmap.fromImage() → cache → return

class AsciiLionSprite(QGraphicsPixmapItem):
    """ASCII art lion on the map."""
    
    entity_hovered = pyqtSignal(str)
    entity_unhovered = pyqtSignal()
    
    def __init__(self, animal_id: str, x: float, y: float, name: str, parent=None):
        # Pixmap: _render_lion_pixmap("#e8a838") (golden)
        # setOffset(-w//2, -h//2) centered on pos
        # setAcceptHoverEvents(True)
        
    def update_state(self, x: float, y: float, is_dead: bool):
        # If state changes: re-render pixmap with appropriate color
        # Update position
```

**Fallback:** If ASCII rendering is too complex for Phase 1, `AsciiLionSprite` can delegate to `AnimalSprite` (create an internal `AnimalSprite` and forward signals/updates). This is documented as acceptable for the prototype.

### 5.5 `ui/visitor_sprite.py` — `VisitorSprite`

```python
class VisitorSprite(QGraphicsEllipseItem):
    """5×5px colored dot for visitors."""
    
    # No hover events (visitors are not interactive)
    # Color: random from 5 pastel colors (assigned at construction, stable per visitor)
    
    def __init__(self, visitor_id: str, x: float, y: float, parent=None):
        # Ellipse: 5×5 centered at (x, y)
        
    def update_state(self, x: float, y: float):
        # Update position only
```

### 5.6 `ui/enclosure_item.py` — `EnclosureItem`

```python
class EnclosureItem(QGraphicsRectItem):
    """Biome-colored rectangle with dashed border and label."""
    
    enclosure_clicked = pyqtSignal(str)   # enclosure_id
    
    def __init__(self, enclosure_id: str, name: str, biome: str, 
                 x: float, y: float, w: float, h: float, 
                 capacity: int, parent=None):
        # Rect at (x, y, w, h)
        # Fill: BIOME_COLORS[biome], semi-transparent
        # Border: dashed, C_BORDER color
        # Label: "Savanne · Lv.1" at bottom center, 9pt, dim
        # mousePressEvent → emit enclosure_clicked
        
    def update_state(self, current_count: int):
        # If current_count > capacity: red 3px solid border
        # Else: normal dashed border
```

### 5.7 `ui/zoo_scene.py` — `ZooScene`

```python
class ZooScene(QGraphicsScene):
    """800×600 map scene managing all entity sprites."""
    
    def __init__(self, parent=None):
        super().__init__(0, 0, MAP_W, MAP_H, parent)
        self.setBackgroundBrush(QColor(C_BG_DEEP))
        
        # Entity dictionaries (id → QGraphicsItem)
        self._animals: dict[str, AnimalSprite | AsciiLionSprite] = {}
        self._visitors: dict[str, VisitorSprite] = {}
        self._enclosures: dict[str, EnclosureItem] = {}
        
        # Lighting overlay
        self._lighting_overlay = QGraphicsRectItem(0, 0, MAP_W, MAP_H)
        self._lighting_overlay.setZValue(Z_OVERLAY)
        self._lighting_overlay.setBrush(QColor(0, 0, 0, 0))
        self.addItem(self._lighting_overlay)
        
        # Create enclosures from ENCLOSURE_DEFS
        self._create_enclosures()
        
    def _create_enclosures(self):
        """Create EnclosureItem for each hardcoded enclosure definition."""
        for edef in ENCLOSURE_DEFS:
            item = EnclosureItem(edef["id"], edef["name"], edef["biome"],
                                 edef["x"], edef["y"], edef["w"], edef["h"],
                                 edef["capacity"])
            self.addItem(item)
            self._enclosures[edef["id"]] = item
            
    def apply_lighting(self, zoo_open: bool):
        """Phase 1: simple day/night. Phase 2: expand to 4 phases."""
        if zoo_open:
            self._lighting_overlay.setBrush(QColor(*LIGHTING_DAY))
        else:
            self._lighting_overlay.setBrush(QColor(*LIGHTING_NIGHT))
            
    def update_entities(self, game_state: dict):
        """Full sprite batching: create/update/remove all entity sprites."""
        # 1. Update animals (create, move, mark dead, remove gone)
        # 2. Update visitors (create, move, remove gone)
        # 3. Update enclosure counts (count animals per enclosure_id)
        # See §5.12 for detailed algorithm
        
    def clear_all(self):
        """Remove all dynamic entities (animals + visitors). Enclosures persist."""
```

### 5.8 `ui/zoo_view.py` — `ZooGraphicsView`

```python
class ZooGraphicsView(QGraphicsView):
    """Zoomable, pannable map view."""
    
    entity_hovered = pyqtSignal(str)
    entity_unhovered = pyqtSignal()
    map_clicked = pyqtSignal(float, float)
    
    def __init__(self, scene: ZooScene, parent=None):
        super().__init__(scene, parent)
        self.setRenderHint(QPainter.Antialiasing)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        # Fixed size: 800×600 + small padding
        self.setFixedSize(MAP_W + 2, MAP_H + 2)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
    def wheelEvent(self, event):
        """Zoom ±15% per wheel step."""
        # Clamp zoom between 0.3x and 3.0x
        
    def mousePressEvent(self, event):
        """Detect click on enclosure → emit map_clicked."""
        # Phase 1: check itemAt for EnclosureItem → emit enclosure_selected
        # Phase 3: check AnimalSprite → start drag
```

### 5.9 `ui/chat_view.py` — `ChatlogWidget`

```python
class ChatlogWidget(QWidget):
    """Read-only message feed with color-coded entries."""
    
    def __init__(self, parent=None):
        # QVBoxLayout
        # QLabel "📋 Nachrichten" header
        # QTextEdit: readOnly, max 500 lines, 200px min height
        # No border styling (clean embed)
        
    def append_messages(self, messages: list[dict]):
        """Append HTML-formatted messages with timestamps and color coding."""
        # Format: '<span style="color:{CHAT_COLORS[type]}">[{time}] {text}</span><br>'
        # Auto-scroll to bottom via ensureCursorVisible()
        # Trim to last 500 entries if exceeded
        
    def clear(self):
        """Clear all messages."""
```

### 5.10 `ui/entity_info_panel.py` — `EntityInfoPanel`

```python
class EntityInfoPanel(QGroupBox):
    """Detail view when hovering/clicking an animal."""
    
    def __init__(self, parent=None):
        super().__init__("🔍 Tier-Info", parent)
        # QFormLayout with 6 rows:
        # 1. Name · Spezies: "Simba · Löwe"
        # 2. Alter · Stadium: "14 Tage · Erwachsen" (stage always "Erwachsen" in Phase 1)
        # 3. HP: QProgressBar 0–100, green→yellow→red color
        # 4. Hunger: QProgressBar 0–100, 0=satt(green) → 100=verhungernd(red)
    #    Note: Backend semantics: hunger=0 means full/satiated, hunger=100 means starvation.
    #    The bar should fill from 0 (green, good) to 100 (red, bad).
        # 5. Wohlbefinden: QProgressBar 0–100, red→yellow→green
        # 6. Effekte: QLabel, comma-separated status effects
        # Optional for lions: ASCII_LION_SMALL in a small QLabel
        # Default state: "Kein Tier ausgewählt" placeholder text
        
    def show_entity(self, data: dict | None):
        """Update panel with hover data or clear to placeholder."""
        # data = None → show placeholder "Kein Tier ausgewählt"
        # data = {} → show placeholder (backend returned empty = unknown ID)
        # data with fields → populate all rows
```

### 5.11 `ui/action_panel.py` — `ActionPanel`

```python
class ActionPanel(QWidget):
    """God-mode action buttons."""
    
    # Signals
    action_triggered = pyqtSignal(str, dict)  # action_name, kwargs
    
    def __init__(self, parent=None):
        # QVBoxLayout
        # QLabel "🎮 Aktionen" header
        # 6 QPushButtons (via styled_button):
        #   1. "Alle Tiere füttern" → feed_all (enabled when any food > 0)
        #   2. "Ausgewähltes füttern" → feed_one (enabled when animal selected + species food > 0)
        #   3. "Tier heilen" → heal (enabled when animal selected AND animal is not dead)
        #   4. "Gehege reinigen" → clean (enabled when enclosure selected)
        #   5. "Leichen entsorgen" → start_cremation (enabled when dead animals exist — Phase 1: always enabled)
        #   6. "Ticket anpassen" → set_ticket_price (always enabled)
        # Phase 1: 6 buttons. Phase 2: adds "Tier umbenennen"
        
    def update_state(self, game_state: dict, selected_animal_id: str | None, 
                     selected_enclosure_id: str | None):
        """Enable/disable buttons based on inventory, selection, and animal state."""
        # Food buttons: check species food type availability
        # Heal button: animal selected + animal not dead (Phase 1: no medicine check)
        # Clean button: enclosure selected
        # Cremation: check for any animal with is_dead=True
```

### 5.12 `ui/shop_panel.py` — `ShopPanel`

```python
class ShopPanel(QWidget):
    """Purchase food, animals, and adjust ticket price."""
    
    # Signals
    buy_food = pyqtSignal(str, int)        # food_type, amount
    buy_animal = pyqtSignal(str)           # species
    set_ticket_price = pyqtSignal(int)     # price in €
    
    def __init__(self, parent=None):
        # QVBoxLayout with 3 sections:
        #
        # Section 1: 🍖 Futter kaufen
        #   QComboBox: "Fleisch (MEAT) · 50€", "Pflanzen (PLANTS) · 30€", "Fisch (FISH) · 40€"
        #   QSpinBox: 1–100
        #   QLabel: "Gesamt: {price * amount}€" (live update on change)
        #   QPushButton: "Kaufen"
        #   QLabel: "Im Lager: MEAT: 15 | PLANTS: 0 | FISH: 3" (live inventory display)
        #
        # Section 2: 🦁 Tiere kaufen
        #   QComboBox: "Löwe · 8.000€", "Giraffe · 5.000€", "Pinguin · 3.000€"
        #   QLabel: Live price display
        #   QPushButton: "Kaufen"
        #   (No "Baby" checkbox in Phase 1 — that's Phase 3)
        #
        # Section 3: 🎫 Ticketpreis
        #   QSlider: 1–100, horizontal
        #   QLabel: "Aktuell: {value}€"
        #   QPushButton: "Übernehmen"
        
    def update_state(self, game_state: dict):
        """Update inventory display labels and enable/disable buy buttons based on budget."""
```

### 5.13 `core/frontend_controller.py` — `FrontendController`

```python
class FrontendController:
    """Thin bridge between the UI and the SimulationEngine.
    
    Responsibilities:
    - Receives a SimulationEngine reference (dependency injection)
    - Translates UI signals into engine method calls
    - Returns typed data back to the UI layer
    - Handles any marshalling between backend and frontend data formats
    """
    
    def __init__(self, engine: SimulationEngine):
        self._engine = engine
    
    def advance_tick(self) -> None:
        """Advance one simulation step.
        
        Calls engine.tick() if engine exists and is not paused.
        If engine has its own internal timer (engine.start()), this becomes a no-op.
        """
        # This is a bridge method — the frontend does NOT directly call engine.tick().
        # In Phase 1: calls engine.tick() if engine is not None and engine is not paused.
        # In later phases: may become a no-op if backend runs its own timer thread.
        
    def get_state(self) -> dict:
        """Get full game state snapshot. Returns empty dict if engine is None."""
        if self._engine is None:
            return {}
        return self._engine.get_game_state()
        
    def get_entity_info(self, entity_id: str) -> dict | None:
        """Get hover data for an entity. Returns None if engine is None."""
        if self._engine is None:
            return None
        return self._engine.get_entity_info(entity_id)
        
    def get_chat_messages(self) -> list[dict]:
        """Get and drain chat messages."""
        if self._engine is None:
            return []
        return self._engine.get_chat_messages()
        
    def execute_action(self, action: str, **kwargs) -> dict:
        """Execute a God-mode action. Returns ActionResult dict."""
        if self._engine is None:
            return {"success": False, "message": "Engine not connected", "chat_entries": []}
        return self._engine.execute_action(action, **kwargs)
```

### 5.14 `core/main_window.py` — `ZooMainWindow`

This is the largest file. It orchestrates all UI components.

```python
class ZooMainWindow(QMainWindow):
    """Top-level window: layout, signal routing, tick loop."""
    
    def __init__(self, controller: FrontendController):
        super().__init__()
        self._controller = controller
        self._selected_animal_id: str | None = None
        self._selected_enclosure_id: str | None = None
        
        self.setWindowTitle(WINDOW_TITLE)
        self.setFixedSize(WINDOW_W, WINDOW_H)
        
        self._build_ui()
        self._connect_signals()
        
        # Tick timer
        self._timer = QTimer()
        self._timer.timeout.connect(self._tick)
        self._timer.start(TICK_MS)
        
    def _build_ui(self):
        """Construct the full window layout."""
        # 1. QMenuBar: Datei → (Speichern/Laden/Beenden — Phase 1: only Beenden works)
        # 2. QToolBar with:
        #    - QLabel "Tag: 1" (tick_count based)
        #    - [Pause] button (toggle)
        #    - QLabel "Speed: 1×"
        #    - QLabel "Öffnen/Geschlossen" (zoo_open based)
        #    - Separator
        #    - QLabel "💰 {money}€"
        #    - QLabel "⭐ {reputation}"
        #    - QLabel "😊 {happiness}"
        # 3. QStatusBar: "Bereit | Tiere: {n} | Besucher: {m} | Gehege: {e}"
        #
        # 4. Central QWidget with QGridLayout:
        #    [0,0] ZooGraphicsView (rowspan=4, stretch=3)
        #    [0,1] QTabWidget (380-420px wide):
        #          Tab "Aktionen" → ActionPanel
        #          Tab "Shop" → ShopPanel
        #          (Phase 2 adds Tab "Upgrades" → UpgradePanel)
        #    [1,1] EntityInfoPanel
        #    [2,1] ChatlogWidget
        #    [3,1] EventBanner (hidden in Phase 1)
        
    def _connect_signals(self):
        """Wire all panel signals to the central dispatch."""
        # Scene signals:
        #   animal_sprite.entity_hovered → self._on_hover(id)
        #   animal_sprite.entity_unhovered → self._on_unhover()
        #   enclosure_item.enclosure_clicked → self._on_enclosure_selected(id)
        #   zoo_view.map_clicked → self._on_map_clicked(x, y) → deselect
        #
        # Panel signals:
        #   action_panel.action_triggered → self._dispatch(action, kwargs)
        #   shop_panel.buy_food → self._dispatch("buy_food", type=type, amount=amount)
        #   shop_panel.buy_animal → self._dispatch("buy_animal", species=species)
        #   shop_panel.set_ticket_price → self._dispatch("set_ticket_price", price=price)
        
    def _tick(self):
        """Main loop: advance simulation → poll state → render.
        
        Phase 1 architecture decision: The SimulationEngine provides both
        engine.start() (internal timer thread) AND engine.tick() (manual step).
        For the prototype, the frontend takes the SIMPLEST approach:
        
        1. Each QTimer tick: call controller.advance_tick() which internally
           calls engine.tick() if the engine exists and is not paused.
        2. Then poll state via controller.get_state().
        3. Render sprites, labels, panels.
        4. Drain chat messages.
        
        If the backend team wires engine.start() with its own internal timer,
        the FrontendController.advance_tick() becomes a no-op and the frontend
        purely polls. Both modes are supported via the controller abstraction.
        """
        # 1. controller.advance_tick()  — calls engine.tick() if engine exists
        # 2. state = controller.get_state()
        # 3. self._update_sprites(state)
        # 4. self._update_labels(state)
        # 5. self._update_panels(state)
        # 6. msgs = controller.get_chat_messages()
        #    if msgs: self.chatlog.append_messages(msgs)
        
    def _update_sprites(self, state: dict):
        """Batch-update all map sprites via scene.update_entities(state)."""
        self._scene.update_entities(state)
        # Also apply lighting
        self._scene.apply_lighting(state.get("system", {}).get("zoo_open", True))
        
    def _update_labels(self, state: dict):
        """Update toolbar and statusbar text."""
        system = state.get("system", {})
        finances = state.get("finances", {})
        animals = state.get("animals_on_map", [])
        visitors = state.get("visitors_on_map", [])
        
        # Toolbar labels: day, budget, rep, happiness
        # Statusbar: animal count, visitor count, enclosure count
        
    def _update_panels(self, state: dict):
        """Update all right-column panels."""
        self._action_panel.update_state(state, self._selected_animal_id, 
                                         self._selected_enclosure_id)
        self._shop_panel.update_state(state)
        # EntityInfoPanel updates only on hover (via _on_hover)
        
    def _on_hover(self, entity_id: str):
        """Handle hover on an animal sprite."""
        data = self._controller.get_entity_info(entity_id)
        self._entity_info_panel.show_entity(data)
        self._selected_animal_id = entity_id
        
    def _on_unhover(self):
        """Clear entity info panel."""
        self._entity_info_panel.show_entity(None)
        self._selected_animal_id = None
        
    def _on_enclosure_selected(self, enclosure_id: str):
        """Handle click on an enclosure."""
        self._selected_enclosure_id = enclosure_id
        # Update action panel to enable clean button
        
    def _on_map_clicked(self, x: float, y: float):
        """Handle click on empty map space → deselect all."""
        self._selected_animal_id = None
        self._selected_enclosure_id = None
        self._entity_info_panel.show_entity(None)
        
    def _dispatch(self, action: str, **kwargs):
        """Route UI actions to the backend."""
        result = self._controller.execute_action(action, **kwargs)
        # Display result message in statusbar
        # If result has chat_entries, append to chatlog
        if result.get("chat_entries"):
            self._chatlog.append_messages(result["chat_entries"])
```

### 5.15 `main.py` — Entry Point

```python
"""
vivizoo — Frontend entry point.

Usage:
    python -m frontend.main              # Run with default engine
    python -m frontend.main --demo       # Run with pre-seeded demo zoo
"""

import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

def _get_qss() -> str:
    """Return the full QSS Dark Theme stylesheet (~100 lines).
    
    Covers: QMainWindow, QToolBar, QStatusBar, QPushButton, 
    QComboBox, QSpinBox, QSlider, QProgressBar, QGroupBox, 
    QTabWidget/QTabBar, QTextEdit, QScrollBar, QMenuBar/QMenu, 
    QCheckBox, QLabel.
    
    All colors reference the C_* constants from core/constants.py.
    """

def launch_frontend(engine=None):
    """Create QApplication, apply QSS, show ZooMainWindow, exec loop."""
    app = QApplication(sys.argv)
    app.setStyleSheet(_get_qss())
    
    # Create engine if not provided (for standalone testing without backend)
    # In production: backend creates engine, frontend receives it via dependency injection
    controller = FrontendController(engine)
    
    window = ZooMainWindow(controller)
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    launch_frontend()
```

---

## 6. QSS Dark Theme (Full Specification)

This goes in `main.py::_get_qss()`. The exact QSS string (~100 lines) follows the `FRONTEND_ARCHITECTURE.md` §9 spec. Key rules:

- `QMainWindow` background: `C_BG_DEEP`
- `QToolBar` background: `C_BG_PANEL`, border-bottom: `1px solid C_BORDER`
- `QStatusBar` background: `C_BG_PANEL`, color: `C_TEXT_DIM`
- `QPushButton`: background `C_BG_CARD`, border `1px solid C_BORDER`, color `C_TEXT`, border-radius `4px`, padding `6px 12px`
- `QPushButton:hover`: background `C_BORDER`
- `QPushButton:pressed`: background `C_ACCENT2`
- `QPushButton:disabled`: opacity 0.5
- `QPushButton[accent="true"]`: background `C_ACCENT`, color white
- `QPushButton[danger="true"]`: background `C_RED`, color white
- `QComboBox`, `QSpinBox`: background `C_BG_CARD`, border `1px solid C_BORDER`, color `C_TEXT`, border-radius `3px`, padding `4px`
- `QSlider::groove:horizontal`: background `C_BORDER`, height `4px`, border-radius `2px`
- `QSlider::handle:horizontal`: background `C_ACCENT`, width `12px`, border-radius `6px`
- `QProgressBar`: background `C_BG_CARD`, border `1px solid C_BORDER`, border-radius `3px`, text-align center
- `QProgressBar::chunk`: background `C_ACCENT`, border-radius `2px`
- `QGroupBox`: border `1px solid C_BORDER`, border-radius `6px`, margin-top `12px`, padding `12px`
- `QGroupBox::title`: color `C_TEXT`, subcontrol-position top left, padding `0 6px`
- `QTabWidget::pane`: border `1px solid C_BORDER`, background `C_BG_PANEL`
- `QTabBar::tab`: background `C_BG_CARD`, padding `8px 16px`, border `1px solid C_BORDER`
- `QTabBar::tab:selected`: background `C_BG_PANEL`, border-bottom `2px solid C_ACCENT`
- `QTextEdit`: background `C_BG_CARD`, color `C_TEXT`, border `1px solid C_BORDER`, border-radius `4px`
- `QScrollBar`: thin, dark, minimal
- `QMenu`: background `C_BG_PANEL`, border `1px solid C_BORDER`
- `QMenu::item:selected`: background `C_ACCENT`

---

## 7. Backend Dependency Requests

These are things the **backend team must add** for the frontend to work correctly. These are **not** bugs — they are missing data fields.

| # | Request | Priority | Backend change needed |
|---|---------|----------|----------------------|
| R1 | Add `enclosure_id` to each animal in `animals_on_map[]` | 🔴 Critical | `get_game_state()` must include `"enclosure_id": str` in each animal dict. Without this, the frontend cannot determine which enclosure an animal belongs to. Fallback: point-in-rect test (see §2.5) |
| R2 | Add `name` field to `animals_on_map[]` | 🔴 Critical | `"name": str` needed for sprite labels. Already in `animal_hover_data`. Must also be in `animals_on_map`. |
| R3 | Confirm `time_of_day` field always present | 🟡 Important | Phase 1 stubs it as "DAY", but field must exist in dict to avoid KeyError |
| R4 | Confirm `zoo_happiness` field always present | 🟡 Important | Phase 1 stubs it as 100, but field must exist |

---

## 8. Testing Strategy (Test Descriptions, Not Implemented)

Per the project requirements, each function must have at least 2 test descriptions (not implemented tests, just documented).

### 8.1 `core/constants.py`
- **Test: All color constants are valid hex strings** — Verify each `C_*` constant matches pattern `#[0-9a-fA-F]{6}`.
- **Test: ENCLOSURE_DEFS covers the map** — Verify all enclosure rectangles are within (0, 0, MAP_W, MAP_H) bounds.
- **Test: SPECIES_COLORS and SPECIES_FOOD have matching keys** — Verify both dicts contain exactly `{"lion", "giraffe", "penguin"}`.

### 8.2 `ui/animal_sprite.py`
- **Test: Sprite created at correct position** — Create AnimalSprite at (100, 200). Verify `sceneBoundingRect().center() ≈ (100, 200)`.
- **Test: Dead state changes color** — Call `update_state(x, y, is_dead=True)`. Verify brush color is gray and border is red.
- **Test: Hover emits correct signal** — Simulate hoverEnterEvent. Verify `entity_hovered` signal emitted with correct animal_id.

### 8.3 `ui/lion_sprite.py`
- **Test: Pixmap cache returns same object for same color** — Call `_render_lion_pixmap("#e8a838")` twice. Verify same QPixmap object returned.
- **Test: Dead lion renders in red** — Call `update_state(x, y, is_dead=True)`. Verify pixmap color changes.

### 8.4 `ui/zoo_scene.py`
- **Test: Enclosures created from ENCLOSURE_DEFS** — Create ZooScene. Verify `len(scene._enclosures) == len(ENCLOSURE_DEFS)`.
- **Test: Lighting overlay exists at correct z-order** — Verify `_lighting_overlay.zValue() == Z_OVERLAY`.
- **Test: update_entities creates new animal sprites** — Pass game_state with 1 animal. Verify scene now has 1 animal sprite.
- **Test: update_entities removes dead animals** — Pass game_state with animal removed. Verify sprite removed from scene.
- **Test: apply_lighting sets dark overlay when closed** — Call `apply_lighting(False)`. Verify overlay brush opacity > 0.

### 8.5 `ui/entity_info_panel.py`
- **Test: Clear shows placeholder** — Call `show_entity(None)`. Verify placeholder text displayed.
- **Test: Valid data populates all fields** — Call `show_entity({name: "Simba", species: "Lion", hp: 85, ...})`. Verify all labels/progress bars updated.
- **Test: Empty dict shows placeholder** — Call `show_entity({})`. Verify placeholder text (unknown ID).

### 8.6 `ui/action_panel.py`
- **Test: Feed all disabled when inventory empty** — Call `update_state(state with zero inventory, None, None)`. Verify feed_all button disabled.
- **Test: Heal enabled when animal selected** — Call `update_state(state, "a_01", None)` with animal not dead. Verify heal button enabled.
- **Test: Heal disabled when animal is dead** — Pass state where selected animal has `is_dead=True`. Verify heal button disabled.

### 8.7 `ui/shop_panel.py`
- **Test: Food price updates on type change** — Select "MEAT" (50€), amount=5. Verify price label shows "250€".
- **Test: Animal buy disabled when insufficient budget** — Set budget to 100€. Verify animal purchase button disabled for all species.
- **Test: Ticket slider range is 1-100** — Verify slider minimum=1, maximum=100.

### 8.8 `ui/chat_view.py`
- **Test: Messages formatted with correct colors** — Append message with type="WARNING". Verify HTML contains C_GOLD color.
- **Test: Message cap at 500** — Append 600 messages. Verify only last 500 remain.

### 8.9 `core/frontend_controller.py`
- **Test: Returns empty dict when engine is None** — Create controller with engine=None. Verify `get_state()` returns `{}`.
- **Test: Delegates to engine correctly** — Mock engine with known state. Verify `get_state()` returns mock data.

### 8.10 `core/main_window.py`
- **Test: Tick loop polls state** — Mock controller. Trigger `_tick()`. Verify `controller.get_state()` was called.
- **Test: Hover updates entity info panel** — Trigger `_on_hover("a_01")`. Verify `controller.get_entity_info()` called and panel updated.
- **Test: Dispatch routes to controller** — Trigger `_dispatch("feed_all")`. Verify `controller.execute_action("feed_all")` called.
- **Test: Map click deselects** — Select animal, trigger `_on_map_clicked()`. Verify selection cleared and info panel shows placeholder.

---

## 9. Implementation Checklist (Sequential)

### Stage A: Foundation
- [ ] A1: Create `core/constants.py` with all constants (§5.1)
- [ ] A2: Create `ui/styled_widgets.py` with `styled_button()` and `styled_label()` (§5.2)
- [ ] A3: Create `assets/__init__.py`
- [ ] A4: Create `assets/ascii_lion.py` with full 40-line ASCII art
- [ ] A5: Create `assets/ascii_lion_small.py` with 25-line compact ASCII art

### Stage B: Map Sprites
- [ ] B1: Create `ui/animal_sprite.py` (§5.3)
- [ ] B2: Create `ui/lion_sprite.py` (§5.4)
- [ ] B3: Create `ui/visitor_sprite.py` (§5.5)
- [ ] B4: Create `ui/enclosure_item.py` (§5.6)

### Stage C: Map Container
- [ ] C1: Create `ui/zoo_scene.py` (§5.7)
- [ ] C2: Create `ui/zoo_view.py` (§5.8)

### Stage D: Panels
- [ ] D1: Create `ui/chat_view.py` (§5.9)
- [ ] D2: Create `ui/entity_info_panel.py` (§5.10)
- [ ] D3: Create `ui/action_panel.py` (§5.11)
- [ ] D4: Create `ui/shop_panel.py` (§5.12)
- [ ] D5: Create `ui/event_banner.py` (stub: always hidden) (§5)

### Stage E: Top-Level Wiring
- [ ] E1: Create `core/frontend_controller.py` (§5.13)
- [ ] E2: Create `core/main_window.py` (§5.14)
- [ ] E3: Create `main.py` with QSS theme and `launch_frontend()` (§5.15)

### Final Verification
- [ ] F1: Verify no file imports from `backend/` or `db/` (except `core/frontend_controller.py` which imports `SimulationEngine` by contract)
- [ ] F2: Verify all Phase 2/3 features are NOT implemented (UpgradePanel, DecoSprite, drag & drop, staff panel, save/load)
- [ ] F3: Verify all test descriptions are documented in relevant files as docstrings
- [ ] F4: Run `python -m frontend.main` — window must appear without import errors
- [ ] F5: Verify QSS theme applies correctly (dark background, green accent elements)

### Grading Artifacts (ABZUGRELEVANT wenn nicht vorhanden!)
- [ ] G1: Mermaid class diagram exists in `frontend/docs/frontend_class_diagram.md`
- [ ] G2: Sequenzdiagramme (optional, bonus) — mindestens 2: Feed-Action und Hover-Info
- [ ] G3: `frontend/docs/KI_REFLEXION.md` ausgefüllt (nicht leer!)
- [ ] G4: JEDE Klasse und JEDE öffentliche Methode hat vollständigen Docstring mit `Tests:` Block
- [ ] G5: `frontend/README.md` nennt Modulverantwortlichen (Erik)
- [ ] G6: `frontend/requirements.txt` ist aktuell
- [ ] G7: Python 3.14 Kompatibilität getestet

---

## 10. Anti-Implementation Checklist (What NOT to build in Phase 1)

- ❌ `UpgradePanel` (Phase 3) — Not created
- ❌ `DecoSprite` (Phase 3) — Not created
- ❌ `SaveLoadDialog` (Phase 3) — Not created
- ❌ `StaffPanel` (Phase 2) — Not created
- ❌ Drag & drop mechanics (Phase 3) — Not in ZooGraphicsView
- ❌ 4-phase lighting (Phase 2) — Only simple day/night toggle
- ❌ `styled_card()` (Phase 3) — Only `styled_button()` and `styled_label()` in Phase 1
- ❌ Baby animal checkbox (Phase 3) — Not in ShopPanel
- ❌ Medicine in shop (Phase 2) — Not in ShopPanel
- ❌ Animal `stage` field reading (Phase 2) — Always hardcoded "Erwachsen"
- ❌ 5 food types (Phase 2+) — Only 3: MEAT, PLANTS, FISH
- ❌ `get_stats()` chart widget (Phase 2) — Not implemented
- ❌ Event calendar dialog (Phase 2) — Not implemented

---

*End of Implementation Plan. When in doubt, re-read §2 Conflict Resolutions.*