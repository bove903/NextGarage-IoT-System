# actuators/parking_light.py
import machine

class ParkingLight:
    def __init__(self, pin):
        self.led = machine.Pin(pin, machine.Pin.OUT)
        self.brightness = 0
        self.off()

    def on(self, brightness=100):
        self.brightness = 100
        self.led.on()

    def off(self):
        self.led.off()
        self.brightness = 0