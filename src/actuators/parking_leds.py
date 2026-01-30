# actuators/parking_leds.py
import machine

class ParkingLeds:
    def __init__(self, red_pin, green_pin):
        self.red = machine.Pin(red_pin, machine.Pin.OUT)
        self.green = machine.Pin(green_pin, machine.Pin.OUT)
        self.set_free()
        
    def set_occupied(self):
        self.red.on()
        self.green.off()
        
    def set_free(self):
        self.red.off()
        self.green.on()