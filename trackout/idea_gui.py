import sys
from pathlib import Path
from datetime import datetime

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QPushButton, QFrame, QScrollArea, QSizePolicy,
    QAction, QMenuBar, QStatusBar, QButtonGroup, QMessageBox, QFileDialog
)
from PyQt5.QtCore import Qt, QSize, QThread, pyqtSignal, QUrl, QEvent
from PyQt5.QtGui import QFont, QColor, QPalette, QIcon, QDesktopServices, QPixmap
import urllib.request

# Mock imports for the example to run standalone (Replace with your actual imports)
try:
    from search import search_youtube_local, download_media
except ImportError:
    # Dummy functions to prevent crash if 'search.py' isn't present for testing
    def search_youtube_local(query, limit=10):
        return {"video_results": [{"title": f"Result {i}", "description": "Description text here...", "views": "1M"} for i in range(limit)]}
    def download_media(url, format_choice, output_dir):
        return {"status": "success", "filepath": "test.mp4"}

# ===========================
# STYLESHEET (QSS)
# ===========================
STYLE_SHEET = """
/* --- MAIN WINDOW & GLOBAL --- */
QMainWindow {
    background-color: #000000; /* Pitch black background per image */
}

QWidget {
    font-family: 'Segoe UI', Roboto, sans-serif;
    color: #f0f0f0;
}

QScrollBar:vertical {
    border: none; background: #0e0e12; width: 10px; margin: 0px; border-radius: 5px;
}
QScrollBar::handle:vertical {
    background: #333340; min-height: 20px; border-radius: 5px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }

/* --- SIDEBAR --- */
QWidget#sidebarContainer {
    background-color: #0e0e12; /* Slightly lighter than main bg */
    border-right: 1px solid #1a1a22;
}

QLabel#appNameLabel {
    color: #ffffff;
    font-size: 22px;
    font-weight: bold;
    padding: 10px;
}

/* Sidebar Navigation Buttons */
QPushButton[class="navBtn"] {
    background-color: transparent;
    border: none;
    text-align: left;
    padding: 12px 20px;
    font-size: 15px;
    color: #aaaaaa;
}
QPushButton[class="navBtn"]:checked {
    color: #ffffff;
    font-weight: bold;
}
QPushButton[class="navBtn"]:hover {
    color: #ffffff;
}

/* --- RIGHT CONTENT AREA --- */
QWidget#contentContainer {
    background-color: #000000;
}

/* Search Input Field - Full Width Look */
QLineEdit#searchInput {
    background-color: #151015; /* Very dark purple/black */
    border: 1px solid #332033;
    border-radius: 25px; /* Fully rounded pill shape */
    padding: 10px 25px;
    font-size: 16px;
    color: #ffffff;
}
QLineEdit#searchInput:focus {
    border: 1px solid #ff3399;
}

/* Main Search Button */
QPushButton[class="pinkGlowBtn"] {
    background-color: #b32d75;
    border: 1px solid #ff66b3;
    border-radius: 20px;
    color: white;
    font-weight: bold;
    font-size: 14px;
    padding: 0 30px;
}
QPushButton[class="pinkGlowBtn"]:hover {
    background-color: #d1368a;
    box-shadow: 0 0 10px #ff66b3;
}

/* --- SEARCH RESULTS PANEL --- */
QLabel#sectionTitle {
    font-size: 18px;
    font-weight: bold;
    color: #eeeeee;
    margin-left: 5px;
}

/* The Container holding the grid cards */
QWidget#resultsPanel {
    background-color: #120a12; /* Dark reddish/purple tint bg */
    border: 1px solid #000000;
    border-radius: 20px;
}

QScrollArea#resultsScrollArea {
    background-color: transparent;
    border: none;
}

/* --- CARD DESIGN (ResultItemWidget) --- */
QFrame#resultCard {
    background-color: #1a101a; /* Dark card bg */
    border: 1px solid #332233;
    border-radius: 15px;
}
QFrame#resultCard:hover {
    border: 1px solid #ff3399; /* Pink glow on hover */
    background-color: #201220;
}

QLabel#thumbLabel {
    background-color: #2a2a35;
    border-radius: 10px;
}

QLabel#resultTitleLabel {
    font-size: 14px; 
    font-weight: bold; 
    color: #ffffff;
}

QLabel#resultDescLabel {
    font-size: 11px; 
    color: #888888;
}

/* The wide pink button at bottom of card */
QPushButton#cardActionBtn {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #992266, stop:1 #cc3388);
    border: none;
    border-radius: 15px;
    color: white;
    font-weight: bold;
    padding: 8px 0;
    margin-top: 5px;
}
QPushButton#cardActionBtn:hover {
    background-color: #ff3399;
}
"""

# --- LIGHT THEME (simple, matching accent colors) ---
LIGHT_STYLE_SHEET = """
QMainWindow { background-color: #f6f7fb; }
QWidget { font-family: 'Segoe UI', Roboto, sans-serif; color: #222222; }
QLineEdit#searchInput { background-color: #ffffff; border: 1px solid #d0c6d6; color: #222; }
QPushButton[class="pinkGlowBtn"] { background-color: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #ff66b3, stop:1 #ff3399); color: white; border-radius: 20px; font-weight: bold; font-size: 14px; padding: 0 30px; border: 1px solid #ff66b3; }
QPushButton[class="pinkGlowBtn"]:hover { background-color: #d1368a; box-shadow: 0 0 10px #ff66b3; }
QWidget#resultsPanel { background-color: #ffffff; border: 1px solid #e6dfe6; }
QFrame#resultCard { background-color: #ffffff; border: 1px solid #e6d6e6; }
QFrame#resultCard:hover { border: 1px solid #ff66b3; background-color: #fff5fb; }
QLabel#resultTitleLabel { color: #111; }
QLabel#resultDescLabel { color: #666; }
QLabel#thumbLabel { background-color: #f0f0f0; }
QScrollBar:vertical { background: #f0f0f0; }
"""


# ===========================
# WORKER THREADS (Unchanged)
# ===========================
class SearchWorker(QThread):
    results_ready = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, query: str, limit: int = 10):
        super().__init__()
        self.query = query
        self.limit = limit

    def run(self):
        try:
            data = search_youtube_local(self.query, limit=self.limit)
            if isinstance(data, dict) and data.get("error"):
                self.error.emit(str(data.get("error")))
                return
            self.results_ready.emit(data)
        except Exception as exc:
            self.error.emit(str(exc))

class DownloadWorker(QThread):
    finished_download = pyqtSignal(dict)

    def __init__(self, url: str, fmt: str, target_dir: Path):
        super().__init__()
        self.url = url
        self.fmt = fmt
        self.target_dir = target_dir

    def run(self):
        result = download_media(self.url, format_choice=self.fmt, output_dir=str(self.target_dir))
        self.finished_download.emit(result)

# ===========================
# CUSTOM WIDGET: CARD (VERTICAL)
# ===========================
class ResultItemWidget(QFrame):
    """
    Refactored to look like a Vertical Card:
    [ Thumbnail ]
    [ Title     ]
    [ Desc      ]
    """
    def __init__(self, data: dict, open_callback, save_callback):
        super().__init__()
        self.setObjectName("resultCard")
        self.data = data
        
        # Compact card size
        self.setFixedSize(185, 180)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        # Vertical Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # 1. Thumbnail (Top)
        self.thumb_lbl = QLabel()
        self.thumb_lbl.setObjectName("thumbLabel")
        self.thumb_lbl.setFixedSize(160, 90)  # compact thumbnail
        self.thumb_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.thumb_lbl, alignment=Qt.AlignmentFlag.AlignCenter)

        # Try to load thumbnail image (short timeout). Fallback to placeholder color.
        thumb_url = None
        tn = data.get("thumbnail")
        if isinstance(tn, dict):
            thumb_url = tn.get("static") or tn.get("url")
        elif isinstance(tn, str):
            thumb_url = tn
        elif data.get("thumbnails"):
            tlist = data.get("thumbnails")
            if isinstance(tlist, list) and tlist:
                last = tlist[-1]
                if isinstance(last, dict):
                    thumb_url = last.get("url")

        if thumb_url:
            try:
                with urllib.request.urlopen(thumb_url, timeout=3) as resp:
                    img_data = resp.read()
                    pix = QPixmap()
                    if pix.loadFromData(img_data):
                        pix = pix.scaled(self.thumb_lbl.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                        self.thumb_lbl.setPixmap(pix)
                    else:
                        self.thumb_lbl.setStyleSheet("background-color: #334455; border-radius: 8px;")
            except Exception:
                self.thumb_lbl.setStyleSheet("background-color: #334455; border-radius: 8px;")
        else:
            self.thumb_lbl.setStyleSheet("background-color: #334455; border-radius: 8px;")

        # 2. Title
        title_text = data.get("title") or "Untitled"
        if len(title_text) > 42:
            title_text = title_text[:39] + "..."
        self.title_lbl = QLabel(title_text)
        self.title_lbl.setObjectName("resultTitleLabel")
        self.title_lbl.setWordWrap(True)
        self.title_lbl.setFixedHeight(30)
        layout.addWidget(self.title_lbl)

        # 3. Description / Channel
        channel = data.get("channel", {}).get("name") or "Unknown Channel"
        self.desc_lbl = QLabel(channel)
        self.desc_lbl.setObjectName("resultDescLabel")
        self.desc_lbl.setFixedHeight(16)
        layout.addWidget(self.desc_lbl)

        layout.addStretch()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            url = self.data.get("link")
            if not url:
                QMessageBox.warning(self, "No URL", "No link available to open.")
            else:
                QApplication.clipboard().setText(url)
                try:
                    # open_callback expects the data dict
                    self.parentWidget()  # keep for debugging
                    QDesktopServices.openUrl(QUrl(url))
                except Exception:
                    pass
        return super().mousePressEvent(event)

# ===========================
# MAIN APPLICATION WINDOW
# ===========================
class SearchOutMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SearchOut")
        self.resize(1280, 800)
        # Apply global styles
        self.setStyleSheet(STYLE_SHEET)
        self.dark_theme = True
        self.history = [] 
        self.current_cards = []
        self.init_ui()

    def init_ui(self):
        # 1. Menu Bar
        self.setup_menu_and_status()

        # 2. Main Layout (Sidebar + Content)
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Use a single content area for full-window layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        content = self.create_content_area()
        # content will take entire central widget
        main_layout.addWidget(content)

    def setup_menu_and_status(self):
        menubar = self.menuBar()
        menubar.setStyleSheet("background-color: #0e0e12; color: #ffffff;")
        file_menu = menubar.addMenu("File")
        tools_menu = menubar.addMenu("Tools")
        help_menu = menubar.addMenu("Help")
        
        # Exit action
        exit_act = QAction("Exit", self)
        exit_act.triggered.connect(lambda: self.close())
        file_menu.addAction(exit_act)
        # Theme toggle (Tools)
        theme_act = QAction("Toggle Theme", self)
        theme_act.setShortcut("Ctrl+T")
        theme_act.triggered.connect(self.toggle_theme)
        tools_menu.addAction(theme_act)
        statusbar = self.statusBar()
        statusbar.showMessage("Ready to search...")
        statusbar.setStyleSheet("background-color: #0e0e12; color: #aaaaaa; border-top: 1px solid #1a1a22;")

    pass

    def create_content_area(self):
        content_container = QWidget()
        content_container.setObjectName("contentContainer")
        
        # Main layout for the right side
        layout = QVBoxLayout(content_container)
        layout.setContentsMargins(30, 30, 30, 30)  # outer padding around whole content area
        layout.setSpacing(30)  # vertical spacing between search bar and results panel

        # --- 1. SEARCH BAR (Full Width) ---
        # Container to hold input and button
        search_container = QWidget()
        search_layout = QHBoxLayout(search_container)
        search_layout.setContentsMargins(0, 0, 0, 0)
        search_layout.setSpacing(15)  # horizontal gap between search input and button

        self.search_input = QLineEdit()
        self.search_input.setObjectName("searchInput")
        self.search_input.setPlaceholderText("Search...")
        self.search_input.setFixedHeight(50)  # controls vertical size of the search input (affects overall bar height)
        self.search_input.returnPressed.connect(self.start_search)

        self.search_btn = QPushButton("Search")
        self.search_btn.setProperty("class", "pinkGlowBtn")
        self.search_btn.setFixedHeight(50)  # make button same height as input
        self.search_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.search_btn.clicked.connect(self.start_search)

        search_layout.addWidget(self.search_input) # Defaults to stretch=1
        search_layout.addWidget(self.search_btn)
        
        layout.addWidget(search_container)

        # --- 2. SEARCH RESULTS PANEL ---
        # Panel widget gets background/styling from QSS via objectName "resultsPanel"
        self.results_panel = QWidget()
        self.results_panel.setObjectName("resultsPanel")
        
        panel_layout = QVBoxLayout(self.results_panel)
        panel_layout.setContentsMargins(30, 30, 30, 30)  # inner padding inside the results panel (space around header + grid)
        
        # Title + meta row
        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        header_row.setSpacing(10)

        self.results_title_label = QLabel("Search Results")
        self.results_title_label.setObjectName("sectionTitle")
        header_row.addWidget(self.results_title_label)
        header_row.addStretch()

        self.results_meta_label = QLabel("Awaiting a search.")
        self.results_meta_label.setStyleSheet("color: #888; font-size: 12px;")
        header_row.addWidget(self.results_meta_label)

        panel_layout.addLayout(header_row)

        # Scroll Area
        self.results_scroll_area = QScrollArea()
        self.results_scroll_area.setObjectName("resultsScrollArea")
        self.results_scroll_area.setWidgetResizable(True)  # lets the grid widget expand/contract with the viewport (important for reflowing cards)
        self.results_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff) # hide horizontal scroll so cards wrap instead

        # Grid Container inside Scroll Area
        self.results_grid_widget = QWidget()
        self.results_grid_widget.setStyleSheet("background: transparent;")  # transparent bg so panel bg shows through
        
        # USE QGRIDLAYOUT HERE for the grid effect (this layout controls card placement)
        self.results_layout = QGridLayout(self.results_grid_widget)
        self.results_layout.setContentsMargins(0, 10, 0, 0)  # top margin between header and first row of cards
        self.results_layout.setSpacing(18)  # spacing between individual cards (horizontal + vertical gap)
        # Keep results aligned to top
        self.results_layout.setAlignment(Qt.AlignmentFlag.AlignTop)  # ensures cards start from top of the scroll area

        self.placeholder_label = QLabel("Enter a query above to find videos.")
        self.placeholder_label.setStyleSheet("color: #666; font-size: 14px;")
        self.results_layout.addWidget(self.placeholder_label, 0, 0)

        self.results_scroll_area.setWidget(self.results_grid_widget)
        panel_layout.addWidget(self.results_scroll_area)

        # Keep layout responsive when the viewport resizes (triggers relayout_cards / eventFilter)
        self.results_scroll_area.viewport().installEventFilter(self)

        layout.addWidget(self.results_panel)

        return content_container

# Note: the actual per-card size is set inside ResultItemWidget:
#     ResultItemWidget.__init__ -> self.setFixedSize(185, 180)
# That fixedSize controls the visual size of each video card; combined with results_layout.setSpacing(...) and contentsMargins
# it determines the spacing and wrapping of cards inside the grid.

    # ---------- Logic ----------
    def clear_results(self):
        # Remove all items from the grid layout
        while self.results_layout.count():
            item = self.results_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        self.current_cards = []

    def start_search(self):
        query = self.search_input.text().strip()
        if not query:
            return

        self.search_btn.setEnabled(False)
        self.search_btn.setText("...")
        self.clear_results()
        self.results_meta_label.setText("Searching...")
        
        # Add loading text
        loading = QLabel("Searching...")
        loading.setStyleSheet("color: #ff66b3; font-size: 16px;")
        self.results_layout.addWidget(loading, 0, 0)

        # Increase limit to fill the grid
        self.search_worker = SearchWorker(query, limit=16) 
        self.search_worker.results_ready.connect(self.handle_search_results)
        self.search_worker.error.connect(self.handle_search_error)
        self.search_worker.start()

    def handle_search_results(self, data: dict):
        self.search_btn.setEnabled(True)
        self.search_btn.setText("Search")
        self.clear_results()

        videos = data.get("video_results", []) if isinstance(data, dict) else []

        if not videos:
            lbl = QLabel("No results found.")
            lbl.setStyleSheet("color: #888;")
            self.results_layout.addWidget(lbl, 0, 0)
            self.results_meta_label.setText("No results to display.")
            return

        self.current_cards = []
        for video in videos:
            card = ResultItemWidget(video, self.open_in_browser, self.save_result)
            self.current_cards.append(card)

        self.relayout_cards()

        total_time = None
        if isinstance(data, dict):
            meta = data.get("search_metadata") or {}
            total_time = meta.get("total_time_taken")
        time_text = f" • {total_time}s" if total_time is not None else ""
        self.results_meta_label.setText(f"Showing {len(videos)} results{time_text}")
        self.statusBar().showMessage(f"Found {len(videos)} results.")

    def handle_search_error(self, message: str):
        self.search_btn.setEnabled(True)
        self.search_btn.setText("Search")
        self.clear_results()
        lbl = QLabel(f"Error: {message}")
        lbl.setStyleSheet("color: red;")
        self.results_layout.addWidget(lbl, 0, 0)
        self.results_meta_label.setText("Something went wrong. Try again.")

    def apply_theme(self, dark: bool):
        """Apply dark or light stylesheet."""
        if dark:
            self.setStyleSheet(STYLE_SHEET)
            self.statusBar().showMessage("Dark theme applied.")
        else:
            self.setStyleSheet(LIGHT_STYLE_SHEET)
            self.statusBar().showMessage("Light theme applied.")

    def toggle_theme(self):
        self.dark_theme = not getattr(self, "dark_theme", True)
        self.apply_theme(self.dark_theme)

    def compute_max_cols(self) -> int:
        """Compute how many columns fit in the current viewport."""
        if not hasattr(self, "results_scroll_area"):
            return 6
        viewport_width = max(1, self.results_scroll_area.viewport().width())
        card_width = 195  # card width + padding approximation
        spacing = self.results_layout.spacing()
        cols = max(2, min(6, viewport_width // (card_width + spacing)))
        return cols

    def relayout_cards(self):
        """Reflow cards into the grid based on available width."""
        if not self.current_cards:
            return

        for card in self.current_cards:
            self.results_layout.removeWidget(card)

        max_cols = self.compute_max_cols()
        for idx, card in enumerate(self.current_cards):
            row = idx // max_cols
            col = idx % max_cols
            self.results_layout.addWidget(card, row, col)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.relayout_cards()

    def eventFilter(self, source, event):
        if source is getattr(self, "results_scroll_area", None) and event.type() == QEvent.Resize:
            self.relayout_cards()
        if source is getattr(self, "results_scroll_area", None) and source is self.results_scroll_area.viewport() and event.type() == QEvent.Resize:
            self.relayout_cards()
        return super().eventFilter(source, event)

    def open_in_browser(self, data: dict):
        url = data.get("link")
        if url:
            QDesktopServices.openUrl(QUrl(url))
        else:
            QMessageBox.warning(self, "Error", "No link available")

    def save_result(self, data: dict):
        # Implement your save logic here
        pass


    class SearchPanel(QWidget):
        """Embeddable search panel (can be imported into the full GUI).

        Usage (in another GUI):
            from search_yt.idea_gui import SearchPanel
            panel = SearchPanel(dark=True)
            main_layout.addWidget(panel)

        The panel exposes the same search behavior as SearchOutMainWindow but
        is a plain QWidget so it can be embedded into `trackout/gui_full.py`.
        """
        def __init__(self, dark: bool = True, parent=None):
            super().__init__(parent)
            self.setObjectName("searchPanel")
            self.dark = dark
            self.current_cards = []
            self._build_ui()

        def _build_ui(self):
            layout = QVBoxLayout(self)
            layout.setContentsMargins(8, 8, 8, 8)
            layout.setSpacing(12)

            # Search bar row
            search_container = QWidget()
            search_layout = QHBoxLayout(search_container)
            search_layout.setContentsMargins(0, 0, 0, 0)
            search_layout.setSpacing(8)

            self.search_input = QLineEdit()
            self.search_input.setObjectName("searchInput")
            self.search_input.setPlaceholderText("Search...")
            self.search_input.setFixedHeight(40)
            self.search_input.returnPressed.connect(self.start_search)

            self.search_btn = QPushButton("Search")
            self.search_btn.setProperty("class", "pinkGlowBtn")
            self.search_btn.setFixedHeight(40)
            self.search_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self.search_btn.clicked.connect(self.start_search)

            search_layout.addWidget(self.search_input)
            search_layout.addWidget(self.search_btn)
            layout.addWidget(search_container)

            # Results panel
            self.results_panel = QWidget()
            self.results_panel.setObjectName("resultsPanel")
            panel_layout = QVBoxLayout(self.results_panel)
            panel_layout.setContentsMargins(8, 8, 8, 8)

            header_row = QHBoxLayout()
            header_row.setContentsMargins(0, 0, 0, 0)
            header_row.setSpacing(8)

            lbl = QLabel("Search Results")
            lbl.setObjectName("sectionTitle")
            header_row.addWidget(lbl)
            header_row.addStretch()

            self.results_meta_label = QLabel("Awaiting a search.")
            self.results_meta_label.setStyleSheet("color: #888; font-size: 12px;")
            header_row.addWidget(self.results_meta_label)

            panel_layout.addLayout(header_row)

            self.results_scroll_area = QScrollArea()
            self.results_scroll_area.setWidgetResizable(True)
            self.results_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

            self.results_grid_widget = QWidget()
            self.results_layout = QGridLayout(self.results_grid_widget)
            self.results_layout.setContentsMargins(0, 10, 0, 0)
            self.results_layout.setSpacing(10)
            self.results_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

            self.placeholder_label = QLabel("Enter a query above to find videos.")
            self.placeholder_label.setStyleSheet("color: #666; font-size: 13px;")
            self.results_layout.addWidget(self.placeholder_label, 0, 0)

            self.results_scroll_area.setWidget(self.results_grid_widget)
            panel_layout.addWidget(self.results_scroll_area)

            self.results_scroll_area.viewport().installEventFilter(self)

            layout.addWidget(self.results_panel)

            # Small status label at bottom
            self.status_label = QLabel("Ready")
            self.status_label.setStyleSheet("color: #999; font-size: 12px;")
            layout.addWidget(self.status_label)

            # Apply initial theme only to this widget (embedding app may override)
            self.apply_theme(self.dark)

        def clear_results(self):
            while self.results_layout.count():
                item = self.results_layout.takeAt(0)
                widget = item.widget()
                if widget:
                    widget.deleteLater()
            self.current_cards = []

        def start_search(self):
            query = self.search_input.text().strip()
            if not query:
                return

            self.search_btn.setEnabled(False)
            self.search_btn.setText("...")
            self.clear_results()

            loading = QLabel("Searching...")
            loading.setStyleSheet("color: #ff66b3; font-size: 14px;")
            self.results_layout.addWidget(loading, 0, 0)
            self.results_meta_label.setText("Searching...")

            self.search_worker = SearchWorker(query, limit=16)
            self.search_worker.results_ready.connect(self.handle_search_results)
            self.search_worker.error.connect(self.handle_search_error)
            self.search_worker.start()

        def handle_search_results(self, data: dict):
            self.search_btn.setEnabled(True)
            self.search_btn.setText("Search")
            self.clear_results()

            videos = data.get("video_results", []) if isinstance(data, dict) else []
            if not videos:
                lbl = QLabel("No results found.")
                lbl.setStyleSheet("color: #888;")
                self.results_layout.addWidget(lbl, 0, 0)
                self.results_meta_label.setText("No results to display.")
                return

            self.current_cards = []
            for video in videos:
                card = ResultItemWidget(video, None, None)
                self.current_cards.append(card)

            self.relayout_cards()

            meta = data.get("search_metadata") if isinstance(data, dict) else {}
            total_time = meta.get("total_time_taken") if isinstance(meta, dict) else None
            time_text = f" • {total_time}s" if total_time is not None else ""
            self.results_meta_label.setText(f"Showing {len(videos)} results{time_text}")
            self.status_label.setText(f"Found {len(videos)} results.")

        def handle_search_error(self, message: str):
            self.search_btn.setEnabled(True)
            self.search_btn.setText("Search")
            self.clear_results()
            lbl = QLabel(f"Error: {message}")
            lbl.setStyleSheet("color: red;")
            self.results_layout.addWidget(lbl, 0, 0)
            self.results_meta_label.setText("Something went wrong. Try again.")

        def apply_theme(self, dark: bool):
            self.dark = dark
            # applying style to this widget helps when embedded standalone
            if dark:
                self.setStyleSheet(STYLE_SHEET)
            else:
                self.setStyleSheet(LIGHT_STYLE_SHEET)

        def compute_max_cols(self) -> int:
            if not hasattr(self, "results_scroll_area"):
                return 6
            viewport_width = max(1, self.results_scroll_area.viewport().width())
            card_width = 195
            spacing = self.results_layout.spacing()
            return max(2, min(6, viewport_width // (card_width + spacing)))

        def relayout_cards(self):
            if not self.current_cards:
                return
            for card in self.current_cards:
                self.results_layout.removeWidget(card)

            cols = self.compute_max_cols()
            for idx, card in enumerate(self.current_cards):
                row = idx // cols
                col = idx % cols
                self.results_layout.addWidget(card, row, col)

        def eventFilter(self, source, event):
            if source is getattr(self, "results_scroll_area", None) and source is self.results_scroll_area.viewport() and event.type() == QEvent.Resize:
                self.relayout_cards()
            return super().eventFilter(source, event)



# ===========================
# MAIN ENTRY POINT
# ===========================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    
    window = SearchOutMainWindow()
    window.show()
    sys.exit(app.exec_())