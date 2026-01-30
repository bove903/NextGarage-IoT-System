# actuators/traffic_light.py
import machine
import time

class TrafficLight:
    def __init__(self, red_pin, yellow_pin, green_pin):
        self.red = machine.Pin(red_pin, machine.Pin.OUT)
        self.yellow = machine.Pin(yellow_pin, machine.Pin.OUT)
        self.green = machine.Pin(green_pin, machine.Pin.OUT)
        
    def red_on(self):
        self.all_off()
        self.red.on()
        
    def yellow_on(self):
        self.all_off()
        self.yellow.on()
        
    def green_on(self):
        self.all_off()
        self.green.on()
        
    def red_off(self):
        self.red.off()
        
    def yellow_off(self):
        self.yellow.off()
        
    def green_off(self):
        self.green.off()
        
    def all_off(self):
        self.red.off()
        self.yellow.off()
        self.green.off()
        
    def yellow_toggle(self):
        """Toggle yellow light state"""
        self.yellow.value(not self.yellow.value())