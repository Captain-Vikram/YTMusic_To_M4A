import sys
from pathlib import Path
from datetime import datetime

from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QPushButton, QFrame, QScrollArea, QMessageBox, QSizePolicy
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QUrl
from PyQt5.QtGui import QFont, QDesktopServices, QPixmap
import urllib.request
from urllib.parse import urlparse, parse_qs, quote_plus


def to_music_url(url: str) -> str:
    """Convert various YouTube URL forms to a YouTube Music watch URL.

    Falls back to the original URL on failure.
    """
    try:
        if not url:
            return url
        p = urlparse(url)
        host = (p.netloc or '').lower()
        # already music
        if 'music.youtube.com' in host:
            return url

        video_id = None
        if 'youtu.be' in host:
            video_id = p.path.lstrip('/')
        elif 'youtube.com' in host or 'www.youtube.com' in host:
            qs = parse_qs(p.query)
            if 'v' in qs:
                video_id = qs['v'][0]
            else:
                parts = [p for p in p.path.split('/') if p]
                if parts:
                    video_id = parts[-1]

        if video_id:
            return f'https://music.youtube.com/watch?v={video_id}'
    except Exception:
        pass
    return url

# Local backend functions (imported at runtime from search_yt.search)
try:
    from search import search_youtube_local, download_media
except Exception:  # pragma: no cover - gracefully fall back for editor
    def search_youtube_local(query, limit=10):
        return {"video_results": [{"title": f"Result {i}", "description": "Description", "views": "1M"} for i in range(limit)]}
    def download_media(url, format_choice, output_dir):
        return {"status": "success", "filepath": "test.mp4"}

# ===========================
# STYLESHEET (QSS) - Soft Dark/Light Themes
# ===========================
STYLE_SHEET = """
/* --- SOFT DARK THEME --- */
QDialog, QMainWindow, QWidget#searchPanel {
    background-color: #070608;
    border-radius: 14px;
}
QWidget { font-family: 'Segoe UI', Roboto, sans-serif; color: #f3eef6; }

/* Search input - pill style with soft border */
QLineEdit#searchInput {
    background-color: #0f0d12;
    border: 1px solid rgba(180,120,160,0.12);
    border-radius: 22px;
    padding: 12px 18px;
    font-size: 15px;
    color: #f3eef6;
}
QLineEdit#searchInput:focus {
    border: 1px solid #ff66b3;
    background-color: #121017;
}

/* Accent button (rounded) */
QPushButton[class="pinkGlowBtn"] {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #ff66b3, stop:1 #d13b85);
    border: none;
    border-radius: 18px;
    color: white;
    font-weight: 600;
    padding: 8px 20px;
}
QPushButton[class="pinkGlowBtn"]:hover {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #ff7bbf, stop:1 #e05aa0);
}

/* Results container with soft outline */
QWidget#resultsPanel {
    background-color: rgba(18,10,18,0.6);
    border: 1px solid rgba(120,80,110,0.12);
    border-radius: 12px;
    padding: 8px;
}

/* Card styling: soft corners and subtle hover */
QFrame#resultCard {
    background-color: rgba(26,16,26,0.9);
    border: 1px solid rgba(70,50,70,0.08);
    border-radius: 14px;
    padding: 6px;
}
QFrame#resultCard:hover {
    border: 1px solid rgba(255,102,179,0.22);
    background-color: rgba(32,18,32,0.95);
}

QLabel#thumbLabel {
    background-color: #24232a;
    border-radius: 10px;
}
QLabel#resultTitleLabel { font-size: 14px; font-weight: 700; color: #fff; }
QLabel#resultDescLabel { font-size: 12px; color: #cfc6d3; }

/* Status / small text */
QLabel { color: #ddd6df; }
"""

LIGHT_STYLE_SHEET = """
/* --- SOFT LIGHT THEME --- */
QDialog, QMainWindow, QWidget#searchPanel {
    background-color: #fbfbfd;
    border-radius: 14px;
}
QWidget { font-family: 'Segoe UI', Roboto, sans-serif; color: #222; }

QLineEdit#searchInput {
    background-color: #ffffff;
    border: 1px solid rgba(200,180,200,0.6);
    border-radius: 22px;
    padding: 12px 18px;
    font-size: 15px;
    color: #222;
}
QLineEdit#searchInput:focus {
    border: 1px solid #ff66b3;
    background-color: #fff;
}

QPushButton[class="pinkGlowBtn"] {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #ff66b3, stop:1 #d13b85);
    border: none;
    border-radius: 18px;
    color: white;
    font-weight: 600;
    padding: 8px 20px;
}
QPushButton[class="pinkGlowBtn"]:hover {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #ff85c2, stop:1 #e05aa0);
}

QWidget#resultsPanel {
    background-color: #ffffff;
    border: 1px solid rgba(220,210,220,0.8);
    border-radius: 12px;
    padding: 8px;
}

QFrame#resultCard {
    background-color: #ffffff;
    border: 1px solid rgba(220,210,220,0.9);
    border-radius: 12px;
    padding: 6px;
}
QFrame#resultCard:hover {
    border: 1px solid rgba(255,102,179,0.25);
    background-color: #fff5fb;
}

QLabel#thumbLabel { background-color: #f5f5f7; border-radius: 10px; }
QLabel#resultTitleLabel { color: #111; font-weight: 700; }
QLabel#resultDescLabel { color: #666; }

QLabel { color: #333; }
QScrollBar:vertical { background: transparent; }
"""

# ===========================
# WORKER THREADS
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
# Result Card Widget
# ===========================
class ResultItemWidget(QFrame):
    def __init__(self, data: dict, open_callback=None, save_callback=None):
        super().__init__()
        self.setObjectName("resultCard")
        self.data = data or {}
        self.setFixedSize(180, 180)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        self.thumb_lbl = QLabel()
        self.thumb_lbl.setObjectName("thumbLabel")
        self.thumb_lbl.setFixedSize(160, 90)
        self.thumb_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.thumb_lbl, alignment=Qt.AlignmentFlag.AlignCenter)

        # load thumbnail (best-effort, small timeout)
        thumb_url = None
        tn = self.data.get("thumbnail")
        if isinstance(tn, dict):
            thumb_url = tn.get("static") or tn.get("url")
        elif isinstance(tn, str):
            thumb_url = tn
        elif self.data.get("thumbnails"):
            tlist = self.data.get("thumbnails")
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

        title_text = self.data.get("title") or "Untitled"
        if len(title_text) > 42:
            title_text = title_text[:39] + "..."
        self.title_lbl = QLabel(title_text)
        self.title_lbl.setObjectName("resultTitleLabel")
        self.title_lbl.setWordWrap(True)
        self.title_lbl.setFixedHeight(30)
        layout.addWidget(self.title_lbl)

        channel = self.data.get("channel", {}).get("name") or self.data.get("uploader") or "Unknown"
        self.desc_lbl = QLabel(channel)
        self.desc_lbl.setObjectName("resultDescLabel")
        self.desc_lbl.setFixedHeight(16)
        layout.addWidget(self.desc_lbl)

        layout.addStretch()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            url = self.data.get("link") or self.data.get("url")
            if not url:
                QMessageBox.warning(self, "No URL", "No link available to open.")
            else:
                # Only copy the music-first link to clipboard; do not open browser
                try:
                    music_url = to_music_url(url)
                except Exception:
                    music_url = url
                QApplication.clipboard().setText(music_url)
        return super().mousePressEvent(event)

# ===========================
# Embeddable Search Panel
# ===========================
class SearchPanel(QWidget):
    """Lightweight, embeddable search panel.

    - Instantiate with `SearchPanel(dark=True)` to apply the dark stylesheet locally.
    - Call `apply_theme(dark: bool)` to switch styles.
    """
    def __init__(self, dark: bool = True, parent=None):
        super().__init__(parent)
        self.setObjectName("searchPanel")
        self.dark = dark
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(12)

        # Search row
        search_row = QWidget()
        search_layout = QHBoxLayout(search_row)
        search_layout.setContentsMargins(0, 0, 0, 0)
        search_layout.setSpacing(8)

        self.search_input = QLineEdit()
        self.search_input.setObjectName("searchInput")
        self.search_input.setPlaceholderText("Search...")
        self.search_input.setFixedHeight(40)

        self.search_btn = QPushButton("Search")
        self.search_btn.setProperty("class", "pinkGlowBtn")
        self.search_btn.setFixedHeight(40)
        # Keep a stable clickable area even when text changes to "..."
        self.search_btn.setMinimumWidth(110)
        self.search_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.search_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.search_btn.clicked.connect(self.start_search)

        # Make the input expand (stretch=1) while the button keeps a fixed width
        search_layout.addWidget(self.search_input, 1)
        search_layout.addWidget(self.search_btn, 0)
        layout.addWidget(search_row)

        # Results area
        self.results_panel = QWidget()
        self.results_panel.setObjectName("resultsPanel")
        panel_layout = QVBoxLayout(self.results_panel)
        panel_layout.setContentsMargins(8, 8, 8, 8)

        title = QLabel("Search Results")
        title.setObjectName("sectionTitle")
        panel_layout.addWidget(title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.results_grid_widget = QWidget()
        self.results_layout = QGridLayout(self.results_grid_widget)
        self.results_layout.setContentsMargins(0, 10, 0, 0)
        self.results_layout.setSpacing(10)
        self.results_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.placeholder_label = QLabel("Enter a query above to find videos.")
        self.placeholder_label.setStyleSheet("color: #666; font-size: 13px;")
        self.results_layout.addWidget(self.placeholder_label, 0, 0)

        scroll.setWidget(self.results_grid_widget)
        panel_layout.addWidget(scroll)
        layout.addWidget(self.results_panel)

        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: #999; font-size: 12px;")
        layout.addWidget(self.status_label)

        self.apply_theme(self.dark)

    def clear_results(self):
        while self.results_layout.count():
            item = self.results_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def start_search(self):
        query = self.search_input.text().strip()
        if not query:
            return
        # Primary music search URL (YouTube Music); YouTube links act as fallback
        try:
            self._search_music_url = f"https://music.youtube.com/search?q={quote_plus(query)}"
        except Exception:
            self._search_music_url = None
        self.search_btn.setEnabled(False)
        self.search_btn.setText("...")
        self.clear_results()

        loading = QLabel("Searching...")
        loading.setStyleSheet("color: #ff66b3; font-size: 14px;")
        self.results_layout.addWidget(loading, 0, 0)

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
            return

        MAX_COLS = 6
        row = 0
        col = 0
        for video in videos:
            card = ResultItemWidget(video, None, None)
            self.results_layout.addWidget(card, row, col)
            col += 1
            if col >= MAX_COLS:
                col = 0
                row += 1

        self.status_label.setText(f"Found {len(videos)} results.")

    def handle_search_error(self, message: str):
        self.search_btn.setEnabled(True)
        self.search_btn.setText("Search")
        self.clear_results()
        lbl = QLabel(f"Error: {message}")
        lbl.setStyleSheet("color: red;")
        self.results_layout.addWidget(lbl, 0, 0)
    
    def apply_theme(self, dark: bool):
        self.dark = dark
        if dark:
            self.setStyleSheet(STYLE_SHEET)
        else:
            self.setStyleSheet(LIGHT_STYLE_SHEET)


# Export names
__all__ = ["SearchPanel", "SearchWorker", "ResultItemWidget"]