# Transcription functionality using Whisper model

import time
import queue
import threading
import gc
from PyQt5.QtCore import QThread, pyqtSignal
from transformers import pipeline
from config import (
    PYDUB_AVAILABLE, HIGHLIGHT_EMOTIONS, HIGHLIGHT_TIMING,
    HIGHLIGHT_WINDOW_SECONDS, HIGHLIGHT_MIN_SPIKES, HIGHLIGHT_MIN_CLIP_LENGTH,
    HIGHLIGHT_MAX_CLIP_LENGTH, HIGHLIGHT_MIN_EMOTION_INTENSITY,
    HIGHLIGHT_REQUIRED_EMOTION_VARIETY
)

# Load the emotion classification model
classifier = pipeline("text-classification", model="bhadresh-savani/distilbert-base-uncased-emotion", top_k=2)

class TranscriptionWorker(QThread):
    """Worker thread for transcription and highlight detection"""
    progress = pyqtSignal(int)
    live_update = pyqtSignal(str)
    finished = pyqtSignal(list)
    partial_results = pyqtSignal(list)  # Add this signal for compatibility with GUI

    def __init__(self, model, audio_path):
        super().__init__()
        self.model = model
        self.audio_path = audio_path
        
        # Default batch and worker settings if psutil not available
        self.batch_size = 10
        self.max_workers = 2
        
        # Try to use psutil for adaptive resource management if available
        if 'PSUTIL_AVAILABLE' in globals() and PSUTIL_AVAILABLE:
            try:
                # Adaptive batch sizing based on system resources
                cpu_cores = psutil.cpu_count(logical=False) or 2
                mem_available_gb = psutil.virtual_memory().available / (1024 * 1024 * 1024)
                
                # Adjust batch size based on available resources
                if mem_available_gb > 8 and cpu_cores >= 4:
                    self.batch_size = 20
                elif mem_available_gb > 4 and cpu_cores >= 2:
                    self.batch_size = 10
                else:
                    self.batch_size = 5
                
                self.max_workers = max(1, min(cpu_cores - 1, 4))  # Leave one core free
            except Exception:
                # Fall back to defaults if there's an error
                pass
                
        self.use_threading = True  # Enable parallel processing

    def run(self):
        # Get full transcription in one go
        result = self.model.transcribe(
            self.audio_path,
            fp16=False,  # Use fp32 for CPU
            language="en",  # Specify language if known
        )
        
        segments = result['segments']
        total_segments = len(segments)
        
        # Try to detect silence for better segmentation
        silence_timestamps = []
        if PYDUB_AVAILABLE:
            try:
                from pydub import AudioSegment
                from pydub.silence import detect_silence
                
                sound = AudioSegment.from_file(self.audio_path)
                silence_regions = detect_silence(sound, min_silence_len=500, silence_thresh=-40)
                
                # Convert silence regions to timestamps (ms → seconds)
                silence_timestamps = [(start/1000, end/1000) for start, end in silence_regions]
                self.live_update.emit("Located natural breaks in audio for better processing")
            except Exception as e:
                print(f"Silence detection error: {e}")
        
        # Pre-process segments into smaller, uniform chunks
        processed_segments = []
        for segment in segments:
            text = segment['text'].strip()
            start = segment['start']
            end = segment['end']
            
            # Use silence detection for more natural segment breaks if available
            if silence_timestamps:
                # Find silence regions within this segment
                segment_silences = [
                    (s_start, s_end) for s_start, s_end in silence_timestamps 
                    if s_start >= start and s_end <= end
                ]
                
                if segment_silences:
                    # Use silence points as natural breaking points
                    last_point = start
                    for s_start, s_end in segment_silences:
                        if s_start - last_point > 1.0:  # At least 1 second of speech
                            processed_segments.append((last_point, text))
                        last_point = s_end
                    if end - last_point > 1.0:
                        processed_segments.append((last_point, text))
                    continue
            
            # Fall back to time-based chunking if no silences found
            if end - start > 10:
                slice_size = 10  # seconds
                num_slices = int((end - start) // slice_size) + 1
                for slice_idx in range(num_slices):
                    slice_start = start + slice_idx * slice_size
                    slice_end = min(slice_start + slice_size, end)
                    processed_segments.append((slice_start, text))
            else:
                processed_segments.append((start, text))
        
        # Process in batches using a work queue
        work_queue = queue.Queue()
        result_queue = queue.Queue()
        individual_highlights = []
        
        # Fill queue with work
        for segment in processed_segments:
            work_queue.put(segment)
        
        # Worker function for thread pool
        def worker():
            while True:
                try:
                    segment = work_queue.get(timeout=1)
                    if segment is None:  # Sentinel to signal end
                        break
                    result = self._process_segment(segment)
                    if result:
                        result_queue.put(result)
                    work_queue.task_done()
                except queue.Empty:
                    break
                except Exception as e:
                    print(f"Worker error: {e}")
                    work_queue.task_done()
        
        # Add sentinels to stop workers
        for _ in range(self.max_workers):
            work_queue.put(None)
        
        # Create progress tracking variables
        total_items = len(processed_segments)
        completed_items = 0
        
        # Start workers if using threading
        if self.use_threading:
            threads = []
            for _ in range(self.max_workers):
                t = threading.Thread(target=worker)
                t.daemon = True
                t.start()
                threads.append(t)
            
            # Monitor progress while workers are running
            last_update_time = time.time()
            update_interval = 0.5  # seconds
            
            while any(t.is_alive() for t in threads):
                # Calculate approximate progress
                current_size = work_queue.qsize()
                if total_items > 0:
                    completed = total_items - current_size
                    percent_complete = min(100, int((completed / total_items) * 100))
                    
                    # Update progress bar periodically
                    current_time = time.time()
                    if current_time - last_update_time > update_interval:
                        self.progress.emit(percent_complete)
                        last_update_time = current_time
                
                # Process any available results
                highlights_batch = []
                while not result_queue.empty():
                    highlights_batch.append(result_queue.get())
                
                # Send batch updates
                if highlights_batch:
                    highlights_text = "\n".join(f"Potential highlight found: {h[2]}" for h in highlights_batch)
                    self.live_update.emit(highlights_text)
                    individual_highlights.extend(highlights_batch)
                
                # Sleep briefly to prevent high CPU usage in this loop
                time.sleep(0.1)
                
                # Periodically force garbage collection
                if int(current_time) % 5 == 0:
                    gc.collect()
            
            # Wait for all threads to complete
            for t in threads:
                t.join()
        else:
            # Sequential processing fallback
            for i, segment in enumerate(processed_segments):
                result = self._process_segment(segment)
                if result:
                    individual_highlights.append(result)
                    self.live_update.emit(f"Highlight found: {result[2]}")
                
                # Update progress every few items
                if i % 5 == 0:
                    percent_complete = min(100, int((i / total_items) * 100))
                    self.progress.emit(percent_complete)
        
        # Get any remaining results from the queue
        while not result_queue.empty():
            individual_highlights.append(result_queue.get())
        
        # Process detected individual highlights into multi-spike highlights
        self.live_update.emit(f"Analyzing emotional patterns for high-quality highlights...")
        self.live_update.emit(f"Found {len(individual_highlights)} individual emotional moments, looking for patterns...")
        final_highlights = self._find_multi_spike_highlights(individual_highlights)
        
        # Final progress update
        self.progress.emit(100)
        
        # Force garbage collection before finishing
        gc.collect()
        
        self.finished.emit(final_highlights)

    def _process_segment(self, segment_data):
        """Process a single segment and return highlight if found"""
        timestamp, text = segment_data
        try:
            # Pre-compute multiple classifications at once
            prediction = classifier(text)
            
            # Get top emotions and scores
            top_label = prediction[0][0]['label']
            top_score = prediction[0][0]['score']
            
            # Get second highest emotion for context
            second_label = prediction[0][1]['label'] if len(prediction[0]) > 1 else None
            second_score = prediction[0][1]['score'] if len(prediction[0]) > 1 else 0
            
            # Check if top emotion meets threshold
            if top_label in HIGHLIGHT_EMOTIONS and top_score > HIGHLIGHT_EMOTIONS[top_label]:
                # Create highlight with adjusted timestamps based on emotion type
                if top_label in ["surprise", "fear"]:
                    # For surprise or fear, include more lead-up time
                    lead_time, follow_time = HIGHLIGHT_TIMING.get(top_label, HIGHLIGHT_TIMING["default"])
                else:
                    # Default timing for other emotions
                    lead_time, follow_time = HIGHLIGHT_TIMING.get(top_label, HIGHLIGHT_TIMING["default"])
                    
                clip_start = max(0, timestamp + lead_time)  # lead_time is negative
                clip_end = timestamp + follow_time
                
                # Add emotion label to text
                labeled_text = f"[{top_label.upper()} {top_score:.3f}] {text}"
                
                return (clip_start, clip_end, labeled_text, top_label)
        except Exception as e:
            # Silently ignore errors in emotional processing
            pass
        return None
        
    def _find_multi_spike_highlights(self, individual_highlights):
        """
        Find sequences of multiple emotional spikes within a time window.
        Much more selective version that looks for intense emotional variety.
        """
        # If we don't have enough individual highlights, return an empty list
        # (being more selective overall)
        if len(individual_highlights) < HIGHLIGHT_MIN_SPIKES:
            self.live_update.emit(f"Not enough high-confidence emotional moments found. Need at least {HIGHLIGHT_MIN_SPIKES}.")
            return []  # Return empty list, not None
            
        # Sort highlights by start time
        sorted_highlights = sorted(individual_highlights, key=lambda x: x[0])
        
        # List to store our multi-spike clips
        multi_spike_clips = []
        
        # Track segments we've already processed to avoid duplicates
        processed_segments = set()
        
        # Analyze windows to find high-quality emotional segments
        for i in range(len(sorted_highlights) - HIGHLIGHT_MIN_SPIKES + 1):
            # Skip if we've already processed this segment as part of another highlight
            if i in processed_segments:
                continue
                
            start_highlight = sorted_highlights[i]
            start_time = start_highlight[0]
            end_window = start_time + HIGHLIGHT_WINDOW_SECONDS
            
            # Find all highlights that fall within our window
            window_highlights = [h for h in sorted_highlights 
                              if h[0] >= start_time and h[0] <= end_window]
            
            # Skip if we don't have enough spikes in this window
            if len(window_highlights) < HIGHLIGHT_MIN_SPIKES:
                continue
                
            # Check for emotion variety - we want a mix of emotions
            unique_emotions = set(h[3] for h in window_highlights)
            if len(unique_emotions) < HIGHLIGHT_REQUIRED_EMOTION_VARIETY:
                continue
                
            # Check for emotional intensity - look for significant changes
            has_intensity = False
            for j in range(1, len(window_highlights)):
                # Compare consecutive highlight emotions
                prev_highlight = window_highlights[j-1]
                curr_highlight = window_highlights[j]
                
                # If different emotions, consider it intense
                if prev_highlight[3] != curr_highlight[3]:
                    has_intensity = True
                    break
            
            if not has_intensity:
                continue
                
            # Create a clip that spans from the first highlight to the end of the last
            latest_highlight = max(window_highlights, key=lambda h: h[1])
            clip_start = start_time
            
            # Enforce maximum clip length
            raw_end = latest_highlight[1]
            clip_end = min(raw_end, start_time + HIGHLIGHT_MAX_CLIP_LENGTH)
            
            # Ensure minimum length
            clip_end = max(clip_end, clip_start + HIGHLIGHT_MIN_CLIP_LENGTH)
            
            # Combine text for the top 3 most significant highlights
            sorted_by_significance = sorted(window_highlights, key=lambda h: h[3], reverse=True)
            top_highlights = sorted_by_significance[:3]
            combined_text = " → ".join(h[2] for h in top_highlights)
            
            # Create a better label showing emotion variety
            emotion_counts = {}
            for h in window_highlights:
                emotion = h[3]
                emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1
            
            # Format the emotion summary
            emotion_summary = "+".join(f"{count}{emotion[:3].upper()}" for emotion, count in emotion_counts.items())
            
            # Create a multi-spike highlight with better labeling
            multi_spike = (
                clip_start, 
                clip_end,
                f"[{emotion_summary}] {combined_text}", 
                "multi-emotion"
            )
            
            # Add to our list if it doesn't overlap too much with existing clips
            if not self._has_major_overlap(multi_spike, multi_spike_clips, overlap_threshold=0.4):
                multi_spike_clips.append(multi_spike)
                self.live_update.emit(f"High-quality highlight found with {len(window_highlights)} peaks and {len(unique_emotions)} different emotions!")
                
                # Mark all indices in this window as processed to avoid duplicates
                for j, h in enumerate(sorted_highlights):
                    if h[0] >= start_time and h[0] <= end_window:
                        processed_segments.add(j)
        
        # If we found high-quality clips, return those
        if multi_spike_clips:
            self.live_update.emit(f"Found {len(multi_spike_clips)} high-quality highlights meeting strict criteria.")
            return multi_spike_clips
        
        # Otherwise return empty list - being more selective!
        self.live_update.emit("No segments met the strict highlight criteria.")
        return []  # Return empty list, not None
    
    def _has_major_overlap(self, new_clip, existing_clips, overlap_threshold=0.4):
        """Check if new_clip overlaps substantially with any existing clip"""
        new_start, new_end = new_clip[0], new_clip[1]
        new_duration = new_end - new_start
        
        for clip in existing_clips:
            existing_start, existing_end = clip[0], clip[1]
            
            # Find overlap
            overlap_start = max(new_start, existing_start)
            overlap_end = min(new_end, existing_end)
            
            if overlap_end > overlap_start:  # There is an overlap
                overlap_duration = overlap_end - overlap_start
                
                # If overlap is more than threshold of either clip's duration
                if (overlap_duration / new_duration > overlap_threshold or
                    overlap_duration / (existing_end - existing_start) > overlap_threshold):
                    return True
                    
        return False

    @staticmethod
    def optimize_classifier_for_batching(classifier):
        """
        Modify the classifier to accept batches of text
        This is a placeholder - implementation depends on your classifier type
        """
        try:
            return pipeline(
                "text-classification", 
                model=classifier.model,
                tokenizer=classifier.tokenizer,
                batch_size=8,
                truncation=True
            )
        except:
            return classifier  # Default: return original classifier