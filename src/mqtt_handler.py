from umqtt.simple import MQTTClient as UMQTTClient
import time
import json

class MQTTHandler:
    """Gestione MQTT per Smart Parking System"""
    
    def __init__(self, config, on_message_callback=None):
        # Salva riferimento alla configurazione (broker, porta, parametri vari).
        self.config = config
        
        # Client MQTT reale (istanza di umqtt.simple.MQTTClient) creato in connect().
        self.client = None
        
        # Flag di connessione: True se connesso al broker e utilizzabile per publish/subscribe.
        self.connected = False
        
        # Callback esterna opzionale, chiamata quando arriva un messaggio MQTT.
        # Firma prevista: on_message_callback(topic_str, msg_str)
        self.on_message_callback = on_message_callback
        
        # Dizionario di tracking degli ultimi publish effettuati (timestamp in ms).
        # Utile per debug o per implementare logiche anti-spam/rate-limit (se servissero).
        self.last_publish = {}
        
    def connect(self):
        """Connessione al broker MQTT"""
        try:
            # Determina broker e porta:
            # - se config contiene MQTT_BROKER/MQTT_PORT usa quelli
            # - altrimenti usa HiveMQ pubblico e porta standard 1883
            broker = self.config.MQTT_BROKER if hasattr(self.config, 'MQTT_BROKER') else "broker.hivemq.com"
            port = self.config.MQTT_PORT if hasattr(self.config, 'MQTT_PORT') else 1883
            
            # Crea il client MQTT (umqtt.simple) con:
            # - client_id fisso (identifica il dispositivo sul broker)
            # - server/port del broker
            # - keepalive=60 (ping periodico per mantenere la sessione attiva)
            self.client = UMQTTClient(
                client_id="nextgarage-esp32",
                server=broker,
                port=port,
                keepalive=60
            )
            
            # Imposta la callback interna che verrà chiamata dal client quando arrivano messaggi.
            # Questa callback poi inoltra i messaggi a on_message_callback (se definita).
            self.client.set_callback(self._on_message)
            
            # Connessione al broker (operazione che può sollevare eccezioni).
            self.client.connect()
            self.connected = True
            print(f"MQTT connected to {broker}:{port}")
            
            # Sottoscrive i topic necessari (comandi e configurazioni).
            self._subscribe_topics()
            
            return True
            
        except Exception as e:
            # In caso di errore:
            # - log su seriale
            # - set connected=False per impedire publish successivi
            print(f"MQTT connection failed: {e}")
            self.connected = False
            return False
    
    def _subscribe_topics(self):
        """Subscribe ai topic necessari"""
        # Lista dei topic da sottoscrivere in forma bytes (richiesto da umqtt.simple).
        # 'parking/cmd/#' cattura tutti i sotto-topic dei comandi.
        # 'parking/cfg/#' cattura tutti i sotto-topic delle configurazioni.
        topics = [
            b"parking/cmd/#",           # Comandi
            b"parking/cfg/#"              # Configurazioni
        ]
        
        # Esegue subscribe per ogni topic; eventuali errori vengono loggati ma non bloccano il sistema.
        for topic in topics:
            try:
                self.client.subscribe(topic)
                print(f"Subscribed to {topic.decode()}")
            except Exception as e:
                print(f"Subscribe failed for {topic.decode()}: {e}")
    
    def _on_message(self, topic, msg):
        """Callback per messaggi ricevuti"""
        try:
            # umqtt.simple fornisce topic e msg come bytes: decodifica in stringhe.
            topic_str = topic.decode()
            msg_str = msg.decode()
            
            # Log ricezione (utile per debug e tracciamento integrazione dashboard).
            print(f"MQTT RX: {topic_str} = {msg_str}")
            
            # Se è stato fornito un callback esterno, inoltra il messaggio al livello applicativo.
            if self.on_message_callback:
                self.on_message_callback(topic_str, msg_str)
                
        except Exception as e:
            # Protezione: un errore di decode/parsing/callback non deve rompere la ricezione.
            print(f"Error processing message: {e}")
    
    def publish(self, topic, value, retain=False):
        """Pubblica un messaggio"""
        # Se non connesso, evita di tentare publish (fallirebbe).
        if not self.connected:
            return False
            
        try:
            # Costruisce il topic completo pubblicato:
            # NOTA: aggiunge sempre prefisso "parking/" al topic passato in input.
            # Esempio: topic="state/gate" -> full_topic="parking/state/gate"
            full_topic = f"parking/{topic}"
            
            # Costruisce il payload stringa in base al tipo del value:
            # - numeri => "123" / "12.5"
            # - boolean => "1" o "0" (scelta tipica per sistemi embedded)
            # - dict => JSON
            # - altro => conversione a stringa
            if isinstance(value, (int, float)):
                payload = str(value)
            elif isinstance(value, bool):
                payload = "1" if value else "0"
            elif isinstance(value, dict):
                payload = json.dumps(value)
            else:
                payload = str(value)
            
            # Pubblica su broker:
            # - encode() necessario perché umqtt.simple usa bytes.
            # - retain permette al broker di conservare l'ultimo valore per nuovi subscriber.
            self.client.publish(full_topic.encode(), payload.encode(), retain=retain)
            
            # Salva timestamp dell'ultimo publish per quel topic "relativo" (senza prefisso parking/).
            self.last_publish[topic] = time.ticks_ms()
            return True
            
        except Exception as e:
            # Se publish fallisce, marca la connessione come non valida:
            # spesso indica broker disconnesso o errore rete.
            print(f"Publish failed: {e}")
            self.connected = False
            return False
    
    def publish_telemetry(self, data):
        """Pubblica telemetria completa"""
        # Pubblica un set di variabili di telemetria su topic differenti.
        # Ogni chiave è opzionale: controlla la presenza nel dict 'data'.
        
        # Stato cancello
        if 'gate_state' in data:
            # retain=True per mantenere l'ultimo stato sbarra sulla dashboard.
            self.publish('state/gate', data['gate_state'], retain=True)
        
        # Stato posto auto
        if 'spot_occupied' in data:
            # Converte booleano in stringa leggibile per interfacce (Node-RED/dashboard).
            spot_text = "OCCUPATO" if data['spot_occupied'] else "LIBERO"
            self.publish('state/spot', spot_text, retain=True)
        
        # Distanza ultrasuoni
        if 'distance' in data:
            # In genere non retained: è un valore “stream” che cambia spesso.
            self.publish('ultrasonic/distance', data['distance'])
        
        # Luminosità
        if 'light' in data:
            self.publish('env/light', data['light'])
        
        # Allarme gas
        if 'gas_alarm' in data:
            # Converte booleano in testo di stato.
            gas_text = "ALLARME!" if data['gas_alarm'] else "OK"
            self.publish('alarms/gas', gas_text, retain=True)
        
        # Livello gas
        if 'gas_level' in data:
            self.publish('sensors/gas', data['gas_level'])
    
    def check_messages(self):
        """Controlla messaggi in arrivo (non bloccante)"""
        # check_msg() di umqtt.simple controlla se c'è un messaggio disponibile e,
        # in caso positivo, invoca la callback impostata con set_callback().
        # È non bloccante: se non ci sono messaggi, ritorna subito.
        if self.connected:
            try:
                self.client.check_msg()
                return True
            except Exception as e:
                # In caso di errore, marca la connessione come persa.
                print(f"Check messages failed: {e}")
                self.connected = False
                return False
        return False
    
    def disconnect(self):
        """Disconnessione dal broker"""
        # Effettua una disconnessione “pulita” se il client è presente e connesso.
        if self.connected and self.client:
            try:
                self.client.disconnect()
            except:
                # Ignora eventuali errori in disconnect per robustezza su embedded.
                pass
            self.connected = False
    
    def reconnect(self):
        """Tentativo di riconnessione"""
        # Strategia semplice:
        # 1) disconnette (se necessario)
        # 2) attende 2 secondi (backoff base)
        # 3) ritenta connect()
        self.disconnect()
        time.sleep(2)
        return self.connect()