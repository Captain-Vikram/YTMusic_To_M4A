"""Lightweight wrapper: expose the beautiful GUI from backups
and bind it to the TrackOut engine functions moved to `trackout.engine`.
This avoids duplicating the large GUI file while consolidating engine + GUI
into the `trackout` package namespace for imports and builds.
"""
try:
    # Package-local import (preferred when running inside `trackout` package)
    from . import core as engine_module
except Exception:
    # Fallback: load core.py from the same directory explicitly (no absolute imports)
    import importlib.util, sys, os
    try:
        core_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'core.py')
        spec = importlib.util.spec_from_file_location('trackout.core', core_path)
        engine_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(engine_module)
    except Exception:
        # Last-resort: minimal stub implementations to avoid crashes
        class _Stub:
            def sanitize_filename(self, x):
                return x
            def process_cover_art(self, a, b):
                return None
            def process_single_track(self, *a, **k):
                return True
            def check_available_formats(self, url):
                return []
        engine_module = _Stub()

try:
    from trackout import gui_full as _backup_gui
except Exception:
    # Fallback: try importing by path if package import fails
    import importlib.util, sys, os
    backup_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'gui_full.py')
    spec = importlib.util.spec_from_file_location('backup_gui', backup_path)
    _backup_gui = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(_backup_gui)

# Inject engine implementations into the backup GUI module so its calls resolve
_backup_gui.sanitize_filename = getattr(engine_module, 'sanitize_filename', lambda x: x)
_backup_gui.process_cover_art = getattr(engine_module, 'process_cover_art', lambda a,b: None)
_backup_gui.process_single_track = getattr(engine_module, 'process_single_track', lambda *a, **k: True)
_backup_gui.check_available_formats = getattr(engine_module, 'check_available_formats', lambda url: [])

# Re-export the GUI class
YouTubeMusicExtractorGUI = getattr(_backup_gui, 'YouTubeMusicExtractorGUI', None)

def main():
    """Launch the GUI (wrapper)."""
    if YouTubeMusicExtractorGUI is None:
        print('GUI not available')
        return
    from PyQt5.QtWidgets import QApplication
    import sys
    app = QApplication(sys.argv)
    window = YouTubeMusicExtractorGUI()
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
