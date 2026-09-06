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
    timeout=1
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

if TOTAL_CHUNKS == 0:

    print("No chunk files found")

    exit()

print(
    f"\nLoaded "
    f"{TOTAL_CHUNKS} chunks"
)

# -------------------------------------------------
# SEND TOTAL CHUNK COUNT
# -------------------------------------------------

chunk_message = (
    "CHUNKS:" + str(TOTAL_CHUNKS)
)

print(
    f"Sending chunk info: "
    f"{chunk_message}"
)

for _ in range(5):

    ser.write(
        chunk_message.encode()
    )

    ser.flush()

    time.sleep(0.5)

# -------------------------------------------------
# TRANSMISSION
# -------------------------------------------------

packet_id = 0

MAX_PACKETS = TOTAL_CHUNKS * 6

print(
    f"\nMAX_PACKETS: "
    f"{MAX_PACKETS}"
)

print(
    "\nStarting Fountain "
    "Transmission...\n"
)

while packet_id < MAX_PACKETS:

    # -----------------------------------------
    # CHECK COMPLETE SIGNAL
    # -----------------------------------------

    if packet_id > (
        2 * TOTAL_CHUNKS
    ):

        incoming = b''

        start_time = time.time()

        while (
            time.time() - start_time
        ) < 0.2:

            if ser.in_waiting:

                incoming += ser.read(
                    ser.in_waiting
                )

            time.sleep(0.02)

        if b'COMPLETE' in incoming:

            print(
                "\nReceiver completed "
                "recovery"
            )

            print(
                "Stopping transmission"
            )

            break

    # -------------------------------------------------
    # OPTIMIZED DEGREE DISTRIBUTION
    # -------------------------------------------------

    r = random.random()

    if r < 0.70:

        degree = 1

    elif r < 0.92:

        degree = 2

    else:

        degree = 3

    degree = min(
        degree,
        TOTAL_CHUNKS
    )

    # -------------------------------------------------
    # SELECT CHUNKS
    # -------------------------------------------------

    selected_indices = random.sample(
        range(TOTAL_CHUNKS),
        degree
    )

    # -------------------------------------------------
    # XOR ENCODING
    # -------------------------------------------------

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

            encoded_data[i] ^= (
                chunk_data[i]
            )

    # -------------------------------------------------
    # CREATE FOUNTAIN PACKET
    # -------------------------------------------------

    packet = Packet(
        packet_id=packet_id,
        indices=selected_indices,
        payload=bytes(encoded_data)
    )

    payload = (
        b'\x01' +
        packet.to_bytes()
    )

    # -------------------------------------------------
    # CRC32
    # -------------------------------------------------

    crc = zlib.crc32(payload)

    # -------------------------------------------------
    # BUILD FRAME
    # -------------------------------------------------

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

    # -------------------------------------------------
    # SEND FRAME
    # -------------------------------------------------

    ser.write(frame)

    ser.flush()

    if packet_id % 20 == 0:

        print(
            f"Sent Packet "
            f"{packet_id}"
        )

    packet_id += 1

    # -------------------------------------------------
    # TX DELAY
    # -------------------------------------------------

    time.sleep(0.55)

print(
    "\nTransmission Complete"
)
