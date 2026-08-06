"""
ZooMainWindow — top-level PyQt6 window for the vivizoo simulation.

Phase 1: Core prototype with map, action panel, shop, chatlog, and entity-info hover.
Tier 1: Gradient theme, drop shadows, button glow, enclosure gradients.
Tier 2: Hover highlight on sprites, floating score popups, toolbar icon enhancements.
Tier 4: Styled top toolbar with glass-morphism stat chips and bottom status bar badges.

Tests:
    - test_tick_loop_polls_state, test_hover_updates_entity_info_panel,
      test_dispatch_routes_to_controller, test_map_click_deselects
"""

from __future__ import annotations

from typing import Optional

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QTabWidget, QLabel, QPushButton, QGraphicsDropShadowEffect,
    QFrame, QSizePolicy, QSpacerItem,
)
from PyQt6.QtCore import QTimer, Qt, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QAction, QColor, QFont

from frontend.core.constants import (
    WINDOW_TITLE, WINDOW_W, WINDOW_H, TICK_MS,
    C_TEXT, C_TEXT_DIM, C_BG_PANEL, C_BG_PANEL2, C_BG_CARD, C_BG_CARD2,
    C_GOLD, C_GOLD_GLOW, C_RED, C_RED_GLOW, C_ACCENT, C_ACCENT2, C_ACCENT_GLOW,
    C_BORDER, SHADOW_BLUR, SHADOW_OFFSET,
    ENCLOSURE_DEFS,
)
from frontend.core.frontend_controller import FrontendController

from frontend.ui.zoo_scene import ZooScene
from frontend.ui.zoo_view import ZooGraphicsView
from frontend.ui.chat_view import ChatlogWidget
from frontend.ui.entity_info_panel import EntityInfoPanel
from frontend.ui.action_panel import ActionPanel
from frontend.ui.shop_panel import ShopPanel
from frontend.ui.event_banner import EventBanner


# ── Drop-shadow helper ─────────────────────────────────────────────────────

def _drop_shadow(widget: QWidget, blur: int = SHADOW_BLUR,
                 dx: int = SHADOW_OFFSET[0], dy: int = SHADOW_OFFSET[1]) -> None:
    shadow = QGraphicsDropShadowEffect()
    shadow.setBlurRadius(blur)
    shadow.setOffset(dx, dy)
    shadow.setColor(QColor(0, 0, 0, 120))
    widget.setGraphicsEffect(shadow)


# ── Styled "chip" badge helper ─────────────────────────────────────────────

_CHIP_QSS = (
    "QFrame {"
    f"  background: qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 {C_BG_CARD2},stop:1 {C_BG_CARD});"
    f"  border: 1px solid {C_BORDER};"
    "  border-radius: 6px;"
    "  padding: 2px 8px;"
    "}"
)

def _make_chip(icon_text: str, value_text: str = "",
               accent_color: str = C_TEXT) -> QFrame:
    """Create a glass-morphism pill badge.

    Args:
        icon_text: Emoji + label prefix (e.g. "💰 Budget").
        value_text: The dynamic value portion (e.g. "5.000 €").
        accent_color: Hex colour for the value text.

    Returns:
        A styled QFrame containing a horizontal layout with icon and value labels.
    """
    chip = QFrame()
    chip.setStyleSheet(_CHIP_QSS)
    lay = QHBoxLayout(chip)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(5)

    icon_lbl = QLabel(icon_text)
    icon_lbl.setStyleSheet(
        f"color: {C_TEXT_DIM}; background: transparent; border: none; "
        "font-size: 11px; font-weight: 500;"
    )
    lay.addWidget(icon_lbl)

    val_lbl = QLabel(value_text)
    val_lbl.setObjectName("chip_value")
    val_lbl.setStyleSheet(
        f"color: {accent_color}; background: transparent; border: none; "
        "font-size: 11px; font-weight: 700;"
    )
    lay.addWidget(val_lbl)

    # Store reference for updating
    chip._val_lbl = val_lbl
    chip._accent = accent_color
    return chip


def _update_chip(chip: QFrame, new_value: str, new_accent: str | None = None) -> None:
    """Update a chip's value label text and optional accent colour.

    Args:
        chip: The QFrame returned by _make_chip.
        new_value: New value text to display.
        new_accent: Optional new colour hex string.
    """
    if new_accent is not None:
        chip._accent = new_accent
    chip._val_lbl.setText(new_value)
    chip._val_lbl.setStyleSheet(
        f"color: {chip._accent}; background: transparent; border: none; "
        "font-size: 11px; font-weight: 700;"
    )


# ── Main Window ─────────────────────────────────────────────────────────────

class ZooMainWindow(QMainWindow):
    """Top-level window with custom toolbar and status bar replacements.

    Tier 4 replaces the native QToolBar (top) and QStatusBar (bottom)
    with custom QFrame-based bars containing glass-morphism chip badges.

    Tests:
        - test_tick_loop_polls_state: Mock controller; trigger _tick();
          verify controller.get_state() was called.
        - test_hover_updates_entity_info_panel: Trigger _on_hover("a_01");
          verify controller.get_entity_info() called and panel updated.
        - test_dispatch_routes_to_controller: Trigger _dispatch("feed_all");
          verify controller.execute_action("feed_all") called.
        - test_map_click_deselects: Select animal, trigger _on_map_clicked();
          verify selection cleared and info panel shows placeholder.
    """

    def __init__(self, controller: FrontendController) -> None:
        super().__init__()
        self._controller = controller
        self._selected_animal_id: Optional[str] = None
        self._selected_enclosure_id: Optional[str] = None
        self._paused = False

        self.setWindowTitle(WINDOW_TITLE)
        self.setFixedSize(WINDOW_W, WINDOW_H)

        self._build_ui()
        self._connect_signals()

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(TICK_MS)

    # ── UI Construction ────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        # ── Menu bar (native, minimal) ──────────────────────────────────
        file_menu = self.menuBar().addMenu("Datei")
        file_menu.addAction(QAction("Beenden", self, triggered=self.close))

        # ── Central container ───────────────────────────────────────────
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        # ═══ TOP BAR — custom toolbar replacement ═══════════════════════
        top_bar = QFrame()
        top_bar.setObjectName("top_bar")
        top_bar.setFixedHeight(30)
        top_bar.setStyleSheet(
            f"#top_bar {{"
            f"  background: qlineargradient(x1:0,y1:0,x2:0,y2:1,"
            f"    stop:0 {C_BG_PANEL2}, stop:0.3 {C_BG_PANEL}, stop:1 {C_BG_PANEL});"
            f"  border-bottom: 1px solid {C_BORDER};"
            f"  border-radius: 8px;"
            f"}}"
        )
        top_lay = QHBoxLayout(top_bar)
        top_lay.setContentsMargins(10, 2, 10, 2)
        top_lay.setSpacing(8)

        # Day chip
        self._chip_day = _make_chip("📅 Tag", "1")
        top_lay.addWidget(self._chip_day)

        # Pause button
        self._btn_pause = QPushButton("⏸ Pause")
        self._btn_pause.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_pause.setFixedHeight(28)
        self._btn_pause.setStyleSheet(
            f"QPushButton {{"
            f"  background: qlineargradient(x1:0,y1:0,x2:0,y2:1,"
            f"    stop:0 {C_ACCENT_GLOW}, stop:1 {C_ACCENT});"
            f"  border: 1px solid {C_ACCENT_GLOW}; color: #fff; border-radius: 6px;"
            f"  padding: 3px 12px; font-weight: bold; font-size: 11px;"
            f"}}"
            f"QPushButton:hover {{"
            f"  background: qlineargradient(x1:0,y1:0,x2:0,y2:1,"
            f"    stop:0 {C_ACCENT}, stop:1 {C_ACCENT2});"
            f"  border: 2px solid #fff;"
            f"}}"
        )
        self._btn_pause.clicked.connect(self._toggle_pause)
        top_lay.addWidget(self._btn_pause)

        # Spacer ─────────────────────────────────────────────────────────
        top_lay.addSpacerItem(QSpacerItem(0, 0, QSizePolicy.Policy.Expanding,
                                           QSizePolicy.Policy.Minimum))

        # Budget chip
        self._chip_budget = _make_chip("💰", "0 €", C_GOLD_GLOW)
        top_lay.addWidget(self._chip_budget)

        # Reputation chip
        self._chip_rep = _make_chip("⭐", "0", C_GOLD_GLOW)
        top_lay.addWidget(self._chip_rep)

        # Happiness chip
        self._chip_happy = _make_chip("😊", "0%", C_ACCENT_GLOW)
        top_lay.addWidget(self._chip_happy)

        # Zoo open/closed chip
        self._chip_open = _make_chip("🔓", "OFFEN", C_ACCENT_GLOW)
        top_lay.addWidget(self._chip_open)

        # Speed indicator
        self._chip_speed = _make_chip("🏃", "1×")
        top_lay.addWidget(self._chip_speed)

        root.addWidget(top_bar)

        # ═══ MIDDLE: Map + right panels ═════════════════════════════════
        body = QHBoxLayout()
        body.setSpacing(8)

        # Left: map
        self._scene = ZooScene()
        self._view = ZooGraphicsView(self._scene)
        body.addWidget(self._view, stretch=3)

        # Right column
        right_col = QVBoxLayout()
        right_col.setSpacing(8)

        self._tabs = QTabWidget()
        self._tabs.setMaximumWidth(420)
        self._tabs.setMinimumWidth(360)
        self._tabs.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)

        self._action_panel = ActionPanel()
        self._shop_panel = ShopPanel()

        # Panels go directly in tabs — QTabWidget pane QSS handles dark bg
        self._tabs.addTab(self._action_panel, "🎮 Aktionen")
        self._tabs.addTab(self._shop_panel, "🛒 Shop")
        right_col.addWidget(self._tabs)

        self._entity_info = EntityInfoPanel()
        right_col.addWidget(self._entity_info)

        self._chatlog = ChatlogWidget()
        right_col.addWidget(self._chatlog, stretch=1)

        self._event_banner = EventBanner()
        right_col.addWidget(self._event_banner)

        # Wrap right column in a widget for body layout
        right_w = QWidget()
        right_w.setLayout(right_col)
        body.addWidget(right_w, stretch=1)

        body_w = QWidget()
        body_w.setLayout(body)
        root.addWidget(body_w, stretch=1)

        _drop_shadow(self._tabs)
        _drop_shadow(self._entity_info)
        _drop_shadow(self._chatlog)

        # ═══ BOTTOM BAR — custom status bar replacement ═════════════════
        self._bot_bar = QFrame()
        self._bot_bar.setObjectName("bot_bar")
        self._bot_bar.setFixedHeight(30)
        self._bot_bar.setStyleSheet(
            f"#bot_bar {{"
            f"  background: qlineargradient(x1:0,y1:0,x2:0,y2:1,"
            f"    stop:0 {C_BG_PANEL}, stop:0.7 {C_BG_PANEL2}, stop:1 {C_BG_PANEL});"
            f"  border-top: 1px solid {C_BORDER};"
            f"  border-radius: 8px;"
            f"}}"
        )
        bot_lay = QHBoxLayout(self._bot_bar)
        bot_lay.setContentsMargins(10, 2, 10, 2)
        bot_lay.setSpacing(8)

        # Status message (left)
        self._lbl_status = QLabel("🟢 Bereit")
        self._lbl_status.setStyleSheet(
            f"color: {C_TEXT}; background: transparent; border: none; "
            "font-size: 11px; font-weight: 600;"
        )
        bot_lay.addWidget(self._lbl_status)

        # Spacer ─────────────────────────────────────────────────────────
        bot_lay.addSpacerItem(QSpacerItem(0, 0, QSizePolicy.Policy.Expanding,
                                           QSizePolicy.Policy.Minimum))

        # Animals chip (alive / dead)
        self._chip_animals = _make_chip("🐾 Tiere", "0 / 0 tot", C_ACCENT_GLOW)
        bot_lay.addWidget(self._chip_animals)

        # Visitors chip
        self._chip_visitors = _make_chip("👥 Besucher", "0", C_GOLD_GLOW)
        bot_lay.addWidget(self._chip_visitors)

        # Enclosures chip
        self._chip_enclosures = _make_chip("🏠 Gehege", "0")
        bot_lay.addWidget(self._chip_enclosures)

        # Last action message chip (rightmost)
        self._chip_action = _make_chip("📋", "—", C_TEXT_DIM)
        bot_lay.addWidget(self._chip_action)

        root.addWidget(self._bot_bar)

        # Tier 2: Floating score label (hidden by default)
        self._score_label = QLabel(self._view)
        self._score_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        self._score_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._score_label.hide()

    # ── Signal Wiring ──────────────────────────────────────────────────────

    def _connect_signals(self) -> None:
        for enc in self._scene._enclosures.values():
            enc.set_click_callback(self._on_enclosure_selected)
        self._view.map_clicked.connect(self._on_map_clicked)
        self._action_panel.action_triggered.connect(self._dispatch)
        self._shop_panel.buy_food.connect(
            lambda ft, amt: self._dispatch("buy_food", type=ft, amount=amt))
        self._shop_panel.buy_animal.connect(
            lambda sp: self._dispatch("buy_animal", species=sp))
        self._wire_sprite_callbacks()

    # ── Tick Loop ──────────────────────────────────────────────────────────

    def _tick(self) -> None:
        self._controller.advance_tick()
        state = self._controller.get_state()
        if not state:
            return
        self._update_sprites(state)
        self._update_labels(state)
        self._update_panels(state)
        msgs = self._controller.get_chat_messages()
        if msgs:
            self._chatlog.append_messages(msgs)

    # ── Update Helpers ─────────────────────────────────────────────────────

    def _wire_sprite_callbacks(self) -> None:
        for sprite in self._scene._animals.values():
            sprite.set_hover_callback(self._on_hover)
            sprite.set_unhover_callback(self._on_unhover)

    def _update_sprites(self, state: dict) -> None:
        self._scene.update_entities(state)
        zoo_open = state.get("system", {}).get("zoo_open", True)
        self._scene.apply_lighting(zoo_open)
        self._wire_sprite_callbacks()

    def _update_labels(self, state: dict) -> None:
        """Update all top-bar chips and bottom-bar badges from game state."""
        system = state.get("system", {})
        finances = state.get("finances", {})
        animals = state.get("animals_on_map", [])
        visitors = state.get("visitors_on_map", [])

        # ── Top bar chips ─────────────────────────────────────────────
        ticks = system.get("tick_count", 0)
        day = max(1, ticks // 480 + 1) if ticks > 0 else 1
        _update_chip(self._chip_day, str(day))

        money = finances.get("money", 0)
        # Budget colour: green when rich, gold when medium, red when broke
        if money >= 10_000:
            budget_accent = C_ACCENT_GLOW
        elif money >= 2_000:
            budget_accent = C_GOLD_GLOW
        else:
            budget_accent = C_RED_GLOW
        _update_chip(self._chip_budget, f"{money:,.0f} €", budget_accent)

        rep = finances.get("reputation", 0)
        _update_chip(self._chip_rep, str(rep))

        happy = finances.get("zoo_happiness", 0)
        if happy >= 70:
            happy_accent = C_ACCENT_GLOW
        elif happy >= 30:
            happy_accent = C_GOLD_GLOW
        else:
            happy_accent = C_RED_GLOW
        _update_chip(self._chip_happy, f"{happy}%", happy_accent)

        zoo_open = system.get("zoo_open", True)
        if zoo_open:
            _update_chip(self._chip_open, "OFFEN", C_ACCENT_GLOW)
            self._chip_open.findChild(QLabel).setText("🔓")
        else:
            _update_chip(self._chip_open, "GESCHL.", C_RED_GLOW)
            self._chip_open.findChild(QLabel).setText("🔒")

        # ── Bottom bar badges ──────────────────────────────────────────
        alive = sum(1 for a in animals if not a.get("is_dead"))
        dead = sum(1 for a in animals if a.get("is_dead"))
        if dead > 0:
            animals_accent = C_GOLD_GLOW
        elif alive == 0:
            animals_accent = C_RED_GLOW
        else:
            animals_accent = C_ACCENT_GLOW
        _update_chip(self._chip_animals, f"{alive} / {dead} tot", animals_accent)

        vcount = len(visitors)
        _update_chip(self._chip_visitors, str(vcount))

        _update_chip(self._chip_enclosures, str(len(ENCLOSURE_DEFS)))

        # Keep the initial status message unless overridden by an action
        if not hasattr(self, '_last_action_msg') or self._last_action_msg is None:
            self._lbl_status.setText(f"🟢 Tag {day} — {alive} Tiere, {vcount} Besucher")

    def _update_panels(self, state: dict) -> None:
        self._action_panel.update_state(
            state, self._selected_animal_id, self._selected_enclosure_id)
        self._shop_panel.update_state(state)

    # ── Hover / Click ──────────────────────────────────────────────────────

    def _on_hover(self, entity_id: str) -> None:
        data = self._controller.get_entity_info(entity_id)
        self._entity_info.show_entity(data)
        self._selected_animal_id = entity_id

    def _on_unhover(self) -> None:
        self._entity_info.show_entity(None)
        self._selected_animal_id = None

    def _on_enclosure_selected(self, enclosure_id: str) -> None:
        self._selected_enclosure_id = enclosure_id
        self._selected_animal_id = None
        self._entity_info.show_entity(None)
        state = self._controller.get_state()
        if state:
            self._update_panels(state)

    def _on_map_clicked(self, x: float, y: float) -> None:
        self._selected_animal_id = None
        self._selected_enclosure_id = None
        self._entity_info.show_entity(None)
        state = self._controller.get_state()
        if state:
            self._update_panels(state)

    # ── God-mode Dispatch ──────────────────────────────────────────────────

    def _dispatch(self, action: str, **kwargs: object) -> None:
        result = self._controller.execute_action(action, **kwargs)
        msg = result.get("message", "")
        success = result.get("success", False)

        # Update action chip in bottom bar
        icon = "✅" if success else "❌"
        _update_chip(self._chip_action, f"{icon} {msg}" if msg else f"{icon} {action}")

        # Flash status label
        self._lbl_status.setText(f"{'✅' if success else '❌'} {msg}" if msg else action)
        self._last_action_msg = msg if msg else None

        entries = result.get("chat_entries", [])
        if entries:
            self._chatlog.append_messages(entries)

        # Tier 2: Show floating score popup on success
        if success:
            self._show_score_popup(action, msg)

    # ── Tier 2: Floating Score Popup ───────────────────────────────────────

    def _show_score_popup(self, action: str, message: str) -> None:
        """Show a floating text overlay that fades out after 2 seconds.

        The text is positioned over the zoo map viewport and auto-fades.

        Args:
            action: The action name (determines text / colour).
            message: Result message to extract amount from.
        """
        colour = C_GOLD_GLOW
        prefix = ""

        if action in ("buy_food", "buy_animal"):
            colour = C_RED
            prefix = "-"
        elif action in ("feed_all", "feed_one", "heal", "clean"):
            colour = C_ACCENT_GLOW
            prefix = "✓"

        self._score_label.setText(f"{prefix} {message}" if prefix else message)
        self._score_label.setStyleSheet(
            f"color: {colour}; background: rgba(0,0,0,160); "
            f"border-radius: 8px; padding: 8px 16px; font-size: 14px;"
        )
        self._score_label.adjustSize()

        vw = self._view.viewport()
        if vw:
            x = (vw.width() - self._score_label.width()) // 2
            y = vw.height() // 4
            self._score_label.move(x, y)

        self._score_label.show()

        self._score_anim = QPropertyAnimation(self._score_label, b"windowOpacity")
        self._score_anim.setDuration(2000)
        self._score_anim.setStartValue(1.0)
        self._score_anim.setEndValue(0.0)
        self._score_anim.setEasingCurve(QEasingCurve.Type.InQuad)
        self._score_anim.finished.connect(self._score_label.hide)
        self._score_anim.start()

    # ── Pause ──────────────────────────────────────────────────────────────

    def _toggle_pause(self) -> None:
        self._paused = self._controller.toggle_pause()
        if self._paused:
            self._btn_pause.setText("▶ Start")
            self._btn_pause.setStyleSheet(
                f"QPushButton {{"
                f"  background: qlineargradient(x1:0,y1:0,x2:0,y2:1,"
                f"    stop:0 {C_RED_GLOW}, stop:1 {C_RED});"
                f"  border: 1px solid {C_RED_GLOW}; color: #fff; border-radius: 8px;"
                f"  padding: 5px 14px; font-weight: bold; font-size: 12px;"
                f"}}"
            )
        else:
            self._btn_pause.setText("⏸ Pause")
            self._btn_pause.setStyleSheet(
                f"QPushButton {{"
                f"  background: qlineargradient(x1:0,y1:0,x2:0,y2:1,"
                f"    stop:0 {C_ACCENT_GLOW}, stop:1 {C_ACCENT});"
                f"  border: 1px solid {C_ACCENT_GLOW}; color: #fff; border-radius: 8px;"
                f"  padding: 5px 14px; font-weight: bold; font-size: 12px;"
                f"}}"
            )