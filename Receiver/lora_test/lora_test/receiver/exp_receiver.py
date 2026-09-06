import serial
import time
import csv
import os
import random
import json

from config import *

# -----------------------------------
# UART SETUP
# -----------------------------------

ser = serial.Serial(
    UART_PORT,
    BAUDRATE,
    timeout=1
)

# -----------------------------------
# CREATE LOGS FOLDER
# -----------------------------------

os.makedirs("./logs", exist_ok=True)

# -----------------------------------
# CSV FILE
# -----------------------------------

CSV_FILE = "./logs/results.csv"

if not os.path.exists(CSV_FILE):

    with open(CSV_FILE, "w", newline="") as f:

        writer = csv.writer(f)

        writer.writerow([
            "packet_id",
            "distance",
            "sf",
            "tx_power",
            "rssi",
            "snr",
            "status",
            "timestamp"
        ])

# -----------------------------------
# INITIAL LIVE DATA FILE
# -----------------------------------

with open("live_data.json", "w") as f:

    json.dump({

        "rssi": 0,
        "snr": 0,
        "packets": 0,
        "tx_time": 0,

        "tx_lat": 20.1480,
        "tx_lon": 85.6680,

        "rx_lat": 20.1495,
        "rx_lon": 85.6701

    }, f)

# -----------------------------------
# EXPERIMENT INFO
# -----------------------------------

print("\n========== RECEIVER ==========")

print(f"SF          : {SPREADING_FACTOR}")
print(f"TX POWER    : {TX_POWER}")
print(f"DISTANCE    : {DISTANCE}")

print("==============================\n")

# -----------------------------------
# START TIMER
# -----------------------------------

start_time = time.time()

# -----------------------------------
# RECEIVE LOOP
# -----------------------------------

packet_id = 0

while packet_id < MAX_PACKETS:

    data = ser.read(128)

    if len(data) > 0:

        # -----------------------------------
        # SIMULATED PACKET LOSS
        # -----------------------------------

        if random.randint(1,100) <= LOSS_PERCENT:

            print(f"Packet {packet_id} DROPPED")

            status = "dropped"

            rssi = 0
            snr = 0

        else:

            # -----------------------------------
            # SIMULATED RSSI/SNR
            # -----------------------------------

            rssi = random.randint(-120, -40)

            snr = round(
                random.uniform(-20, 10),
                2
            )

            print(
                f"Packet {packet_id} | "
                f"RSSI={rssi} | "
                f"SNR={snr}"
            )

            status = "received"

        # -----------------------------------
        # UPDATE LIVE DASHBOARD DATA
        # -----------------------------------

        live_data = {

            "rssi": rssi,

            "snr": snr,

            "packets": packet_id + 1,

            "tx_time": (
                time.time() - start_time
            ),

            "tx_lat": 20.1480,
            "tx_lon": 85.6680,

            "rx_lat": 20.1495,
            "rx_lon": 85.6701
        }

        with open("live_data.json", "w") as f:

            json.dump(
                live_data,
                f
            )

        # -----------------------------------
        # SAVE CSV
        # -----------------------------------

        with open(CSV_FILE, "a", newline="") as f:

            writer = csv.writer(f)

            writer.writerow([
                packet_id,
                DISTANCE,
                SPREADING_FACTOR,
                TX_POWER,
                rssi,
                snr,
                status,
                time.time()
            ])

        packet_id += 1

print("\nExperiment Complete\n")
