# Clip editing functionality

import os
from PyQt5.QtWidgets import QMessageBox, QFileDialog, QApplication
from PyQt5.QtCore import QTimer, QDir
from utils import format_time, parse_time_string

class ClipEditor:
    def __init__(self, parent):
        """Initialize clip editor functionality
        
        Args:
            parent: The parent VideoTranscriberEditor instance
        """
        self.parent = parent
        self.clip_start_time = None
        self.clip_end_time = None
        
        # Connect signals
        self.connect_signals()
    
    def connect_signals(self):
        """Connect clip editor signals"""
        self.parent.start_button.clicked.connect(self.mark_start)
        self.parent.end_button.clicked.connect(self.mark_end)
        self.parent.preview_button.clicked.connect(self.preview_clip)
        self.parent.save_button.clicked.connect(self.save_clip)
        self.parent.apply_manual_button.clicked.connect(self.set_manual_times)
    
    def mark_start(self):
        """Mark the current position as the start of a clip"""
        self.clip_start_time = self.parent.current_time
        self.parent.clip_start_time = self.clip_start_time
        self.parent.start_entry.setText(format_time(self.clip_start_time))
        self.parent.status_label.setText(f"Start marked at {format_time(self.clip_start_time)}")
        self.update_clip_controls()
    
    def mark_end(self):
        """Mark the current position as the end of a clip"""
        self.clip_end_time = self.parent.current_time
        self.parent.clip_end_time = self.clip_end_time
        self.parent.end_entry.setText(format_time(self.clip_end_time))
        self.parent.status_label.setText(f"End marked at {format_time(self.clip_end_time)}")
        self.update_clip_controls()
    
    def set_manual_times(self):
        """Set clip times manually from text input"""
        try:
            # Convert the text entries to seconds
            start_time = parse_time_string(self.parent.start_entry.text())
            end_time = parse_time_string(self.parent.end_entry.text())
            # Check if times are valid
            if start_time >= 0 and end_time > start_time and end_time <= self.parent.video_clip.duration:
                self.clip_start_time = start_time
                self.clip_end_time = end_time
                self.parent.clip_start_time = start_time
                self.parent.clip_end_time = end_time
                self.parent.status_label.setText(f"Manual times set: {format_time(start_time)} to {format_time(end_time)}")
                self.update_clip_controls()
            else:
                raise ValueError("Invalid time range")
        except ValueError:
            QMessageBox.warning(self.parent, "Invalid Time", "Please enter valid times in HH:MM:SS format.")
    
    def preview_clip(self):
        """Preview the selected clip"""
        if self.validate_clip_times():
            # Just seek to the start time and play
            self.parent.media_player.setPosition(int(self.parent.clip_start_time * 1000))
            self.parent.media_player.play()
            
            # Set a timer to stop at the end time
            end_time_ms = int(self.parent.clip_end_time * 1000)
            start_time_ms = int(self.parent.clip_start_time * 1000)
            duration_ms = end_time_ms - start_time_ms
            
            # Create a one-shot timer to stop playback
            QTimer.singleShot(duration_ms, self.parent.media_player.pause)
    
    def save_clip(self):
        """Save the selected clip as a new video file"""
        if self.validate_clip_times():
            try:
                if self.parent.is_audio_only:
                    QMessageBox.warning(self.parent, "Audio Only", "Saving clips is only supported for videos right now.")
                    return

                original_filename = os.path.basename(self.parent.video_file_path)
                name_without_ext = os.path.splitext(original_filename)[0]
                default_output = f"{name_without_ext}_clip_{format_time(self.parent.clip_start_time)}-{format_time(self.parent.clip_end_time)}.mp4"

                output_path, _ = QFileDialog.getSaveFileName(
                    self.parent, 
                    "Save Clip", 
                    os.path.join(QDir.homePath(), default_output), 
                    "Video Files (*.mp4)"
                )
                
                if output_path:
                    self.parent.status_label.setText("Saving clip... Please wait")
                    QMessageBox.processEvents()

                    subclip = self.parent.video_clip.subclip(self.parent.clip_start_time, self.parent.clip_end_time)
                    subclip.write_videofile(output_path, codec='libx264', audio_codec='aac', preset='medium', threads=4)
                    self.parent.status_label.setText(f"Clip saved: {os.path.basename(output_path)}")
            except Exception as e:
                QMessageBox.critical(self.parent, "Save Error", f"Failed to save clip: {str(e)}")
    
    def validate_clip_times(self):
        """Check if clip times are valid"""
        if self.parent.clip_start_time is None or self.parent.clip_end_time is None:
            QMessageBox.warning(self.parent, "Missing Time Markers", "Please mark both start and end times.")
            return False
        if self.parent.clip_end_time <= self.parent.clip_start_time:
            QMessageBox.warning(self.parent, "Invalid Time Range", "End time must be after start time.")
            return False
        if not self.parent.is_audio_only and (self.parent.clip_start_time < 0 or self.parent.clip_end_time > self.parent.video_clip.duration):
            QMessageBox.warning(self.parent, "Out of Range", "Clip times must be within video duration.")
            return False
        return True
    
    def update_clip_controls(self):
        """Update which clip control buttons are enabled based on current state"""
        can_save = (self.parent.clip_start_time is not None and 
                    self.parent.clip_end_time is not None and 
                    self.parent.clip_end_time > self.parent.clip_start_time)
        self.parent.save_button.setEnabled(can_save)
        self.parent.preview_button.setEnabled(can_save)