"""
Global constants for the vivizoo frontend.

All colors, dimensions, z-order values, species mappings, enclosure definitions,
and configuration values used across the entire UI layer.

Phase 1: Tier 1 visual upgrade — added gradient colors, shadow config, glow colors.

Tests:
    - test_colors_valid_hex: Verify each C_* constant matches pattern #[0-9a-fA-F]{6}.
    - test_enclosure_defs_within_map: Verify all enclosure rectangles are within
      (0, 0, MAP_W, MAP_H) bounds.
    - test_species_mappings_match: Verify SPECIES_COLORS, SPECIES_FOOD, FOOD_PRICES,
      and ANIMAL_PRICES all contain exactly {"lion", "giraffe", "penguin"} keys.
"""

# ── Map & Timing ──────────────────────────────────────────────────────────

MAP_W, MAP_H = 800, 600  # Map dimensions in pixels
TICK_MS = 100  # 100ms polling = 10 FPS render rate


# ── Z-Order Layers (rendering stack) ──────────────────────────────────────

Z_ENCLOSURES = 1  # Enclosure background rectangles
Z_DECORATIONS = 2  # Decoration emojis (unused in Phase 1)
Z_ANIMALS = 4  # Animal sprites (lions, giraffes, penguins)
Z_VISITORS = 5  # Visitor dots
Z_DRAG = 10  # Drag ghost (unused in Phase 1)
Z_OVERLAY = 9  # Day/night lighting overlay


# ── Dark Forest Color Palette (Tier 1 — gradient-enhanced) ─────────────────

C_BG_DEEP = "#0d1117"  # Map / main window background
C_BG_MID = "#111922"  # Intermediate depth (gradient mid)
C_BG_PANEL = "#161b22"  # Panel / tab background
C_BG_PANEL2 = "#1a2030"  # Panel gradient endpoint
C_BG_CARD = "#1c2333"  # Card / button background
C_BG_CARD2 = "#222d3d"  # Card gradient endpoint
C_ACCENT = "#3fb950"  # Green — primary action color
C_ACCENT2 = "#2ea043"  # Darker green — hover / pressed
C_ACCENT_GLOW = "#5cdb6e"  # Lighter green for glow effects
C_GOLD = "#d2991d"  # Gold — reputation, events
C_GOLD_GLOW = "#f0c040"  # Lighter gold for glow
C_RED = "#f85149"  # Red — danger, death
C_RED_GLOW = "#ff6b6b"  # Lighter red for glow
C_TEXT = "#e6edf3"  # Primary text
C_TEXT_DIM = "#8b949e"  # Dimmed / secondary text
C_BORDER = "#30363d"  # Borders, separators
C_SHADOW = (0, 0, 0, 80)  # Drop-shadow colour (rgba tuple for effects)


# ── Shadow Configuration ───────────────────────────────────────────────────

SHADOW_BLUR = 16  # Blur radius for panel drop shadows
SHADOW_OFFSET = (4, 4)  # (dx, dy) offset
GLOW_BLUR = 8  # Blur radius for button glow on hover
GLOW_OFFSET = (0, 0)  # Glow is centred


# ── Species Mappings ──────────────────────────────────────────────────────

SPECIES_COLORS: dict[str, str] = {
    "giraffe": "#d4a44a",  # Warm sand
    "penguin": "#7986cb",  # Cool slate-blue
    "lion": "#e8a838",  # Golden (fallback colour; ASCII pixmap preferred)
}

SPECIES_FOOD: dict[str, str] = {
    "lion": "MEAT",
    "giraffe": "PLANTS",
    "penguin": "FISH",
}

FOOD_PRICES: dict[str, int] = {
    "MEAT": 50,
    "PLANTS": 30,
    "FISH": 40,
}

ANIMAL_PRICES: dict[str, int] = {
    "lion": 8_000,
    "giraffe": 5_000,
    "penguin": 3_000,
}


# ── Hardcoded Enclosure Definitions (Phase 1 only) ────────────────────────
# Phase 2+ will read enclosure data from backend.get_game_state()["enclosures_on_map"].

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

# Tier 1: Biome gradient endpoints (lighter variant for depth)
BIOME_COLORS_LIGHT: dict[str, str] = {
    "savanna": "#5a4030",
    "ice": "#2a5a6e",
    "water": "#2a4a5a",
}


# ── Phase 1 Lighting (simple 2-state) ─────────────────────────────────────
# Phase 2 expands to full 4-phase day/night cycle.

LIGHTING_DAY = (0, 0, 0, 0)  # Fully transparent (zoo open)
LIGHTING_NIGHT = (0, 0, 0, 120)  # Semi-transparent black (zoo closed)


# ── Chat Message Color Coding ─────────────────────────────────────────────

CHAT_COLORS: dict[str, str] = {
    "INFO": "#8b949e",
    "WARNING": "#d2991d",
    "ERROR": "#f85149",
    "SUCCESS": "#3fb950",
    "EVENT": "#d2991d",
}


# ── Window Configuration ──────────────────────────────────────────────────

WINDOW_TITLE = "🦁 vivizoo — Zoo Digital Twin"
WINDOW_W, WINDOW_H = 1400, 900
