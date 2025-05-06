# Utility functions used across the application

# For resource monitoring function
import psutil  # Import conditionally using try/except if needed
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

def get_resource_limits():
    """
    Determine resource limits based on system capabilities
    Returns batch_size and max_workers
    """
    from config import PSUTIL_AVAILABLE
    
    # Default batch and worker settings
    batch_size = 10
    max_workers = 2
    
    # Try to use psutil for adaptive resource management if available
    if PSUTIL_AVAILABLE:
        try:
            import psutil
            # Adaptive batch sizing based on system resources
            cpu_cores = psutil.cpu_count(logical=False) or 2
            mem_available_gb = psutil.virtual_memory().available / (1024 * 1024 * 1024)
            
            # Adjust batch size based on available resources
            if mem_available_gb > 8 and cpu_cores >= 4:
                batch_size = 20
            elif mem_available_gb > 4 and cpu_cores >= 2:
                batch_size = 10
            else:
                batch_size = 5
            
            max_workers = max(1, min(cpu_cores - 1, 4))  # Leave one core free
        except Exception:
            # Fall back to defaults if there's an error
            pass
    
    return batch_size, max_workers