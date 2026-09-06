import os
import random
import serial
import time
import zlib
import csv

from packet import Packet

# -------------------------------------------------
# CONFIG
# -------------------------------------------------

SOURCE_WINDOW = 6
D2D_WINDOW = 6

CYCLE_TIME = (
    SOURCE_WINDOW +
    D2D_WINDOW
)

# -------------------------------------------------
# UART
# -------------------------------------------------

ser = serial.Serial(
    '/dev/ttyAMA0',
    9600,
    timeout=10
)

# -------------------------------------------------
# LOGGING
# -------------------------------------------------

os.makedirs(
    "./logs",
    exist_ok=True
)

CSV_FILE = "./logs/source_log.csv"

if not os.path.exists(CSV_FILE):

    with open(
        CSV_FILE,
        "w",
        newline=""
    ) as f:

        writer = csv.writer(f)

        writer.writerow([
            "packet_id",
            "degree",
            "selected_chunks",
            "window",
            "timestamp"
        ])

# -------------------------------------------------
# LOAD CHUNKS
# -------------------------------------------------

CHUNK_FOLDER = "./packets"

chunk_files = sorted(
    [
        f for f in os.listdir(CHUNK_FOLDER)
        if f.startswith("chunk_")
    ],
    key=lambda x: int(
        x.split("_")[1].split(".")[0]
    )
)

chunks = []

for chunk_name in chunk_files:

    path = os.path.join(
        CHUNK_FOLDER,
        chunk_name
    )

    with open(path, "rb") as f:

        chunks.append(f.read())

TOTAL_CHUNKS = len(chunks)

if TOTAL_CHUNKS == 0:

    print("No chunk files found")
    exit()

print(
    f"\nLoaded {TOTAL_CHUNKS} chunks"
)

# -------------------------------------------------
# NETWORK START
# -------------------------------------------------

NETWORK_START_TIME = (
    time.time() + 5
)

start_message = (
    f"START|"
    f"{NETWORK_START_TIME}|"
    f"{TOTAL_CHUNKS}\n"
)

print(
    "\nBroadcasting START..."
)

for _ in range(10):

    ser.write(
        start_message.encode()
    )

    ser.flush()

    time.sleep(0.2)

print(
    "Network synchronized"
)

print(
    f"Network Start Time: "
    f"{NETWORK_START_TIME}"
)

while time.time() < NETWORK_START_TIME:

    time.sleep(0.1)

# -------------------------------------------------
# TRANSMISSION
# -------------------------------------------------

packet_id = 0

MAX_PACKETS = TOTAL_CHUNKS * 10

print(
    f"\nMAX_PACKETS: "
    f"{MAX_PACKETS}"
)

print(
    "\nStarting Cooperative "
    "Transmission...\n"
)

while packet_id < MAX_PACKETS:

    # -----------------------------------------
    # WINDOW CONTROL
    # -----------------------------------------

    cycle_position = (

        time.time()
        -
        NETWORK_START_TIME

    ) % CYCLE_TIME

    # -----------------------------------------
    # D2D WINDOW
    # -----------------------------------------

    if cycle_position >= SOURCE_WINDOW:

        time.sleep(0.1)

        continue

    # -----------------------------------------
    # COMPLETE SIGNAL CHECK
    # -----------------------------------------

    if packet_id > (
        1.5 * TOTAL_CHUNKS
    ) and packet_id % 3 == 0:

        incoming = b''

        start_time = time.time()

        while time.time() - start_time < 1:

            if ser.in_waiting:

                incoming += ser.read(
                    ser.in_waiting
                )

            time.sleep(0.05)

        if b'COMPLETE' in incoming:

            print(
                "\nReceiver completed "
                "recovery"
            )

            print(
                "Stopping transmission"
            )

            break

    # -----------------------------------------
    # DEGREE DISTRIBUTION
    # -----------------------------------------

    r = random.random()

    if r < 0.8:

        degree = random.randint(
            1,
            4
        )

    else:

        degree = random.randint(
            5,
            10
        )

    degree = min(
        degree,
        TOTAL_CHUNKS
    )

    # -----------------------------------------
    # SELECT CHUNKS
    # -----------------------------------------

    selected_indices = random.sample(
        range(TOTAL_CHUNKS),
        degree
    )

    # -----------------------------------------
    # XOR ENCODING
    # -----------------------------------------

    encoded_data = bytearray(
        chunks[
            selected_indices[0]
        ]
    )

    for idx in selected_indices[1:]:

        chunk_data = chunks[idx]

        for i in range(
            min(
                len(encoded_data),
                len(chunk_data)
            )
        ):

            encoded_data[i] ^= (
                chunk_data[i]
            )

    # -----------------------------------------
    # CREATE FOUNTAIN PACKET
    # -----------------------------------------

    packet = Packet(
        packet_id=packet_id,
        indices=selected_indices,
        payload=bytes(
            encoded_data
        )
    )

    payload = (
        b'\x01' +
        packet.to_bytes()
    )

    crc = zlib.crc32(
        payload
    )

    frame = (

        b'\xAA\x55' +

        len(payload).to_bytes(
            2,
            'big'
        ) +

        crc.to_bytes(
            4,
            'big'
        ) +

        payload
    )

    # -----------------------------------------
    # SEND
    # -----------------------------------------

    ser.write(frame)

    ser.flush()

    # -----------------------------------------
    # LOG PACKET
    # -----------------------------------------

    with open(
        CSV_FILE,
        "a",
        newline=""
    ) as f:

        writer = csv.writer(f)

        writer.writerow([
            packet_id,
            degree,
            str(selected_indices),
            "SOURCE_WINDOW",
            time.time()
        ])

    if packet_id % 10 == 0:

        print(
            f"Sent Packet "
            f"{packet_id}"
        )

    packet_id += 1

    time.sleep(0.8)

# -------------------------------------------------
# SUMMARY
# -------------------------------------------------

total_time = (
    time.time()
    - NETWORK_START_TIME
)

print(
    f"\nPackets Sent: "
    f"{packet_id}"
)

print(
    f"Transmission Time: "
    f"{total_time:.2f} sec"
)

SUMMARY_FILE = (
    "./logs/source_summary.csv"
)

summary_exists = os.path.exists(
    SUMMARY_FILE
)

with open(
    SUMMARY_FILE,
    "a",
    newline=""
) as f:

    writer = csv.writer(f)

    if not summary_exists:

        writer.writerow([
            "total_chunks",
            "packets_sent",
            "transmission_time_sec"
        ])

    writer.writerow([
        TOTAL_CHUNKS,
        packet_id,
        round(total_time, 2)
    ])

print(
    "\nTransmission Complete"
)
