# parking.py
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
        self.config = config
        self.state = "INIT"
        self.car_parked = False
        self.gas_alarm = False
        self.parking_assist = False
        self.wifi_connected = False
        self.mqtt = None
        
        # Timer per conferma occupazione/liberazione
        self.occupied_timer = 0
        self.free_timer = 0
        self.last_distance = 999
        
        # WiFi connection
        self.connect_wifi()
        
        # Initialize components
        self.initialize_components()
        
        # MQTT setup
        self.setup_mqtt()
        
    def connect_wifi(self):
        """Connessione WiFi con Icona"""
        # Crea istanza display (se non esiste già)
        if not hasattr(self, 'display'):
            self.display = OLEDDisplay(
                self.config.PIN_SDA,
                self.config.PIN_SCL,
                self.config.OLED_WIDTH,
                self.config.OLED_HEIGHT
            )
            
        # 1. MOSTRA ICONA WIFI invece del testo
        self.display.show_wifi_connecting()
        
        wlan = network.WLAN(network.STA_IF)
        wlan.active(True)
        
        if not wlan.isconnected():
            print(f"Connecting to {self.config.WIFI_SSID}...")
            wlan.connect(self.config.WIFI_SSID, self.config.WIFI_PASSWORD)
            
            timeout = 15
            while not wlan.isconnected() and timeout > 0:
                time.sleep(1)
                timeout -= 1
        
        if wlan.isconnected():
            self.wifi_connected = True
            ip = wlan.ifconfig()[0]
            print(f"WiFi connected! IP: {ip}")
            # NON MOSTRARE PIÙ L'IP SUL DISPLAY, VAI DIRETTAMENTE AVANTI
            # Il logo di caricamento sparirà quando initialize_components chiamerà show_main_screen
        else:
            print("WiFi connection failed!")
            self.display.show_error("WiFi FAILED")
            time.sleep(2)
    
    def setup_mqtt(self):
        """Setup MQTT connection"""
        if not self.wifi_connected:
            print("Skip MQTT setup - no WiFi")
            return
        
        # --- MODIFICA QUI: Usa la nuova schermata CLOUD ---
        # Vecchio codice: self.display.show_loading("Connecting MQTT...")
        self.display.show_mqtt_connecting()
        
        try:
            # Nota: Assicurati che l'import sia corretto in base alla tua struttura
            # Se hai 'connectivity.mqtt_client' o solo 'mqtt_handler'
            # Qui uso quello che avevi nel tuo ultimo parking.py funzionante:
            self.mqtt = MQTTHandler(self.config, self.on_mqtt_message)
            
            if self.mqtt.connect():
                print("MQTT ready")
                # Non serve mostrare altro testo, passiamo al main loop
                time.sleep(1)
            else:
                print("MQTT connection failed")
                self.display.show_error("MQTT FAIL") # show_error esiste ancora
                self.mqtt = None
        except Exception as e:
            print(f"MQTT setup error: {e}")
            self.display.show_error("MQTT ERR")
            self.mqtt = None
    
    def on_mqtt_message(self, topic, message):
        """Callback per messaggi MQTT ricevuti - CON FIX LOOP"""
        
        # 1. STOP AL LOOP: Se il messaggio è una conferma che ho mandato io, IGNORALO.
        if topic.endswith("/confirm"):
            return

        print(f"MQTT RX: {topic} = {message}")
        
        try:
            # Comandi Sbarra
            if topic == "parking/cmd/open_gate":
                self.servo.request_open()
            elif topic == "parking/cmd/close_gate":
                self.servo.request_close()
            
            # Modalità Luci
            elif topic == "parking/cmd/parking_light_mode":
                if self.config.update_light_mode(message):
                    self.apply_parking_light_mode()

            # Reset Configurazione
            elif topic == "parking/cmd/reset_config":
                print("♻️ RESET COMPLETO CONFIGURAZIONE...")
                # Valori di Default
                DEFAULT_MQ2_THRESH = 1500
                DEFAULT_MQ2_HYST = 100
                DEFAULT_LUX_THRESH = 50
                
                # Resetta variabili interne
                self.config.MQ2_THRESHOLD = DEFAULT_MQ2_THRESH
                self.config.MQ2_HYSTERESIS = DEFAULT_MQ2_HYST
                self.config.LUX_THRESHOLD = DEFAULT_LUX_THRESH
                
                # Aggiorna Node-RED
                if self.mqtt:
                    self.mqtt.publish("parking/cfg/mq2_threshold", str(DEFAULT_MQ2_THRESH), retain=True)
                    self.mqtt.publish("parking/cfg/mq2_hyst", str(DEFAULT_MQ2_HYST), retain=True)
                    self.mqtt.publish("parking/cfg/lux_threshold", str(DEFAULT_LUX_THRESH), retain=True)
                print("✅ Reset completato.")

            # Gestione Configurazione Generica (Barre Node-RED)
            elif topic.startswith("parking/cfg/"):
                # Estrae il nome del parametro (es. 'mq2_threshold')
                param = topic.split("/")[-1]
                
                # Aggiorna il valore
                if self.config.update_threshold(param, message):
                    # Invia conferma (SOLO SE il topic originale NON era già una conferma)
                    # Nota: Il check all'inizio della funzione ci protegge, ma per sicurezza:
                    confirm_topic = f"{topic}/confirm"
                    if self.mqtt: 
                        self.mqtt.publish(confirm_topic, message, retain=True)

        except Exception as e:
            print(f"Error processing MQTT: {e}")
    
    def apply_parking_light_mode(self):
        """Applica modalità luci parcheggio"""
        mode = self.config.PARKING_LIGHT_MODE
        print(f"Applying light mode: {mode}")
        
        if mode == "ON":
            self.parking_light.on(100)
            print("Parking light: ALWAYS ON")
        elif mode == "OFF":
            self.parking_light.off()
            print("Parking light: ALWAYS OFF")
        else:  # AUTO
            print("Parking light: AUTO mode (controlled by TSL2561)")
            # In AUTO viene gestito da check_brightness()
        
    def initialize_components(self):
        """Initialize all system components"""
        print("Initializing components...")
        
        # Display già inizializzato in connect_wifi
        self.display.show_logo()
        time.sleep(2)
        
        # Sensors
        self.ir_entrance = IRSensor(self.config.PIN_IR_ENTRANCE, "Entrance")
        self.ir_exit = IRSensor(self.config.PIN_IR_EXIT, "Exit")
        self.ultrasonic = UltrasonicSensor(
            self.config.PIN_ULTRASONIC_TRIG,
            self.config.PIN_ULTRASONIC_ECHO
        )
        self.mq2 = MQ2Sensor(self.config.PIN_MQ2)
        
        # Brightness sensor
        try:
            i2c = machine.I2C(0, sda=machine.Pin(self.config.PIN_SDA), 
                             scl=machine.Pin(self.config.PIN_SCL))
            self.brightness_sensor = BrightnessSensor(i2c, self.config.TSL2561_ADDRESS)
        except Exception as e:
            print(f"Brightness sensor init error: {e}")
            self.brightness_sensor = None
        
        # Actuators
        self.traffic_light = TrafficLight(
            self.config.PIN_TRAFFIC_RED,
            self.config.PIN_TRAFFIC_YELLOW,
            self.config.PIN_TRAFFIC_GREEN
        )
        self.gate_button = Button(self.config.PIN_GATE_BUTTON, name="Gate Button")
        
        self.servo = ServoGate(
            self.config.PIN_SERVO,
            self.ir_entrance,
            self.ir_exit,
            self.traffic_light,
            self.gate_button, is_parking_full_cb=lambda: self.car_parked
        )
        
        self.parking_leds = ParkingLeds(
            self.config.PIN_PARKING_RED,
            self.config.PIN_PARKING_GREEN
        )
        self.buzzer = Buzzer(self.config.PIN_BUZZER)
        self.parking_light = ParkingLight(self.config.PIN_PARKING_LIGHT)
        self.alarm_led = machine.Pin(self.config.PIN_ALARM_LED, machine.Pin.OUT)
        
        # Master button
        self.master_button = Button(self.config.PIN_MASTER_BTN, name="Master Button")
        
        # Stato iniziale
        self.set_initial_state()
        
        self.state = "READY"
        self.display.show_main_screen(
            gate_status=self.servo.is_open(),
            parking_status=self.car_parked,
            gas_level=self.mq2.read_percentage()
        )
        print("System ready")
        
    def set_initial_state(self):
        """Set initial state of all actuators"""
        self.traffic_light.red_on()
        self.parking_leds.set_free()  # Verde acceso di default
        self.alarm_led.off()
        self.parking_light.off()
        self.buzzer.stop()
        self.car_parked = False
        self.occupied_timer = 0
        self.free_timer = 0
        
    def run(self):
        """Main system loop - PRIORITY MODE + RESET 5s"""
        print("Starting main loop...")
        self.state = "RUNNING"
        
        last_display_update = 0
        last_distance_check = 0
        last_gas_check = 0
        last_light_check = 0
        last_mqtt_telemetry = 0
        last_mqtt_check = 0
        
        was_moving = False
        
        while True:
            current_time = time.ticks_ms()
            
            # 1. AGGIORNA SERVO (Priorità)
            self.servo.update()
            is_moving = self.servo.is_moving()
            
            # 2. FLUIDITÀ SBARRA
            if is_moving:
                was_moving = True 
                time.sleep_ms(1) 
                continue 
            
            # 3. FINE MOVIMENTO
            if was_moving and not is_moving:
                self.check_brightness() 
                self.publish_telemetry()
                self.update_display()
                was_moving = False
            
            # --- LOOP PRINCIPALE ---
            
            # MQTT
            if self.mqtt and time.ticks_diff(current_time, last_mqtt_check) >= 100:
                self.mqtt.check_messages()
                last_mqtt_check = current_time
            
            # --- MODIFICA QUI: PULSANTE RESET (5 SECONDI) ---
            # Controlla per quanto tempo è premuto il pulsante master
            # long_duration=5000 significa 5000ms (5 secondi)
            press_type = self.master_button.get_press_type(long_duration=5000)
            
            if press_type == "long_press":
                print("🔘 PULSANTE MASTER: Pressione lunga rilevata (5s)")
                print("🔄 Avvio procedura di RESET...")
                self.system_reset() # Chiama la funzione che riavvia tutto
                
            # Nota: Se press_type == "short_press", non facciamo nulla (ignora)
            
            # Sensori
            if time.ticks_diff(current_time, last_distance_check) >= 200:
                self.check_parking()
                last_distance_check = current_time
                
            if time.ticks_diff(current_time, last_gas_check) >= 500:
                self.check_gas()
                last_gas_check = current_time

            # Luci Auto
            if time.ticks_diff(current_time, last_light_check) >= 1000:
                self.check_brightness()
                last_light_check = current_time
                
            # Display
            if time.ticks_diff(current_time, last_display_update) >= 1000:
                self.update_display()
                last_display_update = current_time
            
            # Telemetria
            if self.mqtt and time.ticks_diff(current_time, last_mqtt_telemetry) >= self.config.MQTT_TELEMETRY_INTERVAL:
                self.publish_telemetry()
                last_mqtt_telemetry = current_time
                
            # Buzzer
            self.buzzer.update()
            
            time.sleep_ms(5)

    def _get_filtered_distance(self):
        """
        Legge 7 valori, scarta i peggiori (min/max) e fa la media.
        Usa anche il valore precedente per stabilizzare (Media Pesata).
        """
        readings = []
        # 1. Burst di 7 letture rapide
        for _ in range(7): 
            d = self.ultrasonic.distance_cm()
            # Accetta solo valori fisicamente possibili (0.5cm - 300cm)
            if 0.5 < d < 300: 
                readings.append(d)
            time.sleep_ms(3) # Pausa cortissima
            
        if not readings:
            return self.last_distance
            
        # 2. Ordina e Rimuovi gli estremi (Trimmed Mean)
        readings.sort()
        if len(readings) >= 5:
            # Rimuovi il più basso e il più alto (spesso rumore)
            readings = readings[1:-1]
            
        # 3. Calcola media attuale
        current_avg = sum(readings) / len(readings)
        
        # 4. LOW PASS FILTER (Il segreto della stabilità)
        # Il nuovo valore è composto per il 70% dalla media attuale e 30% dalla vecchia.
        # Questo rende i numeri "lenti" a cambiare, eliminando gli scatti.
        if self.last_distance == 999: # Primo avvio
            filtered = current_avg
        else:
            filtered = (current_avg * 0.7) + (self.last_distance * 0.3)
            
        return filtered


    def check_parking(self):
        """Check parking spot status - CON ISTERESI E TOLLERANZA"""
        if self.gas_alarm: return

        # Legge distanza ultra-filtrata
        distance = self._get_filtered_distance()
        now = time.ticks_ms()
        
        self.last_distance = distance
        
        # ========== STATO: LIBERO (In fase di parcheggio) ==========
        if not self.car_parked:
            self.free_timer = 0
            
            # --- ZONA DI STOP E CONFERMA ---
            # Se il timer è GIA attivo, usiamo una tolleranza più ampia (es. fino a 3.5 o 4cm)
            # per evitare che una piccola oscillazione lo resetti.
            limit = self.config.ULTRASONIC_MIN_DISTANCE
            if self.occupied_timer > 0:
                limit += 1.0 # TOLLERANZA: Se stiamo già contando, concedi 1cm in più di errore
            
            if 0 < distance <= limit:
                # Buzzer continuo (suono di stop)
                self.buzzer.set_frequency(2000) 
                
                # Avvia timer se non è già partito
                if self.occupied_timer == 0:
                    self.occupied_timer = now
                    print(f"⏱️ Stop rilevato ({distance:.1f}cm). Attesa stabilità...")
                
                # Controlla se sono passati i 3 secondi
                if time.ticks_diff(now, self.occupied_timer) >= self.config.ULTRASONIC_OCCUPIED_CONFIRM:
                    # CONFERMA!
                    self.car_parked = True
                    self.parking_leds.set_occupied()
                    self.parking_assist = False
                    self.buzzer.stop_parking_assist()
                    self.occupied_timer = 0
                    print(f"🚗 PARCHEGGIO COMPLETATO")
                    if self.mqtt: self.mqtt.publish('state/spot', 'OCCUPATO', retain=True)
            
            # --- ZONA DI AVVICINAMENTO ---
            elif distance <= self.config.ULTRASONIC_MAX_DISTANCE:
                self.parking_assist = True
                self.occupied_timer = 0 # Reset solo se ti allontani davvero
                
                # Suono incrementale
                if distance < (self.config.ULTRASONIC_MAX_DISTANCE / 2):
                    self.buzzer.set_frequency(1500)
                else:
                    self.buzzer.set_frequency(800)
            
            # --- LONTANO ---
            else:
                self.parking_assist = False
                self.buzzer.stop_parking_assist()
                self.occupied_timer = 0
        
        # ========== STATO: OCCUPATO (Auto ferma) ==========
        else:
            self.occupied_timer = 0
            self.buzzer.stop_parking_assist()
            
            # Per liberare il posto, l'auto deve uscire DECISAMENTE dalla zona (> MAX + tolleranza)
            if distance > (self.config.ULTRASONIC_MAX_DISTANCE + 2):
                if self.free_timer == 0:
                    self.free_timer = now
                
                if time.ticks_diff(now, self.free_timer) >= self.config.ULTRASONIC_FREE_CONFIRM:
                    self.car_parked = False
                    self.parking_leds.set_free()
                    self.free_timer = 0
                    print(f"✅ POSTO LIBERATO")
                    if self.mqtt: self.mqtt.publish('state/spot', 'LIBERO', retain=True)
            else:
                self.free_timer = 0
    
    def check_gas(self):
        """Check gas levels - USA VALORI RAW!"""
        gas_raw = self.mq2.read_raw()  # Valore RAW 0-4095
        
        # Usa isteresi per evitare flapping
        if not self.gas_alarm and gas_raw > self.config.MQ2_THRESHOLD:
            print(f"⚠️ GAS ALARM! Raw: {gas_raw}")
            self.gas_alarm = True
            self.buzzer.start_alarm(freq=2500, interval=300)  # Suono diverso per gas
            self.alarm_led.on()
            
        elif self.gas_alarm and gas_raw < (self.config.MQ2_THRESHOLD - self.config.MQ2_HYSTERESIS):
            print(f"✅ Gas alarm cleared. Raw: {gas_raw}")
            self.gas_alarm = False
            self.buzzer.stop_alarm()
            self.alarm_led.off()
    
    def check_brightness(self):
        """Check ambient light - SOLO SE MODO AUTO"""
        if self.config.PARKING_LIGHT_MODE != "AUTO":
            return  # Skip se non in modalità AUTO
        
        try:
            if self.brightness_sensor:
                lux = self.brightness_sensor.read_lux()
                
                # Logica semplice: sotto soglia = accendi
                if lux < self.config.LUX_THRESHOLD:
                    self.parking_light.on(100)
                else:
                    self.parking_light.off()
                    
        except Exception as e:
            print(f"Brightness check error: {e}")
    
    def toggle_parking_light(self):
        """Toggle parking light manualmente"""
        print("Manual light toggle")
        if self.parking_light.brightness > 0:
            self.parking_light.off()
        else:
            self.parking_light.on(50)
    
    def system_reset(self):
        """Reset the system with NEW GRAPHIC"""
        print("System reset requested...")
        
        # Usa la nuova funzione grafica
        self.display.show_system_reset()
        
        if self.mqtt:
            self.mqtt.disconnect()
        
        time.sleep(2) # Tempo per ammirare l'icona
        machine.reset()
    
    def publish_telemetry(self):
        """Pubblica telemetria su MQTT con FILTRO DASHBOARD"""
        if not self.mqtt or not self.mqtt.connected:
            return
        
        try:
            # Prendi la distanza attuale (filtrata se possibile, o raw)
            distance = self.last_distance 
            
            # --- MODIFICA PER NODE-RED ---
            # Se la distanza reale è > 8cm (es. 27cm), inviamo 8.0 a Node-RED.
            # In questo modo il gauge resta fermo sul "max" o "vuoto" invece di segnare numeri a caso.
            # Usiamo 8.0 come valore "Fuori Scala / Vuoto"
            mqtt_distance = distance
            if distance > 8.0:
                mqtt_distance = 8.0
            
            # Lettura Lux e Gas
            lux = 0
            if self.brightness_sensor:
                try: lux = self.brightness_sensor.read_lux()
                except: pass
            
            gas_raw = self.mq2.read_raw()
            
            data = {
                'gate_state': self.servo.get_state(),
                'spot_occupied': self.car_parked,
                'distance': round(mqtt_distance, 1), # Usa il valore "tagliato"
                'gas_level': gas_raw,
                'gas_alarm': self.gas_alarm,
                'light': lux
            }
            
            self.mqtt.publish_telemetry(data)
            
        except Exception as e:
            print(f"Telemetry publish error: {e}")
    
    def update_display(self):
        """Update OLED display"""
        gas_raw = self.mq2.read_raw()
        lux_level = None
        
        try:
            if self.brightness_sensor:
                lux_level = self.brightness_sensor.read_lux()
        except:
            pass
        
        gate_open = self.servo.is_open()
        
        if self.gas_alarm:
            self.display.show_gas_alarm(gas_raw)
        elif self.parking_assist:
            distance = self.ultrasonic.distance_cm()
            self.display.show_parking_assist(distance)
        else:
            self.display.show_main_screen(
                gate_status=gate_open,
                parking_status=self.car_parked,
                gas_level=gas_raw,  # Mostra valore RAW
                alarm_active=self.gas_alarm,
                lux_level=lux_level
            )