import os
import serial
import zlib
import time
import csv
import random

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

CSV_FILE = "./logs/receiver_log.csv"

if not os.path.exists(CSV_FILE):

    with open(
        CSV_FILE,
        "w",
        newline=""
    ) as f:

        writer = csv.writer(f)

        writer.writerow([
            "chunk_id",
            "source",
            "progress",
            "timestamp"
        ])

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

chunk_text = chunk_info.decode(
    errors='ignore'
)

TOTAL_CHUNKS = int(
    chunk_text.split(
        "CHUNKS:"
    )[1].split()[0]
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

helper_chunks_used = set()

# -------------------------------------------------
# TIMER
# -------------------------------------------------

start_time = time.time()

last_progress_time = time.time()

print(
    "\nAdaptive Cooperative "
    "Receiver Running...\n"
)

# -------------------------------------------------
# PEELING DECODER
# -------------------------------------------------

def run_decoder(source_name):

    global received_packets
    global decoded_chunks
    global last_progress_time

    progress = True

    while progress:

        progress = False

        removable_packets = []

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

            # ---------------------------------
            # REMOVE RESOLVED
            # ---------------------------------

            if len(unknown) == 0:

                removable_packets.append(pkt)

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

                    print(
                        f"{source_name} "
                        f"Recovered Chunk "
                        f"{chunk_id}"
                    )

                    print(
                        f"Progress: "
                        f"{len(decoded_chunks)}/"
                        f"{TOTAL_CHUNKS}"
                    )

                    # ---------------------------------
                    # UPDATE PROGRESS TIMER
                    # ---------------------------------

                    last_progress_time = time.time()

                    # ---------------------------------
                    # CSV LOGGING
                    # ---------------------------------

                    with open(
                        CSV_FILE,
                        "a",
                        newline=""
                    ) as f:

                        writer = csv.writer(f)

                        writer.writerow([
                            chunk_id,
                            source_name,
                            len(decoded_chunks),
                            time.time()
                        ])

                    progress = True

        # -------------------------------------
        # REMOVE RESOLVED PACKETS
        # -------------------------------------

        for pkt in removable_packets:

            if pkt in received_packets:

                received_packets.remove(pkt)

# -------------------------------------------------
# RECEIVE LOOP
# -------------------------------------------------

while True:

    # -------------------------------------------------
    # FIND START MARKER
    # -------------------------------------------------

    first = ser.read(1)

    if first != b'\xAA':
        continue

    second = ser.read(1)

    if second != b'\x55':
        continue

    # -------------------------------------------------
    # READ LENGTH
    # -------------------------------------------------

    length_bytes = ser.read(2)

    if len(length_bytes) < 2:
        continue

    length = int.from_bytes(
        length_bytes,
        'big'
    )

    if length < 5 or length > 1024:
        continue

    # -------------------------------------------------
    # READ CRC
    # -------------------------------------------------

    crc_bytes = ser.read(4)

    if len(crc_bytes) < 4:
        continue

    received_crc = int.from_bytes(
        crc_bytes,
        'big'
    )

    # -------------------------------------------------
    # READ PAYLOAD
    # -------------------------------------------------

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

    # -------------------------------------------------
    # CRC CHECK
    # -------------------------------------------------

    calculated_crc = zlib.crc32(data)

    if calculated_crc != received_crc:

        print("CRC FAILED")

        continue

    # -------------------------------------------------
    # STALL DETECTION
    # -------------------------------------------------

    stall_mode = (
        time.time()
        - last_progress_time
    ) > 3

    if stall_mode:

        print(
            "\nSTALL MODE ACTIVATED"
        )

    # -------------------------------------------------
    # PACKET TYPE
    # -------------------------------------------------

    packet_type = data[0]

    # -------------------------------------------------
    # SOURCE PACKETS
    # -------------------------------------------------

    if packet_type == 0x01:

        # -----------------------------------------
        # SOURCE SUPPRESSION DURING STALL
        # -----------------------------------------

        if stall_mode:

            if random.random() < 0.7:
                continue

        actual_payload = data[1:]

        try:

            packet = Packet.from_bytes(
                actual_payload
            )

        except:

            continue

        received_packets.append(packet)

        run_decoder("SOURCE")

    # -------------------------------------------------
    # HELPER PACKETS
    # -------------------------------------------------

    elif packet_type == 0x02:

        # -----------------------------------------
        # HELPER SUPPRESSION DURING NORMAL MODE
        # -----------------------------------------

        if not stall_mode:

            if random.random() < 0.4:
                continue

        chunk_id = int.from_bytes(
            data[1:3],
            'big'
        )

        chunk_size = int.from_bytes(
            data[3:5],
            'big'
        )

        chunk_data = data[
            5:5 + chunk_size
        ]

        print(
            f"Received helper chunk "
            f"{chunk_id}"
        )

        if chunk_id in decoded_chunks:
            continue

        if chunk_id in helper_chunks_used:
            continue

        helper_chunks_used.add(
            chunk_id
        )

        # -------------------------------------------------
        # DIRECT HELPER INSERTION
        # -------------------------------------------------

        decoded_chunks[
            chunk_id
        ] = chunk_data

        chunk_path = os.path.join(
            OUTPUT_FOLDER,
            f"chunk_{chunk_id}.bin"
        )

        with open(
            chunk_path,
            "wb"
        ) as chunk_file:

            chunk_file.write(
                chunk_data
            )

        print(
            f"HELPER Directly "
            f"Recovered Chunk "
            f"{chunk_id}"
        )

        print(
            f"Progress: "
            f"{len(decoded_chunks)}/"
            f"{TOTAL_CHUNKS}"
        )

        # -------------------------------------------------
        # UPDATE PROGRESS TIMER
        # -------------------------------------------------

        last_progress_time = time.time()

        # -------------------------------------------------
        # CSV LOGGING
        # -------------------------------------------------

        with open(
            CSV_FILE,
            "a",
            newline=""
        ) as f:

            writer = csv.writer(f)

            writer.writerow([
                chunk_id,
                "HELPER_DIRECT",
                len(decoded_chunks),
                time.time()
            ])

        # -------------------------------------------------
        # RE-RUN PEELING
        # -------------------------------------------------

        run_decoder("HELPER")

    # -------------------------------------------------
    # COMPLETION CHECK
    # -------------------------------------------------

    if len(decoded_chunks) >= TOTAL_CHUNKS:

        end_time = time.time()

        total_time = (
            end_time - start_time
        )

        print(
            "\nAll Chunks Recovered"
        )

        print(
            f"\nTotal Time: "
            f"{total_time:.2f} seconds"
        )

        print(
            f"\nTotal Time: "
            f"{total_time/60:.2f} minutes"
        )

        print(
            "Sending COMPLETE signal"
        )

        for _ in range(5):

            ser.write(b'COMPLETE')

            ser.flush()

            time.sleep(0.3)

        print(
            "Reception Complete"
        )

        break
