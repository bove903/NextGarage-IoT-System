import machine

class ParkingLight:
    def __init__(self, pin):
        # Inizializza una luce/LED di illuminazione parcheggio come uscita digitale.
        self.led = machine.Pin(pin, machine.Pin.OUT)

        # Variabile di stato "logica" che rappresenta la luminosità impostata.
        # In questa implementazione, essendo ON/OFF, ha significato solo indicativo:
        # - 0   => spento
        # - 100 => acceso
        self.brightness = 0

        # Garantisce che all'avvio la luce sia spenta (stato iniziale coerente).
        self.off()

    def on(self, brightness=100):
        """
        Accende la luce del parcheggio.

        Parametri:
        - brightness: valore previsto per rappresentare la luminosità (default 100).
          In questa versione NON viene usato per modulare realmente la luce,
          perché il pin è gestito come digitale (non PWM): quindi è un parametro
          mantenuto per coerenza con un'interfaccia più generale.

        Come funziona:
        - Imposta brightness internamente a 100 (luce considerata "massima").
        - Porta il pin a livello logico alto con .on() => accende la luce.
        
        - Il parametro 'brightness' non influisce sul comportamento: la luce è solo ON/OFF.
        """
        self.brightness = 100
        self.led.on()

    def off(self):
        """
        Spegne la luce del parcheggio.

        Come funziona:
        - Porta il pin a livello logico basso con .off() => spegne la luce.
        - Aggiorna lo stato interno brightness a 0.
        """
        self.led.off()
        self.brightness = 0