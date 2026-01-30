# main.py - DEBUG VERSION
import machine
import time
import gc
import sys

def main():
    print("=" * 50)
    print("SMART PARKING SYSTEM - Starting...")
    print("=" * 50)
    
    # Step-by-step initialization con dettagli errore
    try:
        print("[1/4] Importing Config...")
        from config import Config
        config = Config()
        print("✓ Config OK")
        
        print("[2/4] Importing SmartParking...")
        from parking import SmartParking
        print("✓ Import OK")
        
        print("[3/4] Creating SmartParking instance...")
        parking_system = SmartParking(config)
        print("✓ SmartParking created")
        
        print("[4/4] Starting main loop...")
        print("Free memory:", gc.mem_free())
        parking_system.run()
        
    except ImportError as e:
        print(f"❌ IMPORT ERROR: {e}")
        print(f"   Missing module: {str(e)}")
        sys.print_exception(e)
        
    except AttributeError as e:
        print(f"❌ ATTRIBUTE ERROR: {e}")
        print(f"   Check class methods and variables")
        sys.print_exception(e)
        
    except Exception as e:
        print(f"❌ FATAL ERROR: {type(e).__name__}")
        print(f"   Message: {e}")
        print(f"   Details:")
        sys.print_exception(e)
        
    finally:
        # Emergency error indication
        try:
            led = machine.Pin(2, machine.Pin.OUT)
            for _ in range(10):
                led.on()
                time.sleep(0.2)
                led.off()
                time.sleep(0.2)
        except:
            pass
            
        print("\n" + "=" * 50)
        print("System will reset in 5 seconds...")
        print("=" * 50)
        time.sleep(5)
        machine.reset()

if __name__ == "__main__":
    main()