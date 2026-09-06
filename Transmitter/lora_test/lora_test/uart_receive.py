import os
import random
import serial
import time
import zlib

from packet import Packet


# -------------------------------------------------
# UART
# -------------------------------------------------

ser = serial.Serial(
    '/dev/ttyAMA0',
    9600,
    timeout=0.5
)

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

print(f"\nLoaded {TOTAL_CHUNKS} chunks")

# -------------------------------------------------
# TRANSMISSION
# -------------------------------------------------

packet_id = 0

MAX_PACKETS = 800

print("\nStarting Wireless Transmission...\n")

while packet_id < MAX_PACKETS:

    # -----------------------------------------
    # START FEEDBACK CHECK ONLY LATE
    # -----------------------------------------

    if packet_id > 300:

        incoming = ser.read(100)

        if b'COMPLETE' in incoming:

            print(
                "\nReceiver completed recovery"
            )

            print(
                "Stopping transmission"
            )

            break

    # -----------------------------------------
    # DEGREE DISTRIBUTION
    # -----------------------------------------

    r = random.random()

    if r < 0.50:
        degree = 1

    elif r < 0.85:
        degree = 2

    else:
        degree = 3

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
        chunks[selected_indices[0]]
    )

    for idx in selected_indices[1:]:

        chunk_data = chunks[idx]

        for i in range(
            min(
                len(encoded_data),
                len(chunk_data)
            )
        ):

            encoded_data[i] ^= chunk_data[i]

    # -----------------------------------------
    # CREATE PACKET
    # -----------------------------------------

    packet = Packet(
        packet_id=packet_id,
        indices=selected_indices,
        payload=bytes(encoded_data)
    )

    payload = packet.to_bytes()

    # -----------------------------------------
    # CRC32
    # -----------------------------------------

    crc = zlib.crc32(payload)

    # -----------------------------------------
    # SEND FRAME
    # -----------------------------------------

    ser.write(b'\xAA\x55')

    ser.write(
        len(payload).to_bytes(2, 'big')
    )

    ser.write(
        crc.to_bytes(4, 'big')
    )

    ser.write(payload)

    if packet_id % 25 == 0:

        print(
            f"Sent Packet {packet_id}"
        )

    packet_id += 1

    # -----------------------------------------
    # LORA STABILITY DELAY
    # -----------------------------------------

    time.sleep(0.75)

print("\nTransmission Complete")