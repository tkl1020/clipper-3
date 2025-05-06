# __init__.py - Package initialization file for Clipper
# This file enables Python's package functionality for imports between modules

__version__ = "2.1.0"
__author__ = "Clipper Team"
__description__ = "Video Player + Enhanced AI-Based Highlight Detection"

# Make key classes available at the package level for easier imports
from .gui import VideoTranscriberEditor
from .transcription import TranscriptionWorker