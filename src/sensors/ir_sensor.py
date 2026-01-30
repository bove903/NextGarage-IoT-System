# sensors/ir_sensor.py
import machine
import time

class IRSensor:
    def __init__(self, pin, name="IR_Sensor"):
        # ATTENZIONE: Senza pull-up interno, come nel tuo codice originale
        self.pin = machine.Pin(pin, machine.Pin.IN)
        self.name = name
        self.last_state = False
        self.last_change = time.ticks_ms()
        
    def read(self):
        """Read sensor state - 0 quando rileva ostacolo"""
        # Esattamente come nel tuo codice: value() == 0 significa ostacolo
        return self.pin.value() == 0
    
    def is_obstacle(self):
        """Check if obstacle is detected"""
        return self.read()
    
    def has_changed(self):
        """Check if state has changed"""
        current = self.read()
        if current != self.last_state:
            self.last_state = current
            self.last_change = time.ticks_ms()
            return True
        return False