"""
============================================================
 TEMPERATURE MONITOR — PC Side (Python)
============================================================
 Reads temperature values from Arduino via USB serial port.
 Displays them in real-time in the terminal.
 Publishes each reading to an MQTT broker on your VPS.

 Install dependencies first:
   pip install pyserial paho-mqtt

 Usage:
   python temperature_pc.py

 Configuration: edit the SETTINGS block below.
============================================================
"""

import serial
import serial.tools.list_ports
import paho.mqtt.client as mqtt
import time
import sys
import datetime

# ============================================================
#  SETTINGS — change these to match your setup
# ============================================================

# --- Serial (Arduino) ----------------------------------------
SERIAL_PORT  = "COM9"       # Windows: "COM3", "COM4" etc.
                             # Linux/Mac: "/dev/ttyUSB0" or "/dev/ttyACM0"
SERIAL_BAUD  = 9600
SERIAL_TIMEOUT = 2          # seconds to wait for a line

# --- MQTT Broker (your VPS) ----------------------------------
MQTT_BROKER  = "157.173.101.159"   # e.g. "192.168.1.100" or "myserver.com"
MQTT_PORT    = 1883
MQTT_TOPIC   = "home/temperature"
MQTT_CLIENT_ID = "arduino-temperature-monitor"

# Optional authentication (leave as None if not configured)
MQTT_USERNAME = None        # e.g. "myuser"
MQTT_PASSWORD = None        # e.g. "mypassword"

# How often to print a status line even with no new reading
STATUS_INTERVAL = 10        # seconds
# ============================================================


# ---- Helpers -----------------------------------------------
def timestamp():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def list_serial_ports():
    """Print available serial ports to help you find the right one."""
    ports = serial.tools.list_ports.comports()
    if not ports:
        print("  (no serial ports found)")
    for p in ports:
        print(f"  {p.device}  —  {p.description}")


# ---- MQTT callbacks ----------------------------------------
def on_connect(client, userdata, flags, rc):
    codes = {
        0: "Connected successfully",
        1: "Wrong protocol version",
        2: "Invalid client ID",
        3: "Broker unavailable",
        4: "Bad username/password",
        5: "Not authorised",
    }
    msg = codes.get(rc, f"Unknown error (rc={rc})")
    if rc == 0:
        print(f"[MQTT] ✓ {msg} → broker at {MQTT_BROKER}:{MQTT_PORT}")
    else:
        print(f"[MQTT] ✗ Connection failed: {msg}")

def on_disconnect(client, userdata, rc):
    if rc != 0:
        print(f"[MQTT] Unexpected disconnect (rc={rc}). Will retry...")

def on_publish(client, userdata, mid):
    pass   # silent on publish — we print our own confirmation


# ---- Main --------------------------------------------------
def main():
    print("=" * 55)
    print("  Arduino Temperature Monitor — PC Program")
    print("=" * 55)

    # -- Connect to MQTT broker --------------------------------
    print(f"\n[MQTT] Connecting to broker at {MQTT_BROKER}:{MQTT_PORT} ...")
    mqtt_client = mqtt.Client(client_id=MQTT_CLIENT_ID)
    mqtt_client.on_connect    = on_connect
    mqtt_client.on_disconnect = on_disconnect
    mqtt_client.on_publish    = on_publish

    if MQTT_USERNAME:
        mqtt_client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)

    try:
        mqtt_client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
        mqtt_client.loop_start()   # background thread handles MQTT
    except Exception as e:
        print(f"[MQTT] ✗ Cannot connect to broker: {e}")
        print("       Check your VPS IP, port, and firewall settings.")
        print("       The program will still read from Arduino (no MQTT).")

    # -- Open serial port to Arduino ---------------------------
    print(f"\n[Serial] Opening {SERIAL_PORT} at {SERIAL_BAUD} baud...")
    print("[Serial] Available ports on this computer:")
    list_serial_ports()

    try:
        ser = serial.Serial(SERIAL_PORT, SERIAL_BAUD, timeout=SERIAL_TIMEOUT)
        time.sleep(2)   # Arduino resets when serial opens; wait for it
        ser.reset_input_buffer()
        print(f"[Serial] ✓ Connected to {SERIAL_PORT}")
    except serial.SerialException as e:
        print(f"\n[Serial] ✗ Cannot open {SERIAL_PORT}: {e}")
        print("  Make sure the Arduino is plugged in and the port is correct.")
        print("  Set SERIAL_PORT in the SETTINGS section at the top of this file.")
        sys.exit(1)

    # -- Main reading loop -------------------------------------
    print("\n" + "=" * 55)
    print(f"  {'Timestamp':<22} {'Temperature':>12}   MQTT")
    print("=" * 55)

    last_status = time.time()
    reading_count = 0

    try:
        while True:
            try:
                line = ser.readline().decode("utf-8", errors="ignore").strip()
            except serial.SerialException as e:
                print(f"\n[Serial] Connection lost: {e}")
                break

            if not line:
                # No data this cycle — print periodic heartbeat
                if time.time() - last_status > STATUS_INTERVAL:
                    print(f"  {timestamp():<22} {'(waiting...)':<13}")
                    last_status = time.time()
                continue

            # Parse lines starting with "TEMP:"
            if line.startswith("TEMP:"):
                value_str = line[5:].strip()   # everything after "TEMP:"

                if value_str == "ERROR":
                    display = "Sensor error"
                    mqtt_payload = None
                else:
                    try:
                        temp_value = float(value_str)
                        display = f"{temp_value:.1f} °C"
                        mqtt_payload = str(round(temp_value, 1))
                    except ValueError:
                        display = f"Bad data: {value_str}"
                        mqtt_payload = None

                # Publish to MQTT
                mqtt_status = ""
                if mqtt_payload is not None:
                    try:
                        result = mqtt_client.publish(MQTT_TOPIC, mqtt_payload, qos=1)
                        if result.rc == mqtt.MQTT_ERR_SUCCESS:
                            mqtt_status = f"✓ → {MQTT_TOPIC}"
                        else:
                            mqtt_status = "✗ publish failed"
                    except Exception as e:
                        mqtt_status = f"✗ {e}"

                reading_count += 1
                ts = timestamp()
                print(f"  {ts:<22} {display:>12}   {mqtt_status}")
                last_status = time.time()

            elif line == "READY":
                print(f"  [{timestamp()}] Arduino started OK")

    except KeyboardInterrupt:
        print(f"\n\n[Info] Stopped by user after {reading_count} readings.")

    finally:
        ser.close()
        mqtt_client.loop_stop()
        mqtt_client.disconnect()
        print("[Info] Serial and MQTT connections closed.")


if __name__ == "__main__":
    main()
