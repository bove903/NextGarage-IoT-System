import time
import machine
import network
from config import Config
from sensors.ir_sensor import IRSensor
from sensors.ultrasonic import UltrasonicSensor
from sensors.mq2 import MQ2Sensor
from sensors.brightness_sensor import BrightnessSensor
from actuators.servo_gate import ServoGate
from actuators.traffic_light import TrafficLight
from actuators.parking_leds import ParkingLeds
from actuators.buzzer import Buzzer
from actuators.parking_light import ParkingLight
from input.button import Button
from display.oled_display import OLEDDisplay
from mqtt_handler import MQTTHandler

class SmartParking:
    def __init__(self, config):
        # Salva la configurazione (pin, soglie, parametri MQTT, ecc.).
        self.config = config

        # Stato generale del sistema (stringa descrittiva: INIT, READY, RUNNING, ...).
        self.state = "INIT"

        # Flag di stato applicativo:
        # - car_parked: True se il posto è considerato occupato (auto parcheggiata).
        # - gas_alarm: True se allarme gas attivo (buzzer + led).
        # - parking_assist: True se assistenza parcheggio attiva (buzzer in avvicinamento).
        self.car_parked = False
        self.gas_alarm = False
        self.parking_assist = False

        # Stato connettività:
        # - wifi_connected: True se WiFi connesso.
        # - mqtt: handler MQTT (None se non disponibile).
        self.wifi_connected = False
        self.mqtt = None

        # Timer per conferma occupazione/liberazione:
        # - occupied_timer: timestamp inizio condizione "stop" per confermare OCCUPATO.
        # - free_timer: timestamp inizio condizione "libero" per confermare LIBERO.
        # - last_distance: ultimo valore distanza filtrata (usato anche per stabilizzare la lettura).
        self.occupied_timer = 0
        self.free_timer = 0
        self.last_distance = 999

        # WiFi connection (inizializza anche il display se necessario e mostra icone di connessione).
        self.connect_wifi()

        # Inizializza sensori/attuatori/display, e imposta lo stato iniziale.
        self.initialize_components()

        # MQTT setup (solo se WiFi connesso).
        self.setup_mqtt()

    def connect_wifi(self):
        """Connessione WiFi con Icona"""
        # Se non esiste ancora un display associato all'istanza, lo crea.
        # hasattr evita doppia inizializzazione (utile perché connect_wifi è chiamato nel costruttore).
        if not hasattr(self, 'display'):
            self.display = OLEDDisplay(self.config.PIN_SDA, self.config.PIN_SCL, self.config.OLED_WIDTH, self.config.OLED_HEIGHT)

        # Mostra l'icona di connessione WiFi sul display
        self.display.show_wifi_connecting()

        # Inizializza l'interfaccia WiFi
        wlan = network.WLAN(network.STA_IF)
        wlan.active(True)

        # Se non è connesso, avvia la procedura di connessione con timeout.
        if not wlan.isconnected():
            print(f"Connecting to {self.config.WIFI_SSID}...")
            wlan.connect(self.config.WIFI_SSID, self.config.WIFI_PASSWORD)

            # Timeout massimo di 15 secondi: evita loop infinito se rete non raggiungibile.
            timeout = 15
            while not wlan.isconnected() and timeout > 0:
                time.sleep(1)
                timeout -= 1

        # Se connesso, salva stato e IP; altrimenti mostra errore su display.
        if wlan.isconnected():
            self.wifi_connected = True
            ip = wlan.ifconfig()[0]
            print(f"WiFi connected! IP: {ip}")
        else:
            print("WiFi connection failed!")
            self.display.show_error("WiFi FAILED")
            time.sleep(2)

    def setup_mqtt(self):
        """Setup MQTT connection"""
        # Se il WiFi non è connesso, salta completamente l'inizializzazione MQTT.
        if not self.wifi_connected:
            print("Skip MQTT setup - no WiFi")
            return

        # Mostra una schermata/icone di connessione MQTT (cloud) sul display.
        self.display.show_mqtt_connecting()

        try:
            # Crea l'handler MQTT registrando la callback on_mqtt_message per i messaggi ricevuti.
            self.mqtt = MQTTHandler(self.config, self.on_mqtt_message)

            # Tenta connessione al broker: se OK, sistema pronto per publish/subscribe.
            if self.mqtt.connect():
                print("MQTT ready")
                # Piccola attesa per stabilizzare la transizione UI/logica (non indispensabile ma utile).
                time.sleep(1)
            else:
                # Connessione fallita: segnala errore e disabilita mqtt per evitare uso successivo.
                print("MQTT connection failed")
                self.display.show_error("MQTT FAIL")
                self.mqtt = None
        except Exception as e:
            # Qualsiasi eccezione in fase di setup viene gestita:
            # - log su seriale
            # - errore su display
            # - mqtt disabilitato
            print(f"MQTT setup error: {e}")
            self.display.show_error("MQTT ERR")
            self.mqtt = None

    def on_mqtt_message(self, topic, message):
        """Callback per messaggi MQTT ricevuti - CON FIX LOOP"""

        # Evita loop di conferme:
        # Se arriva un messaggio su un topic che termina con "/confirm", è una conferma
        # pubblicata dal dispositivo stesso (o dalla logica di conferma) e va ignorata.
        if topic.endswith("/confirm"):
            return

        # Log diagnostico della ricezione (utile per debug integrazione con Node-RED/dashboard).
        print(f"MQTT RX: {topic} = {message}")

        try:
            # --- COMANDI SBARRA ---
            # Topic comandi: apri/chiudi sbarra. La logica effettiva di movimento è nel ServoGate.
            if topic == "parking/cmd/open_gate":
                self.servo.request_open()
            elif topic == "parking/cmd/close_gate":
                self.servo.request_close()

            # --- MODALITÀ LUCI PARCHEGGIO ---
            # Aggiorna modalità di funzionamento della luce (ON/OFF/AUTO) tramite configurazione.
            elif topic == "parking/cmd/parking_light_mode":
                # update_light_mode ritorna True se la modalità è stata accettata/aggiornata.
                if self.config.update_light_mode(message):
                    self.apply_parking_light_mode()

            # --- RESET CONFIGURAZIONE ---
            # Ripristina soglie di default e aggiorna Node-RED pubblicando valori retained.
            elif topic == "parking/cmd/reset_config":
                print("RESET COMPLETO CONFIGURAZIONE...")
                # Valori di Default
                DEFAULT_MQ2_THRESH = 1500
                DEFAULT_MQ2_HYST = 100
                DEFAULT_LUX_THRESH = 50

                # Resetta variabili interne di configurazione (soglie/isteresi).
                self.config.MQ2_THRESHOLD = DEFAULT_MQ2_THRESH
                self.config.MQ2_HYSTERESIS = DEFAULT_MQ2_HYST
                self.config.LUX_THRESHOLD = DEFAULT_LUX_THRESH

                # Aggiorna Node-RED (retain=True) per sincronizzare dashboard con valori resettati.
                if self.mqtt:
                    self.mqtt.publish("parking/cfg/mq2_threshold", str(DEFAULT_MQ2_THRESH), retain=True)
                    self.mqtt.publish("parking/cfg/mq2_hyst", str(DEFAULT_MQ2_HYST), retain=True)
                    self.mqtt.publish("parking/cfg/lux_threshold", str(DEFAULT_LUX_THRESH), retain=True)
                print("Reset completato.")

            # --- GESTIONE CONFIGURAZIONE GENERICA ---
            # Gestisce topic del tipo "parking/cfg/<param>" tipici di slider/barre su Node-RED.
            elif topic.startswith("parking/cfg/"):
                # Estrae il nome del parametro (ultima parte del topic).
                param = topic.split("/")[-1]

                # Aggiorna il valore nella config; se accettato, invia conferma.
                if self.config.update_threshold(param, message):
                    # Pubblica conferma sul topic "<topic>/confirm" per far allineare la dashboard.
                    # Nota: il return all'inizio su "/confirm" previene l'effetto ping-pong.
                    confirm_topic = f"{topic}/confirm"
                    if self.mqtt:
                        self.mqtt.publish(confirm_topic, message, retain=True)

        except Exception as e:
            # Qualsiasi errore in parsing/gestione messaggio MQTT viene loggato,
            # evitando che la callback rompa il loop principale.
            print(f"Error processing MQTT: {e}")

    def apply_parking_light_mode(self):
        """Applica modalità luci parcheggio"""
        # Applica il comportamento della luce parcheggio in base alla modalità configurata:
        # - ON  : luce sempre accesa
        # - OFF : luce sempre spenta
        # - AUTO: luce gestita dal sensore di luminosità (TSL2561) in check_brightness()
        mode = self.config.PARKING_LIGHT_MODE
        print(f"Applying light mode: {mode}")

        if mode == "ON":
            # In modalità ON si forza accensione (luminosità logica 100).
            self.parking_light.on(100)
            print("Parking light: ALWAYS ON")
        elif mode == "OFF":
            # In modalità OFF si forza spegnimento.
            self.parking_light.off()
            print("Parking light: ALWAYS OFF")
        else:  # AUTO
            # In AUTO la logica è demandata a check_brightness().
            print("Parking light: AUTO mode (controlled by TSL2561)")
            # In AUTO viene gestito da check_brightness()

    def initialize_components(self):
        print("Initializing components...")

        # Display già inizializzato in connect_wifi.
        # Mostra un logo/boot screen e attende 2s (feedback utente durante init HW).
        self.display.show_logo()
        time.sleep(2)

        # --- SENSORI ---
        # Sensori IR: tipicamente valore 0 quando rileva ostacolo/auto, 1 quando libero (convenzione comune).
        self.ir_entrance = IRSensor(self.config.PIN_IR_ENTRANCE, "Entrance")
        self.ir_exit = IRSensor(self.config.PIN_IR_EXIT, "Exit")

        # Sensore ultrasuoni (trig/echo) per distanza nel posto auto.
        self.ultrasonic = UltrasonicSensor(self.config.PIN_ULTRASONIC_TRIG, self.config.PIN_ULTRASONIC_ECHO)

        # Sensore gas MQ-2 (ADC).
        self.mq2 = MQ2Sensor(self.config.PIN_MQ2)

        # --- SENSORE LUMINOSITÀ (I2C) ---
        # Inizializzazione protetta: se fallisce, brightness_sensor diventa None e il sistema continua.
        try:
            i2c = machine.I2C(0, sda=machine.Pin(self.config.PIN_SDA), scl=machine.Pin(self.config.PIN_SCL))
            self.brightness_sensor = BrightnessSensor(i2c, self.config.TSL2561_ADDRESS)
        except Exception as e:
            print(f"Brightness sensor init error: {e}")
            self.brightness_sensor = None

        # --- ATTUATORI ---
        # Semaforo (rosso/giallo/verde).
        self.traffic_light = TrafficLight(self.config.PIN_TRAFFIC_RED, self.config.PIN_TRAFFIC_YELLOW, self.config.PIN_TRAFFIC_GREEN)

        # Pulsante sbarra (richiesta apertura ingresso).
        self.gate_button = Button(self.config.PIN_GATE_BUTTON, name="Gate Button")

        # ServoGate gestisce la macchina a stati della sbarra.
        # is_parking_full_cb usa lambda che ritorna self.car_parked:
        # - se il posto è occupato, il parcheggio viene considerato "pieno" per l'ingresso.
        self.servo = ServoGate(self.config.PIN_SERVO, self.ir_entrance, self.ir_exit, self.traffic_light, self.gate_button, is_parking_full_cb=lambda: self.car_parked)

        # LED parcheggio (rosso/verde) per stato posto libero/occupato.
        self.parking_leds = ParkingLeds(self.config.PIN_PARKING_RED, self.config.PIN_PARKING_GREEN)

        # Buzzer (PWM) per assistenza parcheggio e allarme gas.
        self.buzzer = Buzzer(self.config.PIN_BUZZER)

        # Luce parcheggio (ON/OFF) gestita da modalità (ON/OFF/AUTO).
        self.parking_light = ParkingLight(self.config.PIN_PARKING_LIGHT)

        # LED di allarme (uscita digitale), usato in caso di gas_alarm.
        self.alarm_led = machine.Pin(self.config.PIN_ALARM_LED, machine.Pin.OUT)

        # Pulsante master (usato qui per reset con pressione lunga).
        self.master_button = Button(self.config.PIN_MASTER_BTN, name="Master Button")

        # Imposta stato iniziale coerente di tutti gli attuatori e variabili.
        self.set_initial_state()

        # Sistema pronto: aggiorna stato e mostra schermata principale.
        self.state = "READY"
        self.display.show_main_screen(gate_status=self.servo.is_open(), parking_status=self.car_parked, gas_level=self.mq2.read_percentage())
        print("System ready")

    def set_initial_state(self):
        # Stato iniziale visivo/attuatori:
        # - semaforo rosso acceso
        # - LED parcheggio su "libero" (verde)
        # - LED allarme spento
        # - luce parcheggio spenta
        # - buzzer fermo
        self.traffic_light.red_on()
        self.parking_leds.set_free()  # Verde acceso di default
        self.alarm_led.off()
        self.parking_light.off()
        self.buzzer.stop()

        # Reset variabili di stato del posto e timer di conferma.
        self.car_parked = False
        self.occupied_timer = 0
        self.free_timer = 0

    def run(self):
        """Main system loop"""
        print("Starting main loop...")
        self.state = "RUNNING"

        # Timestamp per scheduling non bloccante di task periodici:
        last_display_update = 0
        last_distance_check = 0
        last_gas_check = 0
        last_light_check = 0
        last_mqtt_telemetry = 0
        last_mqtt_check = 0

        # was_moving serve per rilevare transizione "fine movimento sbarra"
        # e fare azioni una tantum subito dopo (refresh display/telemetria/luci).
        was_moving = False

        while True:
            current_time = time.ticks_ms()

            # 1. AGGIORNA SERVO (Priorità)
            # La sbarra è trattata come task prioritario: aggiorna la FSM del servo ad ogni ciclo.
            self.servo.update()
            is_moving = self.servo.is_moving()

            # 2. FLUIDITÀ SBARRA
            # Se la sbarra si sta muovendo, si riduce il carico del loop (sleep minimo + continue)
            # per avere maggiore reattività e regolarità nel movimento/lampeggio.
            if is_moving:
                was_moving = True
                time.sleep_ms(1)
                continue

            # 3. FINE MOVIMENTO
            # Se nel ciclo precedente era in movimento e ora non lo è più,
            # esegue alcune azioni di riallineamento una sola volta (post-movimento).
            if was_moving and not is_moving:
                self.check_brightness()
                self.publish_telemetry()
                self.update_display()
                was_moving = False


            # MQTT: check_messages a cadenza ~100ms per ricevere comandi/config in modo responsivo.
            if self.mqtt and time.ticks_diff(current_time, last_mqtt_check) >= 100:
                self.mqtt.check_messages()
                last_mqtt_check = current_time

            # PULSANTE RESET (5 SECONDI)
            # get_press_type identifica la durata pressione:
            # - long_duration=5000 => long_press quando mantenuto premuto per 5s.
            press_type = self.master_button.get_press_type(long_duration=5000)

            if press_type == "long_press":
                print("PULSANTE MASTER: Pressione lunga rilevata (5s)")
                print("Avvio procedura di RESET...")
                self.system_reset() # Riavvia il microcontrollore dopo aver mostrato grafica.

            # Sensori distanza: ogni 200ms (gestione occupato/libero + assistenza parcheggio).
            if time.ticks_diff(current_time, last_distance_check) >= 200:
                self.check_parking()
                last_distance_check = current_time

            # Sensore gas: ogni 500ms (isteresi su soglia).
            if time.ticks_diff(current_time, last_gas_check) >= 500:
                self.check_gas()
                last_gas_check = current_time

            # Luci in AUTO: ogni 1000ms (lettura lux + soglia).
            if time.ticks_diff(current_time, last_light_check) >= 1000:
                self.check_brightness()
                last_light_check = current_time

            # Display: refresh ogni 1000ms (o quando finisce il movimento della sbarra).
            if time.ticks_diff(current_time, last_display_update) >= 1000:
                self.update_display()
                last_display_update = current_time

            # Telemetria: invio MQTT a intervallo configurato (MQTT_TELEMETRY_INTERVAL).
            if self.mqtt and time.ticks_diff(current_time, last_mqtt_telemetry) >= self.config.MQTT_TELEMETRY_INTERVAL:
                self.publish_telemetry()
                last_mqtt_telemetry = current_time

            # Buzzer: update non bloccante (gestione lampeggio allarme).
            self.buzzer.update()

            # Piccolo sleep per ridurre CPU e jitter, mantenendo loop reattivo.
            time.sleep_ms(5)

    def _get_filtered_distance(self):
        """
        Legge 7 valori, scarta i peggiori (min/max) e fa la media.
        Usa anche il valore precedente per stabilizzare (Media Pesata).

        A cosa serve:
        - Ridurre rumore e outlier tipici dei sensori a ultrasuoni.
        - Stabilizzare l'andamento della distanza per evitare attivazioni/disattivazioni rapide
          (flapping) dell'assistenza e dei timer di conferma.

        Come funziona:
        1) Esegue 7 letture ravvicinate.
        2) Scarta letture fuori range fisico plausibile.
        3) Ordina e rimuove minimo e massimo (trimmed mean) se abbastanza campioni.
        4) Calcola media e applica un filtro passa-basso (media pesata con last_distance).
        """
        readings = []

        # 1. Burst di 7 letture rapide
        for _ in range(7):
            d = self.ultrasonic.distance_cm()

            # Accetta solo valori fisicamente possibili (0.5cm - 300cm)
            # per scartare letture spurie (es. 0 o valori enormi dovuti a timeout/eco).
            if 0.5 < d < 300:
                readings.append(d)

            # Pausa molto breve per non leggere sempre lo stesso impulso/eco.
            time.sleep_ms(3)

        # Se non ci sono letture valide, ritorna l'ultima distanza nota (fallback stabile).
        if not readings:
            return self.last_distance

        # 2. Ordina e rimuovi gli estremi (Trimmed Mean)
        readings.sort()
        if len(readings) >= 5:
            # Rimuove il più basso e il più alto: spesso rappresentano rumore.
            readings = readings[1:-1]

        # 3. Media attuale dei campioni ripuliti
        current_avg = sum(readings) / len(readings)

        # 4. LOW PASS FILTER (stabilizzazione temporale)
        # Se last_distance è "sentinella" 999 (primo avvio), usa direttamente current_avg.
        # Altrimenti media pesata: 70% valore nuovo + 30% valore precedente.
        if self.last_distance == 999: # Primo avvio
            filtered = current_avg
        else:
            filtered = (current_avg * 0.7) + (self.last_distance * 0.3)

        return filtered

    def check_parking(self):
        """Check parking spot status - CON ISTERESI E TOLLERANZA"""
        # Se allarme gas attivo, si disabilita la logica parcheggio (priorità sicurezza).
        if self.gas_alarm: return

        # Legge distanza ultra-filtrata (vedi _get_filtered_distance).
        distance = self._get_filtered_distance()
        now = time.ticks_ms()

        # Salva distanza per:
        # - telemetria MQTT
        # - filtro passa-basso nel ciclo successivo
        self.last_distance = distance

        # ========== STATO: LIBERO (In fase di parcheggio) ==========
        if not self.car_parked:
            # Se il posto è libero, non ha senso far contare la liberazione.
            self.free_timer = 0

            # --- ZONA DI STOP E CONFERMA ---
            # limit: soglia di "stop" sotto cui consideriamo l'auto arrivata a fine corsa.
            # Se occupied_timer è già attivo, allarga la soglia di 1cm per tollerare oscillazioni
            # senza resettare continuamente il conteggio (stabilizzazione temporale + tolleranza).
            limit = self.config.ULTRASONIC_MIN_DISTANCE
            if self.occupied_timer > 0:
                limit += 1.0 # TOLLERANZA: se stiamo già contando, concedi 1cm in più

            if 0 < distance <= limit:
                # Buzzer continuo (suono di stop): frequenza alta costante.
                self.buzzer.set_frequency(2000)

                # Avvia timer di conferma occupazione se non è già partito.
                if self.occupied_timer == 0:
                    self.occupied_timer = now
                    print(f"Stop rilevato ({distance:.1f}cm). Attesa stabilità...")

                # Conferma occupazione solo se la condizione resta valida per ULTRASONIC_OCCUPIED_CONFIRM ms.
                if time.ticks_diff(now, self.occupied_timer) >= self.config.ULTRASONIC_OCCUPIED_CONFIRM:
                    # CONFERMA OCCUPATO
                    self.car_parked = True
                    self.parking_leds.set_occupied()
                    self.parking_assist = False
                    self.buzzer.stop_parking_assist()
                    self.occupied_timer = 0
                    print(f"PARCHEGGIO COMPLETATO")

                    # Pubblica stato su MQTT (retain=True) così la dashboard vede l'ultimo stato.
                    if self.mqtt: self.mqtt.publish('state/spot', 'OCCUPATO', retain=True)

            # --- ZONA DI AVVICINAMENTO ---
            # Se l'auto è entro ULTRASONIC_MAX_DISTANCE ma non in "stop", attiva assistenza.
            elif distance <= self.config.ULTRASONIC_MAX_DISTANCE:
                self.parking_assist = True

                # Reset timer occupazione: siamo in avvicinamento, non ancora in stop stabile.
                self.occupied_timer = 0 # Reset solo se ti allontani davvero

                # Suono incrementale (semplice): più vicino => frequenza più alta.
                if distance < (self.config.ULTRASONIC_MAX_DISTANCE / 2):
                    self.buzzer.set_frequency(1500)
                else:
                    self.buzzer.set_frequency(800)

            # --- LONTANO ---
            # Fuori range: niente assistenza e buzzer spento.
            else:
                self.parking_assist = False
                self.buzzer.stop_parking_assist()
                self.occupied_timer = 0

        # ========== STATO: OCCUPATO (Auto ferma) ==========
        else:
            # Se già occupato, non ha senso contare nuovamente per occupazione.
            self.occupied_timer = 0

            # Assicura che l'assistenza parcheggio sia spenta mentre l'auto è considerata ferma.
            self.buzzer.stop_parking_assist()

            # Per liberare il posto, l'auto deve uscire chiaramente dalla zona:
            # distanza > MAX + 2cm (tolleranza anti-flapping).
            if distance > (self.config.ULTRASONIC_MAX_DISTANCE + 2):
                # Avvia timer liberazione se non già attivo.
                if self.free_timer == 0:
                    self.free_timer = now

                # Conferma libero solo se la condizione permane per ULTRASONIC_FREE_CONFIRM ms.
                if time.ticks_diff(now, self.free_timer) >= self.config.ULTRASONIC_FREE_CONFIRM:
                    self.car_parked = False
                    self.parking_leds.set_free()
                    self.free_timer = 0
                    print(f"POSTO LIBERATO")
                    if self.mqtt: self.mqtt.publish('state/spot', 'LIBERO', retain=True)
            else:
                # Se rientra nella zona, resetta il timer: richiesta continuità della condizione.
                self.free_timer = 0

    def check_gas(self):
        """Check gas levels - USA VALORI RAW"""
        # Legge valore ADC raw (0-4095). Viene usato direttamente per confronto con soglie.
        gas_raw = self.mq2.read_raw()  # Valore RAW 0-4095

        # Isteresi anti-flapping:
        # - entra in allarme quando supera MQ2_THRESHOLD
        # - esce dall'allarme solo quando scende sotto (MQ2_THRESHOLD - MQ2_HYSTERESIS)
        if not self.gas_alarm and gas_raw > self.config.MQ2_THRESHOLD:
            print(f"GAS ALARM! Raw: {gas_raw}")
            self.gas_alarm = True
            # Avvia buzzer in modalità allarme con frequenza/interval specifici per il gas.
            self.buzzer.start_alarm(freq=2500, interval=300)  # Suono diverso per gas
            self.alarm_led.on()

        elif self.gas_alarm and gas_raw < (self.config.MQ2_THRESHOLD - self.config.MQ2_HYSTERESIS):
            print(f"Gas alarm cleared. Raw: {gas_raw}")
            self.gas_alarm = False
            self.buzzer.stop_alarm()
            self.alarm_led.off()

    def check_brightness(self):
        """Check ambient light - SOLO SE MODO AUTO"""
        # La luminosità viene controllata solo in modalità AUTO.
        if self.config.PARKING_LIGHT_MODE != "AUTO":
            return  # Skip se non in modalità AUTO

        try:
            if self.brightness_sensor:
                lux = self.brightness_sensor.read_lux()

                # Logica a soglia:
                # - lux sotto soglia => accende la luce parcheggio
                # - lux sopra soglia => spegne
                if lux < self.config.LUX_THRESHOLD:
                    self.parking_light.on(100)
                else:
                    self.parking_light.off()

        except Exception as e:
            # Protezione: eventuali errori I2C/sensore non devono fermare il sistema.
            print(f"Brightness check error: {e}")

    def toggle_parking_light(self):
        """Toggle parking light manualmente"""
        # Toggle semplice basato sullo stato interno brightness della ParkingLight:
        # - se > 0 considerata accesa
        # - altrimenti spenta
        print("Manual light toggle")
        if self.parking_light.brightness > 0:
            self.parking_light.off()
        else:
            self.parking_light.on(50)

    def system_reset(self):
        """Reset system with NEW GRAPHIC"""
        # Esegue un reset completo del microcontrollore:
        # - mostra una schermata grafica
        # - disconnette MQTT se attivo
        # - attende 2s e poi chiama machine.reset()
        print("System reset requested...")

        # Mostra icona/schermata dedicata al reset.
        self.display.show_system_reset()

        # Disconnette MQTT per chiusura pulita della connessione (se presente).
        if self.mqtt:
            self.mqtt.disconnect()

        # Pausa per consentire la visualizzazione della schermata.
        time.sleep(2) # Tempo per ammirare l'icona
        machine.reset()

    def publish_telemetry(self):
        """Pubblica telemetria su MQTT con FILTRO DASHBOARD"""
        # Se MQTT non esiste o non è connesso, non pubblica nulla.
        if not self.mqtt or not self.mqtt.connected:
            return

        try:
            # Distanza attuale: usa last_distance già filtrata e memorizzata.
            distance = self.last_distance

            # FILTRO per dashboard Node-RED:
            # Se la distanza è oltre un certo valore ( > 8cm), invia 8.0 fisso,
            # così il gauge mostra "fuori scala/vuoto" invece di valori variabili poco utili.
            mqtt_distance = distance
            if distance > 8.0:
                mqtt_distance = 8.0

            # Lettura Lux: gestita con try per evitare blocchi se sensore non disponibile.
            lux = 0
            if self.brightness_sensor:
                try: lux = self.brightness_sensor.read_lux()
                except: pass

            # Livello gas raw.
            gas_raw = self.mq2.read_raw()

            # Dizionario telemetria pubblicato: include stati principali e sensori.
            data = {
                'gate_state': self.servo.get_state(),       # Stato descrittivo sbarra (stringa)
                'spot_occupied': self.car_parked,          # True/False occupato
                'distance': round(mqtt_distance, 1),      # Distanza "tagliata" per gauge
                'gas_level': gas_raw,                            # Gas raw 0-4095
                'gas_alarm': self.gas_alarm,                # True/False allarme gas
                'light': lux                                              # Lux (0 se non disponibile)
            }

            # Delega la pubblicazione effettiva all'handler MQTT.
            self.mqtt.publish_telemetry(data)

        except Exception as e:
            # Protezione: un errore di publish non deve interrompere il loop.
            print(f"Telemetry publish error: {e}")

    def update_display(self):
        """Update OLED display"""
        # Gas raw viene mostrato sempre (anche come riferimento durante allarme).
        gas_raw = self.mq2.read_raw()

        # lux_level è opzionale: se non disponibile, resta None.
        lux_level = None

        # Lettura lux protetta (sensore potrebbe non esserci o generare errori I2C).
        try:
            if self.brightness_sensor:
                lux_level = self.brightness_sensor.read_lux()
        except:
            pass

        # Stato sbarra: True se aperta o in apertura/attesa (vedi ServoGate.is_open()).
        gate_open = self.servo.is_open()

        # Priorità display:
        # 1) allarme gas
        # 2) assistenza parcheggio
        # 3) schermata principale
        if self.gas_alarm:
            self.display.show_gas_alarm(gas_raw)
        elif self.parking_assist:
            # Nota: qui usa distance_cm() raw (non filtrata) per mostrare valore "reattivo" sul display.
            distance = self.ultrasonic.distance_cm()
            self.display.show_parking_assist(distance)
        else:
            self.display.show_main_screen(gate_status=gate_open, parking_status=self.car_parked, gas_level=gas_raw, alarm_active=self.gas_alarm, lux_level=lux_level)