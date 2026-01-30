# actuators/servo_gate.py
import machine
import time

class ServoGate:
    # Costanti di stato
    STATE_IDLE = 0
    STATE_GREEN = 1
    STATE_OPENING = 2
    STATE_WAIT_CLEAR = 3
    STATE_CLOSING = 4
    STATE_MANUAL_OPEN = 5

    def __init__(self, pin, ir_entrance, ir_exit, traffic_light, gate_button, is_parking_full_cb=None):
        self.servo = machine.PWM(machine.Pin(pin), freq=50)
        self.ir_entrance = ir_entrance
        self.ir_exit = ir_exit
        self.traffic_light = traffic_light
        self.gate_button = gate_button
        self.is_parking_full_cb = is_parking_full_cb

        # --- DEFINIZIONE LOGICA (Il "cervello" pensa così) ---
        self.SERVO_DOWN = 0   # Logicamente Chiusa
        self.SERVO_UP = 90    # Logicamente Aperta

        # PARAMETRI OTTIMIZZATI
        self.SERVO_STEP = 2
        self.SERVO_INTERVAL = 30     # 30ms

        self.SAFE_DELAY = 1000

        self.state = self.STATE_IDLE
        self.servo_angle = self.SERVO_DOWN
        self.target_angle = self.SERVO_DOWN
        self.set_servo(self.servo_angle)

        self.last_blink = 0
        self.last_servo_move = 0
        self.clear_start = 0

        self.remote_open_requested = False
        self.remote_close_requested = False
        self.manual_mode = False

        self.is_moving_flag = False

    def set_servo(self, logic_angle):
        """
        Set servo angle CON INVERSIONE SOFTWARE.
        Il codice lavora 0->90, ma al motore mandiamo 90->0.
        """
        logic_angle = int(max(0, min(180, logic_angle)))
        physical_angle = 90 - logic_angle
        physical_angle = int(max(0, min(180, physical_angle)))

        duty = 1700 + (physical_angle * 6500) // 180
        self.servo.duty_u16(duty)
        self.servo_angle = logic_angle

    def is_moving(self):
        if self.state in [self.STATE_OPENING, self.STATE_CLOSING]:
            return self.servo_angle != self.target_angle
        return False

    def request_open(self):
        self.remote_open_requested = True
        self.manual_mode = True

    def request_close(self):
        self.remote_close_requested = True

    def update(self):
        now = time.ticks_ms()

        self.is_moving_flag = (self.state in [self.STATE_OPENING, self.STATE_CLOSING])

        # COMANDI REMOTI
        if self.remote_open_requested:
            self.remote_open_requested = False

            if self.state not in [self.STATE_OPENING, self.STATE_MANUAL_OPEN]:
                self.state = self.STATE_OPENING
                self.target_angle = self.SERVO_UP
                self.manual_mode = True
                self.last_servo_move = now
                self.traffic_light.green_off()
                self.traffic_light.red_off()
                return

        if self.remote_close_requested:
            self.remote_close_requested = False
            if self.state in [self.STATE_WAIT_CLEAR, self.STATE_MANUAL_OPEN]:
                if self.ir_entrance.pin.value() == 1 and self.ir_exit.pin.value() == 1:
                    self.state = self.STATE_CLOSING
                    self.target_angle = self.SERVO_DOWN
                    self.manual_mode = False
                    self.last_servo_move = now

        # --- MACCHINA A STATI ---

        # 1. IDLE (Fermo)
        if self.state == self.STATE_IDLE:
            self.traffic_light.red_on()
            self.traffic_light.yellow_off()

            # --- USCITA AUTOMATICA (SEMPRE PERMESSA) ---
            if self.ir_exit.pin.value() == 0:
                print("🚗 Auto in uscita rilevata -> Apertura Automatica")
                self.state = self.STATE_OPENING
                self.target_angle = self.SERVO_UP
                self.last_servo_move = now
                self.last_blink = now
                self.traffic_light.red_off()
                self.manual_mode = False
                return

            # --- BLOCCO INGRESSO SE PARCHEGGIO PIENO ---
            # Se pieno, ignora completamente l'IR di ingresso (non andare in GREEN).
            if self.is_parking_full_cb and self.is_parking_full_cb():
                # resta rosso e chiuso
                return

            # --- INGRESSO: auto rilevata all'ingresso ---
            if self.ir_entrance.pin.value() == 0:
                self.state = self.STATE_GREEN

        # 2. GREEN (Attesa Pulsante)
        elif self.state == self.STATE_GREEN:
            # Se parcheggio pieno mentre siamo in GREEN: rientra in IDLE e resta chiuso.
            if self.is_parking_full_cb and self.is_parking_full_cb():
                self.traffic_light.green_off()
                self.state = self.STATE_IDLE
                return

            self.traffic_light.green_on()

            # Priorità uscita anche qui
            if self.ir_exit.pin.value() == 0:
                self.state = self.STATE_OPENING
                self.target_angle = self.SERVO_UP
                self.last_servo_move = now
                self.last_blink = now
                self.traffic_light.green_off()
                self.manual_mode = False
                return

            # Pulsante premuto -> apertura (solo se NON pieno, già garantito sopra)
            if self.gate_button.pin.value() == 0:
                self.state = self.STATE_OPENING
                self.target_angle = self.SERVO_UP
                self.last_servo_move = now
                self.last_blink = now
                self.traffic_light.green_off()
                self.manual_mode = False

            elif self.ir_entrance.pin.value() == 1:
                self.state = self.STATE_IDLE

        # 3. OPENING
        elif self.state == self.STATE_OPENING:
            if time.ticks_diff(now, self.last_blink) >= 150:
                self.traffic_light.yellow.value(not self.traffic_light.yellow.value())
                self.last_blink = now
            if time.ticks_diff(now, self.last_servo_move) >= self.SERVO_INTERVAL:
                self.servo_angle += self.SERVO_STEP
                if self.servo_angle > self.target_angle:
                    self.servo_angle = self.target_angle
                self.set_servo(self.servo_angle)
                self.last_servo_move = now
                if self.servo_angle >= self.SERVO_UP:
                    self.traffic_light.yellow_off()
                    self.state = self.STATE_MANUAL_OPEN if self.manual_mode else self.STATE_WAIT_CLEAR
                    self.clear_start = 0

        # 4. WAIT CLEAR
        elif self.state == self.STATE_WAIT_CLEAR:
            self.traffic_light.all_off()
            if self.ir_entrance.pin.value() == 1 and self.ir_exit.pin.value() == 1:
                if self.clear_start == 0:
                    self.clear_start = now
                if time.ticks_diff(now, self.clear_start) >= self.SAFE_DELAY:
                    self.state = self.STATE_CLOSING
                    self.target_angle = self.SERVO_DOWN
                    self.last_servo_move = now
                    self.last_blink = now
            else:
                self.clear_start = 0

        # 5. CLOSING
        elif self.state == self.STATE_CLOSING:
            if time.ticks_diff(now, self.last_blink) >= 150:
                self.traffic_light.yellow.value(not self.traffic_light.yellow.value())
                self.last_blink = now
            if self.ir_entrance.pin.value() == 0 or self.ir_exit.pin.value() == 0:
                self.state = self.STATE_OPENING
                self.target_angle = self.SERVO_UP
                return
            if time.ticks_diff(now, self.last_servo_move) >= self.SERVO_INTERVAL:
                self.servo_angle -= self.SERVO_STEP
                if self.servo_angle < self.target_angle:
                    self.servo_angle = self.target_angle
                self.set_servo(self.servo_angle)
                self.last_servo_move = now
                if self.servo_angle <= self.SERVO_DOWN:
                    self.traffic_light.yellow_off()
                    self.traffic_light.red_on()
                    self.state = self.STATE_IDLE

    def is_open(self):
        """Ritorna True se la sbarra è aperta o si sta aprendo"""
        return self.state in [self.STATE_OPENING, self.STATE_WAIT_CLEAR, self.STATE_MANUAL_OPEN]

    def get_state(self):
        """Ritorna una stringa descrittiva dello stato"""
        states = ["CHIUSA", "PRONTA", "APERTURA", "APERTA (AUTO)", "CHIUSURA", "APERTA (MAN)"]
        if 0 <= self.state < len(states):
            return states[self.state]
        return "UNKNOWN"