"""
ZooGraphicsView — QGraphicsView wrapper for the zoo map.

Provides zoom (mouse wheel), pan (middle-mouse drag), and forwards
entity hover/map-click events to the main window.

Phase 1: hover and enclosure-click detection.
Phase 3: will add drag-and-drop mechanics.

Signals:
    entity_hovered(str):    forwarded from sprite on hover.
    entity_unhovered():     forwarded from sprite on unhover.
    map_clicked(float,float): emitted when the user clicks empty space.

Tests:
    - test_view_scene_is_set: Create ZooGraphicsView with a ZooScene;
      verify view.scene() is the same ZooScene.
    - test_wheel_zoom_changes_scale: Simulate wheelEvent with positive
      delta; verify the view's transform has changed (scale != 1.0).
"""

from typing import Optional

from PyQt6.QtWidgets import QGraphicsView
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QPainter, QWheelEvent, QMouseEvent

from frontend.core.constants import MAP_W, MAP_H
from frontend.ui.zoo_scene import ZooScene

_ZOOM_MIN = 0.3
_ZOOM_MAX = 3.0
_ZOOM_STEP = 1.15  # 15 % per wheel notch


class ZooGraphicsView(QGraphicsView):
    """Zoomable, pannable view onto the ZooScene.

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

    entity_hovered = pyqtSignal(str)
    entity_unhovered = pyqtSignal()
    map_clicked = pyqtSignal(float, float)

    def __init__(
        self,
        scene: ZooScene,
        parent: Optional[object] = None,
    ) -> None:
        """Wrap a ZooScene in a view with scroll-hand drag and anti-aliasing.

        Args:
            scene: The ZooScene to display.
            parent: Optional parent widget.
        """
        super().__init__(scene, parent)
        self._scene: ZooScene = scene

        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setFixedSize(MAP_W + 2, MAP_H + 2)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setViewportUpdateMode(
            QGraphicsView.ViewportUpdateMode.BoundingRectViewportUpdate,
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
        factor = _ZOOM_STEP if event.angleDelta().y() > 0 else 1 / _ZOOM_STEP
        current = self.transform().m11()
        if (factor > 1 and current >= _ZOOM_MAX) or (
            factor < 1 and current <= _ZOOM_MIN
        ):
            return
        self.scale(factor, factor)

    # ── Click detection ───────────────────────────────────────────────────

    def mousePressEvent(self, event: Optional[QMouseEvent]) -> None:
        """Detect clicks on enclosures; otherwise emit map_clicked.

        Phase 3 will additionally detect drag-start on animal sprites.

        Args:
            event: The mouse press event.

        Tests:
            - test_click_on_empty_space_emits_map_clicked: Simulate click
              where no item is present; verify map_clicked emitted.
        """
        if event is None:
            return

        scene_pos = self.mapToScene(event.pos())

        # Check for enclosure click — enclosure items handle their own
        # mousePressEvent and emit enclosure_clicked.
        item = self.itemAt(event.pos())
        if item is None or not hasattr(item, "enclosure_clicked"):
            self.map_clicked.emit(scene_pos.x(), scene_pos.y())

        super().mousePressEvent(event)

    # ── Accessors ─────────────────────────────────────────────────────────

    @property
    def zoo_scene(self) -> ZooScene:
        """Return the underlying ZooScene.

        Tests:
            - test_returns_same_scene_as_constructor: Create view with a
              ZooScene; verify zoo_scene property returns that same scene.
        """
        return self._scene
