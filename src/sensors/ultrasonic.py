# sensors/ultrasonic.py
import machine
import time

class UltrasonicSensor:
    def __init__(self, trig_pin, echo_pin):
        self.trig = machine.Pin(trig_pin, machine.Pin.OUT)
        self.echo = machine.Pin(echo_pin, machine.Pin.IN)
        self.trig.off()
        
    def distance_cm(self):
        """Measure distance in cm"""
        # Send trigger pulse
        self.trig.on()
        time.sleep_us(10)
        self.trig.off()
        
        # Wait for echo to go high
        timeout = 10000  # 10ms timeout
        t0 = time.ticks_us()
        while self.echo.value() == 0:
            if time.ticks_diff(time.ticks_us(), t0) > timeout:
                return -1
                
        # Measure pulse duration
        t1 = time.ticks_us()
        while self.echo.value() == 1:
            if time.ticks_diff(time.ticks_us(), t1) > timeout:
                return -1
        t2 = time.ticks_us()
        
        # Calculate distance
        pulse_duration = t2 - t1
        distance = pulse_duration * 0.0343 / 2
        return distance