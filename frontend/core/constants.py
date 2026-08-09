"""
Global constants for the vivizoo frontend.

All colors, dimensions, z-order values, species mappings, enclosure
definitions, and configuration values used across the entire UI layer.

Every value that mirrors a backend fact (prices, tick pacing, day phases)
is documented with its backend source so the two stay verifiable. The
frontend never imports ``backend.*`` here — the values are mirrored
deliberately to keep the layers decoupled.

Tests:
    - test_colors_valid_hex: Verify each C_* constant matches pattern
      #[0-9a-fA-F]{6}.
    - test_enclosure_defs_within_map: Verify all enclosure rectangles are
      within (0, 0, MAP_W, MAP_H) bounds.
    - test_species_mappings_match: Verify SPECIES_COLORS, SPECIES_FOOD,
      SPECIES_LABELS and ANIMAL_PRICES all contain exactly
      {"lion", "giraffe", "penguin"} keys.
    - test_prices_match_backend: Verify FOOD_PRICES equals
      backend.core.inventory.Inventory.FOOD_PRICES and ANIMAL_PRICES
      equals each species class's BUY_PRICE.

Module owner: Erik (frontend).
"""

# ── Map & Timing ──────────────────────────────────────────────────────────

MAP_W, MAP_H = 800, 600  # Map dimensions in pixels
TICK_MS = 100  # 100ms polling = 10 FPS render rate

# Mirrors backend.core.engine.TICKS_PER_DAY. Used to derive the day number
# and in-day clock from the backend's raw tick_count.
TICKS_PER_DAY = 480

# Speed multipliers cycled by the toolbar button. The frontend drives the
# engine manually via tick(), so the multiplier controls how many ticks are
# computed per 100 ms frame (0.5 => one tick every second frame).
SPEED_STEPS: tuple[float, ...] = (1.0, 2.0, 5.0, 0.5)


# ── Z-Order Layers (rendering stack) ──────────────────────────────────────
# Every layer listed here is drawn by a real item. Gaps in the numbering are
# intentional: they leave room for future layers (e.g. decorations between
# enclosures and animals) without renumbering the existing ones.

Z_ENCLOSURES = 1  # Enclosure background rectangles
Z_ANIMALS = 4  # Animal sprites (lions, giraffes, penguins)
Z_VISITORS = 5  # Visitor dots (particles sit one below at Z_VISITORS - 1)
Z_OVERLAY = 9  # Day/night lighting overlay — always on top


# ── Dark Forest Color Palette (gradient-enhanced) ─────────────────────────

C_BG_DEEP = "#0d1117"  # Map / main window background
C_BG_MID = "#111922"  # Intermediate depth (gradient mid)
C_BG_PANEL = "#161b22"  # Panel / tab background
C_BG_PANEL2 = "#1a2030"  # Panel gradient endpoint
C_BG_CARD = "#1c2333"  # Card / button background
C_BG_CARD2 = "#222d3d"  # Card gradient endpoint
C_ACCENT = "#3fb950"  # Green — primary action color
C_ACCENT2 = "#2ea043"  # Darker green — hover / pressed
C_ACCENT_GLOW = "#5cdb6e"  # Lighter green for glow effects
C_GOLD = "#d2991d"  # Gold — warnings, money
C_GOLD_GLOW = "#f0c040"  # Lighter gold for glow
C_RED = "#f85149"  # Red — danger, death
C_RED_GLOW = "#ff6b6b"  # Lighter red for glow
C_TEXT = "#e6edf3"  # Primary text
C_TEXT_DIM = "#8b949e"  # Dimmed / secondary text
C_BORDER = "#30363d"  # Borders, separators


# ── Shadow Configuration ───────────────────────────────────────────────────
# Used by main_window._drop_shadow() for the three right-column panels.

SHADOW_BLUR = 16  # Blur radius for panel drop shadows
SHADOW_OFFSET = (4, 4)  # (dx, dy) offset


# ── Species Mappings ──────────────────────────────────────────────────────

SPECIES_COLORS: dict[str, str] = {
    "giraffe": "#d4a44a",  # Warm sand
    "penguin": "#7986cb",  # Cool slate-blue
    "lion": "#e8a838",  # Golden (fallback colour; ASCII pixmap preferred)
}

# German display names for the lowercase species keys the backend sends.
SPECIES_LABELS: dict[str, str] = {
    "lion": "Löwe",
    "giraffe": "Giraffe",
    "penguin": "Pinguin",
}

# Mirrors each species class's PREFERRED_FOOD in backend.core.animal.
SPECIES_FOOD: dict[str, str] = {
    "lion": "MEAT",
    "giraffe": "PLANTS",
    "penguin": "FISH",
}

# Mirrors backend.core.inventory.Inventory.FOOD_PRICES (budget units/unit).
FOOD_PRICES: dict[str, float] = {
    "MEAT": 8.0,
    "PLANTS": 5.0,
    "FISH": 6.0,
    "MEDICINE": 25.0,
}

# Food types the shop offers. MEDICINE is stocked by the backend inventory
# but has no consumer in Phase 1 (heal() is God-mode and costs nothing), so
# it is displayed read-only instead of being sold — see IMPLEMENTATION_PLAN
# §2.1 and §5.4.
SHOP_FOOD_TYPES: tuple[str, ...] = ("MEAT", "PLANTS", "FISH")

# Every key backend.core.inventory.Inventory.to_dict() returns, in display
# order.
INVENTORY_KEYS: tuple[str, ...] = ("MEAT", "PLANTS", "FISH", "MEDICINE")

FOOD_LABELS: dict[str, str] = {
    "MEAT": "Fleisch",
    "PLANTS": "Pflanzen",
    "FISH": "Fisch",
    "MEDICINE": "Medikamente",
}

# Mirrors the BUY_PRICE class attribute of each species in
# backend.core.animal (Lion 900, Giraffe 700, Penguin 400).
ANIMAL_PRICES: dict[str, float] = {
    "lion": 900.0,
    "giraffe": 700.0,
    "penguin": 400.0,
}


# ── Enclosure Definitions (map geometry) ──────────────────────────────────
# The backend owns enclosure identity, capacity and cleanliness but sends no
# map geometry, so the rectangles live here. Ids and capacities match the
# enclosures created in frontend.main._create_demo_engine(); live values
# (name, biome, cleanliness, free_slots) are read back from the backend via
# engine.get_entity_info(enclosure_id) each frame.

ENCLOSURE_DEFS: list[dict] = [
    {
        "id": "e_01",
        "name": "Savanne 1",
        "biome": "savanna",
        "x": 30,
        "y": 30,
        "w": 340,
        "h": 250,
        "capacity": 5,
    },
    {
        "id": "e_02",
        "name": "Eiswelt 1",
        "biome": "ice",
        "x": 400,
        "y": 30,
        "w": 340,
        "h": 250,
        "capacity": 4,
    },
    {
        "id": "e_03",
        "name": "Aquarium 1",
        "biome": "water",
        "x": 30,
        "y": 310,
        "w": 340,
        "h": 250,
        "capacity": 3,
    },
]

BIOME_COLORS: dict[str, str] = {
    "savanna": "#3d2b1f",
    "ice": "#1b3b4d",
    "water": "#1b2d3b",
}

# Biome gradient endpoints (lighter variant for depth)
BIOME_COLORS_LIGHT: dict[str, str] = {
    "savanna": "#5a4030",
    "ice": "#2a5a6e",
    "water": "#2a4a5a",
}

BIOME_LABELS: dict[str, str] = {
    "savanna": "Savanne",
    "ice": "Eiswelt",
    "water": "Aquarium",
}

# Cleanliness (0-100) thresholds used to colour the enclosure border.
CLEAN_WARN = 60.0  # below this the border turns gold
CLEAN_CRITICAL = 30.0  # below this the border turns red


# ── Day/Night Lighting (4 phases) ─────────────────────────────────────────
# The backend sends system.time_of_day as one of the db.interface.enums
# TimeOfDay values. Each phase maps to an RGBA overlay tint drawn on top of
# the map.

PHASE_LIGHTING: dict[str, tuple[int, int, int, int]] = {
    "MORNING": (255, 190, 120, 28),  # warm low sun
    "NOON": (0, 0, 0, 0),  # full daylight, no tint
    "EVENING": (255, 120, 60, 45),  # orange dusk
    "NIGHT": (10, 20, 60, 130),  # deep blue night
}

PHASE_LABELS: dict[str, str] = {
    "MORNING": "Morgen",
    "NOON": "Mittag",
    "EVENING": "Abend",
    "NIGHT": "Nacht",
}

PHASE_ICONS: dict[str, str] = {
    "MORNING": "🌅",
    "NOON": "☀️",
    "EVENING": "🌇",
    "NIGHT": "🌙",
}

# Fallback tints when the zoo is closed outside the NIGHT phase.
LIGHTING_DAY = (0, 0, 0, 0)
LIGHTING_NIGHT = (10, 20, 60, 130)


# ── Chat Message Color Coding ─────────────────────────────────────────────
# The four severities backend.core.message_logger.LogEntry documents. A type
# outside this map falls back to C_TEXT in ChatlogWidget, so a new backend
# severity renders readably before anyone adds a colour for it.

CHAT_COLORS: dict[str, str] = {
    "INFO": "#8b949e",
    "WARNING": "#d2991d",
    "ERROR": "#f85149",
    "SUCCESS": "#3fb950",
}

# Severities the AlertBanner lifts out of the scrolling feed. Everything else
# is informational and stays in the chat log only.
ALERT_TYPES: tuple[str, ...] = ("WARNING", "ERROR")

# How many render frames an alert stays on screen (100 ms per frame => 6 s).
ALERT_FRAMES = 60

# Chat filter modes offered in the ChatlogWidget header, as
# (label, accepted types or None for "everything").
CHAT_FILTERS: tuple[tuple[str, tuple[str, ...] | None], ...] = (
    ("Alle", None),
    ("Nur Warnungen", ("WARNING", "ERROR")),
    ("Nur Erfolge", ("SUCCESS",)),
)


# ── Animal roster table ───────────────────────────────────────────────────
# Column headers of the AnimalListPanel. The panel exists because the backend
# places every animal on the same fixed coordinate, which makes individual
# sprites impossible to hit with the mouse — see docs/IMPLEMENTATION_PLAN.md §5.2.

ROSTER_COLUMNS: tuple[str, ...] = ("Name", "Art", "HP", "Hunger", "Wohl")

# Thresholds used to colour the roster cells and grade animal values.
VALUE_WARN = 50.0  # below this a 0-100 value is shown in gold
VALUE_CRITICAL = 25.0  # below this it is shown in red

# Colour alone is not an accessible signal — roughly one in twelve men cannot
# tell the red cells from the green ones. Every graded value therefore also
# carries a text marker.
VALUE_MARKERS: dict[str, str] = {"ok": "", "warn": "! ", "critical": "!! "}

# Roster view modes offered above the table.
ROSTER_FILTERS: tuple[str, ...] = ("Alle Tiere", "Braucht Aufmerksamkeit")

# The roster is rebuilt from get_entity_info() per animal, so refreshing it
# on every render frame would query the backend ten times a second for a
# table nobody reads that fast. A changed set of animals still refreshes
# immediately — only the value update is throttled.
ROSTER_REFRESH_FRAMES = 5


# ── Statistics trend chart ────────────────────────────────────────────────
# Which field of a get_stats() row the chart draws, as (label, key). All four
# come from the same day summary the backend persists; no value is derived.

TREND_METRICS: tuple[tuple[str, str], ...] = (
    ("Gewinn (€)", "profit_loss"),
    ("Besucher", "total_visitors"),
    ("Ø Wohlbefinden", "avg_animal_welfare"),
    ("Reputation", "reputation_end_of_day"),
)


# ── Window Configuration ──────────────────────────────────────────────────
# WINDOW_W/H is the size the window opens at; WINDOW_MIN_* is how small it
# may be dragged. The window is deliberately no longer fixed: on a display
# below 1400×900 — which includes most notebooks and every WSLg session on a
# 1080p monitor — a fixed window simply does not fit on screen.

WINDOW_MIN_W, WINDOW_MIN_H = 1000, 640

# Smallest useful size of the map view; below this the enclosures overlap
# their own labels. The view scrolls instead of shrinking further.
VIEW_MIN_W, VIEW_MIN_H = 420, 320


WINDOW_TITLE = "🦁 vivizoo — Zoo Digital Twin"
WINDOW_W, WINDOW_H = 1400, 900
