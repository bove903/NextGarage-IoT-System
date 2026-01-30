# config.py
class Config:
    # I2C Pins for OLED and sensors
    PIN_SDA = 21
    PIN_SCL = 22
    
    # Master button (power on/off and reset)
    PIN_MASTER_BTN = 32
    
    # Gate system
    PIN_IR_ENTRANCE = 14    # IR ingresso
    PIN_IR_EXIT = 26        # IR uscita
    PIN_GATE_BUTTON = 12    # Pulsante apri sbarra
    PIN_SERVO = 15           # Servo motor
    
    # Traffic light
    PIN_TRAFFIC_RED = 27
    PIN_TRAFFIC_YELLOW = 4
    PIN_TRAFFIC_GREEN = 2
    
    # Parking spot sensors
    PIN_ULTRASONIC_TRIG = 5
    PIN_ULTRASONIC_ECHO = 18
    PIN_PARKING_RED = 16
    PIN_PARKING_GREEN = 33
    PIN_BUZZER = 17
    PIN_PARKING_LIGHT = 25
    PIN_ALARM_LED = 13
    
    # Gas sensor
    PIN_MQ2 = 34
    
    # Display settings
    OLED_WIDTH = 128
    OLED_HEIGHT = 64
    OLED_ADDRESS = 0x3C
    
    # TSL2561 settings
    TSL2561_ADDRESS = 0x39
    
    # WiFi Settings
    WIFI_SSID = "iPhone di Chris"
    WIFI_PASSWORD = "christianbove"
    
    # MQTT Settings (usa broker pubblico HiveMQ)
    MQTT_BROKER = "broker.hivemq.com"
    MQTT_PORT = 1883
    
    # ========== THRESHOLDS - CONFIGURABILI DA NODE-RED ==========
    
    # Distanza ultrasuoni (parcheggio piccolo)
    ULTRASONIC_MIN_DISTANCE = 3      # cm - distanza minima per occupazione
    ULTRASONIC_MAX_DISTANCE = 7     # cm - distanza massima rilevazione
    ULTRASONIC_OCCUPIED_CONFIRM = 3000  # ms - tempo conferma occupazione (5 secondi)
    ULTRASONIC_FREE_CONFIRM = 2000   # ms - tempo conferma liberazione (3 secondi)
    
    # Buzzer assistenza parcheggio
    BUZZER_MIN_DISTANCE = 2          # cm - sotto = STOP (no buzzer)
    BUZZER_MAX_DISTANCE = 8          # cm - sopra = no buzzer
    
    # Gas MQ2 - VALORI RAW ADC (0-4095)
    MQ2_THRESHOLD = 1500             # Soglia allarme (valore RAW, non percentuale!)
    MQ2_HYSTERESIS = 200             # Isteresi per evitare flapping
    
    # Luminosità TSL2561 (lux)
    LUX_THRESHOLD = 50               # Sotto questa soglia = accendi luci (se AUTO)
    
    # Parking light mode
    PARKING_LIGHT_MODE = "AUTO"      # AUTO, ON, OFF
    
    # ========== TIMING ==========
    DEBOUNCE_DELAY = 50              # ms
    YELLOW_BLINK_INTERVAL = 150      # ms - lampeggio giallo
    BUZZER_UPDATE_INTERVAL = 100     # ms
    SERVO_MOVE_DELAY = 15            # ms - delay tra step servo (più basso = più veloce)
    
    # Servo angles
    SERVO_OPEN_ANGLE = 90
    SERVO_CLOSE_ANGLE = 0
    
    # Button timing
    SHORT_PRESS_DURATION = 100       # ms per pressione breve
    LONG_PRESS_DURATION = 5000       # ms (5 secondi) per reset
    
    # MQTT publish intervals (ms)
    MQTT_TELEMETRY_INTERVAL = 2000   # Pubblica telemetria ogni 2 secondi
    MQTT_FAST_UPDATE_INTERVAL = 500  # Update veloce per distanza
    
    def update_threshold(self, param, value):
        """Aggiorna una soglia dinamicamente"""
        try:
            value = float(value)
            if param == "mq2_threshold":
                self.MQ2_THRESHOLD = int(value)
                print(f"MQ2_THRESHOLD updated to {self.MQ2_THRESHOLD}")
            elif param == "mq2_hyst":
                self.MQ2_HYSTERESIS = int(value)
                print(f"MQ2_HYSTERESIS updated to {self.MQ2_HYSTERESIS}")
            elif param == "lux_threshold":
                self.LUX_THRESHOLD = int(value)
                print(f"LUX_THRESHOLD updated to {self.LUX_THRESHOLD}")
            return True
        except Exception as e:
            print(f"Error updating {param}: {e}")
            return False
    
    def update_light_mode(self, mode):
        """Aggiorna modalità luci parcheggio"""
        mode = mode.upper().strip()
        if mode in ["AUTO", "ON", "OFF"]:
            self.PARKING_LIGHT_MODE = mode
            print(f"PARKING_LIGHT_MODE updated to {mode}")
            return True
        print(f"Invalid light mode: {mode}")
        return False