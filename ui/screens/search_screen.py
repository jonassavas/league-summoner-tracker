"""
ui/screens/search_screen.py

The main "Search" screen: name/tag input, search button, toggle-flex button,
champ-select navigation button, and the two rank panels (Solo/Duo, Flex).
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QPushButton, QLabel, QSizePolicy,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont

from api.riot_api import RiotAPI
from utils.assets import get_emblem_path
from ui.widgets.rank_panel import RankPanel


class SearchScreen(QWidget):
    """Summoner lookup screen with Solo/Duo and Flex rank panels."""

    def __init__(self, on_show_champ_select, parent=None):
        """
        Parameters
        ----------
        on_show_champ_select : callable
            Called when the user clicks "Show Champ-Select".
        """
        super().__init__(parent)
        self._api = RiotAPI()
        self._flex_visible = False
        self._on_show_champ_select = on_show_champ_select

        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        main_layout = QVBoxLayout(self)

        # --- Input form ---
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("e.g. Jone")
        self.tag_input = QLineEdit()
        self.tag_input.setPlaceholderText("e.g. SWE")

        form = QFormLayout()
        form.addRow("Name:", self.name_input)
        form.addRow("Tag Line #:", self.tag_input)
        main_layout.addLayout(form)

        # --- Content row (buttons | rank panels) ---
        content_layout = QHBoxLayout()

        # Left column: buttons + summoner label
        left = QVBoxLayout()

        self.search_btn = QPushButton("Search")
        self.search_btn.setFixedHeight(40)
        self.search_btn.clicked.connect(self._on_search)

        self.toggle_btn = QPushButton("Show Flex Ranking")
        self.toggle_btn.setFixedHeight(40)
        self.toggle_btn.clicked.connect(self._toggle_flex)
        self.toggle_btn.hide()

        self.champ_btn = QPushButton("Show Champ-Select")
        self.champ_btn.setFixedHeight(40)
        self.champ_btn.clicked.connect(self._on_show_champ_select)

        self.summoner_label = QLabel("")
        self.summoner_label.setAlignment(Qt.AlignCenter)
        self.summoner_label.setWordWrap(True)

        left.addWidget(self.search_btn)
        left.addWidget(self.toggle_btn)
        left.addWidget(self.champ_btn)
        left.addStretch()
        left.addWidget(self.summoner_label)
        content_layout.addLayout(left, 1)

        # Right column: rank panels
        rank_layout = QHBoxLayout()
        self.solo_panel = RankPanel("Solo/Duo")
        self.flex_panel = RankPanel("Flex")
        rank_layout.addWidget(self.solo_panel, 1)
        rank_layout.addWidget(self.flex_panel, 1)
        content_layout.addLayout(rank_layout, 4)

        main_layout.addLayout(content_layout)

        # Base font (scaled on resize)
        self._base_font = QFont()
        self._base_font.setPointSize(12)
        self._apply_font(self._base_font)

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_search(self):
        name = self.name_input.text().strip()
        tag  = self.tag_input.text().strip()

        self._flex_visible = False
        self.solo_panel.clear()
        self.flex_panel.clear()
        self.toggle_btn.hide()

        if not name or not tag:
            self.solo_panel.set_unranked()
            self.solo_panel.text_label.setText("Please enter both Name and Tag line")
            self.summoner_label.setText("")
            return

        self.summoner_label.setText(f"{name}\n#{tag}")

        status, puuid_or_error = self._api.get_puuid(name, tag)
        if status != 200:
            self.solo_panel.show()
            self.solo_panel.text_label.setText(f"Error getting PUUID:\n{puuid_or_error}")
            return

        status, ranked = self._api.get_ranked_data(puuid_or_error)
        if status != 200:
            self.solo_panel.show()
            self.solo_panel.text_label.setText(f"Error getting ranked data:\n{ranked}")
            return

        # Solo/Duo
        solo = ranked.get("solo")
        if solo:
            self.solo_panel.set_rank(
                solo["tier"], solo["rank"], solo["leaguePoints"],
                solo["wins"], solo["losses"],
                get_emblem_path(solo["tier"]),
            )
        else:
            self.solo_panel.set_unranked()

        # Flex
        flex = ranked.get("flex")
        if flex:
            self.flex_panel.set_rank(
                flex["tier"], flex["rank"], flex["leaguePoints"],
                flex["wins"], flex["losses"],
                get_emblem_path(flex["tier"]),
            )
            self.flex_panel.hide()   # hidden until toggled
            self.toggle_btn.show()
        else:
            self.flex_panel.clear()
            self.toggle_btn.hide()

    def _toggle_flex(self):
        if self._flex_visible:
            self.flex_panel.hide()
            self.toggle_btn.setText("Show Flex Ranking")
            self._flex_visible = False
        else:
            self.flex_panel.show()
            self.toggle_btn.setText("Hide Flex Ranking")
            self._flex_visible = True
            QTimer.singleShot(0, self.flex_panel.scale_emblem)

    # ------------------------------------------------------------------
    # Scaling helpers (called from MainWindow on resize)
    # ------------------------------------------------------------------

    def scale_emblems(self):
        self.solo_panel.scale_emblem()
        self.flex_panel.scale_emblem()

    def scale_fonts(self, width: int):
        font_size = max(12, width // 35)
        font = QFont(self._base_font)
        font.setPointSize(font_size)
        self._apply_font(font)

    def _apply_font(self, font: QFont):
        self.solo_panel.set_font(font)
        self.flex_panel.set_font(font)
        self.summoner_label.setFont(font)
