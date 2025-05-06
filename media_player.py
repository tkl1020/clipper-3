# Media player functionality for video and audio playback

import os
from PyQt5.QtCore import QUrl, Qt, QTimer, QDir
from PyQt5.QtWidgets import QMessageBox, QFileDialog, QApplication
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from moviepy.editor import VideoFileClip
from utils import format_time

class MediaPlayerController:
    def __init__(self, parent):
        """Initialize media player functionality
        
        Args:
            parent: The parent VideoTranscriberEditor instance
        """
        self.parent = parent
        self.video_file_path = None
        self.audio_path = None
        self.video_clip = None
        self.current_time = 0
        self.is_playing = False
        self.is_audio_only = False
        
        # Initialize media player component
        self.setup_media_player()
        
        # Connect signals
        self.connect_signals()
        
    def setup_media_player(self):
        """Set up the media player components"""
        # Create the media player that will handle the video playback
        self.parent.media_player = QMediaPlayer(None, QMediaPlayer.VideoSurface)
        self.parent.media_player.setVideoOutput(self.parent.video_widget)
        
        # Create timer to update playback position
        self.parent.update_timer = QTimer(self.parent)
        self.parent.update_timer.setInterval(100)  # Update every 100 milliseconds
    
    def connect_signals(self):
        """Connect media player signals"""
        # Connect media player events to functions
        self.parent.media_player.stateChanged.connect(self.media_state_changed)
        self.parent.media_player.durationChanged.connect(self.duration_changed)
        self.parent.media_player.error.connect(self.handle_error)
        self.parent.update_timer.timeout.connect(self.update_playback_position)
        
        # Connect UI controls to functions
        self.parent.load_button.clicked.connect(self.load_media)
        self.parent.play_button.clicked.connect(self.toggle_play)
        self.parent.timeline_slider.sliderMoved.connect(self.seek_position)
        self.parent.volume_slider.valueChanged.connect(self.change_volume)
    
    def load_media(self):
        """Load a video or audio file"""
        file_dialog = QFileDialog(self.parent)
        file_dialog.setFileMode(QFileDialog.ExistingFile)
        file_dialog.setNameFilter("Media Files (*.mp4 *.mov *.avi *.mkv *.mp3 *.wav)")
        if file_dialog.exec_():
            filepath = file_dialog.selectedFiles()[0]
            if not os.path.exists(filepath):
                QMessageBox.critical(self.parent, "Error", "Selected file does not exist.")
                return

            self.video_file_path = filepath
            self.parent.video_file_path = filepath
            self.parent.audio_path = filepath

            # Determine if it's audio or video based on file extension
            audio_extensions = ['.mp3', '.wav', '.flac', '.aac', '.ogg', '.m4a']
            ext = os.path.splitext(filepath)[1].lower()

            try:
                # Always set the media content
                self.parent.media_player.setMedia(QMediaContent(QUrl.fromLocalFile(filepath)))
                
                if ext in audio_extensions:
                    # Load audio file
                    self.is_audio_only = True
                    self.parent.is_audio_only = True
                    self.video_clip = None
                    self.parent.video_clip = None
                else:
                    # Load video file
                    self.is_audio_only = False
                    self.parent.is_audio_only = False
                    self.video_clip = VideoFileClip(filepath)
                    self.parent.video_clip = self.video_clip
                
                # Make sure video elements have proper size
                self.parent.video_widget.setMinimumHeight(360)
                
                self.parent.status_label.setText(f"Loaded: {os.path.basename(filepath)}")
                self.parent.enable_controls(True)
                self.parent.clip_start_time = None
                self.parent.clip_end_time = None
                self.parent.start_entry.clear()
                self.parent.end_entry.clear()
                self.parent.highlights_textbox.clear()
                self.parent.highlights.clear()
                self.parent.current_highlight_index = -1
                self.parent.transcribe_button.setEnabled(True)
                self.parent.prev_highlight_button.setEnabled(False)
                self.parent.next_highlight_button.setEnabled(False)
                
            except Exception as e:
                QMessageBox.critical(self.parent, "Load Error", f"Failed to load media: {str(e)}")
                return
    
    def toggle_play(self):
        """Toggle between play and pause"""
        if self.parent.media_player.state() == QMediaPlayer.PlayingState:
            self.parent.media_player.pause()  # Pause if playing
        else:
            self.parent.media_player.play()   # Play if paused
    
    def media_state_changed(self, state):
        """Handle media state changes (playing/paused)"""
        if state == QMediaPlayer.PlayingState:
            self.parent.play_button.setIcon(self.parent.pause_icon)  # Show pause icon
            self.is_playing = True
            self.parent.is_playing = True
            self.parent.update_timer.start()  # Start the timer that updates time display
        else:
            self.parent.play_button.setIcon(self.parent.play_icon)  # Show play icon
            self.is_playing = False
            self.parent.is_playing = False
            self.parent.update_timer.stop()   # Stop the update timer
    
    def duration_changed(self, duration):
        """Handle when the video duration is determined"""
        duration_sec = duration / 1000  # Convert milliseconds to seconds
        self.parent.timeline_slider.setRange(0, duration)  # Set the slider range
        self.parent.time_label.setText(f"00:00:00 / {format_time(duration_sec)}")
    
    def update_playback_position(self):
        """Update the playback position display while video is playing"""
        if self.is_playing:
            position = self.parent.media_player.position()  # Get current position in ms
            # Update the slider without triggering signals
            self.parent.timeline_slider.blockSignals(True)
            self.parent.timeline_slider.setValue(position)
            self.parent.timeline_slider.blockSignals(False)
            current_sec = position / 1000  # Convert to seconds
            duration_sec = self.parent.media_player.duration() / 1000
            # Update the time display
            self.parent.time_label.setText(f"{format_time(current_sec)} / {format_time(duration_sec)}")
            self.current_time = current_sec
            self.parent.current_time = current_sec
    
    def seek_position(self, position):
        """Jump to a position in the video when slider is moved"""
        self.parent.media_player.setPosition(position)
        self.current_time = position / 1000
        self.parent.current_time = self.current_time
        duration_sec = self.parent.media_player.duration() / 1000
        self.parent.time_label.setText(f"{format_time(self.current_time)} / {format_time(duration_sec)}")
    
    def change_volume(self, value):
        """Adjust volume when slider is moved"""
        self.parent.media_player.setVolume(value)
    
    def handle_error(self):
        """Handle errors in the media player"""
        error_message = self.parent.media_player.errorString()
        self.parent.status_label.setText(f"Error: {error_message}")
        QMessageBox.critical(self.parent, "Media Error", f"An error occurred: {error_message}")