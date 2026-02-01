import machine
import time

class TrafficLight:
    def __init__(self, red_pin, yellow_pin, green_pin):
        # Inizializza i tre LED del semaforo come uscite digitali.
        #
        # machine.Pin(..., machine.Pin.OUT) configura il pin come uscita:
        # - .on()  => livello logico alto
        # - .off() => livello logico basso
        # - .value() permette lettura/scrittura del livello logico (0/1)
        self.red = machine.Pin(red_pin, machine.Pin.OUT)
        self.yellow = machine.Pin(yellow_pin, machine.Pin.OUT)
        self.green = machine.Pin(green_pin, machine.Pin.OUT)
        
    def red_on(self):
        """
        Accende la luce rossa e spegne tutte le altre.

        A cosa serve:
        - Impostare uno stato "mutuamente esclusivo" del semaforo (solo rosso acceso).

        Come funziona:
        - Chiama all_off() per spegnere giallo e verde (e anche rosso, per reset coerente).
        - Poi accende il rosso.
        """
        self.all_off()
        self.red.on()
        
    def yellow_on(self):
        """
        Accende la luce gialla e spegne tutte le altre.

        A cosa serve:
        - Indicare uno stato di attenzione/lampeggio o fase di transizione.

        Come funziona:
        - Spegne tutte le luci con all_off().
        - Accende il giallo.
        """
        self.all_off()
        self.yellow.on()
        
    def green_on(self):
        """
        Accende la luce verde e spegne tutte le altre.

        A cosa serve:
        - Segnalare "via libera" o autorizzazione (es. pronto per apertura in ingresso).

        Come funziona:
        - Spegne tutte le luci con all_off().
        - Accende il verde.
        """
        self.all_off()
        self.green.on()
        
    def red_off(self):
        """
        Spegne la luce rossa.

        A cosa serve:
        - Disattivare selettivamente il rosso senza influire su giallo/verde.

        Come funziona:
        - Porta il pin del rosso a livello logico basso.
        """
        self.red.off()
        
    def yellow_off(self):
        """
        Spegne la luce gialla.

        A cosa serve:
        - Disattivare selettivamente il giallo (utile durante lampeggio controllato da logica esterna).

        Come funziona:
        - Porta il pin del giallo a livello logico basso.
        """
        self.yellow.off()
        
    def green_off(self):
        """
        Spegne la luce verde.

        A cosa serve:
        - Disattivare selettivamente il verde senza influire su rosso/giallo.

        Come funziona:
        - Porta il pin del verde a livello logico basso.
        """
        self.green.off()
        
    def all_off(self):
        """
        Spegne tutte le luci del semaforo (rosso, giallo, verde).

        A cosa serve:
        - Reset dello stato visivo.
        - Garantire che prima di accendere una luce "esclusiva" le altre siano spente.

        Come funziona:
        - Chiama .off() su tutti e tre i pin.
        """
        self.red.off()
        self.yellow.off()
        self.green.off()
        
    def yellow_toggle(self):
        """
        Inverte (toggle) lo stato della luce gialla.

        A cosa serve:
        - Implementare facilmente il lampeggio: chiamando questa funzione a intervalli regolari
          si alterna acceso/spento.

        Come funziona:
        - self.yellow.value() restituisce lo stato corrente (0/1).
        - not ... inverte il booleano (True/False).
        - value(...) imposta il nuovo stato sul pin.
        
        Nota:
        - Questa funzione non impone esclusività (non spegne rosso/verde).
          È pensata per un lampeggio del giallo gestito da logica esterna.
        """
        self.yellow.value(not self.yellow.value())