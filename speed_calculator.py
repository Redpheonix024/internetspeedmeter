import logging
from collections import deque
from time import time

logger = logging.getLogger('NetSpeedMeter')

class SpeedCalculator:
    def __init__(self, unit='KB/s'):
        self.unit = unit
        self.bytes_in_kb = 1024
        self.bytes_in_mb = 1024 * 1024
        # Remove conversion factors as we'll handle conversion dynamically
        
        self.validate_unit(unit)
        self.sample_buffer_size = 10  # Increased from 5
        self.download_samples = deque(maxlen=self.sample_buffer_size)
        self.upload_samples = deque(maxlen=self.sample_buffer_size)
        self.last_measurement_time = time()
        self.min_interval = 0.1  # Minimum interval between measurements

    def validate_unit(self, unit):
        if unit not in ['KB/s', 'MB/s']:
            msg = f"Invalid unit: {unit}. Using default: KB/s"
            logger.warning(msg)
            return 'KB/s'
        return unit

    def set_unit(self, unit):
        if unit in ['KB/s', 'MB/s']:
            self.unit = unit
        else:
            raise ValueError(f"Unsupported unit: {unit}. Supported units are: MB/s, KB/s")

    def calculate_speed(self, bytes_diff, interval):
        """Calculate speed in bytes per second and convert to appropriate unit"""
        try:
            if bytes_diff < 0 or interval <= 0:
                return 0, 'KB/s'
                
            # Calculate raw bytes per second
            bytes_per_second = bytes_diff / interval
            
            # Convert to KB/s
            speed_in_kb = bytes_per_second / 1024
            
            # Choose appropriate unit and format
            if speed_in_kb >= 1024:
                return speed_in_kb / 1024, 'MB/s'
            else:
                return speed_in_kb, 'KB/s'
                
        except Exception as e:
            logger.error(f"Error calculating speed: {e}")
            return 0, 'KB/s'

    def add_sample(self, bytes_diff, is_download=True):
        """Add a new sample with automatic unit selection"""
        current_time = time()
        interval = current_time - self.last_measurement_time
        
        if interval < self.min_interval:
            return None
            
        speed, unit = self.calculate_speed(bytes_diff, interval)
        sample = (current_time, speed, unit)
        
        if is_download:
            self.download_samples.append(sample)
        else:
            self.upload_samples.append(sample)
            
        self.last_measurement_time = current_time
        return speed, unit

    def get_weighted_average(self, samples):
        """Calculate weighted average"""
        if not samples:
            return 0, 'KB/s'
            
        total_weight = 0
        weighted_sum = 0
        current_time = time()
        
        # Use simpler averaging for more accurate readings
        recent_samples = [s for s in samples if (current_time - s[0]) <= 1.0]
        
        if not recent_samples:
            return 0, 'KB/s'
            
        for _, speed, unit in recent_samples:
            # Convert all speeds to KB/s for averaging
            speed_in_kb = speed * 1024 if unit == 'MB/s' else speed
            weighted_sum += speed_in_kb
            total_weight += 1
            
        avg_speed = weighted_sum / total_weight
        
        # Convert back to appropriate unit
        if avg_speed >= 1024:
            return avg_speed / 1024, 'MB/s'
        return avg_speed, 'KB/s'

    def get_current_speeds(self):
        """Get current speeds with units"""
        download_speed, download_unit = self.get_weighted_average(self.download_samples)
        upload_speed, upload_unit = self.get_weighted_average(self.upload_samples)
        return (download_speed, download_unit), (upload_speed, upload_unit)