# net/wifi_manager.py
import network
import time

class WiFiManager:
    def __init__(self, ssid, password):
        self.ssid = ssid
        self.password = password
        self.wlan = network.WLAN(network.STA_IF)
        
    def connect(self):
        """Connect to WiFi"""
        if not self.wlan.isconnected():
            print(f"Connecting to {self.ssid}...")
            self.wlan.active(True)
            self.wlan.connect(self.ssid, self.password)
            
            # Wait for connection
            for _ in range(10):
                if self.wlan.isconnected():
                    print(f"Connected! IP: {self.wlan.ifconfig()[0]}")
                    return True
                time.sleep(1)
                
            print("Connection failed")
            return False
        return True
    
    def disconnect(self):
        """Disconnect from WiFi"""
        self.wlan.disconnect()
        
    def is_connected(self):
        """Check connection status"""
        return self.wlan.isconnected()