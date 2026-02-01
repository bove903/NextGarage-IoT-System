import machine
import time
import gc
import sys

def main():
    print("NextGarage - Starting...")
    
    # Step-by-step initialization con dettagli errore:
    # L'idea è inizializzare il sistema a "passi", stampando dove si è arrivati.
    # In caso di errore, è più facile capire quale fase ha fallito (import/config/istanza/run).
    try:
        print("[1/4] Importing Config...")
        # Import e creazione della configurazione.
        # Se fallisce qui, tipicamente mancano file/config.py o ci sono errori sintattici in config.
        from config import Config
        config = Config()
        print("✓ Config OK")
        
        print("[2/4] Importing SmartParking...")
        # Import della classe principale applicativa.
        # Se fallisce qui, tipicamente mancano file (parking.py) o dipendenze importate da parking.py.
        from parking import SmartParking
        print("✓ Import OK")
        
        print("[3/4] Creating SmartParking instance...")
        # Crea l'istanza del sistema completo:
        # qui avvengono inizializzazioni hardware (WiFi, sensori, display, attuatori, MQTT...).
        parking_system = SmartParking(config)
        print("✓ SmartParking created")
        
        print("[4/4] Starting main loop...")
        # Stampa memoria libera prima di entrare nel loop infinito:
        # utile su MicroPython per diagnosticare problemi di memoria.
        print("Free memory:", gc.mem_free())
        
        # Avvia il loop principale del sistema (in genere non ritorna mai, salvo eccezioni/reset).
        parking_system.run()
        
    except ImportError as e:
        # Gestione mirata per errori di import:
        # utile per capire subito quale modulo manca o non è stato caricato correttamente.
        print(f"IMPORT ERROR: {e}")
        print(f"   Missing module: {str(e)}")
        # Stampa stacktrace completo con sys.print_exception (MicroPython-friendly).
        sys.print_exception(e)
        
    except AttributeError as e:
        # Gestione mirata per errori di attributo:
        # tipico quando un oggetto non ha un metodo/variabile attesa (refusi o version mismatch).
        print(f"ATTRIBUTE ERROR: {e}")
        print(f"   Check class methods and variables")
        sys.print_exception(e)
        
    except Exception as e:
        # Catch-all per qualsiasi altro errore non previsto.
        # Stampa tipo eccezione + messaggio + stacktrace per debug completo.
        print(f"FATAL ERROR: {type(e).__name__}")
        print(f"   Message: {e}")
        print(f"   Details:")
        sys.print_exception(e)
        
    finally:
        # finally viene eseguito SEMPRE, sia in caso di successo che in caso di errore/eccezione.
        # Qui è usato come segnalazione "di emergenza" e come reset controllato.
        
        # Emergency error indication:
        # Prova a lampeggiare un LED su GPIO2.
        # È dentro try/except per evitare crash se il pin non esiste o non è disponibile.
        try:
            led = machine.Pin(2, machine.Pin.OUT)
            for _ in range(10):
                led.on()
                time.sleep(0.2)
                led.off()
                time.sleep(0.2)
        except:
            # Se non è possibile usare il LED, ignora (robustezza su diverse board).
            pass
            
        print("System will reset in 5 seconds...")
        
        # Attesa 5 secondi prima del reset: dà tempo di leggere l'errore in seriale.
        time.sleep(5)
        
        # Reset hardware del microcontrollore.
        machine.reset()

if __name__ == "__main__":
    main()