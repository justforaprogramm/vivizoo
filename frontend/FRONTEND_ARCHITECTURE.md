# 🎨 Zoo Digital Twin — Frontend-Architektur & Implementierungsdokumentation

> **Stand:** 6. August 2026 | **Datei:** `frontend/main_window.py` (+ `assets/`)  
> **Framework:** PyQt6 | **Map:** QGraphicsScene/QGraphicsView  
> **Layout:** Fixed 1400×900 Grid | **Theme:** Premium Dark Forest

---

## Inhaltsverzeichnis

1. [Architektur-Übersicht](#1-architektur-übersicht)
2. [Core vs. Extended — Systematische Klassifizierung](#2-core-vs-extended)
3. [Globale Konstanten & Theme](#3-globale-konstanten--theme)
4. [Styled Widgets (Utility-Funktionen)](#4-styled-widgets-utility-funktionen)
5. [Graphics Items — Map-Rendering-Schicht](#5-graphics-items--map-rendering-schicht)
6. [Scene & View — Map-Kontrolle](#6-scene--view--map-kontrolle)
7. [UI-Panels (Rechte Spalte)](#7-ui-panels-rechte-spalte)
8. [ZooMainWindow — Signal-Routing & Tick-Loop](#8-zoommainwindow--signal-routing--tick-loop)
9. [QSS Dark Theme](#9-qss-dark-theme)
10. [Datenfluss-Diagramm](#10-datenfluss-diagramm)
11. [Assets-Verzeichnis](#11-assets-verzeichnis)

---

## 1. Architektur-Übersicht

```
QApplication
└── ZooMainWindow (QMainWindow, 1400×900, fixed)
    ├── QMenuBar (Datei → Speichern/Laden/Event-Kalender/Beenden)
    ├── QToolBar (Tag, Pause, Speed, Öffnen/Schließen, Budget, Rep, Happiness)
    ├── QStatusBar (Bereit, Tiere, Besucher, Gehege)
    ├── Central QGridLayout
    │   ├── [0,0] ZooGraphicsView (QGraphicsView, 800×600 Map)
    │   │         └── ZooScene (QGraphicsScene)
    │   │              ├── EnclosureItem[] (Gehege-Rechtecke)
    │   │              ├── AsciiLionSprite[] (ASCII-Löwen-Pixmap)
    │   │              ├── AnimalSprite[] (Giraffe/Pinguin-Kreise)
    │   │              ├── VisitorSprite[] (Besucher-Punkte)
    │   │              ├── DecoSprite[] (Dekorations-Emojis)
    │   │              └── LightingOverlay (Tag/Nacht)
    │   ├── [0,1] QTabWidget (Aktionen | Shop | Upgrades)
    │   ├── [1,1] EntityInfoPanel (QGroupBox — Tier-Info)
    │   ├── [2,1] ChatlogWidget (QTextEdit — Nachrichten-Log)
    │   └── [3,1] EventBanner (QFrame — Event-Ankündigung)
    ├── QTimer(100ms) → _tick() → engine.tick() → get_game_state()
    └── launch_frontend() → app.setStyleSheet() → QSS-Theme
```

---

## 2. Core vs. Extended — Systematische Klassifizierung

### 🔴 CORE (MVP — unverzichtbar für lauffähigen Prototyp)

| Komponente | Typ | Begründung |
|---|---|---|
| **ZooMainWindow** | Klasse | Das Fenster selbst — ohne es keine UI |
| **ZooScene** | Klasse | Die 2D-Map — Kern des Spiels |
| **ZooGraphicsView** | Klasse | Zoom/Pan/Drag — Map-Interaktion |
| **AnimalSprite** | Klasse | Anzeige von Giraffe & Pinguin als farbige Kreise |
| **EnclosureItem** | Klasse | Gehege-Rechtecke mit Biome-Farbe & Level-Label |
| **VisitorSprite** | Klasse | Besucher als farbige 5px-Punkte |
| **ActionPanel** | Widget | "Alle füttern", "Ausgewähltes füttern", "Heilen", "Reinigen" |
| **ChatlogWidget** | Widget | Nachrichten-Feed (color-coded) |
| **EntityInfoPanel** (Basis) | Widget | Name, HP, Hunger, Wohlbefinden (ProgressBars) |
| **ShopPanel** (Food + Animals + Ticket) | Widget | Kern-Shop: Futter kaufen, Tiere kaufen, Ticketpreis |
| **ToolBar** (Budget, Pause, Speed) | Widget | Simulation-Steuerung |
| **StatusBar** (Tiere/Besucher/Gehege) | Widget | Status-Anzeige |
| **QTimer(100ms) Polling-Loop** | Mechanik | Treibt den Tick→Render→Poll-Zyklus |
| **`_dispatch()` (Action-Routing)** | Methode | Zentraler Hub: Button → engine.execute_action() |
| **`_update_sprites()`** | Methode | Sprite-Batching — erstellt/aktualisiert alle Map-Items |
| **`_update_labels()`** | Methode | Toolbar & StatusBar Labels aktualisieren |
| **Phase Lighting** `apply_lighting()` | Methode | Tag/Nacht-Farbüberlagerung auf der Map |
| **QSS Dark Theme** | Styling | Gesamtes visuelles Erscheinungsbild |

### 🟡 EXTENDED (Phase 2–3 — erweiterte Features)

| Komponente | Typ | Begründung |
|---|---|---|
| **AsciiLionSprite** | Klasse | ASCII-Löwe als gerenderter Pixmap-Charakter (Benutzerwunsch) |
| **`_render_lion_pixmap()`** | Funktion | Rendert ASCII-Art → QPixmap mit SmoothTransformation |
| **UpgradePanel** | Widget | 6 Gebäude-Upgrades + Gehege-Upgrade + 5 Dekorationen |
| **EntityInfoPanel** (ASCII-Art) | Widget | Löwen-Art im Info-Panel (species-spezifisch) |
| **ShopPanel** (Medikamente) | Widget | Medikamenten-Kauf für Heilung |
| **EventBanner** | Widget | Saisonale Event-Ankündigung (Lichterfest etc.) |
| **SaveLoadDialog** | QDialog | Speichern/Laden via JSON |
| **DecoSprite** | Klasse | Dekorations-Emojis (Brunnen, Bäume, Büsche etc.) |
| **Drag & Drop** (`ZooGraphicsView`) | Mechanik | Tiere zwischen Gehegen ziehen |
| **`_cycle_speed()`** | Methode | Geschwindigkeits-Zyklus (1×→2×→5×→0.5×) |
| **`_toggle_open()`** | Methode | Zoo manuell öffnen/schließen |
| **`_rename_animal()`** | Methode | Tier umbenennen via QInputDialog |
| **`_show_event_calendar()`** | Methode | Event-Kalender als QMessageBox |
| **`_load_game()`** | Methode | Spielstand laden |

### 🟢 SPÄTER HINZUGEFÜGT (Benutzer-Iterationen)

| Komponente | Grund |
|---|---|
| **Vektor-basierte Tierbewegung** (in `models/tier.py`) | Realistischere Bewegung: Richtung + Schrittanzahl + Abprallen |
| **`_LION_CACHE`** (Pixmap-Cache) | Performance: Löwen-Pixmap nur einmal pro Farbe rendern |
| **`styled_button/label/card`** | Utility-Funktionen für konsistentes Styling |

---

## 3. Globale Konstanten & Theme

```python
# Map-Dimensionen
MAP_W, MAP_H = 800, 600          # Karten-Größe in Pixeln
TICK_MS = 100                     # 100ms = 10 FPS Polling-Rate

# Z-Order (Rendering-Schichten)
Z_ENCLOSURES = 1                  # Gehege-Hintergrund
Z_DECORATIONS = 2                 # Dekorations-Emojis
Z_ANIMALS = 4                     # Tiere (Löwe, Giraffe, Pinguin)
Z_VISITORS = 5                    # Besucher-Punkte
Z_DRAG = 10                       # Drag-Ghost (beim Ziehen)
Z_OVERLAY = 9                     # Tag/Nacht-Beleuchtung

# Dark Forest Farbpalette (10 Farben)
C_BG_DEEP  = "#0d1117"            # Map-Hintergrund
C_BG_PANEL = "#161b22"            # Panel-Hintergrund
C_BG_CARD  = "#1c2333"            # Card-Hintergrund
C_ACCENT   = "#3fb950"            # Grün (Buttons, Fortschritt)
C_ACCENT2  = "#2ea043"            # Dunkleres Grün (Hover)
C_GOLD     = "#d2991d"            # Gold (Reputation, Events)
C_RED      = "#f85149"            # Rot (Tod, Gefahr)
C_TEXT     = "#e6edf3"            # Heller Text
C_TEXT_DIM = "#8b949e"            # Gedimmter Text
C_BORDER   = "#30363d"            # Rahmen-Farbe
```

**Begründung:** GitHub-Dark-Theme-inspiriert. Kein reines Schwarz — dunkle Blautöne mit Grün als Akzentfarbe für eine "Premium"-Ästhetik ohne Eye-Strain.

---

## 4. Styled Widgets — Utility-Funktionen

### `styled_button(text, accent, danger, small)` 🔴 CORE
**Zweck:** Konsistente Button-Styling-Factory. Vermeidet QSS-Duplizierung.
- **accent:** Grüner "Call-to-Action"-Button
- **danger:** Roter "Warnung"-Button  
- **default:** Neutraler Dark-Button mit Hover-Effekt
- **small:** Kompaktere Padding-Variante

### `styled_label(text, dim, large, bold, color, size)` 🔴 CORE
**Zweck:** Konsistente Label-Factory. Alle Labels transparent, kein Border.
- **dim:** Gedimmte Textfarbe (Beschreibungen)
- **large:** 18px Schrift (Überschriften)
- **bold:** Fettdruck

### `styled_card()` 🟡 EXTENDED
**Zweck:** QFrame mit `QGraphicsDropShadowEffect` (20px Blur, 4px Offset) für "Karten"-Look in Shop- und Upgrade-Panels.

---

## 5. Graphics Items — Map-Rendering-Schicht

### `AnimalSprite(QGraphicsEllipseItem)` 🔴 CORE
**Visuelle Repräsentation: Giraffe & Pinguin**

| Eigenschaft | Wert |
|---|---|
| Basis-Klasse | `QGraphicsEllipseItem(0, 0, 18, 18)` |
| Farbe | `SPECIES_COLORS[spezies]` (#d4a44a / #7986cb) |
| Label | Erster Buchstabe (G/P) — weiß, fett, 9pt |
| Position | `setPos(x-9, y-9)` — zentriert |
| Tod-Zustand | Grau (#30363d) + roter Rand + roter Buchstabe |
| Events | `hoverEnterEvent`/`hoverLeaveEvent` → `entity_hovered`/`entity_unhovered` Signal |

**Design-Entscheidung:** Kreis mit Buchstabe statt Pixel-Sprite. Minimaler Rendering-Aufwand, sofort erkennbar. Kein externes Asset-Management nötig.

---

### `AsciiLionSprite(QGraphicsPixmapItem)` 🟡🟢 EXTENDED + BENUTZER
**Visuelle Repräsentation: Löwe als vollständige ASCII-Kunst**

| Eigenschaft | Wert |
|---|---|
| Basis-Klasse | `QGraphicsPixmapItem` |
| Pixmap-Quelle | `_render_lion_pixmap("#e8a838")` — golden |
| Skalierung | ~80×40 Pixel (von ~190×150 native via SmoothTransformation) |
| Position | `setOffset(-w//2, -h//2)` — zentriert auf Tier-Koordinate |
| Tod-Zustand | Erneutes Rendern mit Farbe `C_RED` (#f85149) |
| Events | Identisch zu `AnimalSprite` |

**Rendering-Pipeline (`_render_lion_pixmap`):**
```
1. Lade ASCII_LION aus assets/ascii_lion.py
2. Rendere mit QPainter + QFont("Courier New", 5pt) auf QImage (ARGB32, transparent)
3. QImage.scaled(80, h, KeepAspectRatio, SmoothTransformation)
4. QPixmap.fromImage() → Cache in _LION_CACHE dict
```

**Design-Entscheidung:** Warum Pixmap statt Text-Item?
- **Text-Item (3pt):** Unleserlich, kein Anti-Aliasing bei Winz-Schriften
- **Pixmap (5pt→skaliert):** Lesbare native Schrift, dann bilineare Interpolation → saubere Kanten
- **Cache:** Nur 2 Render-Aufrufe (gold + rot), O(1) pro Farbe

---

### `VisitorSprite(QGraphicsEllipseItem)` 🔴 CORE
**Visuelle Repräsentation: Zoo-Besucher**

| Eigenschaft | Wert |
|---|---|
| Basis-Klasse | `QGraphicsEllipseItem(0, 0, 5, 5)` |
| Farbe | Zufällig aus 5 Pastell-Farben |
| Position | `setPos(x-2, y-2)` — zentriert |
| Kein Hover | Besucher sind nicht interaktiv |

---

### `DecoSprite(QGraphicsTextItem)` 🟡 EXTENDED
**Visuelle Repräsentation: Gekaufte Dekorationen**

| Slot | Emoji | Position |
|---|---|---|
| `brunnen_mitte` | ⛲ | (350, 220) |
| `baeume_eingang` | 🌳 | (250, 30) |
| `buesche_pfad` | 🌿 | (500, 30) |
| `blumenfeld_gehege` | 🌸 | (200, 230) |
| `laternen_pfad` | 🏮 | (350, 50) |

22pt Schrift, nur sichtbar wenn `zoo.decoration_slots[slot_id] == True`.

---

### `EnclosureItem(QGraphicsRectItem)` 🔴 CORE
**Visuelle Repräsentation: Gehege**

| Eigenschaft | Wert |
|---|---|
| Füllung | Halbtransparente Biome-Farbe (Savanne: braun, Eis: blau) |
| Rahmen | Gestrichelt, `C_BORDER`-Farbe |
| Label | "Savanne · Lv.1" — 9pt, gedimmt, zentriert unten |
| Überfüllung | Roter 3px-Rahmen wenn `current_count > max_capacity` |

---

## 6. Scene & View — Map-Kontrolle

### `ZooScene(QGraphicsScene)` 🔴 CORE
- **Größe:** 800×600 — `sceneRect(0,0,800,600)`
- **Hintergrund:** `C_BG_DEEP` (#0d1117)
- **Entity-Dictionaries:** `animals: Dict[str, QGraphicsItem]`, `visitors`, `enclosures`, `decorations`
- **Lighting Overlay:** `QGraphicsRectItem(0,0,800,600)` auf Z_OVERLAY — Tag/Nacht-Tönung
- **`apply_lighting(phase)`:** Setzt semi-transparente Füllung basierend auf `PHASE_LIGHTING`

### `ZooGraphicsView(QGraphicsView)` 🔴 CORE (+ 🟡 Drag & Drop)
- **Signale:** `entity_hovered(str)`, `entity_unhovered()`, `map_clicked(float,float)`, `drop_requested(str,float,float)`
- **Anti-Aliasing:** Aktiviert
- **Pan:** `ScrollHandDrag` (mittlere Maustaste)
- **Zoom:** `wheelEvent` — 15% pro Stufe
- **Drag & Drop:**
  - `mousePressEvent` → `itemAt(pos)` → `isinstance(AnimalSprite, AsciiLionSprite)` → `_start_drag()`
  - `mouseMoveEvent` → Ghost-Sprite folgt Maus
  - `mouseReleaseEvent` → `drop_requested.emit(tier_id, x, y)`
  - Ghost: `QGraphicsEllipseItem` mit 50% Opazität, Farbe vom Original-Sprite

---

## 7. UI-Panels (Rechte Spalte)

### `ActionPanel(QWidget)` 🔴 CORE
**7 Aktions-Buttons in vertikaler Liste:**

| Button | Aktion | Aktivierungs-Bedingung |
|---|---|---|
| "Alle Tiere füttern" | `feed_all` | Inventar hat mindestens 1 Food-Item |
| "Ausgewähltes füttern" | `feed_one` | Tier ausgewählt |
| "Ausgewähltes heilen" | `heal` | Tier ausgewählt + Medikamente > 0 |
| "Gehege reinigen" | `clean` | Gehege ausgewählt |
| "Einäschern starten" | `start_cremation` | Leichen vorhanden |
| "Urne beerdigen" | `bury_urn` | Urnen vorhanden |
| "Tier umbenennen" | `rename_animal` | Tier ausgewählt |

**`update_state(state, sel_a, sel_e)`:** Enabler/Disabler je nach Inventar/Selektion.

---

### `ShopPanel(QWidget)` 🔴 CORE (Food/Animals/Ticket) + 🟡 EXTENDED (Meds)
**4 Karten-Sektionen:**

**🍖 Futter kaufen** (Core)
- QComboBox: 5 Futtertypen mit Preis-Angabe
- QSpinBox: 1–100 Menge
- Live-Preisberechnung: `Preis/Stk × Menge`
- Inventar-Anzeige unter dem Kauf-Button

**🦁 Tiere kaufen** (Core)
- QComboBox: Löwe (8.000€) / Giraffe (5.000€) / Pinguin (3.000€)
- QCheckBox: "Baby (50% billiger)"
- Live-Preis: Passt sich bei Baby-Checkbox an

**💊 Medikamente** (Extended)
- QSpinBox: 1–50
- Preis: 300€/Stk

**🎫 Ticketpreis** (Core)
- QSlider: 1–100€
- Live-Label-Anzeige

---

### `UpgradePanel(QWidget)` 🟡 EXTENDED
**3 Sektionen:**

**Gebäude-Upgrades** (6 Karten)
- Landschaftsverschönerung (5000€), Beleuchtung (4000€), Futterlager (6000€), Krematorium (8000€), Friedhof (5000€), Restaurant (12000€)
- Jede Karte: Name, Beschreibung, Kosten, Status ("Gekauft"/"Nicht gekauft"), Kauf-Button

**Gehege-Upgrade** (1 Karte)
- QComboBox für Gehege-Auswahl
- Kosten: 10000€, Gated by Reputation ≥ 30

**Dekorationen** (5 Karten)
- Brunnen, Bäume, Büsche, Blumenfeld, Laternen
- Status "Gebaut"/"Nicht gebaut" + Bau-Button

---

### `EntityInfoPanel(QGroupBox)` 🔴 CORE (Statistiken) + 🟡 EXTENDED (ASCII-Art)
**Form-Layout mit 6 Zeilen:**

| Zeile | Widget | Beschreibung |
|---|---|---|
| Name · Spezies | QLabel | z.B. "Simba · Löwe" |
| Alter · Stadium | QLabel | z.B. "14 Tage · Erwachsen" |
| HP | QProgressBar | 0–100, grün→gelb→rot |
| Hunger | QProgressBar | Inverted, 100=voll |
| Wohlbefinden | QProgressBar | 0–100, rot→gelb→grün |
| Effekte | QLabel | z.B. "Hungernd Gestresst" |
| Biome | QLabel | Savanne / Eis / Aquarium |
| ASCII-Art (nur Löwe) | QLabel | `ASCII_LION_SMALL`, 6px Monospace, golden |

---

### `ChatlogWidget(QWidget)` 🔴 CORE
- `QTextEdit` readOnly, 500 Nachrichten Maximum, 200px Höhe
- `append_messages(msgs)`: HTML-formatierte Einträge mit timestamp + farbcodiertem Typ
- **Farben:** INFO=grau, WARNUNG=gelb, KRITISCH=rot, ERFOLG=grün, EVENT=gold
- Auto-Scroll zum Ende via `ensureCursorVisible()`

---

### `EventBanner(QFrame)` 🟡 EXTENDED
- Standardmäßig versteckt (`hide()`)
- Zeigt Event-Name + verbleibende Tage während saisonaler Events
- Style: `#1a2a0a` Hintergrund, goldener 2px Rahmen, abgerundet

---

### `SaveLoadDialog(QDialog)` 🟡 EXTENDED
- **Save-Modus:** Editierbare QComboBox mit Dateinamen-Vorschlägen
- **Load-Modus:** QListWidget aller `.json`-Dateien im Verzeichnis
- Speichert `engine.get_game_state()` via `DBManager.save_game()`

---

## 8. ZooMainWindow — Signal-Routing & Tick-Loop

### Aufbau (`_build_ui()`) 🔴 CORE
```
QGridLayout (4 Zeilen × 2 Spalten)
├── [0,0] ZooGraphicsView  (rowspan=4, stretch=3)
├── [0,1] QTabWidget       (380–420px breit)
├── [1,1] EntityInfoPanel
├── [2,1] ChatlogWidget
└── [3,1] EventBanner
```

### Signal-Verkabelung (`_connect_signals()`) 🔴 CORE
Alle Panel-Signale werden via Lambda an `self._dispatch(action, **kwargs)` geroutet:
```
ActionPanel.feed_all    → _dispatch("feed_all")
ShopPanel.buy_food      → _dispatch("buy_food", typ, menge)
UpgradePanel.buy_upgrade → _dispatch("buy_upgrade", upgrade_name)
...etc.
```

### Tick-Loop (`_tick()`) 🔴 CORE
```python
def _tick(self):
    if engine.running and not engine.paused:
        engine.tick()                    # 1. Berechne einen Simulationsschritt
    state = engine.get_game_state()      # 2. Hole vollständigen Snapshot
    self._update_sprites(state)          # 3. Aktualisiere alle Map-Sprites
    self._update_labels(state)           # 4. Aktualisiere Toolbar/StatusBar
    self._update_panels(state)           # 5. Aktualisiere ActionPanel/UpgradePanel
    self._update_event(state)            # 6. Event-Banner prüfen
    msgs = engine.get_chat_messages()    # 7. Hole neue Chat-Nachrichten
    if msgs: self.chatlog.append_messages(msgs)
```

### `_update_sprites(state)` 🔴 CORE + 🟡 (Löwen-Check)
**Sprite-Batching-Mechanik:**
1. **Tiere:** Iteriere `state["tiere_auf_map"]` → erstelle `AsciiLionSprite` für Löwen, `AnimalSprite` für andere. Aktualisiere via `update_pos(x, y, is_dead)`. Entferne tote Sprites.
2. **Besucher:** `VisitorSprite` — gleiches Muster
3. **Gehege:** `EnclosureItem` — nur bei Änderungen neu erstellen
4. **Dekorationen:** `DecoSprite` — konditional auf `decoration_slots`
5. **Lighting:** `scene.apply_lighting(phase)`

---

## 9. QSS Dark Theme

~100 Zeilen CSS-in-Python. Vollständiges Styling für:
- `QMainWindow`, `QToolBar`, `QStatusBar`
- `QPushButton` (default/hover/disabled/accent/danger)
- `QComboBox`, `QSpinBox`, `QSlider`
- `QProgressBar`, `QGroupBox`, `QTabWidget/QTabBar`
- `QTextEdit`, `QScrollArea/QScrollBar`
- `QMenuBar/QMenu`, `QCheckBox`, `QDialog`, `QListWidget`

**Design-Prinzip:** Alle Styles über QSS, keine inline-Styles. Zentrale Verwaltung in `launch_frontend()`.

---

## 10. Datenfluss-Diagramm

```
┌─────────────────────────────────────────────────────────────┐
│                    FRONTEND (PyQt6)                          │
│                                                              │
│  QTimer(100ms)                                               │
│      │                                                       │
│      ▼                                                       │
│  ZooMainWindow._tick()                                       │
│      │                                                       │
│      ├─ engine.tick()           ──── Backend berechnet       │
│      ├─ engine.get_game_state() ──── Dict mit allen Daten    │
│      │                                                       │
│      ├─ _update_sprites(state)                               │
│      │   ├─ AsciiLionSprite (Löwe)                           │
│      │   ├─ AnimalSprite (Giraffe/Pinguin)                   │
│      │   ├─ VisitorSprite (Besucher)                         │
│      │   ├─ EnclosureItem (Gehege)                           │
│      │   ├─ DecoSprite (Dekorationen)                        │
│      │   └─ apply_lighting (Tag/Nacht)                       │
│      │                                                       │
│      ├─ _update_labels(state)                                │
│      │   ├─ Toolbar: Tag, Budget, Rep, Happiness             │
│      │   └─ StatusBar: Tiere, Besucher, Gehege               │
│      │                                                       │
│      └─ _update_panels(state)                                │
│          ├─ ActionPanel.update_state()                       │
│          └─ UpgradePanel.update_state()                      │
│                                                              │
│  User-Interaktion                                            │
│      │                                                       │
│      ├─ Button-Click → ActionPanel/ShopPanel/UpgradePanel    │
│      │   └─ _dispatch(action, **kwargs)                      │
│      │       └─ engine.execute_action() ──── Backend         │
│      │                                                       │
│      └─ Map-Interaktion → ZooGraphicsView                    │
│          ├─ Hover → entity_hovered(tier_id)                  │
│          │   └─ EntityInfoPanel.show_data()                  │
│          ├─ Click → map_clicked(x,y)                         │
│          │   └─ Gehege-Selektion                             │
│          └─ Drag → drop_requested(tier_id,x,y)               │
│              └─ engine.execute_action("drop_animal")         │
└─────────────────────────────────────────────────────────────┘
```

---

## 11. Assets-Verzeichnis

```
assets/
├── __init__.py            ← Leeres Package-Marker
├── ascii_lion.py          ← ASCII_LION (40 Zeilen) — Willkommens-Banner + Map-Pixmap-Quelle
└── ascii_lion_small.py    ← ASCII_LION_SMALL (25 Zeilen) — EntityInfoPanel-Kompaktversion
```

**Verwendung:**
- `ascii_lion.py` → `main.py` (CLI-Splash) + `frontend/main_window.py` (Pixmap-Rendering für Map)
- `ascii_lion_small.py` → `frontend/main_window.py` (EntityInfoPanel bei Löwen-Hover)

---

*Dokument erstellt am 6. August 2026 — Vollständige Frontend-Architekturdokumentation*