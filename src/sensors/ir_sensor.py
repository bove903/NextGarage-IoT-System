# sensors/ir_sensor.py

import machine
import time


class IRSensor:
    """
    Classe che gestisce un sensore a infrarossi (IR) digitale
    usato tipicamente per il rilevamento di ostacoli.
    """

    def __init__(self, pin, name="IR_Sensor"):
        """
        Costruttore della classe IRSensor.

        Parametri:
        - pin: numero del pin GPIO a cui è collegato il sensore IR
        - name: nome simbolico del sensore (utile per debug o logging)

        Inizializza:
        - il pin come input digitale
        - le variabili di stato per il rilevamento dei cambiamenti
        """

        # Inizializzazione del pin come INPUT digitale
        # NOTA: Non viene abilitata alcuna pull-up o pull-down interna,
        # quindi il comportamento dipende interamente dall'hardware del sensore
        self.pin = machine.Pin(pin, machine.Pin.IN)

        self.name = name

        # Stato precedente del sensore (True = ostacolo rilevato, False = nessun ostacolo)
        self.last_state = False

        # Timestamp (in millisecondi) dell'ultimo cambiamento di stato
        self.last_change = time.ticks_ms()
        
    def read(self):
        """
        Legge lo stato attuale del sensore IR.

        Ritorna:
        - True  → ostacolo rilevato
        - False → nessun ostacolo

        NOTA IMPORTANTE:
        Il sensore restituisce:
        - 0 (LOW) quando rileva un ostacolo
        - 1 (HIGH) quando non rileva nulla

        Per questo motivo il valore viene confrontato con 0.
        """

        # Legge il valore digitale del pin
        # value() == 0 → ostacolo presente
        return self.pin.value() == 0
    
    def is_obstacle(self):
        """
        Metodo di comodo per verificare la presenza di un ostacolo.

        È semplicemente un alias di read(),
        utile per rendere il codice più leggibile.
        """

        # Restituisce lo stato del sensore
        return self.read()
    
    def has_changed(self):
        """
        Verifica se lo stato del sensore è cambiato rispetto
        all'ultima lettura.

        Ritorna:
        - True  → lo stato è cambiato (da ostacolo a libero o viceversa)
        - False → lo stato è rimasto invariato

        In caso di cambiamento:
        - aggiorna last_state
        - aggiorna last_change con il timestamp corrente
        """

        current = self.read()

        # Confronto con lo stato precedente
        if current != self.last_state:

            # Aggiorna lo stato salvato
            self.last_state = current

            # Salva il momento del cambiamento (in millisecondi)
            self.last_change = time.ticks_ms()

            # Indica che è avvenuto un cambiamento
            return True

        # Nessun cambiamento rilevato
        return False
