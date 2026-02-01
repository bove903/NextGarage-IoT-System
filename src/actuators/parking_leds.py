import machine

class ParkingLeds:
    def __init__(self, red_pin, green_pin):
        # Inizializza due LED (rosso e verde) come uscite digitali.
        #
        # machine.Pin(..., machine.Pin.OUT) configura il pin come uscita digitale:
        # - .on()  porta il pin a livello logico alto 
        # - .off() porta il pin a livello logico basso
        self.red = machine.Pin(red_pin, machine.Pin.OUT)
        self.green = machine.Pin(green_pin, machine.Pin.OUT)

        # Imposta lo stato iniziale del parcheggio come "libero":
        # LED verde acceso, LED rosso spento.
        self.set_free()
        
    def set_occupied(self):
        """
        Imposta lo stato del parcheggio come "occupato".

        A cosa serve:
        - Segnalazione visiva locale della disponibilità (posto non disponibile).

        Come funziona:
        - Accende il LED rosso.
        - Spegne il LED verde.
        """
        self.red.on()
        self.green.off()
        
    def set_free(self):
        """
        Imposta lo stato del parcheggio come "libero".

        A cosa serve:
        - Segnalazione visiva locale della disponibilità (posto disponibile).

        Come funziona:
        - Spegne il LED rosso.
        - Accende il LED verde.
        """
        self.red.off()
        self.green.on()