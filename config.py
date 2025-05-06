# Configuration settings and constants for the Clipper application

# Check for optional dependencies
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

try:
    from pydub import AudioSegment
    from pydub.silence import detect_silence
    PYDUB_AVAILABLE = True
except ImportError:
    PYDUB_AVAILABLE = False

# Default whisper model settings
DEFAULT_WHISPER_MODEL = "tiny"

# Highlight detection thresholds for emotions - much higher thresholds
HIGHLIGHT_EMOTIONS = {
    "joy": 0.995,       # Happy moments
    "surprise": 0.995,  # Unexpected moments
    "anger": 0.995,     # Dramatic or intense moments
    "fear": 0.995,      # Suspenseful moments
    "sadness": 0.995,   # Emotional or touching moments
}

# Multi-spike detection parameters - more stringent requirements
HIGHLIGHT_WINDOW_SECONDS = 45        # Shorter window to concentrate emotions
HIGHLIGHT_MIN_SPIKES = 4             # Require more emotional spikes
HIGHLIGHT_MIN_CLIP_LENGTH = 15       # Minimum clip length in seconds
HIGHLIGHT_MAX_CLIP_LENGTH = 60       # Maximum clip length in seconds
HIGHLIGHT_MIN_EMOTION_INTENSITY = 0.2 # Minimum emotional "jump" to count as significant
HIGHLIGHT_REQUIRED_EMOTION_VARIETY = 2 # Require at least this many different emotion types

# Timing settings for highlight clips based on emotion
HIGHLIGHT_TIMING = {
    "surprise": (-3, 7),  # (lead_time, follow_time)
    "fear": (-3, 7),
    "anger": (-1.5, 10),
    "default": (-2, 8)    # Default for other emotions
}

# UI styling
DARK_THEME_STYLESHEET = """
QWidget {
    background-color: #2b1d0e; /* dark brown */
    color: #ffae42; /* soft orange text */
    border-radius: 3px; /* Very slight rounded corners everywhere */
}
QPushButton {
    background-color: #3c2a17; /* slightly lighter brown */
    color: #ffae42;
    border: 1px solid #5c3b1c;
    padding: 5px;
    border-radius: 4px;
    min-height: 30px; /* Standardize button heights */
    min-width: 80px; /* Set minimum width for buttons */
}
QPushButton:hover {
    background-color: #5c3b1c; /* hover lighter brown */
}
QPushButton:disabled {
    background-color: #2b1d0e;
    color: #7f5a2e;
}
QLineEdit, QTextEdit {
    background-color: #3c2a17;
    color: #ffae42;
    border: 1px solid #5c3b1c;
    border-radius: 4px;
    padding: 3px;
}
QLineEdit {
    max-height: 25px; /* Reduce height of timestamp boxes */
}
QProgressBar {
    background-color: #3c2a17;
    color: #ffae42;
    border: 1px solid #5c3b1c;
    border-radius: 4px;
    text-align: center;
}
QProgressBar::chunk {
    background-color: #ffae42;
    width: 10px;
}
QSlider::groove:horizontal {
    border: 1px solid #5c3b1c;
    height: 8px;
    background: #3c2a17;
    border-radius: 3px;
}
QSlider::handle:horizontal {
    background: #ffae42;
    border: 1px solid #5c3b1c;
    width: 18px;
    margin: -5px 0;
    border-radius: 9px;
}
QLabel {
    color: #ffae42;
    padding: 2px;
}
QFrame {
    border: 1px solid #5c3b1c;
    border-radius: 5px;
}
QFrame#highlights_frame {
    background-color: #2f1f0f; /* Slightly different background to make highlights stand out */
    border: 1px solid #5c3b1c;
    border-radius: 5px;
    margin-top: 10px;
    padding: 5px;
}
"""