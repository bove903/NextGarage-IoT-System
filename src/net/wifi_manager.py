# net/wifi_manager.py

import network
import time


class WiFiManager:
    """
    Classe che gestisce la connessione WiFi in modalità Station (STA).

    Incapsula:
    - connessione alla rete WiFi
    - disconnessione
    - verifica dello stato di connessione
    """

    def __init__(self, ssid, password):
        """
        Costruttore della classe WiFiManager.

        Parametri:
        - ssid: nome della rete WiFi
        - password: password della rete WiFi
        """

        # Salva SSID e password
        self.ssid = ssid
        self.password = password

        # Inizializza l'interfaccia WiFi in modalità Station
        self.wlan = network.WLAN(network.STA_IF)
        
    def connect(self):
        """
        Connette il dispositivo alla rete WiFi configurata.

        Ritorna:
        - True  → connessione riuscita o già attiva
        - False → connessione fallita
        """

        # Controlla se il dispositivo NON è già connesso
        if not self.wlan.isconnected():
            print(f"Connecting to {self.ssid}...")

            # Attiva l'interfaccia WiFi
            self.wlan.active(True)

            # Avvia la connessione alla rete WiFi
            self.wlan.connect(self.ssid, self.password)
            
            # Attende la connessione (max 10 secondi)
            for _ in range(10):
                # Se la connessione è stabilita
                if self.wlan.isconnected():
                    # Stampa l'indirizzo IP assegnato
                    print(f"Connected! IP: {self.wlan.ifconfig()[0]}")
                    return True

                # Attende 1 secondo prima di ricontrollare
                time.sleep(1)
                
            # Se dopo il timeout non è connesso
            print("Connection failed")
            return False

        # Se era già connesso, ritorna True
        return True
    
    def disconnect(self):
        """
        Disconnette il dispositivo dalla rete WiFi.

        Non disattiva l'interfaccia,
        interrompe solo la connessione corrente.
        """

        self.wlan.disconnect()
        
    def is_connected(self):
        """
        Verifica se il WiFi è attualmente connesso.

        Ritorna:
        - True  → connesso a una rete WiFi
        - False → non connesso
        """

        return self.wlan.isconnected()
