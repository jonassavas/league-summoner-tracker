"""
ui/widgets/team_column.py

A widget representing one team's column in champion select – 5 rows, each row
containing a champion icon and two summoner spell icons.

Colour scheme (border/background) is set via the ``side`` argument: "blue" or
"red".
"""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap


_STYLES = {
    "blue": {
        "champ":  "border:2px solid gray; background-color: #ddeeff;",
        "active": "border:2px solid #0000ff; background-color: #ddeeff;",
    },
    "red": {
        "champ":  "border:2px solid gray; background-color: #ffdddd;",
        "active": "border:2px solid #ff0000; background-color: #ffdddd;",
    },
}


class TeamColumn(QWidget):
    """5-row pick column for one team, with champion icons and spell icons."""

    # Default fixed sizes (scaled dynamically later)
    CHAMP_SIZE  = (64, 64)
    SPELL_SIZE  = (22, 22)

    def __init__(self, side: str = "blue", spells_on_right: bool = True,
                 parent=None):
        """
        Parameters
        ----------
        side             : "blue" or "red"
        spells_on_right  : True  → champ icon then spells (blue side)
                           False → spells then champ icon (red side)
        """
        super().__init__(parent)
        self._side = side
        self._spells_on_right = spells_on_right
        self._styles = _STYLES[side]

        self.champ_labels:  list[QLabel] = []
        self.spell1_labels: list[QLabel] = []
        self.spell2_labels: list[QLabel] = []

        col_layout = QVBoxLayout(self)
        col_layout.setSpacing(5)

        for _ in range(5):
            row = QHBoxLayout()
            row.setSpacing(4)

            champ_lbl = QLabel()
            champ_lbl.setFixedSize(*self.CHAMP_SIZE)
            champ_lbl.setStyleSheet(self._styles["champ"])
            self.champ_labels.append(champ_lbl)

            spell_col = QVBoxLayout()
            spell_col.setSpacing(2)
            spell1, spell2 = QLabel(), QLabel()
            for sp in (spell1, spell2):
                sp.setFixedSize(*self.SPELL_SIZE)
                sp.setPixmap(self._transparent_pixmap(sp.size()))
                sp.show()
            self.spell1_labels.append(spell1)
            self.spell2_labels.append(spell2)
            spell_col.addWidget(spell1)
            spell_col.addWidget(spell2)

            if spells_on_right:
                row.addWidget(champ_lbl)
                row.addLayout(spell_col)
            else:
                row.addLayout(spell_col)
                row.addWidget(champ_lbl)

            col_layout.addLayout(row)

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    def reset(self):
        """Clear all icons and restore default styles."""
        for lbl in self.champ_labels:
            lbl.clear()
            lbl.setStyleSheet(self._styles["champ"])
        for lbl in self.spell1_labels + self.spell2_labels:
            lbl.setPixmap(self._transparent_pixmap(lbl.size()))

    def set_champ(self, index: int, pixmap: QPixmap):
        lbl = self.champ_labels[index]
        lbl.setProperty("_original_pixmap", pixmap)
        lbl.setStyleSheet(self._styles["active"])
        self._scale_to_label(lbl, pixmap)

    def set_spell(self, index: int, slot: int, pixmap: QPixmap | None):
        """slot: 0 or 1"""
        labels = self.spell1_labels if slot == 0 else self.spell2_labels
        lbl = labels[index]
        if pixmap:
            lbl.setPixmap(
                pixmap.scaled(lbl.size(), Qt.KeepAspectRatio,
                              Qt.SmoothTransformation)
            )
        else:
            lbl.setPixmap(self._transparent_pixmap(lbl.size()))
        lbl.show()

    def rescale_all(self, champ_size, spell_size, spacing: int):
        """Resize every label and rescale stored pixmaps."""
        layout: QVBoxLayout = self.layout()
        layout.setSpacing(spacing)

        for lbl in self.champ_labels:
            lbl.setFixedSize(champ_size)
            orig = lbl.property("_original_pixmap")
            if orig:
                self._scale_to_label(lbl, orig)

        for lbl in self.spell1_labels + self.spell2_labels:
            lbl.setFixedSize(spell_size)
            # Re-scale whatever is currently shown
            current = lbl.pixmap()
            if current and not current.isNull():
                lbl.setPixmap(
                    current.scaled(spell_size, Qt.KeepAspectRatio,
                                   Qt.SmoothTransformation)
                )
            else:
                lbl.setPixmap(self._transparent_pixmap(spell_size))

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _transparent_pixmap(size) -> QPixmap:
        pix = QPixmap(size)
        pix.fill(Qt.transparent)
        return pix

    @staticmethod
    def _scale_to_label(lbl: QLabel, pixmap: QPixmap):
        scaled = pixmap.scaled(
            lbl.width(), lbl.height(),
            Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        lbl.setPixmap(scaled)
