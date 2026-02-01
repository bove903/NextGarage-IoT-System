# sensors/brightness_sensor.py

from tsl2561 import TSL2561


class BrightnessSensor:
    """
    Classe wrapper per il sensore di luce TSL2561.
    Serve a semplificare l'uso del sensore e a gestire errori di connessione.
    """

    def __init__(self, i2c, address=0x39):
        """
        Costruttore della classe.

        Parametri:
        - i2c: oggetto bus I2C già inizializzato (es. machine.I2C)
        - address: indirizzo I2C del sensore (default 0x39)

        Tenta di inizializzare il sensore.
        Se fallisce, imposta connected a False per evitare letture future.
        """
        try:
            self.sensor = TSL2561(i2c, address)

            # Flag che indica che il sensore è correttamente connesso
            self.connected = True
        except Exception as e:
            # In caso di errore di inizializzazione (sensore assente o I2C errato)
            print(f"TSL2561 init error: {e}")

            # Il sensore viene marcato come non connesso
            self.connected = False

    def read_lux(self):
        """
        Legge il livello di luce ambientale in lux.

        Ritorna:
        - valore in lux (float o int a seconda della libreria)
        - 0 se il sensore non è connesso o se avviene un errore
        """

        # Se il sensore non è connesso, evita la lettura
        if not self.connected:
            return 0

        try:
            # Lettura del valore di luminosità già convertito in lux
            return self.sensor.read_lux()
        except Exception as e:
            # In caso di errore durante la lettura
            print(f"TSL2561 read error: {e}")

            self.connected = False
            return 0

    def read_raw(self):
        """
        Legge i valori grezzi del sensore.

        Ritorna:
        - una tupla (channel0, channel1)
          dove:
          - channel0 = luce totale (visibile + infrarossa)
          - channel1 = luce infrarossa
        - (0, 0) se il sensore non è connesso o in caso di errore
        """

        if not self.connected:
            return (0, 0)

        try:
            # Lettura diretta dei valori ADC grezzi del sensore
            return self.sensor.read_raw()
        except:
            # In caso di errore, ritorna valori nulli
            return (0, 0)

    def set_integration_time(self, time_ms):
        """
        Imposta il tempo di integrazione del sensore.

        Parametri:
        - time_ms: tempo desiderato in millisecondi

        Il TSL2561 supporta solo tre tempi fissi:
        - 13 ms
        - 101 ms
        - 402 ms

        Questa funzione mappa un valore arbitrario
        al tempo supportato più vicino.
        """

        # Cambia il parametro solo se il sensore è connesso
        if self.connected:

            # Tempo di integrazione minimo (≈13 ms)
            if time_ms <= 14:
                self.sensor.set_integration_time(0)  # 13ms

            # Tempo di integrazione medio (≈101 ms)
            elif time_ms <= 102:
                self.sensor.set_integration_time(1)  # 101ms

            # Tempo di integrazione massimo (≈402 ms)
            else:
                self.sensor.set_integration_time(2)  # 402ms

    def set_gain(self, gain):
        """
        Imposta il guadagno del sensore.

        Parametri:
        - gain: valore desiderato (1 oppure 16)

        Il guadagno aumenta la sensibilità del sensore:
        - 1  = ambienti molto luminosi
        - 16 = ambienti poco illuminati
        """

        # Imposta il guadagno solo se il sensore è connesso
        if self.connected:

            # La libreria usa:
            # 0  per gain = 1x
            # 16 per gain = 16x
            self.sensor.set_gain(0 if gain == 1 else 16)
