from flask import Flask, jsonify, render_template
import serial
import threading
import time
import sqlite3

app = Flask(__name__)

SERIAL_PORT = 'COM7'   # ⚠️ change if needed
BAUD_RATE = 9600
GAS_THRESHOLD = 300

latest_data = {
    "temperature": "Waiting...",
    "humidity": "Waiting...",
    "gas": "Waiting...",
    "status": "WAITING"
}

# ---------- CREATE DATABASE ----------
conn = sqlite3.connect("data.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS sensor_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    temperature REAL,
    humidity REAL,
    gas INTEGER,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
)
""")

conn.commit()
conn.close()
# ------------------------------------


def serial_read_thread():
    global latest_data

    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=2)
        print("✅ Serial Connected:", SERIAL_PORT)
        time.sleep(2)
        ser.flushInput()

        while True:
            line = ser.readline().decode(errors='ignore').strip()

            if line:
                print("📡 DATA:", line)

                if "," in line:
                    parts = line.split(",")

                    if len(parts) == 3:
                        try:
                            temp = float(parts[0])
                            hum = float(parts[1])
                            gas = int(parts[2])

                            status = "SAFE"
                            if gas >= GAS_THRESHOLD:
                                status = "DANGER"

                            latest_data["temperature"] = str(round(temp, 2))
                            latest_data["humidity"] = str(round(hum, 2))
                            latest_data["gas"] = str(gas)
                            latest_data["status"] = status

                            # -------- SAVE TO DATABASE --------
                            conn = sqlite3.connect("data.db")
                            cursor = conn.cursor()

                            cursor.execute(
                                "INSERT INTO sensor_data (temperature, humidity, gas) VALUES (?, ?, ?)",
                                (temp, hum, gas)
                            )

                            conn.commit()
                            conn.close()
                            # ---------------------------------

                        except:
                            pass

    except Exception as e:
        print("❌ Serial Error:", e)


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/data")
def data():
    return jsonify(latest_data)


@app.route("/history")
def history():
    conn = sqlite3.connect("data.db")
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM sensor_data ORDER BY id DESC LIMIT 10")
    rows = cursor.fetchall()

    conn.close()

    return jsonify(rows)


if __name__ == "__main__":
    threading.Thread(target=serial_read_thread, daemon=True).start()
    app.run(debug=False)