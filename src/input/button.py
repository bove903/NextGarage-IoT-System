# input/button.py
import machine
import time

class Button:
    def __init__(self, pin, pull_up=True, name="Button"):
        self.name = name
        # Con pull-up come nel tuo codice originale
        self.pin = machine.Pin(pin, machine.Pin.IN, machine.Pin.PULL_UP)
        self.last_state = self.pin.value()
        self.press_start = 0
        
    def is_pressed(self):
        """Check if button is pressed - versione semplificata"""
        # Con pull-up: pressed = 0, released = 1
        current = self.pin.value()
        if current == 0 and self.last_state == 1:
            self.last_state = current
            return True
        elif current == 1:
            self.last_state = current
        return False
    
    def get_press_type(self, short_duration=100, long_duration=5000):
        """Get the type of button press - semplificata"""
        current = self.pin.value()
        
        if current == 0:  # Button is pressed
            if self.press_start == 0:
                self.press_start = time.ticks_ms()
            else:
                duration = time.ticks_diff(time.ticks_ms(), self.press_start)
                if duration >= long_duration:
                    return "long_press"
        else:  # Button is released
            if self.press_start > 0:
                duration = time.ticks_diff(time.ticks_ms(), self.press_start)
                self.press_start = 0
                if duration > short_duration and duration < long_duration:
                    return "short_press"
                    
        return "none"