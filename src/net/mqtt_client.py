# net/mqtt_client.py

from umqtt.simple import MQTTClient
import time


class MQTTClient:
    """
    Classe wrapper per la gestione della comunicazione MQTT.

    Incapsula:
    - connessione al broker MQTT
    - pubblicazione dei messaggi
    - sottoscrizione ai topic
    - gestione dello stato di connessione
    """

    def __init__(self, config):
        """
        Costruttore della classe MQTTClient.

        Parametri:
        - config: oggetto di configurazione che contiene:
            * MQTT_BROKER
            * MQTT_PORT
            * MQTT_USER
            * MQTT_PASSWORD
        """

        # Salva il riferimento alla configurazione
        self.config = config

        # Oggetto MQTTClient reale (creato alla connessione)
        self.client = None

        # Flag che indica se la connessione MQTT è attiva
        self.connected = False
        
    def connect(self):
        """
        Stabilisce la connessione con il broker MQTT.

        - Crea il client MQTT
        - Effettua la connessione al broker
        - Imposta lo stato come connesso
        - Sottoscrive i topic di controllo
        """

        try:
            # Creazione dell'istanza del client MQTT
            self.client = MQTTClient(
                client_id="smart_parking",          # ID univoco del client
                server=self.config.MQTT_BROKER,     # Indirizzo del broker
                port=self.config.MQTT_PORT,         # Porta MQTT
                user=self.config.MQTT_USER,         # Username (se richiesto)
                password=self.config.MQTT_PASSWORD # Password (se richiesta)
            )

            # Connessione al broker MQTT
            self.client.connect()

            # Aggiorna lo stato di connessione
            self.connected = True

            print("MQTT connected")
            
            # Sottoscrizione ai topic di controllo
            # Il carattere '#' indica un wildcard (tutti i sottotopic)
            self.subscribe("parking/control/#")
            
        except Exception as e:
            # In caso di errore di connessione
            print(f"MQTT connection failed: {e}")
            self.connected = False
            
    def publish(self, topic, message):
        """
        Pubblica un messaggio su un topic MQTT.

        Parametri:
        - topic: topic relativo (senza prefisso)
        - message: payload del messaggio (bytes o string)
        """

        # Pubblica solo se il client è connesso
        if self.connected:
            try:
                # Costruisce il topic completo con prefisso di progetto
                full_topic = f"smart_parking/{topic}"

                # Invio del messaggio al broker
                self.client.publish(full_topic, message)

            except Exception as e:
                # In caso di errore durante la pubblicazione
                print(f"Publish failed: {e}")
                self.connected = False
                
    def subscribe(self, topic):
        """
        Sottoscrive un topic MQTT per ricevere messaggi.

        Parametri:
        - topic: topic da sottoscrivere (può contenere wildcard)
        """

        # Sottoscrive solo se connesso
        if self.connected:
            try:
                self.client.subscribe(topic)
            except Exception as e:
                print(f"Subscribe failed: {e}")
                
    def check_messages(self):
        """
        Controlla se sono arrivati nuovi messaggi MQTT.

        - Deve essere chiamata periodicamente nel main loop
        - Non blocca l'esecuzione
        """

        if self.connected:
            try:
                # Verifica la presenza di nuovi messaggi
                # Se presenti, viene chiamato il callback associato
                self.client.check_msg()
            except Exception as e:
                print(f"Check messages failed: {e}")
                self.connected = False
                
    def disconnect(self):
        """
        Disconnette il client dal broker MQTT
        e aggiorna lo stato interno.
        """

        if self.connected:
            self.client.disconnect()
            self.connected = False
