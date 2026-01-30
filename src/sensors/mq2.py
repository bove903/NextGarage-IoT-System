# sensors/mq2.py
import machine
import time

class MQ2Sensor:
    def __init__(self, pin):
        self.adc = machine.ADC(machine.Pin(pin))
        self.adc.atten(machine.ADC.ATTN_11DB)  # Range completo 0-3.3V
        self.adc.width(machine.ADC.WIDTH_12BIT) # 12 bit = 0-4095
        
        # Calibrazione: leggi valore base all'avvio (aria pulita)
        self.baseline = self._read_average(10)
        print(f"MQ2 baseline: {self.baseline}")
        
    def _read_average(self, samples=5):
        total = 0
        for _ in range(samples):
            total += self.adc.read()
            time.sleep_ms(1)  # <--- CAMBIA DA 10 A 1 (o rimuovi del tutto)
        return total // samples
    
    def read_raw(self):
        """Read raw ADC value (0-4095)"""
        return self._read_average(3)
    
    def read_percentage(self):
        """Read gas level as percentage (0-100)"""
        raw = self.read_raw()
        # Converti in percentuale rispetto al massimo
        percentage = min(100, (raw / 4095) * 100)
        return round(percentage, 1)
    
    def get_ppm_estimate(self):
        """Stima approssimativa ppm (non calibrato!)"""
        raw = self.read_raw()
        # Formula semplificata (da calibrare con gas reale)
        # Questo è solo un esempio!
        if raw < self.baseline:
            return 0
        
        delta = raw - self.baseline
        # Stima molto approssimativa
        ppm = (delta / 4095) * 10000  # Max ~10000 ppm
        return int(ppm)