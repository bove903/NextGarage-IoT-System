# sensors/tsl2561.py
import machine
import time

# Constants for TSL2561
TSL2561_ADDR_FLOAT = 0x39  # Default address
TSL2561_ADDR_LOW = 0x29
TSL2561_ADDR_HIGH = 0x49

TSL2561_COMMAND_BIT = 0x80
TSL2561_WORD_BIT = 0x20
TSL2561_REGISTER_CONTROL = 0x00
TSL2561_REGISTER_TIMING = 0x01
TSL2561_REGISTER_CHAN0_LOW = 0x0C
TSL2561_REGISTER_CHAN1_LOW = 0x0E
TSL2561_REGISTER_ID = 0x0A

TSL2561_CONTROL_POWERON = 0x03
TSL2561_CONTROL_POWEROFF = 0x00

TSL2561_INTEGRATIONTIME_13MS = 0x00  # 13.7ms
TSL2561_INTEGRATIONTIME_101MS = 0x01  # 101ms
TSL2561_INTEGRATIONTIME_402MS = 0x02  # 402ms

TSL2561_GAIN_1X = 0x00
TSL2561_GAIN_16X = 0x10

class TSL2561:
    """MicroPython driver for TSL2561 light sensor"""
    
    def __init__(self, i2c, address=TSL2561_ADDR_FLOAT):
        self.i2c = i2c
        self.address = address
        self.integration_time = TSL2561_INTEGRATIONTIME_402MS
        self.gain = TSL2561_GAIN_1X
        self._enabled = False
        
        # Verify sensor is present
        if not self._check_presence():
            raise ValueError("TSL2561 not found at address 0x{:02X}".format(self.address))
        
        # Set default configuration
        self.set_integration_time(self.integration_time)
        self.set_gain(self.gain)
        
    def _check_presence(self):
        """Check if sensor is present"""
        try:
            id_reg = self._read_byte(TSL2561_REGISTER_ID)
            # Check if it's a TSL2561 (bits 4-7 should be 0000 or 0001)
            return (id_reg & 0xF0) in [0x00, 0x10]
        except:
            return False
    
    def _write_byte(self, register, value):
        """Write a byte to a register"""
        self.i2c.writeto_mem(self.address, register, bytes([value]))
    
    def _read_byte(self, register):
        """Read a byte from a register"""
        return self.i2c.readfrom_mem(self.address, register, 1)[0]
    
    def _read_word(self, register):
        """Read a word (2 bytes) from a register"""
        data = self.i2c.readfrom_mem(self.address, register, 2)
        return (data[1] << 8) | data[0]
    
    def enable(self):
        """Enable the sensor"""
        self._write_byte(TSL2561_COMMAND_BIT | TSL2561_REGISTER_CONTROL,
                        TSL2561_CONTROL_POWERON)
        self._enabled = True
    
    def disable(self):
        """Disable the sensor (power down)"""
        self._write_byte(TSL2561_COMMAND_BIT | TSL2561_REGISTER_CONTROL,
                        TSL2561_CONTROL_POWEROFF)
        self._enabled = False
    
    def set_integration_time(self, integration_time):
        """Set integration time"""
        self.integration_time = integration_time
        self._write_byte(TSL2561_COMMAND_BIT | TSL2561_REGISTER_TIMING,
                        self.integration_time | self.gain)
        
        # Set delay for integration time
        if self.integration_time == TSL2561_INTEGRATIONTIME_13MS:
            self._delay_ms = 15
        elif self.integration_time == TSL2561_INTEGRATIONTIME_101MS:
            self._delay_ms = 120
        else:
            self._delay_ms = 450
    
    def set_gain(self, gain):
        """Set gain (1X or 16X)"""
        self.gain = gain
        self._write_byte(TSL2561_COMMAND_BIT | TSL2561_REGISTER_TIMING,
                        self.integration_time | self.gain)
    
    def read_raw(self):
        """Read raw values from both channels"""
        if not self._enabled:
            self.enable()
        
        # Wait for integration time
        time.sleep_ms(self._delay_ms)
        
        # Read channels
        broadband = self._read_word(TSL2561_COMMAND_BIT | TSL2561_WORD_BIT |
                                   TSL2561_REGISTER_CHAN0_LOW)
        infrared = self._read_word(TSL2561_COMMAND_BIT | TSL2561_WORD_BIT |
                                  TSL2561_REGISTER_CHAN1_LOW)
        
        return broadband, infrared
    
    def read_lux(self):
        """Calculate lux from raw readings"""
        broadband, infrared = self.read_raw()
        
        # Handle saturation
        if broadband == 0xFFFF or infrared == 0xFFFF:
            return 0
        
        # Scale for integration time
        if self.integration_time == TSL2561_INTEGRATIONTIME_13MS:
            ch_scale = 0x7517  # 322/11 * 2^10
        elif self.integration_time == TSL2561_INTEGRATIONTIME_101MS:
            ch_scale = 0x0FE7  # 322/81 * 2^10
        else:
            ch_scale = 1 << 10
        
        # Scale for gain
        if self.gain == TSL2561_GAIN_1X:
            ch_scale = ch_scale << 4
        
        # Scale channels
        channel0 = (broadband * ch_scale) >> 10
        channel1 = (infrared * ch_scale) >> 10
        
        # Avoid division by zero
        if channel0 == 0:
            return 0
        
        # Calculate ratio
        ratio = (channel1 << 10) // channel0
        
        # Calculate lux based on ratio (simplified calculation)
        if ratio <= 0x50:
            lux = (0x030 * channel0 - 0x066 * channel1) // 100
        elif ratio <= 0xA8:
            lux = (0x022 * channel0 - 0x055 * channel1) // 100
        elif ratio <= 0xEC:
            lux = (0x012 * channel0 - 0x037 * channel1) // 100
        elif ratio <= 0x190:
            lux = (0x00E * channel0 - 0x029 * channel1) // 100
        else:
            lux = 0
        
        # Ensure non-negative
        return max(0, lux)
    
    def read_visible(self):
        """Read visible light only"""
        broadband, infrared = self.read_raw()
        visible = broadband - infrared
        return max(0, visible)
