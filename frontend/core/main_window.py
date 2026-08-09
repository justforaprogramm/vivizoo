"""
ZooMainWindow — top-level PyQt6 window for the vivizoo simulation.

Owns the whole layout (custom top bar, map, right column, custom bottom
bar), routes every panel signal into ``_dispatch`` and drives the render
loop: each Qt timer frame advances the simulation, polls the enriched
snapshot and pushes it into the map, the chips and the panels.

Everything shown here comes from the backend snapshot — there are no
placeholder metrics. Values the live snapshot does not carry (reputation,
average happiness) are shown in the statistics tab, where the backend does
report them per finished day.

Tests:
    - test_tick_loop_polls_state: Mock the controller; trigger _tick();
      verify get_state() was called.
    - test_hover_updates_entity_info_panel: Trigger _on_hover("a_01");
      verify get_entity_info() was called and the panel updated.
    - test_dispatch_routes_to_controller: Trigger _dispatch("feed_all");
      verify execute_action("feed_all") was called.
    - test_map_click_deselects: Select an animal, trigger _on_map_clicked();
      verify the selection is cleared and the placeholder is shown.

Module owner: Erik (frontend).
"""

# 1551 lines, of which 555 are code: the rest is 681 lines of docstrings, 68
# lines of comment and 247 blank lines. The submission rule "at least two test
# descriptions per function" roughly doubles the length of every file, and
# pylint counts documentation like any other line. Extracting the top and
# bottom bars into their own widgets was considered: it moves around 310
# lines, still leaves the file above the limit at ~1232, and costs two classes
# that do nothing but pass the same widgets through.
# pylint: disable=too-many-lines

from __future__ import annotations

from typing import Optional

from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QScrollArea,
    QSplitter,
    QTabWidget,
    QLabel,
    QPushButton,
    QGraphicsDropShadowEffect,
    QGraphicsOpacityEffect,
    QFrame,
    QSizePolicy,
    QSpacerItem,
)
from PyQt6.QtCore import QTimer, Qt, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QAction, QColor, QKeySequence, QShortcut

from frontend.core.constants import (
    WINDOW_TITLE,
    WINDOW_W,
    WINDOW_H,
    WINDOW_MIN_W,
    WINDOW_MIN_H,
    ROSTER_REFRESH_FRAMES,
    TICK_MS,
    TICKS_PER_DAY,
    PHASE_ICONS,
    PHASE_LABELS,
    C_TEXT,
    C_TEXT_DIM,
    C_BG_PANEL,
    C_BG_PANEL2,
    C_GOLD_GLOW,
    C_RED,
    C_RED_GLOW,
    C_ACCENT,
    C_ACCENT2,
    C_ACCENT_GLOW,
    C_BORDER,
    SHADOW_BLUR,
    SHADOW_OFFSET,
)
from frontend.core.frontend_controller import FrontendController

from frontend.ui.zoo_scene import ZooScene
from frontend.ui.zoo_view import ZooGraphicsView
from frontend.ui.chat_view import ChatlogWidget
from frontend.ui.entity_info_panel import EntityInfoPanel
from frontend.ui.action_panel import ActionPanel
from frontend.ui.animal_list_panel import AnimalListPanel
from frontend.ui.shop_panel import ShopPanel
from frontend.ui.stats_panel import StatsPanel
from frontend.ui.status_chip import StatusChip
from frontend.ui.alert_banner import AlertBanner
from frontend.ui.help_dialog import SHORTCUTS, HelpDialog


_ALERT_MARGIN = 10  # inset of the alert overlay from the map's top-left
_ALERT_HEIGHT = 28


def _drop_shadow(
    widget: QWidget,
    blur: int = SHADOW_BLUR,
    dx: int = SHADOW_OFFSET[0],
    dy: int = SHADOW_OFFSET[1],
) -> None:
    """Apply a soft drop shadow to a widget for game-like depth.

    Args:
        widget: The widget that receives the effect.
        blur: Blur radius in pixels.
        dx: Horizontal shadow offset.
        dy: Vertical shadow offset.

    Returns:
        None.

    Tests:
        - test_effect_is_attached: Call on a fresh widget; verify
          graphicsEffect() is a QGraphicsDropShadowEffect.
        - test_blur_radius_applied: Call with blur=20; verify the effect
          reports that radius.
    """
    shadow = QGraphicsDropShadowEffect()
    shadow.setBlurRadius(blur)
    shadow.setOffset(dx, dy)
    shadow.setColor(QColor(0, 0, 0, 120))
    widget.setGraphicsEffect(shadow)


# Forty fields instead of the permitted seven. The window is the one place
# where every control comes together: eleven status chips, two control
# buttons, map, scene, four tabs, info card, chat, two overlays plus the
# selection and loop state. Splitting it would mean a second class that does
# nothing but pass the same widgets through.
# too-few-public-methods is a knock-on effect of ignored-modules=PyQt6 (see
# .pylintrc): without a resolvable Qt base, pylint does not count the
# inherited QMainWindow methods.
# pylint: disable-next=too-many-instance-attributes, too-few-public-methods
class ZooMainWindow(QMainWindow):
    """Top-level window: layout, signal routing and the render loop.

    Tests:
        - test_window_has_fixed_size: Create the window; verify its size is
          WINDOW_W × WINDOW_H.
        - test_tabs_contain_three_panels: Verify the tab widget holds the
          action, shop and statistics panels.
    """

    # The window's widget inventory, declared in one place. The values are
    # assigned by the _build_* steps, not by __init__ — building a Qt window
    # in one method would be a 200-line constructor. Declaring them here
    # keeps that split without hiding what the window is made of, and lets a
    # static checker see the attribute before its first use.
    _chip_day: StatusChip
    _chip_phase: StatusChip
    _chip_budget: StatusChip
    _chip_revenue: StatusChip
    _chip_expenses: StatusChip
    _chip_ticket: StatusChip
    _chip_open: StatusChip
    _chip_animals: StatusChip
    _chip_visitors: StatusChip
    _chip_enclosures: StatusChip
    _chip_action: StatusChip
    _btn_pause: QPushButton
    _btn_speed: QPushButton
    _lbl_status: QLabel
    _scene: ZooScene
    _view: ZooGraphicsView
    _tabs: QTabWidget
    _action_panel: ActionPanel
    _animal_list: AnimalListPanel
    _shop_panel: ShopPanel
    _stats_panel: StatsPanel
    _entity_info: EntityInfoPanel
    _chatlog: ChatlogWidget
    _alert_banner: AlertBanner
    _score_label: QLabel
    _score_opacity: QGraphicsOpacityEffect
    _shortcuts: list[QShortcut]

    def __init__(self, controller: FrontendController) -> None:
        """Build the UI, wire the signals and start the render timer.

        Args:
            controller: The FrontendController wrapping the engine.

        Returns:
            None (constructor).

        Tests:
            - test_timer_started: Create the window; verify the internal
              QTimer is active with the TICK_MS interval.
            - test_no_selection_initially: Verify both selection ids are
              None right after construction.
        """
        super().__init__()
        self._controller = controller
        self._selected_animal_id: Optional[str] = None
        self._hovered_animal_id: Optional[str] = None
        self._selected_enclosure_id: Optional[str] = None
        # Which sprite currently carries the glow — tracked separately from
        # the selection because the sprite may not exist yet (or any more).
        self._marked_animal_id: Optional[str] = None
        self._score_anim: Optional[QPropertyAnimation] = None
        self._last_action_msg: Optional[str] = None
        self._last_day = 0
        self._state: dict = {}
        self._frame = 0
        self._roster_ids: list[str] = []

        self.setWindowTitle(WINDOW_TITLE)
        # A minimum, not a fixed size: 1400×900 does not fit on a notebook
        # display, and a window larger than the screen cannot be resized back.
        self.setMinimumSize(WINDOW_MIN_W, WINDOW_MIN_H)
        self.resize(WINDOW_W, WINDOW_H)

        self._build_ui()
        self._connect_signals()

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(TICK_MS)

        self._action_msg_timer = QTimer(self)
        self._action_msg_timer.setSingleShot(True)
        self._action_msg_timer.timeout.connect(self._clear_action_message)

    # ── UI Construction ────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        """Assemble menu bar, top bar, map, right column and bottom bar.

        Returns:
            None.
        
        Tests:
            - test_central_widget_exists: Call it; verify centralWidget() is set.
            - test_score_label_starts_hidden: Call it; verify the floating feedback
              label is not visible.
        """
        self._build_menu()

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        root.addWidget(self._build_top_bar())
        root.addWidget(self._build_body(), stretch=1)
        root.addWidget(self._build_bottom_bar())

        # Floating action feedback overlay (hidden by default)
        self._score_label = QLabel(self._view)
        self._score_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._score_opacity = QGraphicsOpacityEffect(self._score_label)
        self._score_label.setGraphicsEffect(self._score_opacity)
        self._score_label.hide()

        # The alert strip is a child of the map view, not a row in the right
        # column: a banner that only appears now and then must not reserve
        # 36 px of a tight column forever — and over the map is where the eye
        # is anyway. Being a child means its geometry is set in pixels, so it
        # has to follow every resize; see _place_overlays.
        self._alert_banner = AlertBanner(self._view)
        self._place_overlays()

    def _place_overlays(self) -> None:
        """Re-fit the widgets that float over the map after a resize.

        The alert strip and the action popup are children of the map view
        with pixel geometry, not layout items. When the window is resized —
        which it now can be — nothing moves them unless this runs.

        Returns:
            None.

        Tests:
            - test_banner_spans_the_view: Resize the view to 500 px; verify
              the banner is 500 minus two margins wide.
            - test_popup_stays_centred: Show the popup, resize the window;
              verify it is still horizontally centred over the map.
            - test_safe_before_the_view_exists: Call during construction
              before the popup was built; verify no exception.
        """
        view = getattr(self, "_view", None)
        banner = getattr(self, "_alert_banner", None)
        if view is None or banner is None:
            return

        banner.setGeometry(
            _ALERT_MARGIN,
            _ALERT_MARGIN,
            max(0, view.width() - 2 * _ALERT_MARGIN),
            _ALERT_HEIGHT,
        )

        label = getattr(self, "_score_label", None)
        viewport = view.viewport()
        if label is not None and viewport is not None and label.isVisible():
            label.move(
                (viewport.width() - label.width()) // 2,
                viewport.height() // 4,
            )

    def _build_menu(self) -> None:
        """Create the menu bar with the file and help menus.

        The help menu is what makes the keyboard shortcuts discoverable —
        without it they exist but nobody finds them.

        Returns:
            None.

        Tests:
            - test_two_menus_exist: Call it; verify the menu bar holds a
              "Datei" and a "Hilfe" menu.
            - test_help_action_has_f1: Verify the shortcut of the help entry
              is F1.
        """
        menu_bar = self.menuBar()
        if menu_bar is None:  # only possible on a window without a menu bar
            return

        file_menu = menu_bar.addMenu("Datei")
        if file_menu is not None:
            quit_action = QAction("Beenden", self)
            quit_action.setShortcut(QKeySequence("Ctrl+Q"))
            quit_action.triggered.connect(self.close)
            file_menu.addAction(quit_action)

        help_menu = menu_bar.addMenu("Hilfe")
        if help_menu is not None:
            help_action = QAction("Tastenkürzel && Legende", self)
            help_action.setShortcut(QKeySequence("F1"))
            help_action.triggered.connect(self._show_help)
            help_menu.addAction(help_action)

    def _build_top_bar(self) -> QFrame:
        """Create the top bar with the clock, controls and finance chips.

        Returns:
            QFrame: The assembled bar widget.
        
        Tests:
            - test_bar_has_fixed_height: Verify the returned frame is 30 px high.
            - test_all_finance_chips_present: Verify the budget, revenue, expense
              and ticket chips were created.
        """
        top = QFrame()
        top.setObjectName("top_bar")
        top.setFixedHeight(30)
        top.setStyleSheet(
            f"#top_bar {{"
            f"  background: qlineargradient(x1:0,y1:0,x2:0,y2:1,"
            f"    stop:0 {C_BG_PANEL2}, stop:0.3 {C_BG_PANEL}, stop:1 {C_BG_PANEL});"
            f"  border-bottom: 1px solid {C_BORDER};"
            f"  border-radius: 8px;"
            f"}}"
        )
        layout = QHBoxLayout(top)
        layout.setContentsMargins(10, 2, 10, 2)
        layout.setSpacing(8)

        self._chip_day = StatusChip("📅 Tag", "1")
        layout.addWidget(self._chip_day)

        self._chip_phase = StatusChip("☀️", "—", C_GOLD_GLOW)
        layout.addWidget(self._chip_phase)

        self._btn_pause = self._make_pause_button()
        layout.addWidget(self._btn_pause)

        self._btn_speed = self._make_speed_button()
        layout.addWidget(self._btn_speed)

        layout.addSpacerItem(
            QSpacerItem(0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        )

        self._chip_budget = StatusChip("💰", "0 €", C_GOLD_GLOW)
        layout.addWidget(self._chip_budget)

        self._chip_revenue = StatusChip("💵", "0 €", C_ACCENT_GLOW)
        layout.addWidget(self._chip_revenue)

        self._chip_expenses = StatusChip("💸", "0 €", C_RED_GLOW)
        layout.addWidget(self._chip_expenses)

        self._chip_ticket = StatusChip("🎫", "0 €")
        layout.addWidget(self._chip_ticket)

        self._chip_open = StatusChip("🔓", "OFFEN", C_ACCENT_GLOW)
        layout.addWidget(self._chip_open)

        return top

    def _build_body(self) -> QWidget:
        """Create the map view and the right-hand column, joined by a splitter.

        The two halves sit in a :class:`QSplitter` so the user can decide how
        much of the width the map gets. Each tab's content is wrapped in a
        scroll area: the shop panel alone asks for 490 px of height, and
        without a scroll area that single number would set the floor for the
        whole window.

        Returns:
            QWidget: The splitter holding both halves.

        Tests:
            - test_view_and_tabs_created: Call it; verify the map view and the
              tab widget exist.
            - test_splitter_holds_two_halves: Verify the returned splitter has
              exactly two children and neither may collapse.
            - test_right_column_width_is_bounded: Verify the right half stays
              between 340 and 460 px wide.
        """
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(8)
        # Collapsing either half would leave a window that looks broken and
        # offers no obvious way back.
        splitter.setChildrenCollapsible(False)

        self._scene = ZooScene()
        self._view = ZooGraphicsView(self._scene)
        splitter.addWidget(self._view)

        right_col = QVBoxLayout()
        right_col.setContentsMargins(0, 0, 0, 0)
        right_col.setSpacing(8)

        self._tabs = QTabWidget()
        self._tabs.setMinimumHeight(200)
        self._tabs.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding
        )
        # Shorten the captions when the column is narrow. Qt's default is to
        # show scroll arrows instead, which hides whole tabs behind a chevron
        # — an elided "📊 Stat…" is still a tab you can see and hit.
        self._tabs.setElideMode(Qt.TextElideMode.ElideRight)

        self._action_panel = ActionPanel()
        self._animal_list = AnimalListPanel()
        self._shop_panel = ShopPanel()
        self._stats_panel = StatsPanel()
        for panel, caption in (
            (self._action_panel, "🎮 Aktionen"),
            (self._animal_list, "🐾 Tiere"),
            (self._shop_panel, "🛒 Shop"),
            (self._stats_panel, "📊 Statistik"),
        ):
            self._tabs.addTab(self._scrollable(panel), caption)
        right_col.addWidget(self._tabs, stretch=2)

        self._entity_info = EntityInfoPanel()
        right_col.addWidget(self._entity_info)

        self._chatlog = ChatlogWidget()
        right_col.addWidget(self._chatlog, stretch=1)

        right_w = QWidget()
        right_w.setLayout(right_col)
        right_w.setMinimumWidth(340)
        right_w.setMaximumWidth(460)
        splitter.addWidget(right_w)

        # The map takes the growth, the panel column keeps its width.
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 0)

        _drop_shadow(self._tabs)
        _drop_shadow(self._entity_info)
        _drop_shadow(self._chatlog)

        return splitter

    @staticmethod
    def _scrollable(panel: QWidget) -> QScrollArea:
        """Wrap a panel so it can be scrolled instead of forcing the layout.

        Without this, the tallest tab decides the window's minimum height —
        the shop panel asked for 490 px and pushed the total past the screen.
        The area is transparent and frameless on purpose: a default
        ``QScrollArea`` paints its own light viewport and draws a white box
        over the tab background.

        Args:
            panel: The panel widget to wrap.

        Returns:
            QScrollArea: The wrapper to hand to the tab widget.

        Tests:
            - test_panel_is_the_scroll_widget: Wrap a panel; verify widget()
              returns that panel.
            - test_wrapper_is_transparent: Wrap a panel; verify the stylesheet
              asks for a transparent background and no frame.
            - test_minimum_height_drops: Compare the panel's own minimum with
              the wrapper's; verify the wrapper asks for less.
        """
        area = QScrollArea()
        area.setWidget(panel)
        area.setWidgetResizable(True)
        area.setFrameShape(QFrame.Shape.NoFrame)
        area.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }"
            "QScrollArea > QWidget > QWidget { background: transparent; }"
        )
        viewport = area.viewport()
        if viewport is not None:
            viewport.setAutoFillBackground(False)
        return area

    def _build_bottom_bar(self) -> QFrame:
        """Create the bottom bar with population and feedback chips.

        Returns:
            QFrame: The assembled bar widget.
        
        Tests:
            - test_status_label_present: Verify the status label was created.
            - test_population_chips_present: Verify the animal, visitor and
              enclosure chips exist.
        """
        bottom = QFrame()
        bottom.setObjectName("bot_bar")
        bottom.setFixedHeight(30)
        bottom.setStyleSheet(
            f"#bot_bar {{"
            f"  background: qlineargradient(x1:0,y1:0,x2:0,y2:1,"
            f"    stop:0 {C_BG_PANEL}, stop:0.7 {C_BG_PANEL2}, stop:1 {C_BG_PANEL});"
            f"  border-top: 1px solid {C_BORDER};"
            f"  border-radius: 8px;"
            f"}}"
        )
        layout = QHBoxLayout(bottom)
        layout.setContentsMargins(10, 2, 10, 2)
        layout.setSpacing(8)

        self._lbl_status = QLabel("🟢 Bereit")
        self._lbl_status.setStyleSheet(
            f"color: {C_TEXT}; background: transparent; border: none; "
            "font-size: 11px; font-weight: 600;"
        )
        layout.addWidget(self._lbl_status)

        layout.addSpacerItem(
            QSpacerItem(0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        )

        self._chip_animals = StatusChip("🐾 Tiere", "0 / 0 tot", C_ACCENT_GLOW)
        layout.addWidget(self._chip_animals)

        self._chip_visitors = StatusChip("👥 Besucher", "0", C_GOLD_GLOW)
        layout.addWidget(self._chip_visitors)

        self._chip_enclosures = StatusChip("🏠 Gehege", "0")
        layout.addWidget(self._chip_enclosures)

        self._chip_action = StatusChip("📋", "—", C_TEXT_DIM)
        layout.addWidget(self._chip_action)

        return bottom

    def _make_pause_button(self) -> QPushButton:
        """Create the pause/resume button.

        Returns:
            QPushButton: The styled, connected button.
        
        Tests:
            - test_button_starts_in_running_style: Verify the label reads
              "⏸ Pause".
            - test_click_is_connected: Click the button; verify the controller
              reports paused == True.
        """
        btn = QPushButton("⏸ Pause")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFixedHeight(24)
        btn.setStyleSheet(self._pause_qss(running=True))
        btn.clicked.connect(self._toggle_pause)
        return btn

    def _make_speed_button(self) -> QPushButton:
        """Create the speed-cycle button.

        Returns:
            QPushButton: The styled, connected button.
        
        Tests:
            - test_button_starts_at_one: Verify the label reads "🏃 1×".
            - test_click_cycles_speed: Click once; verify the controller speed is
              SPEED_STEPS[1].
        """
        btn = QPushButton("🏃 1×")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFixedHeight(24)
        btn.setToolTip("Simulationsgeschwindigkeit umschalten")
        btn.setStyleSheet(
            f"QPushButton {{ background: transparent; border: 1px solid {C_BORDER};"
            f"  color: {C_TEXT}; border-radius: 6px; padding: 2px 10px;"
            f"  font-size: 11px; font-weight: 700; }}"
            f"QPushButton:hover {{ border: 1px solid {C_ACCENT_GLOW}; color: #fff; }}"
        )
        btn.clicked.connect(self._cycle_speed)
        return btn

    @staticmethod
    def _pause_qss(running: bool) -> str:
        """Return the pause button stylesheet for the given run state.

        Args:
            running: True while the simulation is advancing.

        Returns:
            str: A QSS snippet — green while running, red while paused.
        
        Tests:
            - test_running_style_is_green: Call with running=True; verify the
              snippet contains the accent colour.
            - test_paused_style_is_red: Call with running=False; verify the
              snippet contains the red colour.
        """
        top = C_ACCENT_GLOW if running else C_RED_GLOW
        bottom = C_ACCENT if running else C_RED
        hover_top = C_ACCENT if running else C_RED_GLOW
        hover_bottom = C_ACCENT2 if running else C_RED
        return (
            f"QPushButton {{"
            f"  background: qlineargradient(x1:0,y1:0,x2:0,y2:1,"
            f"    stop:0 {top}, stop:1 {bottom});"
            f"  border: 1px solid {top}; color: #fff; border-radius: 6px;"
            f"  padding: 2px 12px; font-weight: bold; font-size: 11px;"
            f"}}"
            f"QPushButton:hover {{"
            f"  background: qlineargradient(x1:0,y1:0,x2:0,y2:1,"
            f"    stop:0 {hover_top}, stop:1 {hover_bottom});"
            f"  border: 1px solid #fff;"
            f"}}"
        )

    # ── Signal Wiring ──────────────────────────────────────────────────────

    def _connect_signals(self) -> None:
        """Connect every panel and map signal to its handler.

        Returns:
            None.
        
        Tests:
            - test_enclosure_callbacks_registered: Call it; verify clicking an
              enclosure item selects it.
            - test_shop_signals_routed: Emit buy_food from the shop panel; verify
              execute_action was called with type and amount.
        """
        for enclosure in self._scene.enclosures.values():
            enclosure.set_click_callback(self._on_enclosure_selected)
        self._view.map_clicked.connect(self._on_map_clicked)
        # The overlays are pixel-positioned children of the view, so they
        # have to be told whenever the splitter or the window resizes it.
        self._view.resized.connect(self._place_overlays)
        # The signal carries (action, kwargs-dict). Connecting it straight to
        # _dispatch(action, **kwargs) makes PyQt drop the dict, because that
        # slot accepts only one positional argument — every selection-bound
        # action then reached the backend with animal_id/enclosure_id = None.
        self._action_panel.action_triggered.connect(
            lambda action, params: self._dispatch(action, **(params or {}))
        )
        self._shop_panel.buy_food.connect(
            lambda food_type, amount: self._dispatch(
                "buy_food", type=food_type, amount=amount
            )
        )
        self._shop_panel.buy_animal.connect(
            lambda species, name, enclosure_id: self._dispatch(
                "buy_animal", species=species, name=name, enclosure_id=enclosure_id
            )
        )
        # A roster row and a sprite are two doors into the same selection.
        self._animal_list.animal_selected.connect(self._on_animal_selected)
        self._wire_sprite_callbacks()
        self._register_shortcuts()
        self._setup_accessibility()

    def _setup_accessibility(self) -> None:
        """Name every control for screen readers and order the focus chain.

        Two things a mouse user never notices and a keyboard user cannot work
        around: a button whose accessible name is its emoji, and a Tab key
        that jumps from the pause button into the map instead of into the
        panels. The chips get names too — their caption is an icon, which a
        screen reader either skips or reads as "pile of poo".

        Returns:
            None.

        Tests:
            - test_every_chip_has_a_name: Call it; verify no chip reports an
              empty accessibleName.
            - test_tab_order_starts_at_the_controls: Press Tab from the pause
              button; verify the speed button gets focus.
            - test_map_is_named: Verify the graphics view has an accessible
              name so it is announced as the zoo map.
        """
        for chip, name in (
            (self._chip_day, "Spieltag"),
            (self._chip_phase, "Tageszeit"),
            (self._chip_budget, "Budget"),
            (self._chip_revenue, "Einnahmen"),
            (self._chip_expenses, "Ausgaben"),
            (self._chip_ticket, "Ticketpreis"),
            (self._chip_open, "Zoo geöffnet"),
            (self._chip_animals, "Tierbestand"),
            (self._chip_visitors, "Besucher"),
            (self._chip_enclosures, "Gehege"),
            (self._chip_action, "Letzte Aktion"),
        ):
            chip.setAccessibleName(name)

        self._btn_pause.setAccessibleName("Simulation anhalten oder fortsetzen")
        self._btn_speed.setAccessibleName("Simulationsgeschwindigkeit")
        self._tabs.setAccessibleName("Bereiche: Aktionen, Tiere, Shop, Statistik")
        self._lbl_status.setAccessibleName("Statuszeile")

        # Controls first, then the panels, then the map — the order in which
        # someone actually works, not the order the widgets were created in.
        self.setTabOrder(self._btn_pause, self._btn_speed)
        self.setTabOrder(self._btn_speed, self._tabs)
        self.setTabOrder(self._tabs, self._entity_info)
        self.setTabOrder(self._entity_info, self._chatlog)
        self.setTabOrder(self._chatlog, self._view)

    def _register_shortcuts(self) -> None:
        """Bind every entry of ``help_dialog.SHORTCUTS`` to its handler.

        The key sequences are read from the same tuple the help dialog
        prints, so a shortcut cannot exist undocumented and a documented
        shortcut cannot be missing. Tab keys are generated from the tab
        widget itself for the same reason.

        Returns:
            None.

        Tests:
            - test_every_shortcut_is_bound: Call it; verify one QShortcut
              exists per SHORTCUTS entry plus one per tab.
            - test_space_toggles_pause: Trigger the Space shortcut; verify
              the controller reports paused == True.
            - test_unknown_action_is_skipped: Add an entry with an unknown
              action name; verify no exception and no binding.
        """
        handlers = {
            "pause": self._toggle_pause,
            "speed": self._cycle_speed,
            "feed_all": lambda: self._dispatch("feed_all"),
            "feed_one": lambda: self._dispatch_selected("feed_one"),
            "heal": lambda: self._dispatch_selected("heal"),
            "clean": self._clean_selected,
            "deselect": lambda: self._on_map_clicked(0.0, 0.0),
            "help": self._show_help,
        }
        self._shortcuts: list[QShortcut] = []
        for keys, action, _text in SHORTCUTS:
            handler = handlers.get(action)
            if handler is None:  # "tabs" is generated below, not bound here
                continue
            shortcut = QShortcut(QKeySequence(keys), self)
            shortcut.activated.connect(handler)
            self._shortcuts.append(shortcut)

        for index in range(self._tabs.count()):
            shortcut = QShortcut(QKeySequence(str(index + 1)), self)
            shortcut.activated.connect(
                lambda checked_index=index: self._tabs.setCurrentIndex(checked_index)
            )
            self._shortcuts.append(shortcut)

    def _wire_sprite_callbacks(self) -> None:
        """Re-attach the hover callbacks after each sprite batch.

        Returns:
            None.
        
        Tests:
            - test_new_sprites_get_callbacks: Add an animal, run a frame; verify
              its hover callback is set.
            - test_rewiring_is_idempotent: Call twice; verify hovering still fires
              the handler exactly once.
            - test_recreated_sprite_keeps_glow: Remove and re-add the selected
              animal; verify its new sprite carries the selection glow again.
        """
        for animal_id, sprite in self._scene.animals.items():
            sprite.set_hover_callback(self._on_hover)
            sprite.set_unhover_callback(self._on_unhover)
            sprite.set_click_callback(self._on_animal_selected)
            # Self-healing: a sprite recreated after the animal briefly left
            # the snapshot would otherwise come back without its marker.
            sprite.set_selected(animal_id == self._selected_animal_id)

    # ── Tick Loop ──────────────────────────────────────────────────────────

    def _tick(self) -> None:
        """Advance the simulation, poll the snapshot and render one frame.

        Returns:
            None.

        Tests:
            - test_tick_polls_state: Mock the controller; call _tick();
              verify get_state() was called exactly once.
            - test_tick_skips_render_without_state: Return {} from the
              controller; verify no panel update is attempted.
        """
        self._frame += 1
        self._controller.advance_tick()
        state = self._controller.get_state()
        if not state:
            return
        self._state = state
        self._reconcile_selection(state)
        self._update_sprites(state)
        self._update_labels(state)
        self._update_panels(state)
        self._refresh_info_panel()

        messages = self._controller.get_chat_messages()
        if messages:
            self._chatlog.append_messages(
                messages, int((state.get("system") or {}).get("tick_count", 0))
            )
            if self._alert_banner.push(messages):
                self._alert_banner.raise_()
        # Counted in render frames, not milliseconds, so an alert lives as
        # long on screen at 5× speed as the situation behind it does.
        self._alert_banner.tick()

    def _reconcile_selection(self, state: dict) -> None:
        """Drop a selection whose entity no longer exists in the snapshot.

        Animals leave the snapshot when the backend removes them (the zoo
        deletes an animal from its enclosure in the same tick it dies).
        Without this reconciliation the info panel would keep showing a
        gone animal and the action buttons would stay enabled for it.

        Args:
            state: The enriched snapshot of the current frame.

        Returns:
            None.

        Tests:
            - test_clears_gone_animal: Select an animal, then pass a
              snapshot without it; verify the selection is None.
            - test_keeps_present_animal: Pass a snapshot that still holds
              the selected animal; verify the selection survives.
        """
        if self._selected_animal_id is None and self._hovered_animal_id is None:
            return
        alive_ids = {a.get("id") for a in state.get("animals_on_map") or []}
        if self._selected_animal_id not in alive_ids:
            self._selected_animal_id = None
            self._marked_animal_id = None  # its sprite is gone with it
        if self._hovered_animal_id not in alive_ids:
            self._hovered_animal_id = None

    # ── Update Helpers ─────────────────────────────────────────────────────

    def _update_sprites(self, state: dict) -> None:
        """Push the snapshot into the scene and update the day lighting.

        Args:
            state: The enriched snapshot.

        Returns:
            None.
        
        Tests:
            - test_scene_receives_state: Call with a snapshot; verify the scene
              created the matching sprites.
            - test_lighting_follows_phase: Call with time_of_day="NIGHT"; verify
              the scene phase is NIGHT.
        """
        self._scene.update_entities(state)
        system = state.get("system") or {}
        self._scene.apply_lighting(
            str(system.get("time_of_day", "")), bool(system.get("zoo_open", True))
        )
        self._wire_sprite_callbacks()

    def _update_labels(self, state: dict) -> None:
        """Update every top-bar and bottom-bar chip from the snapshot.

        Split into three groups — clock, money, population — because the
        chips fall into exactly those three, and one method that touches
        eleven widgets is one method nobody reads to the end.

        Args:
            state: The enriched snapshot.

        Returns:
            None.

        Tests:
            - test_status_line_reports_the_live_summary: Pass two animals
              and one visitor; verify the status line names both counts.
            - test_day_change_refreshes_the_statistics: Pass a snapshot one
              day later; verify the statistics panel was refreshed once and
              the tab caption carries the day count.
            - test_running_action_message_survives_a_frame: Dispatch an
              action, then render a frame; verify the status line still
              shows the action result instead of the live summary.
        """
        system = state.get("system") or {}
        visitors = state.get("visitors_on_map") or []

        day = self._update_clock_chips(system)
        self._update_finance_chips(
            state.get("finances") or {}, bool(system.get("zoo_open", True))
        )
        alive = self._update_population_chips(
            state.get("animals_on_map") or [],
            visitors,
            state.get("enclosures_on_map") or [],
        )

        if self._last_action_msg is None:
            self._lbl_status.setText(
                f"⏸ Pausiert — Tag {day}"
                if self._controller.paused
                else f"🟢 Tag {day} — {alive} Tiere, {len(visitors)} Besucher"
            )

        if day != self._last_day:
            self._last_day = day
            self._stats_panel.refresh(self._controller.get_stats())
            closed = self._stats_panel.day_count
            self._tabs.setTabText(
                3, f"📊 Statistik ({closed})" if closed else "📊 Statistik"
            )

    def _update_clock_chips(self, system: dict) -> int:
        """Write the day number and the in-game clock into their chips.

        Args:
            system: The snapshot's ``system`` block.

        Returns:
            int: The current day number, 1-based — the caller needs it for
            the status line and the day-change check.

        Tests:
            - test_returns_the_day_number: Pass tick_count=480; verify the
              return value is 2.
            - test_phase_chip_uses_german_label: Pass time_of_day="NIGHT";
              verify the chip reads "Nacht".
            - test_unknown_phase_falls_back_to_a_clock_icon: Pass an unknown
              phase; verify the chip icon is the neutral clock.
        """
        ticks = int(system.get("tick_count", 0))
        day = ticks // TICKS_PER_DAY + 1
        self._chip_day.set_value(str(day))

        phase = str(system.get("time_of_day", ""))
        minutes = self.clock_minutes(ticks)
        self._chip_phase.set_icon(PHASE_ICONS.get(phase, "🕐"))
        self._chip_phase.set_value(
            f"{PHASE_LABELS.get(phase, phase or '—')} {minutes // 60:02d}:"
            f"{minutes % 60:02d}"
        )
        return day

    def _update_finance_chips(self, finances: dict, zoo_open: bool) -> None:
        """Write budget, revenue, expenses, ticket price and the open sign.

        Args:
            finances: The snapshot's ``finances`` block.
            zoo_open: The snapshot's ``system.zoo_open`` flag.

        Returns:
            None.

        Tests:
            - test_budget_chip_turns_red_when_broke: Pass money=100; verify
              the budget chip uses the red accent.
            - test_rich_zoo_gets_the_green_accent: Pass money=9000; verify
              the budget chip uses the accent colour.
            - test_closed_zoo_shows_a_lock: Pass zoo_open=False; verify the
              chip reads "GESCHL." behind a closed padlock.
        """
        money = float(finances.get("money", 0))
        if money >= 5_000:
            self._chip_budget.set_accent(C_ACCENT_GLOW)
        elif money >= 1_000:
            self._chip_budget.set_accent(C_GOLD_GLOW)
        else:
            self._chip_budget.set_accent(C_RED_GLOW)
        self._chip_budget.set_value(f"{money:,.0f} €".replace(",", "."))

        self._chip_revenue.set_value(
            f'{float(finances.get("revenue", 0)):,.0f} €'.replace(",", ".")
        )
        self._chip_expenses.set_value(
            f'{float(finances.get("expenses", 0)):,.0f} €'.replace(",", ".")
        )
        self._chip_ticket.set_value(f'{float(finances.get("ticket_price", 0)):.2f} €')

        if zoo_open:
            self._chip_open.set_accent(C_ACCENT_GLOW)
            self._chip_open.set_value("OFFEN")
            self._chip_open.set_icon("🔓")
        else:
            self._chip_open.set_accent(C_RED_GLOW)
            self._chip_open.set_value("GESCHL.")
            self._chip_open.set_icon("🔒")

    def _update_population_chips(
        self, animals: list, visitors: list, enclosures: list
    ) -> int:
        """Write the animal, visitor and enclosure chips of the bottom bar.

        Args:
            animals: The snapshot's ``animals_on_map`` list.
            visitors: The snapshot's ``visitors_on_map`` list.
            enclosures: The snapshot's ``enclosures_on_map`` list.

        Returns:
            int: How many animals are alive — the status line reports it.

        Tests:
            - test_returns_the_living_count: Pass two living and one dead
              animal; verify the return value is 2.
            - test_empty_zoo_turns_the_chip_red: Pass no animals; verify the
              animal chip uses the red accent.
            - test_enclosure_chip_reports_occupancy: Pass one enclosure with
              capacity 5 and 3 occupied; verify the chip reads "1 · 3/5".
        """
        # The backend removes an animal from its enclosure in the same tick
        # it dies, so animals_on_map effectively never carries is_dead=True.
        # The chip therefore reports the living population and the capacity
        # it occupies, not a death counter that would always read zero.
        alive = sum(1 for a in animals if not a.get("is_dead"))
        dead = sum(1 for a in animals if a.get("is_dead"))
        capacity = sum(int(e.get("capacity", 0)) for e in enclosures)
        if dead > 0:
            self._chip_animals.set_accent(C_GOLD_GLOW)
        elif alive == 0:
            self._chip_animals.set_accent(C_RED_GLOW)
        else:
            self._chip_animals.set_accent(C_ACCENT_GLOW)
        label = f"{alive}" + (f" (+{dead} tot)" if dead else "")
        self._chip_animals.set_value(
            f"{label} / {capacity}" if capacity else label
        )

        self._chip_visitors.set_value(str(len(visitors)))

        occupied = sum(int(e.get("occupied", 0)) for e in enclosures)
        self._chip_enclosures.set_value(
            f"{len(enclosures)} · {occupied}/{capacity}" if enclosures else "0"
        )
        return alive

    @staticmethod
    def clock_minutes(ticks: int) -> int:
        """Convert a tick number into minutes since midnight of that day.

        The backend starts its day at ``MORNING`` (tick 0) and advances one
        phase every 120 ticks. Anchoring tick 0 at 00:00 would therefore
        label 06:00 as "Mittag". The clock is shifted by a quarter day so
        MORNING covers 06:00–11:59, NOON 12:00–17:59, EVENING 18:00–23:59
        and NIGHT 00:00–05:59.

        Args:
            ticks: The backend's raw ``tick_count``.

        Returns:
            int: Minutes since midnight, 0–1439.

        Tests:
            - test_tick_zero_is_six_am: clock_minutes(0) returns 360.
            - test_noon_phase_starts_at_twelve: clock_minutes(120) returns
              720, matching the backend's NOON boundary.
            - test_wraps_within_a_day: clock_minutes(479) stays below 1440.
        """
        into_day = (ticks % TICKS_PER_DAY) * (24 * 60 // TICKS_PER_DAY)
        return (into_day + 360) % 1440

    def _update_panels(self, state: dict, force_roster: bool = False) -> None:
        """Forward the snapshot to the action, shop and roster panels.

        Args:
            state: The enriched snapshot.
            force_roster: Refresh the roster even if the throttle would skip
                this frame — used when the selection changed and the table
                has to mirror it right away.

        Returns:
            None.

        Tests:
            - test_action_panel_updated: Call it; verify the action panel received
              the current selection.
            - test_shop_panel_updated: Call it with an inventory; verify the shop
              label shows those amounts.
            - test_roster_shows_every_animal: Call it with two animals; verify
              the roster tab caption reports two.
            - test_roster_is_throttled: Call it five times with an unchanged
              animal set; verify get_animal_details ran only once.
            - test_new_animal_refreshes_immediately: Call it with an extra
              animal mid-throttle; verify the roster updated in that frame.
        """
        self._action_panel.update_state(
            state, self._selected_animal_id, self._selected_enclosure_id
        )
        self._shop_panel.update_state(state)
        self._refresh_roster(state, force=force_roster)

    def _refresh_roster(self, state: dict, force: bool = False) -> None:
        """Rebuild the animal roster, but not on every single frame.

        Each roster row needs one ``get_entity_info()`` call, so refreshing
        it ten times a second means ten calls per animal per second for a
        table nobody reads that fast. The values are therefore updated every
        ``ROSTER_REFRESH_FRAMES`` frames — while a *changed set* of animals
        (one bought, one died) still shows up in the very next frame,
        because that comparison is free: the ids are already in the snapshot.

        Args:
            state: The enriched snapshot of this frame.
            force: Bypass the throttle, e.g. after a selection change.

        Returns:
            None.

        Tests:
            - test_skips_intermediate_frames: Call five times unchanged;
              verify the controller was queried once.
            - test_reacts_to_a_new_animal_at_once: Add an animal between two
              calls; verify the roster refreshed without waiting.
            - test_force_bypasses_the_throttle: Call twice with force=True;
              verify both refreshed.
        """
        ids = [str(a.get("id", "")) for a in state.get("animals_on_map") or []]
        due = self._frame % ROSTER_REFRESH_FRAMES == 0
        if not (force or due or ids != self._roster_ids):
            return

        self._roster_ids = ids
        animals = self._controller.get_animal_details(state)
        self._animal_list.refresh(animals, self._selected_animal_id)
        self._tabs.setTabText(1, f"🐾 Tiere ({len(animals)})")

    def _refresh_info_panel(self) -> None:
        """Show whichever entity is currently selected, or the placeholder.

        Returns:
            None.
        
        Tests:
            - test_animal_selection_shows_animal_form: Select an animal; verify
              the animal form is visible.
            - test_enclosure_selection_shows_enclosure_form: Select an enclosure;
              verify the enclosure form is visible.
            - test_no_selection_shows_placeholder: Clear both selections; verify
              the placeholder is shown.
        """
        animal_id = self._hovered_animal_id or self._selected_animal_id
        if animal_id:
            self._entity_info.show_entity(self._controller.get_entity_info(animal_id))
        elif self._selected_enclosure_id:
            self._entity_info.show_enclosure(
                self._enclosure_entry(self._selected_enclosure_id)
            )
        else:
            self._entity_info.clear()

    def _enclosure_entry(self, enclosure_id: str) -> dict | None:
        """Return the enriched snapshot entry for one enclosure.

        Prefers the cached ``enclosures_on_map`` entry (it carries the
        capacity as well) and falls back to the backend's raw hover payload
        before the first frame has been rendered.

        Args:
            enclosure_id: The enclosure id to look up.

        Returns:
            dict | None: The enclosure data, or None when unknown.

        Tests:
            - test_uses_cached_entry: Render one frame, then look up
              "e_01"; verify the result carries a "capacity" key.
            - test_falls_back_to_engine: Look up before the first frame;
              verify get_entity_info was queried instead.
        """
        for entry in self._state.get("enclosures_on_map") or []:
            if entry.get("id") == enclosure_id:
                return entry
        return self._controller.get_entity_info(enclosure_id)

    # ── Hover / Click ──────────────────────────────────────────────────────

    def _on_hover(self, entity_id: str) -> None:
        """Preview the hovered animal in the info panel.

        Hovering is deliberately only a preview: the pointer has to travel
        to the action buttons in the right column, which fires
        hoverLeaveEvent on the way. If hovering set the selection, both
        selection-bound actions would disable themselves before the click
        ever landed. Clicking is what pins an animal — see
        :meth:`_on_animal_selected`.

        Args:
            entity_id: The animal id reported by the sprite.

        Returns:
            None.

        Tests:
            - test_hover_fetches_entity_info: Call with "a_01"; verify
              get_entity_info("a_01") was requested.
            - test_hover_does_not_pin: Hover an animal without clicking;
              verify _selected_animal_id stays None.
        """
        self._hovered_animal_id = entity_id
        self._refresh_info_panel()

    def _on_unhover(self) -> None:
        """Drop the preview and fall back to whatever is pinned.

        Returns:
            None.

        Tests:
            - test_unhover_clears_preview: Hover then unhover; verify the
              hovered id is None.
            - test_unhover_keeps_clicked_animal: Click an animal, hover a
              second one, unhover; verify the clicked one is shown again.
        """
        self._hovered_animal_id = None
        self._refresh_info_panel()

    def _on_animal_selected(self, entity_id: str) -> None:
        """Pin an animal as the selection for the action buttons.

        Reached from two places that must not disagree: a click on the
        sprite and a click on a roster row.

        Args:
            entity_id: The animal id reported by the sprite or the roster.

        Returns:
            None.

        Tests:
            - test_click_enables_heal: Click a living animal; verify the
              heal button becomes enabled and stays enabled after the
              pointer leaves the sprite.
            - test_click_clears_enclosure_selection: Click an animal while
              an enclosure is selected; verify the enclosure is deselected.
            - test_roster_click_marks_sprite: Select from the roster; verify
              the animal's sprite carries the selection glow.
        """
        self._selected_animal_id = entity_id
        self._selected_enclosure_id = None
        self._mark_selected_sprite(entity_id)
        self._refresh_info_panel()
        if self._state:
            self._update_panels(self._state, force_roster=True)

    def _mark_selected_sprite(self, entity_id: str | None) -> None:
        """Move the selection glow to the given animal's sprite.

        Args:
            entity_id: The newly selected animal id, or None to clear the
                marker entirely.

        Returns:
            None.

        Tests:
            - test_previous_sprite_is_unmarked: Select two animals in turn;
              verify only the second one carries the glow.
            - test_missing_sprite_is_tolerated: Select an id whose sprite was
              already removed; verify no exception is raised.
        """
        if self._marked_animal_id == entity_id:
            return
        previous = self._scene.animal_sprite(self._marked_animal_id or "")
        if previous is not None:
            previous.set_selected(False)
        current = self._scene.animal_sprite(entity_id or "")
        if current is not None:
            current.set_selected(True)
        self._marked_animal_id = entity_id if current is not None else None

    def _on_enclosure_selected(self, enclosure_id: str) -> None:
        """Select an enclosure and show its backend details.

        Args:
            enclosure_id: The clicked enclosure id.

        Returns:
            None.

        Tests:
            - test_selection_enables_clean_button: Select "e_01"; verify the
              action panel's clean button becomes enabled.
            - test_selection_shows_enclosure_form: Select "e_01"; verify the
              info panel switches to the enclosure form.
        """
        self._selected_enclosure_id = enclosure_id
        self._selected_animal_id = None
        self._hovered_animal_id = None
        self._mark_selected_sprite(None)
        self._refresh_info_panel()
        if self._state:
            self._update_panels(self._state, force_roster=True)

    def _on_map_clicked(self, _x: float, _y: float) -> None:
        """Clear every selection when empty map space is clicked.

        Args:
            _x: Scene x coordinate — unused, required by the signal.
            _y: Scene y coordinate — unused, required by the signal.

        Returns:
            None.

        Tests:
            - test_click_clears_selection: Select an enclosure, click empty
              space; verify both selection ids are None.
            - test_click_shows_placeholder: Click empty space; verify the
              info panel shows the placeholder.
        """
        self._selected_animal_id = None
        self._hovered_animal_id = None
        self._selected_enclosure_id = None
        self._mark_selected_sprite(None)
        self._refresh_info_panel()
        if self._state:
            self._update_panels(self._state, force_roster=True)

    # ── God-mode Dispatch ──────────────────────────────────────────────────

    def _dispatch(self, action: str, **kwargs: object) -> None:
        """Run a God-mode action and surface its result in the UI.

        Args:
            action: The backend action name.
            **kwargs: Action-specific parameters.

        Returns:
            None.

        Tests:
            - test_dispatch_forwards_to_controller: Call with "feed_all";
              verify execute_action("feed_all") was called.
            - test_failed_action_shows_cross: Return success=False; verify
              the feedback chip starts with "❌".
        """
        result = self._controller.execute_action(action, **kwargs)
        message = result.get("message", "")
        success = result.get("success", False)

        icon = "✅" if success else "❌"
        self._chip_action.set_value(f"{icon} {message}" if message else f"{icon} {action}")
        self._chip_action.set_accent(C_ACCENT_GLOW if success else C_RED_GLOW)
        self._lbl_status.setText(f"{icon} {message}" if message else f"{icon} {action}")
        self._last_action_msg = message or None
        # One owned, restartable timer — a fresh QTimer.singleShot per action
        # could not be cancelled, so an older action's timer would wipe a
        # newer message before its own five seconds were up.
        self._action_msg_timer.start(5000)

        entries = result.get("chat_entries", [])
        if entries:
            self._chatlog.append_messages(
                entries, int((self._state.get("system") or {}).get("tick_count", 0))
            )

        if success:
            self._show_score_popup(action, message)

    def _dispatch_selected(self, action: str) -> None:
        """Run a selection-bound action from a keyboard shortcut.

        The buttons carry the same guard through their enabled state; the
        shortcuts need it explicitly, because a key press does not know
        whether anything is selected.

        Args:
            action: "feed_one" or "heal".

        Returns:
            None.

        Tests:
            - test_runs_with_selection: Select an animal, call with "heal";
              verify execute_action received that animal_id.
            - test_hints_without_selection: Call with no selection; verify
              the status line asks the user to pick an animal and no action
              was sent.
        """
        if self._selected_animal_id is None:
            self._lbl_status.setText("ℹ️ Erst ein Tier auswählen (Karte oder Tab 2).")
            return
        self._dispatch(action, animal_id=self._selected_animal_id)

    def _clean_selected(self) -> None:
        """Clean the selected enclosure from a keyboard shortcut.

        Returns:
            None.

        Tests:
            - test_cleans_the_selected_enclosure: Select "e_01", call it;
              verify execute_action("clean", enclosure_id="e_01") was sent.
            - test_hints_without_an_enclosure: Call with no enclosure
              selected; verify the status line explains what is missing.
        """
        if self._selected_enclosure_id is None:
            self._lbl_status.setText("ℹ️ Erst ein Gehege anklicken.")
            return
        self._dispatch("clean", enclosure_id=self._selected_enclosure_id)

    def _show_help(self) -> None:
        """Open the modal shortcut and legend dialog.

        Returns:
            None.

        Tests:
            - test_dialog_is_created: Call it with the dialog patched;
              verify a HelpDialog was constructed with this window as parent.
            - test_can_be_opened_twice: Call it twice; verify no exception
              and no leftover dialog from the first call.
        """
        HelpDialog(self).exec()

    def _clear_action_message(self) -> None:
        """Hand the status line back to the live tick summary.

        Returns:
            None.

        Tests:
            - test_clears_pending_message: Dispatch an action, call it;
              verify the next _update_labels writes the live summary again.
            - test_is_safe_without_message: Call it twice in a row; verify
              no exception and the field stays None.
        """
        self._last_action_msg = None

    def _show_score_popup(self, action: str, message: str) -> None:
        """Fade a floating confirmation over the map for two seconds.

        Args:
            action: The action name, used to pick the colour and prefix.
            message: The backend's result message.

        Returns:
            None.

        Tests:
            - test_purchase_popup_is_red: Call with "buy_food"; verify the
              label stylesheet uses the red colour.
            - test_care_popup_is_green: Call with "heal"; verify the label
              stylesheet uses the accent glow colour.
        """
        if action in ("buy_food", "buy_animal"):
            colour, prefix = C_RED, "−"
        elif action in ("feed_all", "feed_one", "heal", "clean"):
            colour, prefix = C_ACCENT_GLOW, "✓"
        else:
            colour, prefix = C_GOLD_GLOW, ""

        self._score_label.setText(f"{prefix} {message}".strip())
        self._score_label.setStyleSheet(
            f"color: {colour}; background: rgba(0,0,0,170); "
            f"border-radius: 8px; padding: 8px 16px; "
            f"font-size: 14px; font-weight: bold;"
        )
        self._score_label.adjustSize()

        viewport = self._view.viewport()
        if viewport is not None:
            self._score_label.move(
                (viewport.width() - self._score_label.width()) // 2,
                viewport.height() // 4,
            )

        self._score_opacity.setOpacity(1.0)
        self._score_label.show()

        # One reusable animation instead of a new object per action —
        # otherwise every successful action leaves a stopped
        # QPropertyAnimation parented to the window for the whole session.
        if self._score_anim is None:
            self._score_anim = QPropertyAnimation(self._score_opacity, b"opacity", self)
            self._score_anim.setDuration(2000)
            self._score_anim.setStartValue(1.0)
            self._score_anim.setEndValue(0.0)
            self._score_anim.setEasingCurve(QEasingCurve.Type.InQuad)
            self._score_anim.finished.connect(self._score_label.hide)
        self._score_anim.stop()
        self._score_anim.start()

    # ── Simulation controls ────────────────────────────────────────────────

    def _toggle_pause(self) -> None:
        """Toggle the tick gate and restyle the pause button.

        The paused flag itself lives in the controller — keeping a second
        copy here would be one more thing that can drift out of step.

        Returns:
            None.

        Tests:
            - test_pause_stops_ticks: Click pause; verify the controller
              reports paused == True.
            - test_pause_button_label_flips: Click twice; verify the label
              goes "▶ Start" then back to "⏸ Pause".
            - test_space_and_button_agree: Press Space, then click the
              button; verify the simulation is running again.
        """
        paused = self._controller.toggle_pause()
        self._btn_pause.setText("▶ Start" if paused else "⏸ Pause")
        self._btn_pause.setStyleSheet(self._pause_qss(running=not paused))
        self._lbl_status.setText(
            "⏸ Pausiert" if paused else "🟢 Läuft"
        )

    def _cycle_speed(self) -> None:
        """Step to the next simulation speed and update the button label.

        Returns:
            None.

        Tests:
            - test_speed_button_shows_new_value: Click once; verify the
              label reads "🏃 2×".
            - test_speed_wraps_to_start: Click as often as there are steps;
              verify the label is back at "🏃 1×".
        """
        speed = self._controller.cycle_speed()
        label = f"{speed:g}×"
        self._btn_speed.setText(f"🏃 {label}")
