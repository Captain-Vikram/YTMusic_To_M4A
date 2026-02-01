"""Lightweight wrapper: expose the beautiful GUI from backups
and bind it to the TrackOut engine functions moved to `trackout.engine`.
This avoids duplicating the large GUI file while consolidating engine + GUI
into the `trackout` package namespace for imports and builds.
"""
import importlib, importlib.util, sys, os
import traceback, tempfile, datetime
# Optional: suppress noisy Qt font warnings and set a sane default font for the app
try:
    from PyQt5.QtCore import qInstallMessageHandler
    from PyQt5.QtGui import QFont
except Exception:
    qInstallMessageHandler = None
    QFont = None

def _load_engine():
    """Robustly load trackout.core whether frozen or run as a package."""
    base_dir = os.path.dirname(os.path.abspath(__file__))

    # 1) Try absolute import first (works when trackout is a proper package in PyInstaller)
    try:
        return importlib.import_module('trackout.core')
    except Exception:
        pass

    # 2) When frozen, modules live under sys._MEIPASS; add it to sys.path and retry
    if getattr(sys, 'frozen', False):
        meipass = getattr(sys, '_MEIPASS', None)
        if meipass and meipass not in sys.path:
            sys.path.insert(0, meipass)
        try:
            return importlib.import_module('trackout.core')
        except Exception:
            pass

    # 3) Directly load the sibling core.py via spec_from_file_location
    try:
        core_path = os.path.join(base_dir, 'core.py')
        spec = importlib.util.spec_from_file_location('trackout.core', core_path)
        engine_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(engine_module)
        return engine_module
    except Exception:
        pass

    # 4) Last-resort stub to keep GUI from crashing (limited functionality)
    class _Stub:
        def sanitize_filename(self, x):
            return x
        def process_cover_art(self, a, b):
            return None
        def process_single_track(self, *a, **k):
            return True
        def check_available_formats(self, url):
            return []
    return _Stub()


engine_module = _load_engine()


def _expose_bundled_ffmpeg():
    """If ffmpeg was bundled into the onefile EXE, set IMAGEIO_FFMPEG_EXE and PATH.

    The build script places the binary inside a folder named 'ffmpeg' within the
    extracted bundle, so the expected runtime location is `sys._MEIPASS/ffmpeg/ffmpeg.exe`.
    """
    try:
        meipass = getattr(sys, '_MEIPASS', None)
        candidates = []
        if meipass:
            candidates.append(os.path.join(meipass, 'ffmpeg', 'ffmpeg.exe'))
            candidates.append(os.path.join(meipass, 'ffmpeg.exe'))

        # Also check project-local paths when running non-frozen (development)
        base_dir = os.path.dirname(os.path.abspath(__file__))
        candidates.append(os.path.join(base_dir, '..', 'ffmpeg', 'ffmpeg.exe'))
        candidates.append(os.path.join(base_dir, '..', 'ffmpeg.exe'))
        candidates.append(os.path.join(base_dir, 'ffmpeg', 'ffmpeg.exe'))

        for p in candidates:
            if p and os.path.exists(p):
                ff = os.path.abspath(p)
                os.environ['IMAGEIO_FFMPEG_EXE'] = ff
                # Prepend ffmpeg dir to PATH so subprocesses find it
                ff_dir = os.path.dirname(ff)
                os.environ['PATH'] = ff_dir + os.pathsep + os.environ.get('PATH', '')
                try:
                    print(f"Using bundled ffmpeg: {ff}")
                except Exception:
                    pass
                return ff
    except Exception:
        return None


_expose_bundled_ffmpeg()


def _install_exception_hook():
    """Install hooks that write unhandled exceptions to a log file (helps with frozen EXE)."""
    try:
        log_dir = tempfile.gettempdir() or os.path.dirname(os.path.abspath(__file__))
        log_file = os.path.join(log_dir, 'ytme_error.log')

        def _write_log(exc_type, exc, tb):
            try:
                with open(log_file, 'a', encoding='utf-8') as fh:
                    fh.write('\n----- Unhandled Exception (%s) -----\n' % (datetime.datetime.utcnow().isoformat()))
                    traceback.print_exception(exc_type, exc, tb, file=fh)
                    fh.write('\n')
            except Exception:
                pass
            # Also fallback to default hook so crashes still show in console when available
            try:
                sys.__excepthook__(exc_type, exc, tb)
            except Exception:
                pass

        sys.excepthook = _write_log

        # threading.excepthook available starting Python 3.8
        try:
            import threading
            def _thread_excepthook(args):
                # args: threading.ExceptHookArgs
                try:
                    with open(log_file, 'a', encoding='utf-8') as fh:
                        fh.write('\n----- Unhandled Thread Exception (%s) -----\n' % (datetime.datetime.utcnow().isoformat()))
                        traceback.print_exception(args.exc_type, args.exc_value, args.exc_traceback, file=fh)
                        fh.write('\n')
                except Exception:
                    pass
            threading.excepthook = _thread_excepthook
        except Exception:
            pass
    except Exception:
        pass


_install_exception_hook()

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
    # Install a simple Qt message filter to hide specific font warnings
    try:
        if qInstallMessageHandler is not None:
            def _qt_msg_handler(msg_type, context, message):
                try:
                    text = message if isinstance(message, str) else str(message)
                except Exception:
                    text = ''
                if 'OpenType support missing for' in text:
                    return
                # fallback to default behaviour (print)
                sys.__stderr__.write(text + "\n")
            qInstallMessageHandler(_qt_msg_handler)
    except Exception:
        pass

    from PyQt5.QtWidgets import QApplication
    import sys
    app = QApplication(sys.argv)
    # Set a default, available font to avoid platform-specific fallbacks
    try:
        if QFont is not None:
            app.setFont(QFont('Segoe UI', 10))
    except Exception:
        pass
    window = YouTubeMusicExtractorGUI()
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
