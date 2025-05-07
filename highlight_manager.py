# Highlight management functionality

from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtGui import QTextCursor
from PyQt5.QtCore import Qt
from utils import format_time, optimize_memory

class HighlightManager:
    def __init__(self, parent):
        """Initialize highlight management functionality
        
        Args:
            parent: The parent VideoTranscriberEditor instance
        """
        self.parent = parent
        self.highlights = []
        self.current_highlight_index = -1
        
        # Connect signals
        self.connect_signals()
        
        # Handle highlight text box mouse events
        self.setup_highlight_events()
    
    def connect_signals(self):
        """Connect highlight related signals"""
        self.parent.cut_clip_button.clicked.connect(self.handle_highlight_cut)
        self.parent.save_clip_button.clicked.connect(self.handle_highlight_save)
        self.parent.reject_button.clicked.connect(self.handle_highlight_reject)
        self.parent.prev_highlight_button.clicked.connect(self.go_to_previous_highlight)
        self.parent.next_highlight_button.clicked.connect(self.go_to_next_highlight)
    
    def setup_highlight_events(self):
        """Set up highlight textbox mouse events"""
        # Store the original mouse double click event handler
        self.original_double_click = self.parent.highlights_textbox.mouseDoubleClickEvent
        # Replace with our custom handler
        self.parent.highlights_textbox.mouseDoubleClickEvent = self.highlight_double_clicked
        
        # Add hover tracking to show cursor changes
        self.parent.highlights_textbox.setMouseTracking(True)
        self.original_mouse_move = self.parent.highlights_textbox.mouseMoveEvent
        self.parent.highlights_textbox.mouseMoveEvent = self.highlight_mouse_move
    
    def highlight_mouse_move(self, event):
        """Handle mouse movement over highlights to show pointer cursor"""
        cursor = self.parent.highlights_textbox.cursorForPosition(event.pos())
        cursor.select(QTextCursor.LineUnderCursor)
        line = cursor.selectedText()
        
        # Change cursor if over a timestamp line
        if "Highlight #" in line:
            self.parent.highlights_textbox.viewport().setCursor(Qt.PointingHandCursor)
        else:
            self.parent.highlights_textbox.viewport().setCursor(Qt.IBeamCursor)
    
    def display_highlights(self):
        """Display highlights in the highlights text box"""
        self.parent.highlights_textbox.clear()
        
        if not self.highlights:
            self.parent.highlights_textbox.setPlainText("No highlights detected.")
            return
            
        # Add a summary header
        emotion_counts = {}
        for _, _, _, emotion in self.highlights:
            emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1
            
        summary_parts = []
        for emotion, count in emotion_counts.items():
            summary_parts.append(f"{count} {emotion}")
        
        summary = ", ".join(summary_parts)
        self.parent.highlights_textbox.append(f"<h3>Found {len(self.highlights)} highlights: {summary}</h3>")
        self.parent.highlights_textbox.append("<hr>")
        
        # Format for improved timestamp visibility
        for i, (start, end, text, emotion) in enumerate(self.highlights):
            # Create a timestamp that stands out
            highlight_num = i + 1
            duration = end - start
            timestamp_text = f"Highlight #{highlight_num}: {format_time(start)} to {format_time(end)} ({duration:.1f}s)"
            
            # Format the text with HTML to style the timestamp differently
            # Use underline and different color for timestamp
            formatted_text = f'<span style="color:#ff9933; text-decoration:underline; font-weight:bold;">{timestamp_text}</span><br>'
            formatted_text += f"<b>Emotion:</b> {emotion}<br>"
            formatted_text += f"<b>Text:</b> {text}<br>"
            formatted_text += "-" * 50 + "<br><br>"
            
            self.parent.highlights_textbox.append(formatted_text)
    
    def go_to_next_highlight(self):
        """Navigate to the next highlight in the list"""
        if not self.highlights:
            return
            
        # Move to the next highlight
        if self.current_highlight_index < len(self.highlights) - 1:
            self.current_highlight_index += 1
        else:
            # Wrap around to the first highlight
            self.current_highlight_index = 0
            
        # Jump to this highlight
        self.jump_to_current_highlight()
    
    def go_to_previous_highlight(self):
        """Navigate to the previous highlight in the list"""
        if not self.highlights:
            return
            
        # Move to the previous highlight
        if self.current_highlight_index > 0:
            self.current_highlight_index -= 1
        else:
            # Wrap around to the last highlight
            self.current_highlight_index = len(self.highlights) - 1
            
        # Jump to this highlight
        self.jump_to_current_highlight()
    
    def jump_to_current_highlight(self):
        """Jump to the currently selected highlight"""
        if not self.highlights:
            return
            
        if 0 <= self.current_highlight_index < len(self.highlights):
            start_time, end_time, text, emotion = self.highlights[self.current_highlight_index]
            
            # Jump to the start time in the video
            self.parent.media_player.setPosition(int(start_time * 1000))
            self.parent.current_time = start_time
            
            # Set this as the current clip start/end times
            self.parent.clip_start_time = start_time
            self.parent.clip_end_time = end_time
            self.parent.start_entry.setText(format_time(start_time))
            self.parent.end_entry.setText(format_time(end_time))
            self.parent.clip_editor.update_clip_controls()
            
            # Highlight the text in the textbox
            self.highlight_in_textbox(self.current_highlight_index + 1)
            
            # Show a brief preview popup for the clip
            duration = end_time - start_time
            self.parent.status_label.setText(f"Viewing {emotion} highlight #{self.current_highlight_index+1}/{len(self.highlights)} - {duration:.1f}s")
    
    def highlight_in_textbox(self, highlight_num):
        """Highlight the specified highlight number in the text box"""
        # Find the highlight in the text box
        highlight_text = f"Highlight #{highlight_num}:"
        
        # Get the current text
        full_text = self.parent.highlights_textbox.toPlainText()
        
        # Find the position of the highlight
        cursor = self.parent.highlights_textbox.textCursor()
        cursor.setPosition(0)
        self.parent.highlights_textbox.setTextCursor(cursor)
        
        # Use the find method to locate and select the highlight
        if self.parent.highlights_textbox.find(highlight_text):
            # The text is now selected - make sure it's visible
            self.parent.highlights_textbox.ensureCursorVisible()
    
    def highlight_double_clicked(self, event):
        """Handle double-click on a highlight entry"""
        cursor = self.parent.highlights_textbox.cursorForPosition(event.pos())
        cursor.select(QTextCursor.LineUnderCursor)
        selected_line = cursor.selectedText()
        
        # Check if the selected line contains a highlight time
        if "Highlight #" in selected_line:
            try:
                # Extract highlight number
                highlight_num = int(selected_line.split("Highlight #")[1].split(":")[0]) - 1
                if 0 <= highlight_num < len(self.highlights):
                    # Set as the current highlight index and jump to it
                    self.current_highlight_index = highlight_num
                    self.jump_to_current_highlight()
                    
                    # Auto-preview the highlight
                    self.preview_current_highlight()
            except Exception as e:
                print(f"Error processing highlight click: {e}")
    
    def preview_current_highlight(self):
        """Preview the current highlight"""
        if not self.highlights or self.current_highlight_index < 0:
            return
            
        if 0 <= self.current_highlight_index < len(self.highlights):
            start_time, end_time, text, emotion = self.highlights[self.current_highlight_index]
            
            # Seek to start time and play
            self.parent.media_player.setPosition(int(start_time * 1000))
            self.parent.media_player.play()
            
            # Set a timer to stop at end time
            duration_ms = int((end_time - start_time) * 1000)
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(duration_ms, self.parent.media_player.pause)
    
    def handle_highlight_cut(self):
        """Handle cutting the current highlight directly"""
        if not self.highlights or self.current_highlight_index < 0:
            return
            
        # Get currently selected highlight
        if 0 <= self.current_highlight_index < len(self.highlights):
            start_time, end_time, title, emotion = self.highlights[self.current_highlight_index]
            self.parent.clip_start_time = start_time
            self.parent.clip_end_time = end_time
            self.parent.clip_editor.save_clip()
    
    def handle_highlight_save(self):
        """Handle saving the current highlight"""
        if not self.highlights or self.current_highlight_index < 0:
            return
            
        # Similar to cut but just sets the times without saving
        if 0 <= self.current_highlight_index < len(self.highlights):
            start_time, end_time, title, emotion = self.highlights[self.current_highlight_index]
            self.parent.clip_start_time = start_time
            self.parent.clip_end_time = end_time
            self.parent.start_entry.setText(format_time(start_time))
            self.parent.end_entry.setText(format_time(end_time))
            self.parent.clip_editor.update_clip_controls()
            
            # Show confirmation with duration
            duration = end_time - start_time
            self.parent.status_label.setText(f"Set times to {emotion} highlight #{self.current_highlight_index+1} - {duration:.1f}s")
    
    def handle_highlight_reject(self):
        """Handle rejecting/removing a highlight"""
        if not self.highlights or self.current_highlight_index < 0:
            return
            
        # Remove the current highlight
        if 0 <= self.current_highlight_index < len(self.highlights):
            # Get info for status message
            removed_idx = self.current_highlight_index + 1
            
            # Remove the highlight
            self.highlights.pop(self.current_highlight_index)
            
            # Update display
            self.display_highlights()
            
            # Status update
            self.parent.status_label.setText(f"Removed highlight #{removed_idx}. {len(self.highlights)} highlights remaining.")
            
            # Handle case where all highlights are removed
            if not self.highlights:
                self.parent.cut_clip_button.setEnabled(False)
                self.parent.save_clip_button.setEnabled(False)
                self.parent.reject_button.setEnabled(False)
                self.parent.prev_highlight_button.setEnabled(False)
                self.parent.next_highlight_button.setEnabled(False)
                self.parent.highlights_textbox.setPlainText("All highlights have been reviewed.")
                self.current_highlight_index = -1
            else:
                # Adjust current index if needed
                if self.current_highlight_index >= len(self.highlights):
                    self.current_highlight_index = len(self.highlights) - 1
                
                # Jump to new current highlight
                self.jump_to_current_highlight()
                
        # Clean up memory
        optimize_memory()

'''

# Highlight management functionality

from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtGui import QTextCursor
from PyQt5.QtCore import Qt
from utils import format_time

class HighlightManager:
    def __init__(self, parent):
        """Initialize highlight management functionality
        
        Args:
            parent: The parent VideoTranscriberEditor instance
        """
        self.parent = parent
        self.highlights = []
        self.current_highlight_index = -1
        
        # Connect signals
        self.connect_signals()
        
        # Handle highlight text box mouse events
        self.setup_highlight_events()
    
    def connect_signals(self):
        """Connect highlight related signals"""
        self.parent.cut_clip_button.clicked.connect(self.handle_highlight_cut)
        self.parent.save_clip_button.clicked.connect(self.handle_highlight_save)
        self.parent.reject_button.clicked.connect(self.handle_highlight_reject)
        self.parent.prev_highlight_button.clicked.connect(self.go_to_previous_highlight)
        self.parent.next_highlight_button.clicked.connect(self.go_to_next_highlight)
    
    def setup_highlight_events(self):
        """Set up highlight textbox mouse events"""
        # Store the original mouse double click event handler
        self.original_double_click = self.parent.highlights_textbox.mouseDoubleClickEvent
        # Replace with our custom handler
        self.parent.highlights_textbox.mouseDoubleClickEvent = self.highlight_double_clicked
    
    def display_highlights(self):
        """Display highlights in the highlights text box"""
        self.parent.highlights_textbox.clear()
        
        # Format for improved timestamp visibility
        for i, (start, end, text, emotion) in enumerate(self.highlights):
            # Create a timestamp that stands out
            highlight_num = i + 1
            timestamp_text = f"Highlight #{highlight_num}: {format_time(start)} to {format_time(end)}"
            
            # Format the text with HTML to style the timestamp differently
            # Use underline and different color for timestamp
            formatted_text = f'<span style="color:#ff9933; text-decoration:underline;">{timestamp_text}</span><br>'
            formatted_text += f"Text: {text}<br>"
            formatted_text += "-" * 50 + "<br><br>"
            
            self.parent.highlights_textbox.append(formatted_text)
    
    def go_to_next_highlight(self):
        """Navigate to the next highlight in the list"""
        if not self.highlights:
            return
            
        # Move to the next highlight
        if self.current_highlight_index < len(self.highlights) - 1:
            self.current_highlight_index += 1
        else:
            # Wrap around to the first highlight
            self.current_highlight_index = 0
            
        # Jump to this highlight
        self.jump_to_current_highlight()
    
    def go_to_previous_highlight(self):
        """Navigate to the previous highlight in the list"""
        if not self.highlights:
            return
            
        # Move to the previous highlight
        if self.current_highlight_index > 0:
            self.current_highlight_index -= 1
        else:
            # Wrap around to the last highlight
            self.current_highlight_index = len(self.highlights) - 1
            
        # Jump to this highlight
        self.jump_to_current_highlight()
    
    def jump_to_current_highlight(self):
        """Jump to the currently selected highlight"""
        if 0 <= self.current_highlight_index < len(self.highlights):
            start_time, end_time, text, emotion = self.highlights[self.current_highlight_index]
            
            # Jump to the start time in the video
            self.parent.media_player.setPosition(int(start_time * 1000))
            self.parent.current_time = start_time
            
            # Set this as the current clip start/end times
            self.parent.clip_start_time = start_time
            self.parent.clip_end_time = end_time
            self.parent.start_entry.setText(format_time(start_time))
            self.parent.end_entry.setText(format_time(end_time))
            self.parent.clip_editor.update_clip_controls()
            
            # Highlight the text in the textbox
            self.highlight_in_textbox(self.current_highlight_index + 1)
            
            self.parent.status_label.setText(f"Viewing {emotion} highlight #{self.current_highlight_index+1}/{len(self.highlights)}")
    
    def highlight_in_textbox(self, highlight_num):
        """Highlight the specified highlight number in the text box"""
        # Find the highlight in the text box
        highlight_text = f"Highlight #{highlight_num}:"
        
        # Get the current text
        full_text = self.parent.highlights_textbox.toPlainText()
        
        # Find the position of the highlight
        cursor = self.parent.highlights_textbox.textCursor()
        cursor.setPosition(0)
        self.parent.highlights_textbox.setTextCursor(cursor)
        
        # Use the find method to locate and select the highlight
        if self.parent.highlights_textbox.find(highlight_text):
            # The text is now selected - make sure it's visible
            self.parent.highlights_textbox.ensureCursorVisible()
    
    def highlight_double_clicked(self, event):
        """Handle double-click on a highlight entry"""
        cursor = self.parent.highlights_textbox.cursorForPosition(event.pos())
        cursor.select(QTextCursor.LineUnderCursor)
        selected_line = cursor.selectedText()
        
        # Check if the selected line contains a highlight time
        if "Highlight #" in selected_line:
            try:
                # Extract highlight number
                highlight_num = int(selected_line.split("Highlight #")[1].split(":")[0]) - 1
                if 0 <= highlight_num < len(self.highlights):
                    # Set as the current highlight index and jump to it
                    self.current_highlight_index = highlight_num
                    self.jump_to_current_highlight()
            except Exception as e:
                print(f"Error processing highlight click: {e}")
    
    def handle_highlight_cut(self):
        """Handle cutting the current highlight directly"""
        if not self.highlights or self.current_highlight_index < 0:
            return
            
        # Get currently selected highlight
        if 0 <= self.current_highlight_index < len(self.highlights):
            start_time, end_time, title, emotion = self.highlights[self.current_highlight_index]
            self.parent.clip_start_time = start_time
            self.parent.clip_end_time = end_time
            self.parent.clip_editor.save_clip()
    
    def handle_highlight_save(self):
        """Handle saving the current highlight"""
        if not self.highlights or self.current_highlight_index < 0:
            return
            
        # Similar to cut but just sets the times without saving
        if 0 <= self.current_highlight_index < len(self.highlights):
            start_time, end_time, title, emotion = self.highlights[self.current_highlight_index]
            self.parent.clip_start_time = start_time
            self.parent.clip_end_time = end_time
            self.parent.start_entry.setText(format_time(start_time))
            self.parent.end_entry.setText(format_time(end_time))
            self.parent.clip_editor.update_clip_controls()
            self.parent.status_label.setText(f"Set times to {emotion} highlight #{self.current_highlight_index+1}")
    
    def handle_highlight_reject(self):
        """Handle rejecting/removing a highlight"""
        if not self.highlights or self.current_highlight_index < 0:
            return
            
        # Remove the current highlight
        if 0 <= self.current_highlight_index < len(self.highlights):
            # Remove the highlight
            self.highlights.pop(self.current_highlight_index)
            
            # Update display
            self.display_highlights()
            
            # Handle case where all highlights are removed
            if not self.highlights:
                self.parent.cut_clip_button.setEnabled(False)
                self.parent.save_clip_button.setEnabled(False)
                self.parent.reject_button.setEnabled(False)
                self.parent.prev_highlight_button.setEnabled(False)
                self.parent.next_highlight_button.setEnabled(False)
                self.parent.highlights_textbox.setPlainText("All highlights have been reviewed.")
                self.current_highlight_index = -1
            else:
                # Adjust current index if needed
                if self.current_highlight_index >= len(self.highlights):
                    self.current_highlight_index = len(self.highlights) - 1
                
                # Jump to new current highlight
                self.jump_to_current_highlight()

'''