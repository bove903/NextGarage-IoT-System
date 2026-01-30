# mqtt_handler.py
from umqtt.simple import MQTTClient as UMQTTClient
import time
import json

class MQTTHandler:
    """Gestione MQTT per Smart Parking System"""
    
    def __init__(self, config, on_message_callback=None):
        self.config = config
        self.client = None
        self.connected = False
        self.on_message_callback = on_message_callback
        self.last_publish = {}
        
    def connect(self):
        """Connessione al broker MQTT"""
        try:
            # Usa broker pubblico HiveMQ se non configurato
            broker = self.config.MQTT_BROKER if hasattr(self.config, 'MQTT_BROKER') else "broker.hivemq.com"
            port = self.config.MQTT_PORT if hasattr(self.config, 'MQTT_PORT') else 1883
            
            self.client = UMQTTClient(
                client_id="nextgarage-esp32",
                server=broker,
                port=port,
                keepalive=60
            )
            
            # Imposta callback per messaggi in arrivo
            self.client.set_callback(self._on_message)
            
            self.client.connect()
            self.connected = True
            print(f"MQTT connected to {broker}:{port}")
            
            # Subscribe ai topic di comando e configurazione
            self._subscribe_topics()
            
            return True
            
        except Exception as e:
            print(f"MQTT connection failed: {e}")
            self.connected = False
            return False
    
    def _subscribe_topics(self):
        """Subscribe ai topic necessari"""
        topics = [
            b"parking/cmd/#",           # Comandi
            b"parking/cfg/#"            # Configurazioni
        ]
        
        for topic in topics:
            try:
                self.client.subscribe(topic)
                print(f"Subscribed to {topic.decode()}")
            except Exception as e:
                print(f"Subscribe failed for {topic.decode()}: {e}")
    
    def _on_message(self, topic, msg):
        """Callback per messaggi ricevuti"""
        try:
            topic_str = topic.decode()
            msg_str = msg.decode()
            
            print(f"MQTT RX: {topic_str} = {msg_str}")
            
            # Chiama il callback esterno se definito
            if self.on_message_callback:
                self.on_message_callback(topic_str, msg_str)
                
        except Exception as e:
            print(f"Error processing message: {e}")
    
    def publish(self, topic, value, retain=False):
        """Pubblica un messaggio"""
        if not self.connected:
            return False
            
        try:
            full_topic = f"parking/{topic}"
            
            # Converti in stringa se necessario
            if isinstance(value, (int, float)):
                payload = str(value)
            elif isinstance(value, bool):
                payload = "1" if value else "0"
            elif isinstance(value, dict):
                payload = json.dumps(value)
            else:
                payload = str(value)
            
            self.client.publish(full_topic.encode(), payload.encode(), retain=retain)
            self.last_publish[topic] = time.ticks_ms()
            return True
            
        except Exception as e:
            print(f"Publish failed: {e}")
            self.connected = False
            return False
    
    def publish_telemetry(self, data):
        """Pubblica telemetria completa"""
        # Stato cancello
        if 'gate_state' in data:
            self.publish('state/gate', data['gate_state'], retain=True)
        
        # Stato posto auto
        if 'spot_occupied' in data:
            spot_text = "OCCUPATO" if data['spot_occupied'] else "LIBERO"
            self.publish('state/spot', spot_text, retain=True)
        
        # Distanza ultrasuoni
        if 'distance' in data:
            self.publish('ultrasonic/distance', data['distance'])
        
        # Luminosità
        if 'light' in data:
            self.publish('env/light', data['light'])
        
        # Allarme gas
        if 'gas_alarm' in data:
            gas_text = "ALLARME!" if data['gas_alarm'] else "OK"
            self.publish('alarms/gas', gas_text, retain=True)
        
        # Livello gas
        if 'gas_level' in data:
            self.publish('sensors/gas', data['gas_level'])
    
    def check_messages(self):
        """Controlla messaggi in arrivo (non bloccante)"""
        if self.connected:
            try:
                self.client.check_msg()
                return True
            except Exception as e:
                print(f"Check messages failed: {e}")
                self.connected = False
                return False
        return False
    
    def disconnect(self):
        """Disconnessione dal broker"""
        if self.connected and self.client:
            try:
                self.client.disconnect()
            except:
                pass
            self.connected = False
    
    def reconnect(self):
        """Tentativo di riconnessione"""
        self.disconnect()
        time.sleep(2)
        return self.connect()