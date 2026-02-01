# tsl2561.py
import time

# I2C Addresses
TSL2561_ADDR_LOW   = 0x29
TSL2561_ADDR_FLOAT = 0x39
TSL2561_ADDR_HIGH  = 0x49

# Command/register bits
TSL2561_COMMAND_BIT = 0x80
TSL2561_WORD_BIT    = 0x20

# Registers
TSL2561_REGISTER_CONTROL    = 0x00
TSL2561_REGISTER_TIMING     = 0x01
TSL2561_REGISTER_ID         = 0x0A
TSL2561_REGISTER_CHAN0_LOW  = 0x0C
TSL2561_REGISTER_CHAN1_LOW  = 0x0E

# Control values
TSL2561_CONTROL_POWERON  = 0x03
TSL2561_CONTROL_POWEROFF = 0x00

# Integration time values
TSL2561_INTEGRATIONTIME_13MS  = 0x00  # 13.7ms
TSL2561_INTEGRATIONTIME_101MS = 0x01  # 101ms
TSL2561_INTEGRATIONTIME_402MS = 0x02  # 402ms

# Gain values
TSL2561_GAIN_1X  = 0x00
TSL2561_GAIN_16X = 0x10


class TSL2561:
    def __init__(self, i2c, address=TSL2561_ADDR_FLOAT):
        self.i2c = i2c
        self.address = address

        # default configuration
        self.integration_time = TSL2561_INTEGRATIONTIME_402MS
        self.gain = TSL2561_GAIN_1X

        # IMPORTANT: questi attributi devono esistere sempre
        self._enabled = False
        self._delay_ms = 450  # default coerente con 402ms

        # check presenza
        if not self._check_presence():
            raise ValueError("TSL2561 not found at address 0x{:02X}".format(self.address))

        # FIX: power-on logico + stabilizzazione
        self.enable()
        time.sleep_ms(100)

        # applica config (set_integration_time aggiorna anche _delay_ms)
        self.set_integration_time(self.integration_time)
        self.set_gain(self.gain)

    def _check_presence(self):
        try:
            id_reg = self._read_byte(TSL2561_COMMAND_BIT | TSL2561_REGISTER_ID)

            if id_reg in (0x00, 0xFF):
                return False

            # Non forziamo pattern sul nibble alto: alcuni moduli/clone non matchano.
            return True

        except Exception:
            return False

    def _write_byte(self, register, value):
        self.i2c.writeto_mem(self.address, register, bytes([value & 0xFF]))

    def _read_byte(self, register):
        return self.i2c.readfrom_mem(self.address, register, 1)[0]

    def _read_word(self, register):
        data = self.i2c.readfrom_mem(self.address, register, 2)
        return (data[1] << 8) | data[0]

    def enable(self):
        """Power on sensor."""
        self._write_byte(TSL2561_COMMAND_BIT | TSL2561_REGISTER_CONTROL, TSL2561_CONTROL_POWERON)
        self._enabled = True

    def disable(self):
        """Power off sensor."""
        self._write_byte(TSL2561_COMMAND_BIT | TSL2561_REGISTER_CONTROL, TSL2561_CONTROL_POWEROFF)
        self._enabled = False

    def set_integration_time(self, integration_time):
        self.integration_time = integration_time

        # aggiorna timing register = integration + gain
        self._write_byte(
            TSL2561_COMMAND_BIT | TSL2561_REGISTER_TIMING,
            (self.integration_time | self.gain) & 0xFF
        )

        # delay per completare integrazione (con margine)
        if self.integration_time == TSL2561_INTEGRATIONTIME_13MS:
            self._delay_ms = 20
        elif self.integration_time == TSL2561_INTEGRATIONTIME_101MS:
            self._delay_ms = 120
        else:
            self._delay_ms = 450

    def set_gain(self, gain):
        self.gain = gain

        self._write_byte(
            TSL2561_COMMAND_BIT | TSL2561_REGISTER_TIMING,
            (self.integration_time | self.gain) & 0xFF
        )

    def read_raw(self):
        """Read raw values (broadband, infrared)."""
        if not self._enabled:
            self.enable()
            time.sleep_ms(10)

        # attesa integrazione
        time.sleep_ms(self._delay_ms)

        ch0 = self._read_word(TSL2561_COMMAND_BIT | TSL2561_WORD_BIT | TSL2561_REGISTER_CHAN0_LOW)
        ch1 = self._read_word(TSL2561_COMMAND_BIT | TSL2561_WORD_BIT | TSL2561_REGISTER_CHAN1_LOW)

        return ch0, ch1

    def read_lux(self):
        ch0, ch1 = self.read_raw()

        # saturazione
        if ch0 == 0xFFFF or ch1 == 0xFFFF:
            return 0

        # evita divisione per zero
        if ch0 == 0:
            return 0

        # scaling per integrazione (schema tipico)
        if self.integration_time == TSL2561_INTEGRATIONTIME_13MS:
            ch_scale = 0x7517  # 322/11 * 2^10
        elif self.integration_time == TSL2561_INTEGRATIONTIME_101MS:
            ch_scale = 0x0FE7  # 322/81 * 2^10
        else:
            ch_scale = 1 << 10

        # scaling per gain
        if self.gain == TSL2561_GAIN_1X:
            ch_scale <<= 4

        channel0 = (ch0 * ch_scale) >> 10
        channel1 = (ch1 * ch_scale) >> 10

        if channel0 == 0:
            return 0

        ratio = (channel1 << 10) // channel0

        # approssimazione in base al ratio
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

        return max(0, int(lux))