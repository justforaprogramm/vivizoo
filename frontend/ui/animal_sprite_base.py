"""
AnimalSpriteBase — shared behaviour of every animal sprite on the map.

Implements the template method :meth:`update_state`: it moves the sprite and
detects the alive/dead transition, then delegates the actual drawing to the
subclass through :meth:`render_alive` and :meth:`render_dead`. The hover
plumbing (callback registration, Qt hover events, the highlight hooks), the
click-to-select handling and the selection glow live here as well, so the
ellipse sprite and the ASCII pixmap sprites share one implementation instead
of three copies.

Inheritance chain::

    EntitySprite                       (contract: entity_id, update_position)
    └── AnimalSpriteBase               (template: update_state, hover, death)
        ├── AnimalSprite               (ellipse + letter)
        └── AsciiAnimalSprite          (ASCII pixmap)
            ├── AsciiLionSprite
            ├── AsciiPenguinSprite
            └── AsciiGiraffeSprite

Callbacks are used instead of pyqtSignal because Qt6 graphics items are not
QObject subclasses and cannot declare signals.

Module owner: Erik (frontend).

Tests:
    - test_update_state_moves_sprite: Call update_state(100, 200, False);
      verify update_position was invoked with those coordinates.
    - test_death_transition_renders_once: Call update_state twice with
      is_dead=True; verify render_dead ran only on the first call.
"""

from __future__ import annotations

from typing import Callable

from PyQt6.QtWidgets import QGraphicsDropShadowEffect, QGraphicsSceneMouseEvent
from PyQt6.QtGui import QColor

from frontend.core.constants import C_ACCENT_GLOW
from frontend.ui.entity_sprite import EntitySprite

SELECTION_GLOW_BLUR = 22  # px — visible around both the circle and the pixmaps


# Eight fields, pylint allows seven: id, name, death, hover and selection
# state plus the three callbacks. Those callbacks replace exactly the three
# pyqtSignals a QGraphicsItem is not allowed to have in Qt6 (see the module
# docstring) — the only way to have fewer is to put them in a dict and lose
# every type check.
class AnimalSpriteBase(EntitySprite):  # pylint: disable=too-many-instance-attributes
    """Abstract animal sprite: position, death state and hover handling.

    Subclasses must call :meth:`init_animal` from their constructor and
    implement :meth:`update_position`, :meth:`render_alive` and
    :meth:`render_dead`.

    This is a **mixin**: the Qt base class is mixed in by the concrete
    sprite (``AnimalSprite(AnimalSpriteBase, QGraphicsEllipseItem)``), so
    calls like ``setGraphicsEffect`` resolve at runtime but not while a
    static checker looks at this file alone. Those few lines carry both a
    ``type: ignore`` and a ``pylint: disable`` for that reason.

    Tests:
        - test_hover_callback_receives_id: Register a callback, trigger
          hoverEnterEvent; verify it was called with the animal id.
        - test_is_dead_tracks_last_update: Call update_state with
          is_dead=True; verify the is_dead property reports True.
    """

    # Declared here, assigned in init_animal: the sip constructor of the Qt
    # base class has to run before any Python attribute is set, so a plain
    # __init__ is not available (see init_animal). The declaration keeps the
    # sprite's whole state readable in one place all the same.
    _animal_id: str
    _name: str
    _is_dead: bool
    _hovered: bool
    _selected: bool
    _hover_callback: Callable[[str], None] | None
    _unhover_callback: Callable[[], None] | None
    _click_callback: Callable[[str], None] | None

    def init_animal(self, animal_id: str, name: str) -> None:
        """Initialise the shared animal state.

        Called from each subclass constructor after the Qt base class has
        been initialised, because a plain mixin cannot run ``__init__``
        reliably ahead of the sip base.

        Args:
            animal_id: Backend animal id, e.g. "a_01".
            name: Display name used in tooltips and labels.

        Returns:
            None.

        Tests:
            - test_sets_id_and_name: Call with ("a_01", "Simba"); verify
              both are readable through the properties.
            - test_starts_alive: Call it; verify is_dead is False.
        """
        self._animal_id = animal_id
        self._name = name
        self._is_dead = False
        self._hovered = False
        self._selected = False
        self._hover_callback = None
        self._unhover_callback = None
        self._click_callback = None

    # ── Callback registration ─────────────────────────────────────────────

    def set_hover_callback(self, callback: Callable[[str], None]) -> None:
        """Register the function invoked when the pointer enters the sprite.

        Args:
            callback: Receives this sprite's animal id.

        Returns:
            None.

        Tests:
            - test_callback_invoked_on_hover: Register a mock, simulate
              hoverEnterEvent; verify it was called with the animal id.
            - test_callback_can_be_replaced: Register two callbacks in
              turn; verify only the second one fires.
        """
        self._hover_callback = callback

    def set_unhover_callback(self, callback: Callable[[], None]) -> None:
        """Register the function invoked when the pointer leaves the sprite.

        Args:
            callback: Takes no arguments.

        Returns:
            None.

        Tests:
            - test_callback_invoked_on_unhover: Register a mock, simulate
              hoverLeaveEvent; verify it was called.
            - test_no_callback_is_safe: Simulate hoverLeaveEvent without a
              callback; verify no exception is raised.
        """
        self._unhover_callback = callback

    def set_click_callback(self, callback: Callable[[str], None]) -> None:
        """Register the function invoked when the sprite is clicked.

        Hovering only previews an animal; clicking pins the selection so it
        survives the pointer travelling to the action buttons.

        Args:
            callback: Receives this sprite's animal id.

        Returns:
            None.

        Tests:
            - test_click_invokes_callback: Register a mock, simulate
              mousePressEvent; verify it was called with the animal id.
            - test_click_without_callback_is_safe: Simulate a click with no
              callback registered; verify no exception.
        """
        self._click_callback = callback

    # ── Properties ────────────────────────────────────────────────────────

    @property
    def entity_id(self) -> str:
        """Return the backend animal id (EntitySprite contract).

        Returns:
            str: The id passed to init_animal.

        Tests:
            - test_matches_animal_id: Verify entity_id equals animal_id.
            - test_returns_constructor_value: Build with "a_07"; verify the
              property returns "a_07".
        """
        return self._animal_id

    @property
    def animal_id(self) -> str:
        """Return the backend animal id.

        Returns:
            str: The id passed to init_animal, e.g. "a_01".

        Tests:
            - test_returns_constructor_id: Build with "a_42"; verify the
              property returns "a_42".
            - test_id_is_read_only: Verify the property exposes no setter.
        """
        return self._animal_id

    @property
    def name(self) -> str:
        """Return the animal's display name.

        Returns:
            str: The name passed to init_animal.

        Tests:
            - test_returns_constructor_name: Build with "Simba"; verify the
              property returns "Simba".
            - test_name_used_in_tooltip: Verify the sprite tooltip contains
              the same name.
        """
        return self._name

    # ── Selection marker ──────────────────────────────────────────────────

    def set_selected(self, selected: bool) -> None:
        """Mark or unmark this animal as the window's current selection.

        The selection can also be made in the roster table, where no sprite
        is touched at all, so the map needs a marker of its own — otherwise
        the two views disagree about which animal the action buttons will
        act on. A coloured glow is used instead of a border because it works
        identically for the ellipse sprite and the pixmap sprites: a
        ``QGraphicsDropShadowEffect`` composites around whatever the item
        draws, so no subclass has to override anything.

        Args:
            selected: True to add the glow, False to remove it.

        Returns:
            None.

        Tests:
            - test_selected_sprite_has_effect: Call with True; verify
              graphicsEffect() is not None.
            - test_deselect_removes_effect: Call with True then False;
              verify graphicsEffect() is None again.
            - test_repeated_calls_are_cheap: Call with True twice; verify the
              same effect object is still attached.
        """
        if selected == self._selected:
            return
        self._selected = selected
        if not selected:
            # Mixin: the Qt base is only mixed in by the concrete subclass.
            # pylint: disable-next=no-member
            self.setGraphicsEffect(None)  # type: ignore[attr-defined]
            return
        glow = QGraphicsDropShadowEffect()
        glow.setBlurRadius(SELECTION_GLOW_BLUR)
        glow.setOffset(0, 0)
        glow.setColor(QColor(C_ACCENT_GLOW))
        # Mixin: the Qt base is only mixed in by the concrete subclass.
        # pylint: disable-next=no-member
        self.setGraphicsEffect(glow)  # type: ignore[attr-defined]

    @property
    def is_selected(self) -> bool:
        """Return whether this sprite currently carries the selection glow.

        Returns:
            bool: True between ``set_selected(True)`` and
            ``set_selected(False)``.

        Tests:
            - test_false_initially: Verify a fresh sprite reports False.
            - test_tracks_set_selected: Call set_selected(True); verify the
              property reports True.
        """
        return self._selected

    @property
    def is_dead(self) -> bool:
        """Return whether the sprite currently renders its dead variant.

        Returns:
            bool: True after an update_state call with is_dead=True.

        Tests:
            - test_alive_initially: Verify a fresh sprite reports False.
            - test_true_after_dead_update: Call update_state(..., True);
              verify the property reports True.
        """
        return self._is_dead

    # ── Template method ───────────────────────────────────────────────────

    def update_state(self, x: float, y: float, is_dead: bool) -> None:
        """Move the sprite and switch its rendering when life state changes.

        This is the template method the scene calls once per frame for every
        animal. It never draws anything itself — the concrete look comes
        from the subclass hooks.

        Args:
            x: New centre X coordinate in map pixels.
            y: New centre Y coordinate in map pixels.
            is_dead: The backend's ``is_dead`` flag for this animal.

        Returns:
            None.

        Tests:
            - test_position_always_updated: Call with (10, 20, False);
              verify the sprite centre moved to (10, 20).
            - test_render_dead_called_once: Call twice with is_dead=True;
              verify render_dead ran only on the first transition.
            - test_revival_restores_alive_look: Call with True then False;
              verify render_alive ran on the second call.
        """
        self.update_position(x, y)

        if is_dead and not self._is_dead:
            self._is_dead = True
            self.render_dead()
        elif not is_dead and self._is_dead:
            self._is_dead = False
            self.render_alive()

    # ── Subclass hooks ────────────────────────────────────────────────────

    def render_alive(self) -> None:
        """Draw the sprite in its living appearance.

        Returns:
            None.

        Raises:
            NotImplementedError: Always — subclasses must override it.

        Tests:
            - test_raises_on_base: Call on the base class; verify
              NotImplementedError.
            - test_ellipse_restores_species_colour: Call on an AnimalSprite
              after a death; verify the brush is the species colour again.
        """
        raise NotImplementedError("Animal sprites must implement render_alive")

    def render_dead(self) -> None:
        """Draw the sprite in its deceased appearance.

        Returns:
            None.

        Raises:
            NotImplementedError: Always — subclasses must override it.

        Tests:
            - test_render_dead_raises_on_base: Call on the base class;
              verify NotImplementedError.
            - test_ascii_switches_to_red_pixmap: Call on an ASCII sprite;
              verify the pixmap is the red variant.
        """
        raise NotImplementedError("Animal sprites must implement render_dead")

    def highlight_on(self) -> None:
        """React to the pointer entering the sprite. No-op by default.

        Pixmap sprites keep their appearance; the ellipse sprite overrides
        this to grow and draw a glow ring.

        Returns:
            None.

        Tests:
            - test_base_is_noop: Call on an ASCII sprite; verify the pixmap
              is unchanged.
            - test_ellipse_grows: Call on an AnimalSprite; verify its
              bounding rect grew.
        """

    def highlight_off(self) -> None:
        """React to the pointer leaving the sprite. No-op by default.

        Returns:
            None.

        Tests:
            - test_highlight_off_is_noop_on_base: Call on an ASCII sprite;
              verify the pixmap is unchanged.
            - test_ellipse_shrinks_back: Call on an AnimalSprite after
              highlight_on; verify the original size is restored.
        """

    # ── Qt mouse events ───────────────────────────────────────────────────

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent | None) -> None:
        """Pin this animal as the current selection.

        Args:
            event: The Qt mouse press event, accepted so it stops here.

        Returns:
            None.

        The event is accepted so it stops here. Qt's default item handler
        ignores mouse presses, which would let the click fall through the
        whole stack under the cursor — other animals standing on the same
        spot and finally the enclosure beneath, whose handler would clear
        the very selection this click just made.

        Tests:
            - test_click_pins_selection: Click a sprite, move the pointer
              away; verify the window still reports it as selected.
            - test_click_does_not_fall_through: Click an animal standing
              inside an enclosure; verify the enclosure was not selected
              instead.
        """
        if self._click_callback is not None:
            self._click_callback(self._animal_id)
        if event is not None:
            event.accept()

    # ── Qt hover events ───────────────────────────────────────────────────

    def hoverEnterEvent(self, event: object) -> None:
        """Highlight the sprite and notify the main window.

        Args:
            event: The Qt hover event, forwarded to the base class.

        Returns:
            None.

        Tests:
            - test_fires_hover_callback: Register a mock; simulate the
              event; verify it received the animal id.
            - test_dead_sprite_is_not_highlighted: Mark the sprite dead,
              simulate the event; verify highlight_on was skipped.
        """
        if not self._is_dead:
            self._hovered = True
            self.highlight_on()
        if self._hover_callback is not None:
            self._hover_callback(self._animal_id)
        # Mixin: the Qt base is only mixed in by the concrete subclass.
        # pylint: disable-next=no-member
        super().hoverEnterEvent(event)  # type: ignore[misc]

    def hoverLeaveEvent(self, event: object) -> None:
        """Remove the highlight and notify the main window.

        Args:
            event: The Qt hover event, forwarded to the base class.

        Returns:
            None.

        Tests:
            - test_fires_unhover_callback: Register a mock; simulate the
              event; verify it was called exactly once.
            - test_highlight_removed: Hover then unhover an AnimalSprite;
              verify the sprite is back at its normal size.
        """
        # Both the flag and the visual hook must run unconditionally: an
        # animal that dies while the pointer is over it would otherwise keep
        # _hovered = True and stay stuck at the enlarged hover geometry.
        # Each subclass decides what "un-highlighted" means while dead.
        self._hovered = False
        self.highlight_off()
        if self._unhover_callback is not None:
            self._unhover_callback()
        # Mixin: the Qt base is only mixed in by the concrete subclass.
        # pylint: disable-next=no-member
        super().hoverLeaveEvent(event)  # type: ignore[misc]
