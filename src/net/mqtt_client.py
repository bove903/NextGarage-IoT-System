# net/mqtt_client.py
from umqtt.simple import MQTTClient
import time

class MQTTClient:
    def __init__(self, config):
        self.config = config
        self.client = None
        self.connected = False
        
    def connect(self):
        """Connect to MQTT broker"""
        try:
            self.client = MQTTClient(
                client_id="smart_parking",
                server=self.config.MQTT_BROKER,
                port=self.config.MQTT_PORT,
                user=self.config.MQTT_USER,
                password=self.config.MQTT_PASSWORD
            )
            self.client.connect()
            self.connected = True
            print("MQTT connected")
            
            # Subscribe to topics
            self.subscribe("parking/control/#")
            
        except Exception as e:
            print(f"MQTT connection failed: {e}")
            self.connected = False
            
    def publish(self, topic, message):
        """Publish message to topic"""
        if self.connected:
            try:
                full_topic = f"smart_parking/{topic}"
                self.client.publish(full_topic, message)
            except Exception as e:
                print(f"Publish failed: {e}")
                self.connected = False
                
    def subscribe(self, topic):
        """Subscribe to topic"""
        if self.connected:
            try:
                self.client.subscribe(topic)
            except Exception as e:
                print(f"Subscribe failed: {e}")
                
    def check_messages(self):
        """Check for incoming messages"""
        if self.connected:
            try:
                self.client.check_msg()
            except Exception as e:
                print(f"Check messages failed: {e}")
                self.connected = False
                
    def disconnect(self):
        """Disconnect from broker"""
        if self.connected:
            self.client.disconnect()
            self.connected = False