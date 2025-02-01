class SpeedCalculator:
    def __init__(self, unit='Mbps'):  # Changed default to Mbps as it's more common
        self.unit = unit
        self.conversion_factors = {
            'MBps': 1_048_576,    # 1024 * 1024 (bytes to megabytes)
            'kBps': 1_024,        # 1024 (bytes to kilobytes)
            'Mbps': 8_388_608,    # 1024 * 1024 * 8 (bytes to megabits)
            'Kbps': 8_192         # 1024 * 8 (bytes to kilobits)
        }

    def set_unit(self, unit):
        if unit in self.conversion_factors:
            self.unit = unit
        else:
            raise ValueError(f"Unsupported unit: {unit}. Supported units are: {', '.join(self.conversion_factors.keys())}")

    def convert_speed(self, bytes_received, bytes_sent, old_value):
        # Calculate bytes transferred during the interval
        bytes_received_diff = bytes_received - old_value.bytes_recv
        bytes_sent_diff = bytes_sent - old_value.bytes_sent
        
        # Get the appropriate conversion factor
        conversion_factor = self.get_conversion_factor()
        
        # Calculate speeds
        download_speed = bytes_received_diff / conversion_factor
        upload_speed = bytes_sent_diff / conversion_factor
        
        return download_speed, upload_speed

    def get_conversion_factor(self):
        return self.conversion_factors.get(self.unit, 1_024)  # Default to kBps if unit not found

    def calculate_speed(self, bytes_diff):
        """
        Calculate speed from a bytes difference using the current unit.
        """
        try:
            if bytes_diff < 0:  # Handle counter reset
                return 0
            speed = bytes_diff / self.get_conversion_factor()
            return max(0, speed)  # Ensure non-negative speed
        except Exception as e:
            print(f"Error calculating speed: {e}")
            return 0