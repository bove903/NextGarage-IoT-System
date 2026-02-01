import machine
import time

class ServoGate:
    # Costanti di stato
    # Questi valori identificano gli stati della macchina a stati finiti (FSM) che governa la sbarra.
    # La logica di update() cambia comportamento in base allo stato corrente.
    STATE_IDLE = 0
    STATE_GREEN = 1
    STATE_OPENING = 2
    STATE_WAIT_CLEAR = 3
    STATE_CLOSING = 4
    STATE_MANUAL_OPEN = 5

    def __init__(self, pin, ir_entrance, ir_exit, traffic_light, gate_button, is_parking_full_cb=None):
        # Inizializza il servo tramite PWM a 50 Hz.
        # freq=50 => periodo 20 ms, il duty (ampiezza impulso) determina l'angolo.
        self.servo = machine.PWM(machine.Pin(pin), freq=50)

        # Sensori IR e dispositivi di contesto:
        # - ir_entrance: sensore presenza veicolo lato ingresso
        # - ir_exit: sensore presenza veicolo lato uscita (uscita sempre permessa)
        # - traffic_light: riferimento al semaforo (verde/rosso/giallo) per segnalazioni visive
        # - gate_button: pulsante fisico per richiesta apertura in ingresso
        self.ir_entrance = ir_entrance
        self.ir_exit = ir_exit
        self.traffic_light = traffic_light
        self.gate_button = gate_button

        # Callback che ritorna True se il parcheggio è pieno.
        # Serve per bloccare gli ingressi automatici (ma NON le uscite).
        self.is_parking_full_cb = is_parking_full_cb

        # --- DEFINIZIONE LOGICA (Il "cervello" pensa così) ---
        # Questi sono gli angoli LOGICI usati dall'algoritmo:
        # - SERVO_DOWN = 0  => sbarra chiusa
        # - SERVO_UP   = 90 => sbarra aperta
        self.SERVO_DOWN = 0   # Logicamente Chiusa
        self.SERVO_UP = 90       # Logicamente Aperta

        # PARAMETRI OTTIMIZZATI
        # SERVO_STEP: incremento/decremento dell'angolo ad ogni step di movimento.
        # SERVO_INTERVAL: tempo minimo (ms) tra uno step e il successivo.
        # Questi due parametri determinano la "velocità" e la fluidità di apertura/chiusura.
        self.SERVO_STEP = 2
        self.SERVO_INTERVAL = 30     # 30ms

        # SAFE_DELAY: tempo (ms) in cui entrambi i sensori devono risultare "liberi"
        # prima di autorizzare la chiusura automatica (evita chiusure immediate per transitori).
        self.SAFE_DELAY = 1000

        # Stato iniziale: sbarra ferma (IDLE) e chiusa.
        self.state = self.STATE_IDLE

        # servo_angle: angolo logico corrente della sbarra.
        # target_angle: angolo logico obiettivo verso cui il servo deve muoversi.
        self.servo_angle = self.SERVO_DOWN
        self.target_angle = self.SERVO_DOWN

        # Applica fisicamente la posizione iniziale al servo.
        self.set_servo(self.servo_angle)

        # Timestamp/variabili temporali per gestire eventi periodici senza bloccare:
        # - last_blink: ultimo istante in cui è stato togglato il giallo lampeggiante
        # - last_servo_move: ultimo istante in cui è stato fatto uno step del servo
        # - clear_start: istante in cui entrambi i sensori risultano liberi (per SAFE_DELAY)
        self.last_blink = 0
        self.last_servo_move = 0
        self.clear_start = 0

        # Flag di comandi remoti (via MQTT):
        # - remote_open_requested: richiesta di apertura remota
        # - remote_close_requested: richiesta di chiusura remota
        #
        # Questi flag vengono consumati in update() (una volta letti vengono azzerati).
        self.remote_open_requested = False
        self.remote_close_requested = False

        # manual_mode: indica se l'apertura è stata richiesta "manuale/remota"
        # e quindi la sbarra deve restare aperta (STATE_MANUAL_OPEN) finché non arriva close.
        self.manual_mode = False

        # Flag “riassuntivo” del movimento, aggiornato in update().
        # (Non calcola la differenza tra angolo e target: riflette solo lo stato della FSM.)
        self.is_moving_flag = False

    def set_servo(self, logic_angle):
        """
        Imposta l'angolo del servo applicando una inversione software.

        A cosa serve:
        - Il codice ragiona in termini LOGICI (0 = chiuso, 90 = aperto).
        - Per vincoli di montaggio/meccanica, l'angolo fisico potrebbe essere invertito.
          Qui si traduce: LOGICO 0->90  in FISICO 90->0.

        Come funziona:
        1) Clamp dell'angolo logico in [0, 180] per sicurezza.
        2) Calcolo dell'angolo fisico: physical_angle = 90 - logic_angle.
           - Se logic_angle = 0  => physical_angle = 90
           - Se logic_angle = 90 => physical_angle = 0
        3) Mappatura dell'angolo fisico in duty_u16:
           duty = 1700 + (physical_angle * 6500) // 180
           - 1700 è un offset minimo di impulso (in unità u16 del PWM)
           - 6500 è l'escursione utile
           - divisione intera // 180 per scalare su 0..180 gradi
        4) Invio del duty al PWM e aggiornamento dello stato interno servo_angle (logico).
        """
        # Converte in intero e limita l'angolo logico a un range sicuro.
        logic_angle = int(max(0, min(180, logic_angle)))

        # Inversione software: il verso fisico del servo è invertito rispetto alla logica.
        physical_angle = 90 - logic_angle

        # Anche l'angolo fisico viene clampato per evitare valori fuori range.
        physical_angle = int(max(0, min(180, physical_angle)))

        # Conversione angolo -> duty PWM (16-bit).
        # Formula lineare: offset + scala*(angolo/180).
        duty = 1700 + (physical_angle * 6500) // 180

        # Imposta il duty in formato u16 (0..65535) per pilotare il servo.
        self.servo.duty_u16(duty)

        # Salva l'angolo LOGICO corrente (quello usato dalla FSM).
        self.servo_angle = logic_angle

    def is_moving(self):
        """
        Ritorna True se la sbarra è in movimento (apertura/chiusura) e non ha ancora raggiunto il target.

        Come funziona:
        - Se lo stato è OPENING o CLOSING, confronta servo_angle con target_angle.
        - Se servo_angle != target_angle significa che non ha ancora completato il movimento.
        - In tutti gli altri stati ritorna False.
        """
        if self.state in [self.STATE_OPENING, self.STATE_CLOSING]:
            return self.servo_angle != self.target_angle
        return False

    def request_open(self):
        """
        Richiede l'apertura remota della sbarra.

        A cosa serve:
        - chiamata quando arriva un comando esterno (MQTT).

        Come funziona:
        - Imposta un flag (remote_open_requested) che verrà processato in update().
        - Imposta manual_mode=True: l'apertura viene considerata "manuale/remota",
          quindi dopo l'apertura completa si andrà nello stato STATE_MANUAL_OPEN
          (sbarra mantenuta aperta finché non arriva una richiesta di chiusura).
        """
        self.remote_open_requested = True
        self.manual_mode = True

    def request_close(self):
        """
        Richiede la chiusura remota della sbarra.

        A cosa serve:
        - chiamata da remoto per chiudere una sbarra mantenuta aperta manualmente.

        Come funziona:
        - Imposta un flag (remote_close_requested) che verrà processato in update().
        - La chiusura effettiva avverrà solo in stati compatibili (WAIT_CLEAR / MANUAL_OPEN)
          e solo se i sensori risultano liberi (entrambi a 1).
        """
        self.remote_close_requested = True

    def update(self):
        """
        Aggiorna la macchina a stati della sbarra.

        A cosa serve:
        - Deve essere chiamata ciclicamente nel loop principale.
        - Gestisce: comandi remoti, logica ingresso/uscita, apertura/chiusura graduale,
          lampeggio giallo, sicurezza in chiusura (SAFE_DELAY).

        Come funziona:
        - Usa time.ticks_ms() come clock non bloccante.
        - Implementa una FSM con stati:
          IDLE -> GREEN -> OPENING -> WAIT_CLEAR -> CLOSING
          e un ramo MANUAL_OPEN per aperture manuali/remoto.
        """
        # Timestamp corrente in ms (gestione corretta overflow con ticks_diff).
        now = time.ticks_ms()

        # Flag movimento basato sullo stato: utile per telemetria o logica esterna.
        self.is_moving_flag = (self.state in [self.STATE_OPENING, self.STATE_CLOSING])

        # COMANDI REMOTI
        # Gestione prioritaria: se arriva un comando remoto, lo processiamo subito
        # e in molti casi facciamo "return" per evitare di eseguire altra logica nello stesso ciclo.
        if self.remote_open_requested:
            # Consuma il comando: lo azzera per evitare di ripeterlo nei cicli successivi.
            self.remote_open_requested = False

            # Se non stiamo già aprendo e non siamo già in stato di apertura manuale,
            # avviamo un'apertura forzata.
            if self.state not in [self.STATE_OPENING, self.STATE_MANUAL_OPEN]:
                self.state = self.STATE_OPENING
                self.target_angle = self.SERVO_UP
                self.manual_mode = True
                self.last_servo_move = now

                # Spenge verde e rosso: durante il movimento si userà il giallo lampeggiante.
                self.traffic_light.green_off()
                self.traffic_light.red_off()
                return

        if self.remote_close_requested:
            # Consuma il comando remoto di chiusura.
            self.remote_close_requested = False

            # La chiusura remota è consentita solo se la sbarra è "aperta"
            # in contesto automatico (WAIT_CLEAR) o in manuale (MANUAL_OPEN).
            if self.state in [self.STATE_WAIT_CLEAR, self.STATE_MANUAL_OPEN]:
                # Chiusura consentita solo se entrambi i sensori risultano liberi:
                # qui si assume convenzione: valore 1 = nessun ostacolo rilevato.
                if self.ir_entrance.pin.value() == 1 and self.ir_exit.pin.value() == 1:
                    self.state = self.STATE_CLOSING
                    self.target_angle = self.SERVO_DOWN
                    self.manual_mode = False
                    self.last_servo_move = now

        # --- MACCHINA A STATI ---

        # 1. IDLE (Fermo)
        if self.state == self.STATE_IDLE:
            # Stato di riposo: sbarra chiusa e semaforo rosso acceso.
            self.traffic_light.red_on()
            self.traffic_light.yellow_off()

            # --- USCITA AUTOMATICA (SEMPRE PERMESSA) ---
            # Se il sensore di uscita rileva un veicolo (convenzione: 0 = rilevato),
            # la sbarra si apre indipendentemente dal fatto che il parcheggio sia pieno.
            if self.ir_exit.pin.value() == 0:
                print("Auto in uscita rilevata -> Apertura Automatica")
                self.state = self.STATE_OPENING
                self.target_angle = self.SERVO_UP
                self.last_servo_move = now
                self.last_blink = now

                # Spegne il rosso: durante l'apertura si usa il giallo lampeggiante.
                self.traffic_light.red_off()

                # Apertura per uscita => non è manuale.
                self.manual_mode = False
                return

            # --- BLOCCO INGRESSO SE PARCHEGGIO PIENO ---
            # Se pieno, ignora completamente l'IR di ingresso: non si passa a GREEN.
            # Questo evita che l'ingresso venga "pre-autorizzato".
            if self.is_parking_full_cb and self.is_parking_full_cb():
                # Resta rosso e chiuso.
                return

            # --- INGRESSO: auto rilevata all'ingresso ---
            # Se il sensore di ingresso rileva un veicolo (0 = rilevato),
            # entra nello stato GREEN in cui attende la pressione del pulsante.
            if self.ir_entrance.pin.value() == 0:
                self.state = self.STATE_GREEN

        # 2. GREEN (Attesa Pulsante)
        elif self.state == self.STATE_GREEN:
            # Se il parcheggio diventa pieno mentre si è in GREEN,
            # annulla l'autorizzazione e torna in IDLE mantenendo la sbarra chiusa.
            if self.is_parking_full_cb and self.is_parking_full_cb():
                self.traffic_light.green_off()
                self.state = self.STATE_IDLE
                return

            # Segnala "pronto ingresso" accendendo il verde.
            self.traffic_light.green_on()

            # Priorità uscita anche qui: se rilevo veicolo in uscita, apro.
            if self.ir_exit.pin.value() == 0:
                self.state = self.STATE_OPENING
                self.target_angle = self.SERVO_UP
                self.last_servo_move = now
                self.last_blink = now
                self.traffic_light.green_off()
                self.manual_mode = False
                return

            # Pulsante premuto (0 = premuto): avvia apertura.
            # Il controllo "parcheggio pieno" è già stato fatto sopra, quindi qui è implicito
            # che l'apertura per ingresso è consentita.
            if self.gate_button.pin.value() == 0:
                self.state = self.STATE_OPENING
                self.target_angle = self.SERVO_UP
                self.last_servo_move = now
                self.last_blink = now
                self.traffic_light.green_off()
                self.manual_mode = False

            # Se il veicolo non è più rilevato all'ingresso (sensore torna a 1),
            # annulla lo stato GREEN e torna in IDLE.
            elif self.ir_entrance.pin.value() == 1:
                self.state = self.STATE_IDLE

        # 3. OPENING
        elif self.state == self.STATE_OPENING:
            # Lampeggio giallo ogni 150 ms: alterna lo stato del LED giallo.
            # value(not value()) è un toggle: True->False o False->True.
            if time.ticks_diff(now, self.last_blink) >= 150:
                self.traffic_light.yellow.value(not self.traffic_light.yellow.value())
                self.last_blink = now

            # Movimento del servo a step temporizzati per avere apertura graduale e non bloccante.
            if time.ticks_diff(now, self.last_servo_move) >= self.SERVO_INTERVAL:
                self.servo_angle += self.SERVO_STEP

                # Evita di superare target_angle: clamp al target.
                if self.servo_angle > self.target_angle:
                    self.servo_angle = self.target_angle

                # Applica la nuova posizione.
                self.set_servo(self.servo_angle)
                self.last_servo_move = now

                # Se raggiunta l'apertura completa:
                # - spegne il giallo
                # - passa a WAIT_CLEAR (auto) o MANUAL_OPEN (manuale/remoto)
                if self.servo_angle >= self.SERVO_UP:
                    self.traffic_light.yellow_off()
                    self.state = self.STATE_MANUAL_OPEN if self.manual_mode else self.STATE_WAIT_CLEAR

                    # Reset del timer di "clear": verrà inizializzato quando i sensori sono liberi.
                    self.clear_start = 0

        # 4. WAIT CLEAR
        elif self.state == self.STATE_WAIT_CLEAR:
            # In stato di sbarra aperta automatica:
            # si spengono tutte le luci e si aspetta che l'area sia libera
            # per SAFE_DELAY prima di chiudere.
            self.traffic_light.all_off()

            # Se entrambi i sensori sono liberi (1 e 1), avvia/continua il conteggio di sicurezza.
            if self.ir_entrance.pin.value() == 1 and self.ir_exit.pin.value() == 1:
                # Se è la prima volta che risultano liberi, memorizza l'istante di inizio.
                if self.clear_start == 0:
                    self.clear_start = now

                # Se sono rimasti liberi abbastanza a lungo, avvia chiusura.
                if time.ticks_diff(now, self.clear_start) >= self.SAFE_DELAY:
                    self.state = self.STATE_CLOSING
                    self.target_angle = self.SERVO_DOWN
                    self.last_servo_move = now
                    self.last_blink = now
            else:
                # Se almeno uno dei sensori rileva presenza, resetta il timer
                # per richiedere di nuovo SAFE_DELAY continui di area libera.
                self.clear_start = 0

        # 5. CLOSING
        elif self.state == self.STATE_CLOSING:
            # Lampeggio giallo durante la chiusura (stessa logica dell'apertura).
            if time.ticks_diff(now, self.last_blink) >= 150:
                self.traffic_light.yellow.value(not self.traffic_light.yellow.value())
                self.last_blink = now

            # Sicurezza: se durante la chiusura si rileva un veicolo (ingresso o uscita),
            # interrompe la chiusura e torna ad aprire.
            if self.ir_entrance.pin.value() == 0 or self.ir_exit.pin.value() == 0:
                self.state = self.STATE_OPENING
                self.target_angle = self.SERVO_UP
                return

            # Movimento a step temporizzati per chiusura graduale.
            if time.ticks_diff(now, self.last_servo_move) >= self.SERVO_INTERVAL:
                self.servo_angle -= self.SERVO_STEP

                # Evita di scendere sotto target_angle: clamp al target.
                if self.servo_angle < self.target_angle:
                    self.servo_angle = self.target_angle

                # Applica la nuova posizione.
                self.set_servo(self.servo_angle)
                self.last_servo_move = now

                # Se raggiunta la chiusura completa:
                # - spegne il giallo
                # - accende il rosso
                # - torna in IDLE
                if self.servo_angle <= self.SERVO_DOWN:
                    self.traffic_light.yellow_off()
                    self.traffic_light.red_on()
                    self.state = self.STATE_IDLE

    def is_open(self):
        """Ritorna True se la sbarra è aperta o si sta aprendo"""
        # Considera "open" anche gli stati in cui:
        # - sta aprendo (OPENING)
        # - è aperta automatica in attesa area libera (WAIT_CLEAR)
        # - è aperta manuale (MANUAL_OPEN)
        return self.state in [self.STATE_OPENING, self.STATE_WAIT_CLEAR, self.STATE_MANUAL_OPEN]

    def get_state(self):
        """Ritorna una stringa descrittiva dello stato"""
        # Tabella di mapping stato -> stringa leggibile (per debug/display).
        # L'indice della lista corrisponde direttamente ai valori STATE_* definiti sopra.
        states = ["CHIUSA", "PRONTA", "APERTURA", "APERTA (AUTO)", "CHIUSURA", "APERTA (MAN)"]

        # Controllo bounds per evitare IndexError in caso di stati non previsti.
        if 0 <= self.state < len(states):
            return states[self.state]
        return "UNKNOWN"