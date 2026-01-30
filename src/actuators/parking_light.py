# actuators/parking_light.py
import machine

class ParkingLight:
    def __init__(self, pin):
        self.led = machine.PWM(machine.Pin(pin))
        self.led.freq(1000)
        self.brightness = 0
        self.off()
        
    def on(self, brightness=100):
        self.brightness = min(100, max(0, brightness))
        duty = int(self.brightness * 10.23)
        self.led.duty(duty)
        
    def off(self):
        self.led.duty(0)
        self.brightness = 0