import os
import serial
import zlib
import time
import csv
import random

from packet import Packet

# -------------------------------------------------
# CONFIG
# -------------------------------------------------

HELPER_ID = 2

BASE_BACKOFF = 1.0

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
# OUTPUT
# -------------------------------------------------

OUTPUT_FOLDER = "./recovered_chunks"

LOG_FOLDER = "./logs"

os.makedirs(
    OUTPUT_FOLDER,
    exist_ok=True
)

os.makedirs(
    LOG_FOLDER,
    exist_ok=True
)

# -------------------------------------------------
# CSV LOGGING
# -------------------------------------------------

CSV_FILE = "./logs/helper_log.csv"

if not os.path.exists(CSV_FILE):

    with open(
        CSV_FILE,
        "w",
        newline=""
    ) as f:

        writer = csv.writer(f)

        writer.writerow([
            "helper_id",
            "chunk_id",
            "event",
            "decoded_count",
            "timestamp"
        ])

# -------------------------------------------------
# START SYNC
# -------------------------------------------------

print(
    "Waiting for START..."
)

NETWORK_START_TIME = None
TOTAL_CHUNKS = None

while True:

    line = ser.readline().decode(
        errors="ignore"
    ).strip()

    if line.startswith(
        "START|"
    ):

        parts = line.split("|")

        NETWORK_START_TIME = float(
            parts[1]
        )

        TOTAL_CHUNKS = int(
            parts[2]
        )

        break

print(
    f"Network Start: "
    f"{NETWORK_START_TIME}"
)

print(
    f"Total Chunks: "
    f"{TOTAL_CHUNKS}"
)

while time.time() < NETWORK_START_TIME:

    time.sleep(0.1)

# -------------------------------------------------
# STORAGE
# -------------------------------------------------

received_packets = []

decoded_chunks = {}

relay_queue = {}

sent_chunks = set()

# -------------------------------------------------
# TIMER
# -------------------------------------------------

helper_start_time = time.time()

helper_complete = False

print(
    "\nD2D Helper Running...\n"
)
# -------------------------------------------------
# MAIN LOOP
# -------------------------------------------------

while True:

    cycle_position = (

        time.time()
        -
        NETWORK_START_TIME

    ) % CYCLE_TIME

    # -----------------------------------------
    # D2D WINDOW
    # -----------------------------------------

    while (
        len(relay_queue) > 0
    ):

            chunk_id = next(
                iter(relay_queue)
            )

            recovered_data = relay_queue.pop(
                chunk_id
            )

            if chunk_id in sent_chunks:
                continue

            time.sleep(
                BASE_BACKOFF +
                random.uniform(
                    0.2,
                    0.8
                )
            )

            helper_payload = (

                b'\x02' +

                HELPER_ID.to_bytes(
                    1,
                    'big'
                ) +

                chunk_id.to_bytes(
                    2,
                    'big'
                ) +

                len(
                    recovered_data
                ).to_bytes(
                    2,
                    'big'
                ) +

                recovered_data
            )

            crc = zlib.crc32(
                helper_payload
            )

            frame = (

                b'\xAA\x55' +

                len(
                    helper_payload
                ).to_bytes(
                    2,
                    'big'
                ) +

                crc.to_bytes(
                    4,
                    'big'
                ) +

                helper_payload
            )

            ser.write(frame)

            ser.flush()

            print(
                f"Helper "
                f"{HELPER_ID} "
                f"Sent Chunk "
                f"{chunk_id}"
            )

            with open(
                CSV_FILE,
                "a",
                newline=""
            ) as f:

                writer = csv.writer(f)

                writer.writerow([
                    HELPER_ID,
                    chunk_id,
                    "SENT",
                    len(decoded_chunks),
                    time.time()
                ])

            sent_chunks.add(
                chunk_id
            )


    # -----------------------------------------
    # COMPLETE SIGNAL
    # -----------------------------------------

    # -----------------------------------------
    # HELPER COMPLETE MODE
    # -----------------------------------------

    if helper_complete:

        time.sleep(0.1)

        continue


    # -----------------------------------------
    # RECEIVE PACKET
    # -----------------------------------------

    first = ser.read(1)

    if first != b'\xAA':
        continue

    second = ser.read(1)

    if second != b'\x55':
        continue

    length_bytes = ser.read(2)

    if len(length_bytes) < 2:
        continue

    length = int.from_bytes(
        length_bytes,
        'big'
    )

    crc_bytes = ser.read(4)

    if len(crc_bytes) < 4:
        continue

    received_crc = int.from_bytes(
        crc_bytes,
        'big'
    )

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

    calculated_crc = zlib.crc32(
        data
    )

    if calculated_crc != received_crc:

        continue

    packet_type = data[0]

    if packet_type != 0x01:
        continue

    actual_payload = data[1:]

    if helper_complete:
        continue

    try:

        packet = Packet.from_bytes(
            actual_payload
        )

    except:

        continue

    received_packets.append(
        packet
    )
    # -------------------------------------------------
    # FAST PEELING DECODER
    # -------------------------------------------------

    progress = True

    while progress:

        progress = False

        removable_packets = []

        for pkt in received_packets:

            payload = bytearray(
                pkt.payload
            )

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

                    unknown.append(
                        idx
                    )

            # ---------------------------------
            # RESOLVED PACKET
            # ---------------------------------

            if len(unknown) == 0:

                removable_packets.append(
                    pkt
                )

                continue

            # ---------------------------------
            # DEGREE-1 RECOVERY
            # ---------------------------------

            if len(unknown) == 1:

                chunk_id = unknown[0]

                if chunk_id not in decoded_chunks:

                    recovered_data = bytes(
                        payload
                    )

                    decoded_chunks[
                        chunk_id
                    ] = recovered_data

                    # -------------------------
                    # QUEUE FOR D2D RELAY
                    # -------------------------

                    relay_queue[
                        chunk_id
                    ] = recovered_data

                    print(
                        f"Recovered Chunk "
                        f"{chunk_id}"
                    )

                    print(
                        f"Progress: "
                        f"{len(decoded_chunks)}"
                        f"/"
                        f"{TOTAL_CHUNKS}"
                    )

                    # -------------------------
                    # SAVE CHUNK
                    # -------------------------

                    chunk_path = os.path.join(
                        OUTPUT_FOLDER,
                        f"chunk_{chunk_id}.bin"
                    )

                    with open(
                        chunk_path,
                        "wb"
                    ) as chunk_file:

                        chunk_file.write(
                            recovered_data
                        )

                    # -------------------------
                    # CSV LOG
                    # -------------------------

                    with open(
                        CSV_FILE,
                        "a",
                        newline=""
                    ) as f:

                        writer = csv.writer(f)

                        writer.writerow([
                            HELPER_ID,
                            chunk_id,
                            "RECOVERED",
                            len(decoded_chunks),
                            time.time()
                        ])

                    progress = True

        # -------------------------------------
        # REMOVE RESOLVED PACKETS
        # -------------------------------------

        for pkt in removable_packets:

            if pkt in received_packets:

                received_packets.remove(
                    pkt
                )

    # -------------------------------------------------
    # FULL FILE DECODED
    # -------------------------------------------------

    if (
        len(decoded_chunks)
        >= TOTAL_CHUNKS
        and
        not helper_complete
    ):

        helper_complete = True

        helper_total = (
            time.time()
            -
            helper_start_time
        )

        print(
            "\nHelper Fully Decoded "
            "All Chunks"
        )

        print(
            f"\nHelper Decode Time: "
            f"{helper_total:.2f} seconds"
        )

        print(
            f"\nHelper Decode Time: "
            f"{helper_total/60:.2f} minutes"
        )

        with open(
            CSV_FILE,
            "a",
            newline=""
        ) as f:

            writer = csv.writer(f)

            writer.writerow([
                HELPER_ID,
                -1,
                f"COMPLETE_{helper_total:.2f}",
                len(decoded_chunks),
                time.time()
            ])

        print(
            "\nHelper entering "
            "relay-only mode"
        )
