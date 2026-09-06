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
    timeout=0.5
)

# -------------------------------------------------
# RECEIVE TOTAL CHUNK COUNT
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
    f"Total Chunks: {TOTAL_CHUNKS}"
)

# -------------------------------------------------
# OUTPUT FOLDER
# -------------------------------------------------

OUTPUT_FOLDER = "./recovered_chunks"

os.makedirs(
    OUTPUT_FOLDER,
    exist_ok=True
)

# -------------------------------------------------
# STORAGE
# -------------------------------------------------

received_packets = []

decoded_chunks = {}

# -------------------------------------------------
# METRICS
# -------------------------------------------------

total_packets = 0

crc_failures = 0

# -------------------------------------------------
# TIMER
# -------------------------------------------------

start_time = time.time()

print("\nWaiting for Wireless Packets...\n")

# -------------------------------------------------
# RECEIVE LOOP
# -------------------------------------------------

while True:

    # -----------------------------------------
    # FRAME HEADER
    # -----------------------------------------

    first = ser.read(1)

    if first != b'\xAA':
        continue

    second = ser.read(1)

    if second != b'\x55':
        continue

    # -----------------------------------------
    # LENGTH
    # -----------------------------------------

    length_bytes = ser.read(2)

    if len(length_bytes) < 2:
        continue

    length = int.from_bytes(
        length_bytes,
        'big'
    )

    if length < 5 or length > 300:
        continue

    # -----------------------------------------
    # CRC
    # -----------------------------------------

    crc_bytes = ser.read(4)

    if len(crc_bytes) < 4:
        continue

    received_crc = int.from_bytes(
        crc_bytes,
        'big'
    )

    # -----------------------------------------
    # PAYLOAD
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

    total_packets += 1

    # -----------------------------------------
    # CRC CHECK
    # -----------------------------------------

    calculated_crc = zlib.crc32(data)

    if calculated_crc != received_crc:

        crc_failures += 1

        print(
            f"CRC Failed "
            f"({crc_failures})"
        )

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

        packets_to_remove = []

        for pkt in received_packets:

            payload = bytearray(pkt.payload)

            unknown = []

            # -----------------------------------------
            # REMOVE KNOWN CHUNKS
            # -----------------------------------------

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
            # FULLY RESOLVED
            # -----------------------------------------

            if len(unknown) == 0:

                packets_to_remove.append(pkt)

                continue

            # -----------------------------------------
            # DEGREE-1 RECOVERY
            # -----------------------------------------

            if len(unknown) == 1:

                chunk_id = unknown[0]

                if chunk_id in decoded_chunks:

                    packets_to_remove.append(pkt)

                    continue

                decoded_chunks[chunk_id] = bytes(payload)

                packets_to_remove.append(pkt)

                # -----------------------------------------
                # SAVE CHUNK
                # -----------------------------------------

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

                recovered = len(
                    decoded_chunks
                )

                print(
                    f"Recovered Chunk "
                    f"{chunk_id}"
                )

                print(
                    f"Progress: "
                    f"{recovered}/"
                    f"{TOTAL_CHUNKS}"
                )

                progress = True

                # -----------------------------------------
                # TARGETED RECOVERY MODE
                # -----------------------------------------

                threshold = int(
                    0.90 * TOTAL_CHUNKS
                )

                if recovered >= threshold:

                    missing_chunks = []

                    for i in range(
                        TOTAL_CHUNKS
                    ):

                        if i not in decoded_chunks:

                            missing_chunks.append(i)

                    # -----------------------------------------
                    # SEND MISSING IDS
                    # -----------------------------------------

                    if len(missing_chunks) > 0:

                        missing_msg = (
                            "MISSING:" +
                            ",".join(
                                map(
                                    str,
                                    missing_chunks
                                )
                            )
                        )

                        print(
                            "\nTARGETED MODE"
                        )

                        print(
                            "Missing:",
                            missing_chunks
                        )

                        print(
                            f"Sending: "
                            f"{missing_msg}"
                        )

                        # -----------------------------------------
                        # FEEDBACK TRANSMISSION
                        # -----------------------------------------

                        print(
                            "\nSending feedback "
                            "to sender..."
                        )

                        # LoRa turnaround delay
                        time.sleep(1)

                        for _ in range(1):

                            ser.write(
                                missing_msg.encode()
                            )

                            ser.flush()

                            print(
                                f"Feedback Sent: "
                                f"{missing_msg}"
                            )

                            time.sleep(0.5)

                # -----------------------------------------
                # FULL RECOVERY
                # -----------------------------------------

                if recovered >= TOTAL_CHUNKS:

                    end_time = time.time()

                    total_time = (
                        end_time -
                        start_time
                    )

                    print(
                        "\nAll Chunks Recovered"
                    )

                    print(
                        f"\nRecovered: "
                        f"{recovered}/"
                        f"{TOTAL_CHUNKS}"
                    )

                    print(
                        f"Total Packets: "
                        f"{total_packets}"
                    )

                    print(
                        f"CRC Failures: "
                        f"{crc_failures}"
                    )

                    print(
                        f"\nTotal Time: "
                        f"{total_time:.2f} "
                        f"seconds"
                    )

                    print(
                        f"Total Time: "
                        f"{total_time/60:.2f} "
                        f"minutes"
                    )

                    print(
                        "\nSending COMPLETE..."
                    )

                    # -----------------------------------------
                    # COMPLETE FEEDBACK
                    # -----------------------------------------

                    time.sleep(2)

                    for _ in range(5):

                        ser.write(
                            b'COMPLETE'
                        )

                        ser.flush()

                        print(
                            "COMPLETE sent"
                        )

                        time.sleep(0.5)

                    print(
                        "\nReception Complete"
                    )

                    exit()

        # -----------------------------------------
        # REMOVE RESOLVED PACKETS
        # -----------------------------------------

        for pkt in packets_to_remove:

            if pkt in received_packets:

                received_packets.remove(pkt)
