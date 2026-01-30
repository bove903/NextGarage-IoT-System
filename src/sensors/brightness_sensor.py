# sensors/brightness_sensor.py
from tsl2561 import TSL2561

class BrightnessSensor:
    """Wrapper for TSL2561 light sensor"""
    
    def __init__(self, i2c, address=0x39):
        try:
            self.sensor = TSL2561(i2c, address)
            self.connected = True
        except Exception as e:
            print(f"TSL2561 init error: {e}")
            self.connected = False
            
    def read_lux(self):
        """Read light level in lux"""
        if not self.connected:
            return 0
            
        try:
            return self.sensor.read_lux()
        except Exception as e:
            print(f"TSL2561 read error: {e}")
            self.connected = False
            return 0
    
    def read_raw(self):
        """Read raw sensor values"""
        if not self.connected:
            return (0, 0)
            
        try:
            return self.sensor.read_raw()
        except:
            return (0, 0)
    
    def set_integration_time(self, time_ms):
        """Set integration time"""
        if self.connected:
            if time_ms <= 14:
                self.sensor.set_integration_time(0)  # 13ms
            elif time_ms <= 102:
                self.sensor.set_integration_time(1)  # 101ms
            else:
                self.sensor.set_integration_time(2)  # 402ms
    
    def set_gain(self, gain):
        """Set gain (1 or 16)"""
        if self.connected:
            self.sensor.set_gain(0 if gain == 1 else 16) 