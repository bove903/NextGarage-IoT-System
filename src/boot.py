# boot.py
import machine
import time
import gc

def boot():
    """System boot sequence"""
    print("NextGarage System Booting...")
    
    # Enable garbage collection
    gc.enable()
    
    # Check power button state
    power_pin = machine.Pin(32, machine.Pin.IN, machine.Pin.PULL_UP)
    
    # If power button is held for 3 seconds on boot, go to deep sleep
    start_time = time.ticks_ms()
    while time.ticks_diff(time.ticks_ms(), start_time) < 3000:
        if power_pin.value() == 1:  # Button released
            break
        time.sleep_ms(100)
    else:
        # Button held for 3 seconds, go to deep sleep
        print("Entering deep sleep...")
        machine.deepsleep()
    
    print("Boot sequence completed")
    print("Free memory:", gc.mem_free())
    
if __name__ == "__main__":
    boot()