# input/button.py

import machine
import time


class Button:
    """
    Classe per la gestione di un pulsante fisico collegato a un GPIO.
    """

    def __init__(self, pin, pull_up=True, name="Button"):
        """
        Costruttore della classe Button.

        Parametri:
        - pin: numero del GPIO a cui è collegato il pulsante
        - pull_up: mantenuto per compatibilità (non usato direttamente)
        - name: nome logico del pulsante (debug / log)
        """

        self.name = name

        # Configurazione del pin come INPUT con PULL-UP interno
        # Con questa configurazione:
        # - pin.value() == 1 → pulsante NON premuto
        # - pin.value() == 0 → pulsante premuto
        self.pin = machine.Pin(pin, machine.Pin.IN, machine.Pin.PULL_UP)

        # Stato precedente del pulsante (serve per rilevare il fronte di discesa)
        self.last_state = self.pin.value()

        # Timestamp di inizio pressione (in millisecondi)
        # 0 significa "pulsante non premuto"
        self.press_start = 0
        
    def is_pressed(self):
        """
        Verifica se il pulsante è stato appena premuto.

        Rileva il fronte di discesa:
        - da 1 (rilasciato)
        - a 0 (premuto)

        Ritorna:
        - True  → pressione rilevata
        - False → nessuna nuova pressione
        """

        # Lettura stato attuale del pin
        current = self.pin.value()

        # Caso: pulsante appena premuto (1 → 0)
        if current == 0 and self.last_state == 1:
            # Aggiorna lo stato precedente
            self.last_state = current
            return True

        # Caso: pulsante rilasciato
        elif current == 1:
            # Aggiorna lo stato precedente
            self.last_state = current

        # Nessun evento di pressione
        return False
    
    def get_press_type(self, short_duration=100, long_duration=5000):
        """
        Determina il tipo di pressione del pulsante.

        Parametri:
        - short_duration: durata minima (ms) per una pressione breve
        - long_duration: durata minima (ms) per una pressione lunga

        Ritorna:
        - "short_press" → pressione breve
        - "long_press"  → pressione lunga
        - "none"        → nessun evento valido
        """

        # Lettura stato attuale del pin
        current = self.pin.value()
        
        # === PULSANTE PREMUTO ===
        if current == 0:
            # Se è la prima volta che viene premuto
            if self.press_start == 0:
                # Salva il tempo di inizio pressione
                self.press_start = time.ticks_ms()
            else:
                # Calcola la durata della pressione
                duration = time.ticks_diff(time.ticks_ms(), self.press_start)

                # Se supera la soglia di pressione lunga
                if duration >= long_duration:
                    return "long_press"

        # === PULSANTE RILASCIATO ===
        else:
            # Se il pulsante era precedentemente premuto
            if self.press_start > 0:
                # Calcola la durata totale della pressione
                duration = time.ticks_diff(time.ticks_ms(), self.press_start)

                # Reset del timestamp
                self.press_start = 0

                # Se la durata rientra nel range della pressione breve
                if duration > short_duration and duration < long_duration:
                    return "short_press"
                    
        # Nessun evento riconosciuto
        return "none"
