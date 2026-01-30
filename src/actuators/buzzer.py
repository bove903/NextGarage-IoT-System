# actuators/buzzer.py
import machine
import time

class Buzzer:
    def __init__(self, pin):
        self.pwm = machine.PWM(machine.Pin(pin))
        self.pwm.duty(0)
        self.active = False
        self.mode = "off"  # off, parking, alarm
        
    def set_frequency(self, freq):
        """Set frequency for parking assist"""
        self.pwm.freq(freq)
        self.pwm.duty(512)
        self.mode = "parking"
        self.active = True
        
    def start_alarm(self, freq=2000, interval=200):
        """Start alarm buzzer"""
        self.alarm_freq = freq
        self.alarm_interval = interval
        self.alarm_timer = time.ticks_ms()
        self.mode = "alarm"
        self.active = True
        
    def stop_parking_assist(self):
        """Stop parking assist buzzer"""
        if self.mode == "parking":
            self.pwm.duty(0)
            self.active = False
            self.mode = "off"
            
    def stop_alarm(self):
        """Stop alarm buzzer"""
        if self.mode == "alarm":
            self.pwm.duty(0)
            self.active = False
            self.mode = "off"
            
    def stop(self):
        """Stop all buzzer activity"""
        self.pwm.duty(0)
        self.active = False
        self.mode = "off"
        
    def update(self):
        """Update buzzer state (for blinking alarm)"""
        if self.mode == "alarm" and self.active:
            current = time.ticks_ms()
            if time.ticks_diff(current, self.alarm_timer) >= self.alarm_interval:
                if self.pwm.duty() > 0:
                    self.pwm.duty(0)
                else:
                    self.pwm.freq(self.alarm_freq)
                    self.pwm.duty(512)
                self.alarm_timer = current