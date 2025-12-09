"""
TrackOut Package
A modern YouTube music extractor with beautiful GUI
"""

__version__ = "1.0.0"
__author__ = "TrackOut Team"

# Make core functions available at package level
try:
    from .core import (
        sanitize_filename,
        process_cover_art,
        process_single_track,
        check_available_formats
    )
except ImportError:
    # Fallback for when package is not properly installed
    pass

__all__ = [
    'sanitize_filename',
    'process_cover_art', 
    'process_single_track',
    'check_available_formats'
]
