# sensors/mq2.py

import machine
import time


class MQ2Sensor:
    """
    Classe per la gestione del sensore di gas MQ-2.
    Il sensore fornisce un'uscita analogica proporzionale
    alla concentrazione di gas rilevati (GPL, metano, fumo, ecc.).
    """

    def __init__(self, pin):
        """
        Costruttore della classe MQ2Sensor.

        Parametri:
        - pin: pin GPIO collegato all'uscita analogica del sensore MQ-2

        Inizializza:
        - il convertitore ADC
        - il range di tensione e la risoluzione
        - una calibrazione di base in aria pulita
        """

        # Inizializzazione dell'ADC sul pin specificato
        self.adc = machine.ADC(machine.Pin(pin))

        # Imposta l'attenuazione a 11 dB
        # Permette di leggere tensioni fino a circa 3.3V
        self.adc.atten(machine.ADC.ATTN_11DB)  

        # Imposta la risoluzione dell'ADC a 12 bit
        # I valori letti vanno da 0 a 4095
        self.adc.width(machine.ADC.WIDTH_12BIT) # 12 bit = 0-4095
        
        # Calibrazione iniziale:
        # Viene letto il valore medio del sensore all'avvio,
        # assumendo che l'ambiente sia in aria pulita
        self.baseline = self._read_average(10)

        # Stampa il valore di baseline per debug o monitoraggio
        print(f"MQ2 baseline: {self.baseline}")
        
    def _read_average(self, samples=5):
        """
        Metodo interno (privato) che legge più campioni ADC
        e ne calcola la media per ridurre il rumore.

        Parametri:
        - samples: numero di letture ADC da effettuare

        Ritorna:
        - valore medio intero delle letture ADC
        """

        total = 0

        # Ciclo per il numero di campioni richiesti
        for _ in range(samples):

            # Lettura del valore analogico dal sensore
            total += self.adc.read()

            # Breve ritardo per stabilizzare le letture successive
            time.sleep_ms(1)  

        # Calcolo della media intera dei campioni
        return total // samples
    
    def read_raw(self):
        """
        Legge il valore grezzo del sensore MQ-2.

        Ritorna:
        - valore ADC compreso tra 0 e 4095

        Usa una media di più letture per maggiore stabilità.
        """

        # Ritorna la media di 3 campioni ADC
        return self._read_average(3)
    
    def read_percentage(self):
        """
        Restituisce una percentuale indicativa del livello di gas.

        Ritorna:
        - valore percentuale tra 0 e 100 (%)

        NOTA:
        Questo valore non rappresenta una misura scientifica,
        ma solo una normalizzazione del valore ADC.
        """

        # Lettura del valore ADC grezzo
        raw = self.read_raw()

        # Conversione del valore ADC in percentuale rispetto al massimo
        # min(100, ...) evita valori superiori al 100%
        percentage = min(100, (raw / 4095) * 100)

        # Arrotonda il valore a una cifra decimale
        return round(percentage, 1)
    
    def get_ppm_estimate(self):
        """
        Stima molto approssimativa della concentrazione di gas in ppm.

        Ritorna:
        - valore stimato in ppm (intero)

        ATTENZIONE:
        - NON è una misura calibrata
        - serve solo come riferimento indicativo
        """

        # Lettura del valore ADC grezzo
        raw = self.read_raw()

        # Se il valore è inferiore alla baseline,
        # si assume che non ci sia gas rilevante
        if raw < self.baseline:
            return 0
        
        # Differenza rispetto alla baseline (aria pulita)
        delta = raw - self.baseline

        # Stima estremamente semplificata della concentrazione
        # Scala il delta su un massimo ipotetico di 10000 ppm
        ppm = (delta / 4095) * 10000  # Max ~10000 ppm

        # Ritorna il valore come intero
        return int(ppm)
