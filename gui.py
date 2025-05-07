# Main GUI components for the Video Transcriber Editor

import os
import whisper
import time
import torch
from PyQt5.QtWidgets import (
    QWidget, QPushButton, QTextEdit, QVBoxLayout, QHBoxLayout,
    QLabel, QProgressBar, QSlider, QStyle, QMessageBox,
    QLineEdit, QFrame, QApplication, QFileDialog
)
from PyQt5.QtCore import Qt, QUrl, QTimer, QDir
from PyQt5.QtGui import QTextCursor, QFont, QColor
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtMultimediaWidgets import QVideoWidget

from config import DEFAULT_WHISPER_MODEL, DARK_THEME_STYLESHEET
from utils import format_time, optimize_memory
from media_player import MediaPlayerController
from clip_editor import ClipEditor
from highlight_manager import HighlightManager
from transcription import TranscriptionWorker

class VideoTranscriberEditor(QWidget):
    def __init__(self):
        super().__init__()  # Initialize the parent class (QWidget)

        # Load the speech recognition model (whisper)
        self.model = whisper.load_model(DEFAULT_WHISPER_MODEL)
        if torch.cuda.is_available():
            self.model = self.model.to("cuda")

        # Initialize variables
        self.video_file_path = None
        self.video_clip = None
        self.current_time = 0
        self.clip_start_time = None
        self.clip_end_time = None
        self.is_playing = False
        self.is_audio_only = False
        self.audio_path = None
        self.full_text = ""
        self.pending_segments = []
        self.current_typing_text = ""
        self.current_char_index = 0
        self.highlights = []
        self.current_highlight_index = -1

        # Timer to control the typing animation
        self.typing_timer = QTimer()
        self.typing_timer.timeout.connect(self.type_next_character)

        # Create a frame for the video player
        self.video_frame = QFrame()
        self.video_frame.setFrameShape(QFrame.StyledPanel)
        self.video_frame.setFrameShadow(QFrame.Raised)
        self.video_frame.setStyleSheet("background-color: #1a130a;")  # Darker background for video

        # Set up the application
        self.setup_window()
        self.create_ui_components()
        self.video_widget = QVideoWidget(self)
        self.video_widget.setMinimumHeight(360)
        self.create_layouts()
        
        # Create controller modules
        self.media_player_controller = MediaPlayerController(self)
        self.clip_editor = ClipEditor(self)
        self.highlight_manager = HighlightManager(self)
        
        # Setup connections after controllers are created
        self.setup_connections()
        
        # Apply theme
        self.apply_dark_theme()

    def setup_window(self):
        """Set up the main application window properties"""
        self.setWindowTitle("Clipper v2.1 - Enhanced AI Highlight Detection")
        self.setGeometry(100, 100, 1200, 800)  # (x, y, width, height)
        self.setMinimumSize(900, 600)          # Minimum allowed window size

    def create_ui_components(self):
        """Create all UI elements (buttons, text boxes, etc.) with optimized sizes"""
        # Video player components
        self.load_button = QPushButton("Load Video")
        self.load_button.setMinimumHeight(30)  # Reduced height

        # Create a custom frame for highlights with ID for CSS styling
        self.highlights_frame = QFrame()
        self.highlights_frame.setObjectName("highlights_frame")
        
        # Play/pause button with icon
        self.play_button = QPushButton()
        self.play_icon = self.style().standardIcon(QStyle.SP_MediaPlay)
        self.pause_icon = self.style().standardIcon(QStyle.SP_MediaPause)
        self.play_button.setIcon(self.play_icon)
        self.play_button.setFixedSize(40, 40)
        self.play_button.setEnabled(False)
        self.play_button.setStyleSheet("QPushButton { color: #ffae42; }")

        # Slider for navigating through the video
        self.timeline_slider = QSlider(Qt.Horizontal)
        self.timeline_slider.setRange(0, 0)
        self.timeline_slider.setTracking(True)

        # Label to show current playback time and total duration
        self.time_label = QLabel("00:00:00 / 00:00:00")

        # Clip editing buttons
        self.start_button = QPushButton("Mark Start")
        self.start_button.setMinimumHeight(30)  # Reduced height
        self.start_button.setEnabled(False)

        self.end_button = QPushButton("Mark End")
        self.end_button.setMinimumHeight(30)  # Reduced height
        self.end_button.setEnabled(False)

        # Preview and Save buttons
        self.preview_button = QPushButton("Preview")
        self.preview_button.setMinimumHeight(30)  # Reduced height
        self.preview_button.setEnabled(False)

        self.save_button = QPushButton("Save")
        self.save_button.setMinimumHeight(30)  # Reduced height
        self.save_button.setEnabled(False)

        # Manual time entry for precise clip control
        self.start_label = QLabel("Start:")
        self.start_entry = QLineEdit()
        self.start_entry.setMaximumWidth(80)

        self.end_label = QLabel("End:")
        self.end_entry = QLineEdit()
        self.end_entry.setMaximumWidth(80)

        self.apply_manual_button = QPushButton("Apply")
        self.apply_manual_button.setMinimumHeight(30)  # Reduced height
        self.apply_manual_button.setEnabled(False)

        # Transcription section label
        self.transcription_label = QLabel("Transcription & AI Detection")
        
        # Transcription components
        self.transcribe_button = QPushButton("Detect Highlights")
        self.transcribe_button.setMinimumHeight(30)  # Reduced height
        self.transcribe_button.setEnabled(False)

        # Save Transcript button
        self.save_transcript_button = QPushButton("Save Transcript")
        self.save_transcript_button.setMinimumHeight(30)  # Reduced height
        self.save_transcript_button.setEnabled(False)

        # Cancel Processing button (initially hidden)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setMinimumHeight(30)  # Reduced height
        self.cancel_button.setStyleSheet("background-color: #8B0000; color: white;")
        self.cancel_button.setVisible(False)

        # Progress bar for transcription status
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)  # Hidden until transcription starts

        # Text display for transcription results
        self.result_textbox = QTextEdit()
        self.result_textbox.setReadOnly(True)
        font = QFont()
        font.setPointSize(10)
        self.result_textbox.setFont(font)
        self.result_textbox.setMaximumHeight(100)  # Limit height for transcription

        # Highlights section
        self.highlights_label = QLabel("AI-DETECTED HIGHLIGHTS")
        font = QFont()
        font.setPointSize(11)
        font.setBold(True)
        self.highlights_label.setFont(font)
        
        self.highlights_textbox = QTextEdit()
        self.highlights_textbox.setReadOnly(True)
        self.highlights_textbox.setFont(QFont())
        self.highlights_textbox.setMinimumHeight(300)  # Increased height

        # Buttons for handling highlights
        self.cut_clip_button = QPushButton("Cut")
        self.cut_clip_button.setMinimumHeight(30)  # Reduced height
        self.cut_clip_button.setEnabled(False)

        self.save_clip_button = QPushButton("Save")
        self.save_clip_button.setMinimumHeight(30)  # Reduced height
        self.save_clip_button.setEnabled(False)

        self.reject_button = QPushButton("Reject")
        self.reject_button.setMinimumHeight(30)  # Reduced height
        self.reject_button.setEnabled(False)
        
        # Navigation buttons
        self.prev_highlight_button = QPushButton("← Prev")
        self.prev_highlight_button.setMinimumHeight(30)  # Reduced height
        self.prev_highlight_button.setEnabled(False)
        
        self.next_highlight_button = QPushButton("Next →")
        self.next_highlight_button.setMinimumHeight(30)  # Reduced height
        self.next_highlight_button.setEnabled(False)

        # Volume control slider
        self.volume_label = QLabel("Vol:")
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(50)
        self.volume_slider.setFixedWidth(80)
        self.volume_slider.setTracking(True)

        # Status label to show information messages
        self.status_label = QLabel("Ready to load video :)")

    def create_layouts(self):
        """Create and arrange all layouts with optimized space usage"""
        # Main layout
        main_layout = QHBoxLayout()
        main_layout.setSpacing(8)  # Reduced spacing
        
        # LEFT SECTION - Video player takes entire left side
        left_section = QVBoxLayout()
        left_section.setSpacing(6)  # Reduced spacing
        
        # Add video player to the frame with no padding
        video_frame_layout = QVBoxLayout()
        video_frame_layout.setContentsMargins(0, 0, 0, 0)
        video_frame_layout.addWidget(self.video_widget)
        self.video_frame.setLayout(video_frame_layout)
        
        # Add the frame to the left section
        left_section.addWidget(self.video_frame, 1)  # Video takes all available space
        
        # Timeline slider just below video
        left_section.addWidget(self.timeline_slider)
        
        # Video playback controls at the bottom
        playback_controls = QHBoxLayout()
        playback_controls.setSpacing(8)  # Reduced spacing
        playback_controls.addWidget(self.play_button)
        playback_controls.addWidget(self.time_label)
        
        # Volume controls
        volume_layout = QHBoxLayout()
        volume_layout.addWidget(self.volume_label)
        volume_layout.addWidget(self.volume_slider)
        volume_layout.setSpacing(4)  # Reduced spacing
        playback_controls.addLayout(volume_layout)
        
        left_section.addLayout(playback_controls)
        
        # Status bar at the bottom of left section
        left_section.addWidget(self.status_label)
        
        # RIGHT SECTION - Controls and highlights with optimized layout
        right_section = QVBoxLayout()
        right_section.setSpacing(8)  # Reduced spacing
        
        # Load video button
        right_section.addWidget(self.load_button)
        
        # Clip editing controls - all in one row to save space
        mark_buttons = QHBoxLayout()
        mark_buttons.addWidget(self.start_button)
        mark_buttons.addWidget(self.end_button)
        mark_buttons.addWidget(self.preview_button)
        mark_buttons.addWidget(self.save_button)
        right_section.addLayout(mark_buttons)
        
        # Manual time entry section - all in one row
        time_entry_layout = QHBoxLayout()
        time_entry_layout.addWidget(self.start_label)
        time_entry_layout.addWidget(self.start_entry)
        time_entry_layout.addWidget(self.end_label)
        time_entry_layout.addWidget(self.end_entry)
        time_entry_layout.addWidget(self.apply_manual_button)
        right_section.addLayout(time_entry_layout)
        
        # Transcription section with compact layout
        right_section.addWidget(self.transcription_label)
        
        # Transcription controls - all in one row
        transcription_buttons = QHBoxLayout()
        transcription_buttons.addWidget(self.transcribe_button)
        transcription_buttons.addWidget(self.save_transcript_button)
        transcription_buttons.addWidget(self.cancel_button)
        right_section.addLayout(transcription_buttons)
        
        right_section.addWidget(self.progress_bar)
        
        # Navigation and action buttons in one row
        highlight_action_row = QHBoxLayout()
        highlight_action_row.addWidget(self.prev_highlight_button)
        highlight_action_row.addWidget(self.next_highlight_button)
        highlight_action_row.addWidget(self.cut_clip_button)
        highlight_action_row.addWidget(self.save_clip_button)
        highlight_action_row.addWidget(self.reject_button)
        right_section.addLayout(highlight_action_row)
        
        # AI-Detected Highlights section - give it more space
        right_section.addWidget(self.highlights_label)
        
        # Make highlights textbox take much more space
        right_section.addWidget(self.highlights_textbox, 3)  # Increased stretch factor
        
        # Add transcription text area with less height priority
        right_section.addWidget(self.result_textbox, 1)
        
        # Set fixed width for right section - slightly narrower
        right_widget = QWidget()
        right_widget.setLayout(right_section)
        right_widget.setFixedWidth(400)  # Reduced from 450
        
        # Add left and right sections to main layout
        main_layout.addLayout(left_section, 1)  # Video side gets all remaining space
        main_layout.addWidget(right_widget, 0)  # Right side has fixed width
        
        # Set the main layout
        self.setLayout(main_layout)
        
    def setup_connections(self):
        """Connect signals and slots for UI elements"""
        # Connect transcription button
        self.transcribe_button.clicked.connect(self.transcribe_video)
        
        # Connect save transcript button
        self.save_transcript_button.clicked.connect(self.save_transcript)
        
        # Connect cancel button
        self.cancel_button.clicked.connect(self.cancel_processing)

    def apply_dark_theme(self):
        """Apply a dark color theme to the application"""
        self.setStyleSheet(DARK_THEME_STYLESHEET)

    def transcribe_video(self):
        """Start the transcription and highlight detection process"""
        if not self.audio_path:
            QMessageBox.warning(self, "No Media", "Please load a video or audio file before transcribing.")
            return

        # Update UI to show processing is starting
        self.status_label.setText("Transcribing and analyzing... please wait.")
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)
        self.result_textbox.clear()
        self.highlights_textbox.clear()
        self.highlights.clear()
        self.current_highlight_index = -1
        
        # Show cancel button and disable transcribe button
        self.cancel_button.setText("Cancel Processing")
        self.cancel_button.setEnabled(True)
        self.cancel_button.setVisible(True)
        self.transcribe_button.setEnabled(False)
        
        QApplication.processEvents()  # Update the UI immediately

        # Reset text variables
        self.full_text = ""
        self.pending_segments.clear()

        # Create and start the worker thread for transcription
        self.worker = TranscriptionWorker(self.model, self.audio_path)
        self.worker.progress.connect(self.update_progress)
        self.worker.live_update.connect(self.animate_typing)
        self.worker.finished.connect(self.handle_transcription_finished)
        
        # Connect partial results signal for chunked processing
        self.worker.partial_results.connect(self.handle_partial_results)
        
        self.worker.start()

    def cancel_processing(self):
        """Cancel the transcription and highlight detection process"""
        if hasattr(self, 'worker') and self.worker.isRunning():
            self.status_label.setText("Cancelling processing... This may take a moment.")
            self.worker.cancel()
            
            # Disable cancel button while cancelling
            self.cancel_button.setText("Cancelling...")
            self.cancel_button.setEnabled(False)

    def handle_partial_results(self, partial_highlights):
        """Handle partial results from processing chunks"""
        # Only use this the first time to allow early reviewing
        if not self.highlights:
            self.highlights = partial_highlights
            self.highlight_manager.highlights = partial_highlights
            
            # Display highlights
            self.highlight_manager.display_highlights()
            self.status_label.setText(f"Found {len(partial_highlights)} potential highlights so far (processing continues)")
            
            # Enable highlight controls
            self.cut_clip_button.setEnabled(True)
            self.save_clip_button.setEnabled(True)
            self.reject_button.setEnabled(True)
            self.prev_highlight_button.setEnabled(True)
            self.next_highlight_button.setEnabled(True)

    def update_progress(self, value):
        """Update the progress bar when transcription advances"""
        self.progress_bar.setValue(value)

    def animate_typing(self, new_text):
        """Create a typing animation for new text segments"""
        if self.typing_timer.isActive():
            # If already typing, add this to queue
            self.pending_segments.append(new_text)
        else:
            # Start typing this text
            self.current_typing_text = new_text
            self.current_char_index = 0
            self.typing_timer.start(20)  # Type a character every 20ms

    def type_next_character(self):
        """Type one character at a time for a more natural appearance"""
        if self.current_char_index < len(self.current_typing_text):
            # Add the next character to the full text
            self.full_text += self.current_typing_text[self.current_char_index]
            self.result_textbox.setPlainText(self.full_text)
            self.result_textbox.moveCursor(QTextCursor.End)  # Scroll to end
            self.current_char_index += 1
        else:
            # Finished typing this segment
            self.typing_timer.stop()
            if self.pending_segments:
                # Start typing the next segment if any
                next_text = self.pending_segments.pop(0)
                self.current_typing_text = next_text
                self.current_char_index = 0
                self.typing_timer.start(20)

    def handle_transcription_finished(self, detected_highlights):
        """Handle when the transcription and highlight detection is finished"""
        self.highlights = detected_highlights
        self.highlight_manager.highlights = detected_highlights
        
        # Hide the cancel button and re-enable transcribe button
        self.cancel_button.setVisible(False)
        self.transcribe_button.setEnabled(True)
        
        # Group highlights by emotion type for summary
        emotion_counts = {}
        for _, _, _, emotion in detected_highlights:
            emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1
        
        if emotion_counts:
            emotion_summary = ", ".join([f"{count} {emotion}" for emotion, count in emotion_counts.items()])
            summary = f"Transcription complete! {len(detected_highlights)} highlights detected: {emotion_summary}"
        else:
            summary = f"Transcription complete! {len(detected_highlights)} highlights detected."
            
        self.status_label.setText(summary)
        self.progress_bar.setVisible(False)
        self.save_transcript_button.setEnabled(True)
        
        # Display highlights in the highlights text box
        if detected_highlights:
            self.highlight_manager.display_highlights()
            self.cut_clip_button.setEnabled(True)
            self.save_clip_button.setEnabled(True)
            self.reject_button.setEnabled(True)
            self.prev_highlight_button.setEnabled(True)
            self.next_highlight_button.setEnabled(True)
        else:
            self.highlights_textbox.setPlainText("No highlights detected in this video.")
            
        # Complete typing any remaining text
        if self.pending_segments:
            for segment in self.pending_segments:
                self.full_text += segment
            self.result_textbox.setPlainText(self.full_text)
            self.result_textbox.moveCursor(QTextCursor.End)
            self.pending_segments.clear()
            
        # Clean up memory
        optimize_memory()

    def save_transcript(self):
        """Save the full transcript to a text file"""
        if not self.full_text:
            QMessageBox.warning(self, "No Transcript", "There is no transcript to save.")
            return
            
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save Transcript", 
            os.path.join(QDir.homePath(), f"{os.path.splitext(os.path.basename(self.video_file_path))[0]}_transcript.txt"),
            "Text Files (*.txt)"
        )
        
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(self.full_text)
                self.status_label.setText(f"Transcript saved to {os.path.basename(filename)}")
            except Exception as e:
                QMessageBox.critical(self, "Save Error", f"Failed to save transcript: {str(e)}")

    def enable_controls(self, enabled):
        """Enable or disable controls based on whether media is loaded"""
        self.play_button.setEnabled(enabled)
        self.start_button.setEnabled(enabled)
        self.end_button.setEnabled(enabled)
        self.preview_button.setEnabled(enabled)
        self.apply_manual_button.setEnabled(enabled)
        self.transcribe_button.setEnabled(enabled)