import machine
import time

class Buzzer:
    def __init__(self, pin):
        # Inizializza un buzzer pilotato in PWM sul pin specificato.
        # - Il duty cycle controlla l'energia inviata (qui si usa come ON/OFF: 0 = spento, 512 ≈ 50%).
        self.pwm = machine.PWM(machine.Pin(pin))
        
        # Imposta subito duty = 0 per garantire che il buzzer parta spento.
        self.pwm.duty(0)
        
        # Flag logico che indica se il buzzer è considerato "attivo" (in uso) dal sistema.
        self.active = False
        
        # Modalità corrente del buzzer:
        # - "off": spento
        # - "parking": assistenza parcheggio (tono continuo variabile)
        # - "alarm": allarme (lampeggio sonoro ON/OFF a intervalli)
        self.mode = "off"  # off, parking, alarm
        
        
    def set_frequency(self, freq):
        """
        Imposta la frequenza del buzzer per la modalità "parking assist".

        A cosa serve:
        - Usato per segnalare la distanza (es. più vicino = beep più acuto o più frequente),
          qui implementato come tono continuo alla frequenza indicata.

        Come funziona:
        - Imposta la frequenza PWM (freq) => determina il tono emesso.
        - Imposta un duty cycle diverso da 0 (512) => attiva fisicamente il buzzer.
        - Aggiorna gli stati interni (mode, active) per indicare che è in modalità parcheggio.
        """
        self.pwm.freq(freq)
        self.pwm.duty(512)
        self.mode = "parking"
        self.active = True
        
        
    def start_alarm(self, freq=2000, interval=200):
        """
        Avvia la modalità "alarm" (allarme) con beep intermittente.

        Parametri:
        - freq: frequenza del tono quando l'allarme è ON (default 2000 Hz).
        - interval: intervallo di commutazione ON/OFF in millisecondi (default 200 ms).
          Ogni 'interval' ms il buzzer passa da acceso a spento (o viceversa).

        Come funziona:
        - Salva le impostazioni dell'allarme (frequenza e intervallo).
        - Salva un timestamp iniziale (alarm_timer) da usare come riferimento temporale.
        - Imposta mode = "alarm" e active = True.
        
        Nota:
        - Il "lampeggio sonoro" non è gestito qui con sleep/blocchi: viene gestito in update()
          tramite controllo del tempo, così il programma può continuare a fare altro.
        """
        self.alarm_freq = freq
        self.alarm_interval = interval
        self.alarm_timer = time.ticks_ms()
        self.mode = "alarm"
        self.active = True
        
    def stop_parking_assist(self):
        """
        Ferma il buzzer solo se è attualmente in modalità "parking".

        A cosa serve:
        - Permette di spegnere l'assistenza parcheggio senza interferire
          con un eventuale allarme (se la modalità non è "parking", non fa nulla).

        Come funziona:
        - Controlla la modalità corrente.
        - Se "parking": duty=0 (buzzer fisicamente spento), active=False e mode="off".
        """
        if self.mode == "parking":
            self.pwm.duty(0)
            self.active = False
            self.mode = "off"
            
            
    def stop_alarm(self):
        """
        Ferma il buzzer solo se è attualmente in modalità "alarm".

        A cosa serve:
        - Spegne l'allarme senza toccare altre modalità (se non è in alarm, non fa nulla).

        Come funziona:
        - Controlla la modalità corrente.
        - Se "alarm": duty=0 (buzzer spento), active=False e mode="off".
        """
        if self.mode == "alarm":
            self.pwm.duty(0)
            self.active = False
            self.mode = "off"
            
            
    def stop(self):
        """
        Arresto generale del buzzer, indipendentemente dalla modalità.

        A cosa serve:
        - Funzione per spegnere il buzzer in ogni situazione.

        Come funziona:
        - duty=0 spegne l'uscita PWM (nessun tono).
        - active=False e mode="off" riportano lo stato interno a riposo.
        """
        self.pwm.duty(0)
        self.active = False
        self.mode = "off"
        
        
    def update(self):
        """
        Aggiorna lo stato del buzzer, usato per implementare l'allarme intermittente.

        A cosa serve:
        - Deve essere chiamata periodicamente dal loop principale.
        - In modalità "alarm" alterna ON/OFF senza bloccare l'esecuzione del programma.

        Come funziona:
        - Se siamo in modalità "alarm" e active=True:
          1) legge il tempo corrente (ticks_ms)
          2) calcola da quanto tempo è passato dall'ultima commutazione (ticks_diff)
          3) se il tempo trascorso >= alarm_interval:
             - se il buzzer è acceso (duty > 0) lo spegne (duty=0)
             - altrimenti lo accende impostando freq e duty
             - aggiorna alarm_timer al tempo corrente (nuovo riferimento)
        
        Dettaglio tecnico:
        - time.ticks_ms() restituisce un contatore millisecondi che può andare in overflow.
        - time.ticks_diff(a, b) gestisce correttamente la differenza anche con overflow,
          evitando bug temporali tipici se si facesse (a - b) direttamente.
        """
        if self.mode == "alarm" and self.active:
            current = time.ticks_ms()
            if time.ticks_diff(current, self.alarm_timer) >= self.alarm_interval:
                # Se il duty è > 0, significa che il PWM sta pilotando il buzzer (stato ON).
                # In tal caso, lo spegniamo mettendo duty=0 (stato OFF).
                if self.pwm.duty() > 0:
                    self.pwm.duty(0)
                else:
                    # Se era OFF, lo riaccendiamo:
                    # - impostiamo la frequenza del tono dell'allarme
                    # - impostiamo duty=512 (circa 50%) per far emettere suono
                    self.pwm.freq(self.alarm_freq)
                    self.pwm.duty(512)
                
                # Aggiorna il riferimento temporale dell'ultima commutazione,
                # così il prossimo toggle avverrà dopo 'alarm_interval' ms da qui.
                self.alarm_timer = current