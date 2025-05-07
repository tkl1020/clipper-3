# Utility functions used across the application

import os
import sys
import gc
import time
from config import PSUTIL_AVAILABLE

def format_time(seconds):
    """Format time in seconds to HH:MM:SS format"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = int(seconds % 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

def parse_time_string(time_str):
    """Parse a time string in HH:MM:SS format to seconds"""
    parts = time_str.split(':')
    if len(parts) == 3:
        hours, minutes, seconds = map(int, parts)
        return hours * 3600 + minutes * 60 + seconds
    elif len(parts) == 2:
        minutes, seconds = map(int, parts)
        return minutes * 60 + seconds
    else:
        try:
            return int(time_str)
        except ValueError:
            raise ValueError("Invalid time format")

def optimize_memory():
    """Force garbage collection and release as much memory as possible"""
    # Force full garbage collection
    gc.collect(2)
    
    # If on Linux, try to release memory back to OS
    if 'linux' in sys.platform:
        try:
            import ctypes
            libc = ctypes.CDLL('libc.so.6')
            libc.malloc_trim(0)
        except:
            pass
    
    # If psutil is available, check memory usage
    if PSUTIL_AVAILABLE:
        try:
            import psutil
            process = psutil.Process()
            memory_info = process.memory_info()
            memory_mb = memory_info.rss / (1024 * 1024)
            return f"Memory usage: {memory_mb:.1f} MB"
        except:
            return "Memory optimized"
    
    return "Memory optimized"

def get_resource_limits(task_type="emotion"):
    """
    Determine resource limits based on system capabilities and current load
    Returns batch_size and max_workers
    
    task_type: "transcription" or "emotion" - different tasks need different optimizations
    """
    # Default batch and worker settings
    batch_size = 10
    max_workers = 2
    
    # Try to use psutil for adaptive resource management if available
    if PSUTIL_AVAILABLE:
        try:
            import psutil
            # Get system specs
            cpu_cores = psutil.cpu_count(logical=False) or 2
            cpu_threads = psutil.cpu_count(logical=True) or 4
            mem_available_gb = psutil.virtual_memory().available / (1024 * 1024 * 1024)
            cpu_percent = psutil.cpu_percent(interval=0.1)
            
            # Current system load factor (0.0-1.0)
            # Higher means system is more loaded, should be more conservative
            load_factor = cpu_percent / 100.0 
            
            # Calculate available cores considering current load
            available_cores = max(1, cpu_cores * (1.0 - load_factor * 0.5))
            
            # Task-specific optimizations
            if task_type == "transcription":
                # Transcription is more memory-intensive
                if mem_available_gb > 8:
                    max_workers = max(1, min(int(available_cores), 2))
                else:
                    max_workers = 1
                
                batch_size = 1  # Transcription doesn't batch well
                
            elif task_type == "emotion":
                # Emotion classification is more CPU-intensive
                # More aggressive batching with lots of memory
                if mem_available_gb > 8 and available_cores >= 3:
                    batch_size = 32
                    max_workers = max(1, min(int(available_cores) - 1, 4))
                elif mem_available_gb > 4 and available_cores >= 2:
                    batch_size = 16
                    max_workers = max(1, min(int(available_cores) - 1, 3)) 
                else:
                    batch_size = 8
                    max_workers = 2
            
            print(f"Resource limits for {task_type}: batch_size={batch_size}, workers={max_workers}")
        except Exception as e:
            print(f"Error determining resources: {e}")
            # Fall back to defaults
            pass
    
    return batch_size, max_workers

def estimate_time_remaining(processed_frames, total_frames, elapsed_time):
    """Estimate time remaining based on processed frames"""
    if processed_frames == 0:
        return "Calculating..."
    
    frames_per_second = processed_frames / elapsed_time
    remaining_frames = total_frames - processed_frames
    
    if frames_per_second > 0:
        seconds_remaining = remaining_frames / frames_per_second
        
        # Format nicely
        if seconds_remaining < 60:
            return f"About {int(seconds_remaining)} seconds"
        elif seconds_remaining < 3600:
            return f"About {int(seconds_remaining / 60)} minutes"
        else:
            hours = int(seconds_remaining / 3600)
            minutes = int((seconds_remaining % 3600) / 60)
            return f"About {hours} hours, {minutes} minutes"
    else:
        return "Calculating..."