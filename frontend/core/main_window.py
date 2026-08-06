"""
ZooMainWindow — top-level PyQt6 window for the vivizoo simulation.

Phase 1: Core prototype with map, action panel, shop, chatlog, and entity-info hover.
Tier 1: Gradient theme, drop shadows, button glow, enclosure gradients.
Tier 2: Hover highlight on sprites, floating score popups, toolbar icon enhancements.

Tests:
    - test_tick_loop_polls_state: Mock controller; trigger _tick();
      verify controller.get_state() was called.
    - test_hover_updates_entity_info_panel: Trigger _on_hover("a_01");
      verify controller.get_entity_info() called and panel updated.
    - test_dispatch_routes_to_controller: Trigger _dispatch("feed_all");
      verify controller.execute_action("feed_all") called.
    - test_map_click_deselects: Select an animal, trigger _on_map_clicked();
      verify selection cleared and info panel shows placeholder.
"""

from __future__ import annotations

from typing import Optional, TYPE_CHECKING

from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QTabWidget,
    QLabel,
    QPushButton,
    QGraphicsDropShadowEffect,
    QFrame,
    QSizePolicy,
    QSpacerItem,
)
from PyQt6.QtCore import QTimer, Qt, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QAction, QColor

from frontend.core.constants import (
    WINDOW_TITLE,
    WINDOW_W,
    WINDOW_H,
    TICK_MS,
    C_TEXT,
    C_TEXT_DIM,
    C_BG_PANEL,
    C_BG_PANEL2,
    C_BG_CARD,
    C_BG_CARD2,
    C_GOLD,
    C_GOLD_GLOW,
    C_RED,
    C_RED_GLOW,
    C_ACCENT,
    C_ACCENT2,
    C_ACCENT_GLOW,
    C_BORDER,
    SHADOW_BLUR,
    SHADOW_OFFSET,
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

if TYPE_CHECKING:
    from frontend.ui.animal_sprite import AnimalSprite
    from frontend.ui.lion_sprite import AsciiLionSprite
    from frontend.ui.enclosure_item import EnclosureItem

# ── Drop-shadow helper ─────────────────────────────────────────────────────


def _drop_shadow(
    widget: QWidget,
    blur: int = SHADOW_BLUR,
    dx: int = SHADOW_OFFSET[0],
    dy: int = SHADOW_OFFSET[1],
) -> None:
    """Apply a soft drop-shadow effect to a widget for game-like depth."""
    shadow = QGraphicsDropShadowEffect()
    shadow.setBlurRadius(blur)
    shadow.setOffset(dx, dy)
    shadow.setColor(QColor(0, 0, 0, 120))
    widget.setGraphicsEffect(shadow)


# ── StatusChip — glass-morphism pill badge ──────────────────────────────────

_CHIP_QSS = (
    "QFrame {"
    f"  background: qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 {C_BG_CARD2},stop:1 {C_BG_CARD});"
    f"  border: 1px solid {C_BORDER};"
    "  border-radius: 6px;"
    "  padding: 2px 8px;"
    "}"
)


class StatusChip(QFrame):
    """Glass-morphism pill badge with an icon label and a dynamic value label.

    Replaces the old _make_chip() / _update_chip() function pair with
    a proper QFrame subclass so all attributes are public and pylint
    does not flag protected-access.

    Tests:
        - test_set_value_updates_label: Call set_value("42"); verify
          the value label text equals "42".
        - test_set_accent_changes_colour: Call set_accent("#ff0000");
          verify value label stylesheet contains #ff0000.
    """

    def __init__(
        self,
        icon_text: str = "",
        value_text: str = "",
        accent_color: str = C_TEXT,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setStyleSheet(_CHIP_QSS)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(5)

        self.icon_label = QLabel(icon_text)
        self.icon_label.setStyleSheet(
            f"color: {C_TEXT_DIM}; background: transparent; border: none; "
            "font-size: 11px; font-weight: 500;"
        )
        lay.addWidget(self.icon_label)

        self.value_label = QLabel(value_text)
        self.value_label.setStyleSheet(
            f"color: {accent_color}; background: transparent; border: none; "
            "font-size: 11px; font-weight: 700;"
        )
        lay.addWidget(self.value_label)

        self._accent = accent_color

    def set_value(self, text: str) -> None:
        """Update the displayed value text."""
        self.value_label.setText(text)

    def set_accent(self, color: str) -> None:
        """Change the accent colour of the value text."""
        self._accent = color
        self.value_label.setStyleSheet(
            f"color: {color}; background: transparent; border: none; "
            "font-size: 11px; font-weight: 700;"
        )


# ── Main Window ─────────────────────────────────────────────────────────────


class ZooMainWindow(QMainWindow):
    """Top-level window with custom toolbar and status bar replacements."""

    def __init__(self, controller: FrontendController) -> None:
        super().__init__()
        self._controller = controller
        self._selected_animal_id: Optional[str] = None
        self._selected_enclosure_id: Optional[str] = None
        self._paused = False
        self._score_anim: Optional[QPropertyAnimation] = None
        self._last_action_msg: Optional[str] = None

        self.setWindowTitle(WINDOW_TITLE)
        self.setFixedSize(WINDOW_W, WINDOW_H)

        self._build_ui()
        self._connect_signals()

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(TICK_MS)

    # ── UI Construction ────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        # ── Menu bar ────────────────────────────────────────────────────
        file_menu = self.menuBar().addMenu("Datei")
        file_menu.addAction(QAction("Beenden", self, triggered=self.close))

        # ── Central container ───────────────────────────────────────────
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        # ═══ TOP BAR ════════════════════════════════════════════════════
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

        self._chip_day = StatusChip("📅 Tag", "1")
        top_lay.addWidget(self._chip_day)

        self._btn_pause = self._make_pause_button()
        top_lay.addWidget(self._btn_pause)

        top_lay.addSpacerItem(
            QSpacerItem(0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        )

        self._chip_budget = StatusChip("💰", "0 €", C_GOLD_GLOW)
        top_lay.addWidget(self._chip_budget)

        self._chip_rep = StatusChip("⭐", "0", C_GOLD_GLOW)
        top_lay.addWidget(self._chip_rep)

        self._chip_happy = StatusChip("😊", "0%", C_ACCENT_GLOW)
        top_lay.addWidget(self._chip_happy)

        self._chip_open = StatusChip("🔓", "OFFEN", C_ACCENT_GLOW)
        top_lay.addWidget(self._chip_open)

        self._chip_speed = StatusChip("🏃", "1×")
        top_lay.addWidget(self._chip_speed)

        root.addWidget(top_bar)

        # ═══ MIDDLE: Map + right panels ═══════════════════════════════════
        body = QHBoxLayout()
        body.setSpacing(8)

        self._scene = ZooScene()
        self._view = ZooGraphicsView(self._scene)
        body.addWidget(self._view, stretch=3)

        right_col = QVBoxLayout()
        right_col.setSpacing(8)

        self._tabs = QTabWidget()
        self._tabs.setMaximumWidth(420)
        self._tabs.setMinimumWidth(360)
        self._tabs.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)

        self._action_panel = ActionPanel()
        self._shop_panel = ShopPanel()
        self._tabs.addTab(self._action_panel, "🎮 Aktionen")
        self._tabs.addTab(self._shop_panel, "🛒 Shop")
        right_col.addWidget(self._tabs)

        self._entity_info = EntityInfoPanel()
        right_col.addWidget(self._entity_info)

        self._chatlog = ChatlogWidget()
        right_col.addWidget(self._chatlog, stretch=1)

        self._event_banner = EventBanner()
        right_col.addWidget(self._event_banner)

        right_w = QWidget()
        right_w.setLayout(right_col)
        body.addWidget(right_w, stretch=1)

        body_w = QWidget()
        body_w.setLayout(body)
        root.addWidget(body_w, stretch=1)

        _drop_shadow(self._tabs)
        _drop_shadow(self._entity_info)
        _drop_shadow(self._chatlog)

        # ═══ BOTTOM BAR ═══════════════════════════════════════════════════
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

        self._lbl_status = QLabel("🟢 Bereit")
        self._lbl_status.setStyleSheet(
            f"color: {C_TEXT}; background: transparent; border: none; "
            "font-size: 11px; font-weight: 600;"
        )
        bot_lay.addWidget(self._lbl_status)

        bot_lay.addSpacerItem(
            QSpacerItem(0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        )

        self._chip_animals = StatusChip("🐾 Tiere", "0 / 0 tot", C_ACCENT_GLOW)
        bot_lay.addWidget(self._chip_animals)

        self._chip_visitors = StatusChip("👥 Besucher", "0", C_GOLD_GLOW)
        bot_lay.addWidget(self._chip_visitors)

        self._chip_enclosures = StatusChip("🏠 Gehege", "0")
        bot_lay.addWidget(self._chip_enclosures)

        self._chip_action = StatusChip("📋", "—", C_TEXT_DIM)
        bot_lay.addWidget(self._chip_action)

        root.addWidget(self._bot_bar)

        # Tier 2: Floating score label (hidden by default)
        self._score_label = QLabel(self._view)
        self._score_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        self._score_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._score_label.hide()

    def _make_pause_button(self) -> QPushButton:
        """Create the styled pause/resume button."""
        btn = QPushButton("⏸ Pause")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFixedHeight(28)
        btn.setStyleSheet(
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
        btn.clicked.connect(self._toggle_pause)
        return btn

    # ── Signal Wiring ──────────────────────────────────────────────────────

    def _connect_signals(self) -> None:
        for enc in self._scene.enclosures.values():
            enc.set_click_callback(self._on_enclosure_selected)
        self._view.map_clicked.connect(self._on_map_clicked)
        self._action_panel.action_triggered.connect(self._dispatch)
        self._shop_panel.buy_food.connect(
            lambda ft, amt: self._dispatch("buy_food", type=ft, amount=amt)
        )
        self._shop_panel.buy_animal.connect(
            lambda sp: self._dispatch("buy_animal", species=sp)
        )
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
        for sprite in self._scene.animals.values():
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

        ticks = system.get("tick_count", 0)
        day = max(1, ticks // 480 + 1) if ticks > 0 else 1
        self._chip_day.set_value(str(day))

        money = finances.get("money", 0)
        if money >= 10_000:
            self._chip_budget.set_accent(C_ACCENT_GLOW)
        elif money >= 2_000:
            self._chip_budget.set_accent(C_GOLD_GLOW)
        else:
            self._chip_budget.set_accent(C_RED_GLOW)
        self._chip_budget.set_value(f"{money:,.0f} €")

        rep = finances.get("reputation", 0)
        self._chip_rep.set_value(str(rep))

        happy = finances.get("zoo_happiness", 0)
        if happy >= 70:
            self._chip_happy.set_accent(C_ACCENT_GLOW)
        elif happy >= 30:
            self._chip_happy.set_accent(C_GOLD_GLOW)
        else:
            self._chip_happy.set_accent(C_RED_GLOW)
        self._chip_happy.set_value(f"{happy}%")

        zoo_open = system.get("zoo_open", True)
        if zoo_open:
            self._chip_open.set_accent(C_ACCENT_GLOW)
            self._chip_open.set_value("OFFEN")
            self._chip_open.icon_label.setText("🔓")
        else:
            self._chip_open.set_accent(C_RED_GLOW)
            self._chip_open.set_value("GESCHL.")
            self._chip_open.icon_label.setText("🔒")

        alive = sum(1 for a in animals if not a.get("is_dead"))
        dead = sum(1 for a in animals if a.get("is_dead"))
        if dead > 0:
            self._chip_animals.set_accent(C_GOLD_GLOW)
        elif alive == 0:
            self._chip_animals.set_accent(C_RED_GLOW)
        else:
            self._chip_animals.set_accent(C_ACCENT_GLOW)
        self._chip_animals.set_value(f"{alive} / {dead} tot")

        vcount = len(visitors)
        self._chip_visitors.set_value(str(vcount))

        self._chip_enclosures.set_value(str(len(ENCLOSURE_DEFS)))

        if self._last_action_msg is None:
            self._lbl_status.setText(f"🟢 Tag {day} — {alive} Tiere, {vcount} Besucher")

    def _update_panels(self, state: dict) -> None:
        self._action_panel.update_state(
            state, self._selected_animal_id, self._selected_enclosure_id
        )
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

    def _on_map_clicked(self, _x: float, _y: float) -> None:
        """Deselect on empty map click.

        Args:
            _x: Unused — required by signal signature.
            _y: Unused — required by signal signature.
        """
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

        icon = "✅" if success else "❌"
        self._chip_action.set_value(f"{icon} {msg}" if msg else f"{icon} {action}")

        self._lbl_status.setText(
            f"{'✅' if success else '❌'} {msg}" if msg else action
        )
        self._last_action_msg = msg if msg else None

        entries = result.get("chat_entries", [])
        if entries:
            self._chatlog.append_messages(entries)

        if success:
            self._show_score_popup(action, msg)

    # ── Tier 2: Floating Score Popup ───────────────────────────────────────

    def _show_score_popup(self, action: str, message: str) -> None:
        """Show a floating text overlay that fades out after 2 seconds."""
        if action in ("buy_food", "buy_animal"):
            colour = C_RED
            prefix = "-"
        elif action in ("feed_all", "feed_one", "heal", "clean"):
            colour = C_ACCENT_GLOW
            prefix = "✓"
        else:
            colour = C_GOLD_GLOW
            prefix = ""

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
