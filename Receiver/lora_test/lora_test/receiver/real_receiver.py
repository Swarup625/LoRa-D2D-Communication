import os
import serial
import zlib
import time

from packet import Packet


# -------------------------------------------------
# UART
# -------------------------------------------------

ser = serial.Serial(
    '/dev/ttyAMA0',
    9600,
    timeout=10
)

# -------------------------------------------------
# OUTPUT
# -------------------------------------------------

OUTPUT_FOLDER = "./recovered_chunks"

os.makedirs(
    OUTPUT_FOLDER,
    exist_ok=True
)

# -------------------------------------------------
# RECEIVE TOTAL CHUNKS
# -------------------------------------------------

print("Waiting for chunk count...")

chunk_info = b''

start = time.time()

while time.time() - start < 15:

    if ser.in_waiting:

        chunk_info += ser.read(
            ser.in_waiting
        )

        if b'CHUNKS:' in chunk_info:
            break

    time.sleep(0.1)

chunk_info = chunk_info.decode()

TOTAL_CHUNKS = int(
    chunk_info.split(
        "CHUNKS:"
    )[1]
)

print(
    f"Total Chunks: "
    f"{TOTAL_CHUNKS}"
)

# -------------------------------------------------
# STORAGE
# -------------------------------------------------

received_packets = []

decoded_chunks = {}

# -------------------------------------------------
# START TIMER
# -------------------------------------------------

start_time = time.time()

print("\nWaiting for Wireless Packets...\n")

# -------------------------------------------------
# RECEIVE LOOP
# -------------------------------------------------

while True:

    # -----------------------------------------
    # FIND START MARKER
    # -----------------------------------------

    first = ser.read(1)

    if first != b'\xAA':
        continue

    second = ser.read(1)

    if second != b'\x55':
        continue

    # -----------------------------------------
    # READ LENGTH
    # -----------------------------------------

    length_bytes = ser.read(2)

    if len(length_bytes) < 2:
        continue

    length = int.from_bytes(
        length_bytes,
        'big'
    )

    # -----------------------------------------
    # LENGTH VALIDATION
    # -----------------------------------------

    if length < 5 or length > 300:
        continue

    # -----------------------------------------
    # READ CRC
    # -----------------------------------------

    crc_bytes = ser.read(4)

    if len(crc_bytes) < 4:
        continue

    received_crc = int.from_bytes(
        crc_bytes,
        'big'
    )

    # -----------------------------------------
    # READ FULL PAYLOAD
    # -----------------------------------------

    data = b''

    while len(data) < length:

        chunk = ser.read(
            length - len(data)
        )

        if not chunk:
            break

        data += chunk

    if len(data) < length:
        continue

    # -----------------------------------------
    # CRC CHECK
    # -----------------------------------------

    calculated_crc = zlib.crc32(data)

    if calculated_crc != received_crc:

        print("CRC Failed")

        continue

    # -----------------------------------------
    # DESERIALIZE
    # -----------------------------------------

    try:

        packet = Packet.from_bytes(data)

    except:

        continue

    received_packets.append(packet)

    # -----------------------------------------
    # PEELING DECODER
    # -----------------------------------------

    progress = True

    while progress:

        progress = False

        for pkt in received_packets:

            payload = bytearray(pkt.payload)

            unknown = []

            for idx in pkt.indices:

                if idx in decoded_chunks:

                    known = decoded_chunks[idx]

                    for i in range(
                        min(
                            len(payload),
                            len(known)
                        )
                    ):

                        payload[i] ^= known[i]

                else:

                    unknown.append(idx)

            # -----------------------------------------
            # DEGREE-1 RECOVERY
            # -----------------------------------------

            if len(unknown) == 1:

                chunk_id = unknown[0]

                if chunk_id not in decoded_chunks:

                    decoded_chunks[chunk_id] = bytes(payload)

                    chunk_path = os.path.join(
                        OUTPUT_FOLDER,
                        f"chunk_{chunk_id}.bin"
                    )

                    with open(
                        chunk_path,
                        "wb"
                    ) as chunk_file:

                        chunk_file.write(
                            bytes(payload)
                        )

                    print(
                        f"Recovered Chunk "
                        f"{chunk_id}"
                    )

                    print(
                        f"Progress: "
                        f"{len(decoded_chunks)}/"
                        f"{TOTAL_CHUNKS}"
                    )

                    progress = True

                    # ---------------------------------
                    # AUTO STOP + FEEDBACK
                    # ---------------------------------

                    if len(decoded_chunks) >= TOTAL_CHUNKS:

                        end_time = time.time()

                        total_time = (
                            end_time - start_time
                        )

                        print(
                            "\nAll Chunks Recovered"
                        )

                        print(
                            f"\nTotal Transmission Time: "
                            f"{total_time:.2f} seconds"
                        )
                        print(
                            f"\nTotal Transmission Time: "
                            f"{total_time/60:.2f}"
                            f"minutes"
                        )

                        print(
                            "Sending COMPLETE signal"
                        )

                        time.sleep(2)

                        for _ in range(5):

                            ser.write(
                                b'COMPLETE'
                            )

                            ser.flush()

                            time.sleep(0.5)

                        print(
                            "Reception Complete"
                        )

                        exit()
