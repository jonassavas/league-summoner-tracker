"""
ui/main_window.py

Thin top-level window.  Owns the QStackedLayout and handles window-state
events (maximise / fullscreen) and resize propagation.  All actual UI lives in
the two screen widgets.
"""
from PySide6.QtWidgets import QWidget, QStackedLayout
from PySide6.QtCore import Qt, QEvent, QRect, QTimer
from PySide6.QtGui import QFont

from ui.screens.search_screen import SearchScreen
from ui.screens.champ_select_screen import ChampSelectScreen


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("League Summoner Tracker")
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)

        # Track geometry for restoring after maximise/fullscreen
        self._normal_geometry_data = self.saveGeometry()
        self._normal_geometry_rect = self.geometry()
        self._was_maximized  = False
        self._is_fullscreen  = False

        # ------------------------------------------------------------------
        # Stacked layout: index 0 = search, index 1 = champ select
        # ------------------------------------------------------------------
        self._stack = QStackedLayout(self)

        self._search_screen = SearchScreen(
            on_show_champ_select=self._show_champ_select
        )
        self._champ_screen = ChampSelectScreen(
            on_back=self._show_search
        )

        self._stack.addWidget(self._search_screen)   # index 0
        self._stack.addWidget(self._champ_screen)    # index 1

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def _show_champ_select(self):
        self._stack.setCurrentIndex(1)
        self._champ_screen.start()

    def _show_search(self):
        self._stack.setCurrentIndex(0)

    # ------------------------------------------------------------------
    # Window state events (maximise / fullscreen handling)
    # ------------------------------------------------------------------

    def changeEvent(self, event):
        if event.type() == QEvent.WindowStateChange:
            maximized = bool(self.windowState() & Qt.WindowMaximized)
            if maximized:
                self._was_maximized = True
            else:
                if self._was_maximized:
                    try:
                        self.showNormal()
                    except Exception:
                        pass
                    QTimer.singleShot(50, self._restore_normal_geometry)
                self._was_maximized = False

            if self.windowState() & Qt.WindowFullScreen:
                self._is_fullscreen = True
            else:
                if self._is_fullscreen:
                    try:
                        self.restoreGeometry(self._normal_geometry_data)
                    except Exception:
                        pass
                    self._is_fullscreen = False

        super().changeEvent(event)

    def _restore_normal_geometry(self):
        try:
            screen   = self.screen()
            scr_geom = screen.availableGeometry() if screen else None
        except Exception:
            scr_geom = None

        use_rect = None
        if isinstance(self._normal_geometry_rect, QRect) and \
                not self._normal_geometry_rect.isNull():
            if scr_geom:
                too_wide = self._normal_geometry_rect.width()  >= scr_geom.width()  * 0.9
                too_tall = self._normal_geometry_rect.height() >= scr_geom.height() * 0.9
                if not too_wide and not too_tall:
                    use_rect = self._normal_geometry_rect

        if use_rect is None:
            fw, fh = 800, 600
            if scr_geom:
                cx = scr_geom.x() + (scr_geom.width()  - fw) // 2
                cy = scr_geom.y() + (scr_geom.height() - fh) // 2
                use_rect = QRect(cx, cy, fw, fh)
            else:
                use_rect = QRect(100, 100, fw, fh)

        try:
            self.setGeometry(use_rect)
        except Exception:
            try:
                self.restoreGeometry(self._normal_geometry_data)
            except Exception:
                pass

        QTimer.singleShot(0, self._search_screen.scale_emblems)

    # ------------------------------------------------------------------
    # Resize propagation
    # ------------------------------------------------------------------

    def resizeEvent(self, event):
        if not (self.windowState() & Qt.WindowMaximized) and \
                not (self.windowState() & Qt.WindowFullScreen):
            try:
                self._normal_geometry_rect = self.geometry()
                self._normal_geometry_data = self.saveGeometry()
            except Exception:
                pass

        self._search_screen.scale_fonts(self.width())
        QTimer.singleShot(0, self._search_screen.scale_emblems)
        QTimer.singleShot(0, self._champ_screen.rescale)

        super().resizeEvent(event)
