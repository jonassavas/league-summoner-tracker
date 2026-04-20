"""
ui/widgets/rank_panel.py

A self-contained widget that displays a rank emblem + rank text for one queue
type (Solo/Duo or Flex).  Handles its own pixmap scaling via an event filter.
"""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QSizePolicy
from PySide6.QtCore import Qt, QEvent, QSize, QTimer
from PySide6.QtGui import QPixmap, QFont


class RankPanel(QWidget):
    """Displays a queue title, rank emblem image, and rank info text."""

    def __init__(self, title: str, parent=None):
        super().__init__(parent)

        self._original_pixmap: QPixmap | None = None

        layout = QVBoxLayout(self)

        self.title_label = QLabel(title)
        self.title_label.setAlignment(Qt.AlignCenter)

        self.emblem_label = QLabel()
        self.emblem_label.setAlignment(Qt.AlignCenter)
        self.emblem_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Ignored)
        self.emblem_label.setMinimumSize(1, 1)
        self.emblem_label.installEventFilter(self)

        self.text_label = QLabel("")
        self.text_label.setAlignment(Qt.AlignCenter)
        self.text_label.setWordWrap(True)

        layout.addWidget(self.title_label)
        layout.addWidget(self.emblem_label, 1)
        layout.addWidget(self.text_label)

        self.hide()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_rank(self, tier: str, rank: str, lp: int, wins: int, losses: int,
                 emblem_path: str):
        """Populate the panel with rank data and show it."""
        self._original_pixmap = QPixmap(emblem_path)
        self.emblem_label.clear()
        self.text_label.setText(
            f"{tier.title()} {rank} - {lp} LP\n"
            f"Wins: {wins}  Losses: {losses}"
        )
        self.show()
        QTimer.singleShot(0, self.scale_emblem)

    def set_unranked(self):
        """Show the panel in the unranked state."""
        self._original_pixmap = None
        self.emblem_label.clear()
        self.text_label.setText(f"{self.title_label.text()}\nUnranked")
        self.show()

    def clear(self):
        self._original_pixmap = None
        self.emblem_label.clear()
        self.text_label.setText("")
        self.hide()

    def set_font(self, font: QFont):
        for lbl in (self.title_label, self.text_label):
            lbl.setFont(font)

    def scale_emblem(self):
        if not self._original_pixmap:
            return
        lw, lh = self.emblem_label.width(), self.emblem_label.height()
        if lw > 1 and lh > 1:
            scaled = self._original_pixmap.scaled(
                QSize(lw, lh), Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            self.emblem_label.setPixmap(scaled)

    # ------------------------------------------------------------------
    # Event filter – rescale when the emblem label is resized
    # ------------------------------------------------------------------

    def eventFilter(self, obj, event):
        if obj is self.emblem_label and event.type() == QEvent.Resize:
            QTimer.singleShot(0, self.scale_emblem)
        return super().eventFilter(obj, event)
