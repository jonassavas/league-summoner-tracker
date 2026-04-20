"""
ui/screens/champ_select_screen.py

The champion-select overlay screen.  Polls the League Client every second and
renders blue/red team picks (with summoner spells) and bans.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QSizePolicy,
)
from PySide6.QtCore import Qt, QSize, QTimer
from PySide6.QtGui import QPixmap

from api.league_client import LeagueClient
from api.champion_data import ChampionData
from ui.widgets.team_column import TeamColumn


class ChampSelectScreen(QWidget):
    """Displays live champion select data from the local League client."""

    def __init__(self, on_back, parent=None):
        """
        Parameters
        ----------
        on_back : callable
            Called when the user clicks the back button.
        """
        super().__init__(parent)
        self._on_back = on_back
        self._champ_data = ChampionData()
        self._client     = LeagueClient()

        # Cache original pixmaps so we can rescale on resize
        self._pick_pixmaps: dict[QLabel, QPixmap] = {}
        self._ban_pixmaps:  dict[QLabel, QPixmap] = {}

        self._build_ui()
        self._build_timer()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # Back button + status label
        self.back_btn = QPushButton("← Back")
        self.back_btn.clicked.connect(self._go_back)

        self.status_label = QLabel("Champion select will appear here.")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setWordWrap(True)

        top = QVBoxLayout()
        top.addWidget(self.back_btn)
        top.addWidget(self.status_label)
        layout.addLayout(top)

        # --- Bans row ---
        self.bans_container = QWidget()
        self.bans_container.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Fixed
        )
        bans_layout = QHBoxLayout(self.bans_container)
        bans_layout.setContentsMargins(10, 10, 10, 10)
        bans_layout.setSpacing(10)

        self.blue_ban_labels = self._make_ban_labels(5, "blue")
        self.red_ban_labels  = self._make_ban_labels(5, "red")

        blue_bans_row = QHBoxLayout()
        blue_bans_row.setSpacing(4)
        blue_bans_row.setAlignment(Qt.AlignLeft)
        for lbl in self.blue_ban_labels:
            blue_bans_row.addWidget(lbl)

        red_bans_row = QHBoxLayout()
        red_bans_row.setSpacing(4)
        red_bans_row.setAlignment(Qt.AlignRight)
        for lbl in self.red_ban_labels:
            red_bans_row.addWidget(lbl)

        bans_layout.addLayout(blue_bans_row)
        bans_layout.addStretch()
        bans_layout.addLayout(red_bans_row)
        self.bans_container.hide()
        layout.addWidget(self.bans_container)

        # --- Picks row ---
        self.picks_container = QWidget()
        picks_layout = QHBoxLayout(self.picks_container)

        self.blue_col = TeamColumn(side="blue", spells_on_right=True)
        self.red_col  = TeamColumn(side="red",  spells_on_right=False)

        picks_layout.addLayout(self._as_layout(self.blue_col))
        picks_layout.addStretch()
        picks_layout.addLayout(self._as_layout(self.red_col))

        # Keep a flat list of all ban labels for resize helpers
        self._all_ban_labels = self.blue_ban_labels + self.red_ban_labels

        self.picks_container.hide()
        layout.addWidget(self.picks_container, alignment=Qt.AlignTop)

    @staticmethod
    def _make_ban_labels(count: int, side: str) -> list[QLabel]:
        bg = "#ddeeff" if side == "blue" else "#ffdddd"
        labels = []
        for _ in range(count):
            lbl = QLabel()
            lbl.setFixedSize(48, 48)
            lbl.setStyleSheet(f"border:2px solid gray; background-color: {bg};")
            labels.append(lbl)
        return labels

    @staticmethod
    def _as_layout(widget: QWidget) -> QVBoxLayout:
        """Wrap a widget in a layout so we can addLayout() it."""
        wrapper = QVBoxLayout()
        wrapper.addWidget(widget)
        return wrapper

    def _build_timer(self):
        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self.update)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self):
        self._timer.start()
        self.update()
        QTimer.singleShot(0, self.rescale)

    def stop(self):
        self._timer.stop()

    def _go_back(self):
        self.stop()
        self._reset_styles()
        self._on_back()

    # ------------------------------------------------------------------
    # Data update
    # ------------------------------------------------------------------

    def update(self):  # noqa: A003
        status, data = self._client.get_champ_select()

        self._clear_all_labels()

        if status != 200 or not data:
            self.status_label.setText("Not in champ select.")
            self.status_label.show()
            self.bans_container.hide()
            self.picks_container.hide()
            self._reset_styles()
            return

        self.status_label.hide()
        self.bans_container.show()
        self.picks_container.show()
        QTimer.singleShot(0, self.rescale)

        blue_team = [c for c in data.get("myTeam", []) + data.get("theirTeam", [])
                     if c.get("team") == 1]
        red_team  = [c for c in data.get("myTeam", []) + data.get("theirTeam", [])
                     if c.get("team") != 1]

        self._populate_team(self.blue_col, blue_team)
        self._populate_team(self.red_col,  red_team)
        self._populate_bans(data.get("actions", []))

    def _populate_team(self, column: TeamColumn, team: list[dict]):
        for i, champ in enumerate(team[:5]):
            icon_path = self._champ_data.get_champion_icon(champ.get("championId"))
            if icon_path:
                column.set_champ(i, QPixmap(icon_path))

            for slot, spell_key in enumerate(("spell1Id", "spell2Id")):
                spell_id = champ.get(spell_key)
                pixmap = None
                if spell_id:
                    path = self._champ_data.get_spell_icon(spell_id)
                    if path:
                        pixmap = QPixmap(path)
                column.set_spell(i, slot, pixmap)

    def _populate_bans(self, actions: list):
        blue_idx = 0
        red_idx  = 4  # red bans fill right-to-left

        for group in actions:
            for action in group:
                if action.get("type") != "ban" or not action.get("completed"):
                    continue
                icon_path = self._champ_data.get_champion_icon(
                    action.get("championId")
                )
                if not icon_path:
                    continue

                pix = QPixmap(icon_path)
                is_ally = action.get("isAllyAction", False)

                if is_ally and blue_idx < 5:
                    lbl = self.blue_ban_labels[blue_idx]
                    self._ban_pixmaps[lbl] = pix
                    self._scale_to_label(lbl, pix)
                    lbl.setStyleSheet(
                        "border:2px solid #0000ff; background-color: #ddeeff;"
                    )
                    blue_idx += 1
                elif not is_ally and red_idx >= 0:
                    lbl = self.red_ban_labels[red_idx]
                    self._ban_pixmaps[lbl] = pix
                    self._scale_to_label(lbl, pix)
                    lbl.setStyleSheet(
                        "border:2px solid #ff0000; background-color: #ffdddd;"
                    )
                    red_idx -= 1

    # ------------------------------------------------------------------
    # Dynamic resizing
    # ------------------------------------------------------------------

    def rescale(self):
        if not self.isVisible():
            return

        total_w = self.width()
        total_h = self.height()

        reserved_h  = 120
        available_h = max(total_h - reserved_h, 1)
        available_w = max(total_w - 40, 1)

        pick_orig_w, pick_orig_h = 42, 42
        ban_orig_w,  ban_orig_h  = 32, 32
        pick_rows = 5

        spacing_px    = int(pick_orig_h * 0.1)
        total_spacing = (pick_rows - 1) * spacing_px

        scale_v = (available_h - total_spacing) / (pick_orig_h * pick_rows)
        scale_h = available_w / (pick_orig_w * 2)
        scale   = min(scale_v, scale_h)

        champ_size = QSize(int(pick_orig_w * scale), int(pick_orig_h * scale))
        spacing    = max(5, int(champ_size.height() * 0.1))

        spell_side = int(champ_size.height() * 0.40)
        spell_size = QSize(spell_side, spell_side)

        ban_size = QSize(
            int(ban_orig_w * scale * 0.75),
            int(ban_orig_h * scale * 0.75),
        )

        self.blue_col.rescale_all(champ_size, spell_size, spacing)
        self.red_col.rescale_all(champ_size, spell_size, spacing)

        for lbl in self._all_ban_labels:
            lbl.setFixedSize(ban_size)
            if lbl in self._ban_pixmaps:
                self._scale_to_label(lbl, self._ban_pixmaps[lbl])

        picks_layout = self.picks_container.layout()
        bans_layout  = self.bans_container.layout()
        if picks_layout:
            picks_layout.setContentsMargins(0, spacing, 0, spacing)
        if bans_layout:
            bans_layout.setContentsMargins(10, spacing, 10, spacing)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _clear_all_labels(self):
        self.blue_col.reset()
        self.red_col.reset()
        for lbl in self._all_ban_labels:
            lbl.clear()

    def _reset_styles(self):
        self.blue_col.reset()
        self.red_col.reset()
        for lbl in self.blue_ban_labels:
            lbl.setStyleSheet("border:2px solid gray; background-color: #ddeeff;")
        for lbl in self.red_ban_labels:
            lbl.setStyleSheet("border:2px solid gray; background-color: #ffdddd;")
        self._pick_pixmaps.clear()
        self._ban_pixmaps.clear()

    @staticmethod
    def _scale_to_label(lbl: QLabel, pixmap: QPixmap):
        scaled = pixmap.scaled(
            lbl.width(), lbl.height(),
            Qt.KeepAspectRatio, Qt.SmoothTransformation,
        )
        lbl.setPixmap(scaled)
