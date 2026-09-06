import serial
import time
import random
import csv
import os

from config import *

# -----------------------------------
# UART SETUP
# -----------------------------------

ser = serial.Serial(
    UART_PORT,
    BAUDRATE,
    timeout=0.5
)

# -----------------------------------
# CSV LOGGING
# -----------------------------------

LOG_FILE = "./logs/sender_log.csv"

os.makedirs("./logs", exist_ok=True)

if not os.path.exists(LOG_FILE):

    with open(LOG_FILE, "w", newline="") as f:

        writer = csv.writer(f)

        writer.writerow([
            "packet_id",
            "timestamp",
            "sf",
            "tx_power",
            "distance"
        ])

# -----------------------------------
# EXPERIMENT INFO
# -----------------------------------

print("\n========== LoRa Experiment ==========")

print(f"SF          : {SPREADING_FACTOR}")
print(f"TX POWER    : {TX_POWER}")
print(f"DISTANCE    : {DISTANCE}")
print(f"MAX PACKETS : {MAX_PACKETS}")

print("=====================================\n")

# -----------------------------------
# SEND PACKETS
# -----------------------------------

for packet_id in range(MAX_PACKETS):

    # Create dummy payload

    payload = bytes(
        random.getrandbits(8)
        for _ in range(PACKET_SIZE)
    )

    # Send frame

    ser.write(payload)

    # Console output

    print(f"Sent Packet {packet_id}")

    # CSV log

    with open(LOG_FILE, "a", newline="") as f:

        writer = csv.writer(f)

        writer.writerow([
            packet_id,
            time.time(),
            SPREADING_FACTOR,
            TX_POWER,
            DISTANCE
        ])

    time.sleep(SEND_DELAY)

print("\nTransmission Complete\n")