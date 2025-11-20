# NextGarage-IoT-System
🧱 Project Structure
--------------------

```
NextGarage-IoT-System/
│
├── firmware/                   → codice MicroPython
│   ├── main.py
│   ├── hardware/
│   │   ├── servo.py
│   │   ├── mq2.py
│   │   ├── ir_sensor.py
│   │   ├── oled.py
│   │   └── buzzer.py
│   ├── network/
│   │   ├── wifi_manager.py
│   │   ├── mqtt_client.py
│   │   └── config.py
│   ├── utils/
│   │   └── logger.py
│   └── requirements.txt
│
├── node-red/                   → flow.json per dashboard
│
├── docs/                       → documentazione, schema elettrico
│   ├── wiring_diagram.png
│   ├── flow_MQTT.png
│   └── project_description.md                   
│
├── README.md
├── LICENSE
└── .gitignore
```
