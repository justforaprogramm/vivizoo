"""
ZooGraphicsView — QGraphicsView wrapper for the zoo map.

Provides zoom (mouse wheel), pan (drag), and forwards map-click events to
the main window.

The view no longer has a fixed size. It used to be nailed to the scene's
802×602 pixels, which in turn nailed the whole window to 1400×900 — a size
that does not fit on a notebook display or in a WSLg session on a 1080p
monitor. The view now takes whatever space the splitter gives it, shows
scrollbars when that is less than the scene, and reports its new size so the
window can move its overlays along.

Signals:
    map_clicked(float, float): emitted when the user clicks empty space.
    resized(): emitted after the viewport changed size, so the owner can
        reposition the widgets it parented onto this view.

Hover and selection do NOT travel through signals: Qt6 graphics items are
not QObjects, so the sprites report to the window through callbacks
instead (see AnimalSpriteBase). The view itself *is* a QObject, which is why
these two may be real signals.

Tests:
    - test_view_scene_is_set: Create ZooGraphicsView with a ZooScene;
      verify view.scene() is the same ZooScene.
    - test_wheel_zoom_changes_scale: Simulate wheelEvent with positive
      delta; verify the view's transform has changed (scale != 1.0).
    - test_resize_emits_signal: Resize the view; verify resized was emitted.

Module owner: Erik (frontend).
"""

from typing import Optional

from PyQt6.QtWidgets import QGraphicsView, QSizePolicy, QWidget
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QPainter, QResizeEvent, QWheelEvent, QMouseEvent

from frontend.core.constants import VIEW_MIN_W, VIEW_MIN_H
from frontend.ui.zoo_scene import ZooScene
from frontend.ui.enclosure_item import EnclosureItem

_ZOOM_MIN = 0.3
_ZOOM_MAX = 3.0
_ZOOM_STEP = 1.15  # 15 % per wheel notch


class ZooGraphicsView(QGraphicsView):
    """Zoomable, pannable, resizable view onto the ZooScene.

    Supports mouse-wheel zoom (15% per step, clamped 0.3–3.0×),
    scroll-hand-drag panning, and click detection for enclosures.

    Tests:
        - test_initial_scale_is_one: Verify the view's transform scale is
          approximately 1.0 at construction.
        - test_wheel_zoom_changes_scale: Simulate wheelEvent with positive
          delta; verify the transform scale is now > 1.0.
        - test_zoom_clamped_at_max: Zoom in many times; verify scale never
          exceeds 3.0.
    """

    map_clicked = pyqtSignal(float, float)
    resized = pyqtSignal()

    def __init__(
        self,
        scene: ZooScene,
        parent: Optional[QWidget] = None,
    ) -> None:
        """Wrap a ZooScene in a resizable view with drag and anti-aliasing.

        Args:
            scene: The ZooScene to display.
            parent: Optional parent widget.

        Tests:
            - test_scene_is_attached: Create a view with a ZooScene; verify
              scene() returns that same scene.
            - test_has_a_minimum_but_no_fixed_size: Verify the view requests
              at least VIEW_MIN_W × VIEW_MIN_H and can grow beyond it.
            - test_scrollbars_appear_when_too_small: Shrink below the scene;
              verify the scrollbar policy allows them.
        """
        super().__init__(scene, parent)
        self._scene: ZooScene = scene

        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setMinimumSize(VIEW_MIN_W, VIEW_MIN_H)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        # AsNeeded, not AlwaysOff: once the window may be smaller than the
        # 800×600 scene, hiding the scrollbars would hide part of the zoo.
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setViewportUpdateMode(
            QGraphicsView.ViewportUpdateMode.BoundingRectViewportUpdate,
        )
        self.setAccessibleName("Zookarte")
        self.setAccessibleDescription(
            "Karte mit Gehegen, Tieren und Besuchern. Mausrad zoomt, "
            "Ziehen verschiebt."
        )

    # ── Zoom ──────────────────────────────────────────────────────────────

    def wheelEvent(self, event: Optional[QWheelEvent]) -> None:
        """Zoom in or out by 15 % per wheel step, clamped to [0.3, 3.0].

        Args:
            event: The wheel event from Qt.

        Tests:
            - test_wheel_up_zooms_in: Simulate positive delta; verify
              transform scale > 1.0.
            - test_wheel_down_zooms_out: Simulate negative delta; verify
              transform scale < 1.0.
            - test_zoom_clamped: Zoom in many times; verify scale <= 3.0.
        """
        if event is None:
            return
        step = _ZOOM_STEP if event.angleDelta().y() > 0 else 1 / _ZOOM_STEP
        current = self.transform().m11()
        # Clamp the RESULT, not the precondition: testing `current` alone
        # lets the last accepted step overshoot by one 15 % notch.
        target = max(_ZOOM_MIN, min(_ZOOM_MAX, current * step))
        if abs(target - current) < 1e-9:
            return
        self.scale(target / current, target / current)

    # ── Resizing ──────────────────────────────────────────────────────────

    def resizeEvent(self, event: Optional[QResizeEvent]) -> None:
        """Let Qt resize the viewport, then announce the new size.

        The window parents two overlays onto this view — the alert strip and
        the action popup — and their geometry is set in pixels, not by a
        layout. Without this signal they would stay where they were when the
        window opened.

        Args:
            event: The Qt resize event, forwarded to the base class.

        Returns:
            None.

        Tests:
            - test_signal_is_emitted: Resize the view; verify resized fired
              exactly once.
            - test_base_class_still_runs: Resize the view; verify the
              viewport reports the new size.
        """
        super().resizeEvent(event)
        self.resized.emit()

    # ── Click detection ───────────────────────────────────────────────────

    def mousePressEvent(self, event: Optional[QMouseEvent]) -> None:
        """Emit map_clicked unless the click landed on an enclosure.

        The lighting overlay spans the whole scene and sits above every
        other item, so ``itemAt()`` would always report the overlay. The
        check therefore walks the full item stack under the cursor and asks
        whether an EnclosureItem is among them. Qt then delivers the press
        itself, and the enclosure's own handler selects it.

        Args:
            event: The mouse press event; None is ignored.

        Returns:
            None.

        Tests:
            - test_click_on_empty_space_emits_map_clicked: Click a point
              covered by no enclosure; verify map_clicked was emitted with
              the scene coordinates.
            - test_click_on_enclosure_does_not_deselect: Click inside an
              enclosure rectangle; verify map_clicked was NOT emitted, so
              the enclosure's own selection survives.
            - test_none_event_is_ignored: Call with None; verify no signal
              and no exception.
        """
        if event is None:
            return

        position = event.pos()
        on_enclosure = any(
            isinstance(item, EnclosureItem) for item in self.items(position)
        )
        if not on_enclosure:
            scene_pos = self.mapToScene(position)
            self.map_clicked.emit(scene_pos.x(), scene_pos.y())

        super().mousePressEvent(event)

    # ── Accessors ─────────────────────────────────────────────────────────

    @property
    def zoo_scene(self) -> ZooScene:
        """Return the underlying ZooScene.

        Returns:
            ZooScene: The scene passed to the constructor.

        Tests:
            - test_returns_same_scene_as_constructor: Create a view with a
              ZooScene; verify the property returns that same object.
            - test_matches_qt_scene: Verify the property and Qt's own
              scene() return the same object.
        """
        return self._scene
