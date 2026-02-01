# sensors/ultrasonic.py

import machine
import time


class UltrasonicSensor:
    """
    Classe per la gestione di un sensore a ultrasuoni (es. HC-SR04).
    Permette di misurare la distanza di un oggetto tramite l'eco
    di un impulso ultrasonico.
    """

    def __init__(self, trig_pin, echo_pin):
        """
        Costruttore della classe UltrasonicSensor.

        Parametri:
        - trig_pin: pin GPIO collegato al TRIG del sensore
        - echo_pin: pin GPIO collegato all'ECHO del sensore

        Inizializza:
        - il pin TRIG come uscita
        - il pin ECHO come ingresso
        """

        # Pin TRIG configurato come uscita digitale
        self.trig = machine.Pin(trig_pin, machine.Pin.OUT)

        # Pin ECHO configurato come ingresso digitale
        self.echo = machine.Pin(echo_pin, machine.Pin.IN)

        # Assicura che il pin TRIG sia inizialmente LOW
        self.trig.off()
        
    def distance_cm(self):
        """
        Misura la distanza di un oggetto in centimetri.

        Ritorna:
        - distanza in cm (float)
        - -1 in caso di timeout o errore di lettura
        """

        # Porta il pin TRIG a livello HIGH
        self.trig.on()

        # Mantiene HIGH per 10 microsecondi
        # Questo impulso attiva l'emissione dell'onda ultrasonica
        time.sleep_us(10)

        # Riporta il pin TRIG a livello LOW
        self.trig.off()
        
        # Timeout massimo per evitare blocchi infiniti (10 ms)
        timeout = 10000  

        # Timestamp iniziale in microsecondi
        t0 = time.ticks_us()

        # Attende che il pin ECHO passi da LOW a HIGH
        # (significa che l'impulso ultrasonico è stato inviato)
        while self.echo.value() == 0:
            # Se il tempo di attesa supera il timeout, ritorna errore
            if time.ticks_diff(time.ticks_us(), t0) > timeout:
                return -1
                
        # Timestamp quando ECHO diventa HIGH
        t1 = time.ticks_us()

        # Attende che il pin ECHO torni LOW
        # (fine della ricezione dell'eco)
        while self.echo.value() == 1:
            # Se il segnale resta HIGH troppo a lungo, ritorna errore
            if time.ticks_diff(time.ticks_us(), t1) > timeout:
                return -1

        # Timestamp quando ECHO torna LOW
        t2 = time.ticks_us()
        
        # Durata dell'impulso ECHO in microsecondi
        pulse_duration = t2 - t1

        # Calcolo della distanza:
        # 0.0343 cm/us = velocità del suono
        # divisione per 2 perché l'onda va e torna
        distance = pulse_duration * 0.0343 / 2

        # Ritorna la distanza calcolata in centimetri
        return distance
