import os
import serial
import zlib
import time
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
    timeout=1
)

# -------------------------------------------------
# OUTPUT
# -------------------------------------------------

OUTPUT_FOLDER = "./recovered_chunks"

os.makedirs(
    OUTPUT_FOLDER,
    exist_ok=True
)

os.makedirs(
    "./logs",
    exist_ok=True
)

# -------------------------------------------------
# CSV
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
            "helper_id",
            "progress",
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

# -------------------------------------------------
# TIMER
# -------------------------------------------------

start_time = time.time()

print(
    "\nReceiver Running...\n"
)
def run_decoder():

    global received_packets

    progress = True

    while progress:

        progress = False

        removable = []

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

            if len(unknown) == 0:

                removable.append(
                    pkt
                )

                continue

            if len(unknown) == 1:

                chunk_id = unknown[0]

                if chunk_id not in decoded_chunks:

                    recovered = bytes(
                        payload
                    )

                    decoded_chunks[
                        chunk_id
                    ] = recovered

                    chunk_path = os.path.join(
                        OUTPUT_FOLDER,
                        f"chunk_{chunk_id}.bin"
                    )

                    with open(
                        chunk_path,
                        "wb"
                    ) as f:

                        f.write(
                            recovered
                        )

                    print(
                        f"SOURCE "
                        f"Recovered "
                        f"{chunk_id}"
                    )

                    print(
                        f"Progress "
                        f"{len(decoded_chunks)}"
                        f"/"
                        f"{TOTAL_CHUNKS}"
                    )

                    with open(
                        CSV_FILE,
                        "a",
                        newline=""
                    ) as f:

                        writer = csv.writer(f)

                        writer.writerow([
                            chunk_id,
                            "SOURCE",
                            0,
                            len(decoded_chunks),
                            time.time()
                        ])

                    progress = True

        for pkt in removable:

            if pkt in received_packets:

                received_packets.remove(
                    pkt
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
    # FIND START MARKER
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

    calculated_crc = zlib.crc32(
        data
    )

    if calculated_crc != received_crc:

        print(
            "CRC FAILED"
        )

        continue

    packet_type = data[0]

    # =================================================
    # SOURCE WINDOW
    # =================================================

    if cycle_position < SOURCE_WINDOW:

        if packet_type != 0x01:
            continue

        try:

            packet = Packet.from_bytes(
                data[1:]
            )

        except:

            continue

        received_packets.append(
            packet
        )

        run_decoder()

    # =================================================
    # D2D WINDOW
    # =================================================

    else:

        if packet_type != 0x02:
            continue

        try:

            helper_id = data[1]

            chunk_id = int.from_bytes(
                data[2:4],
                'big'
            )

            chunk_size = int.from_bytes(
                data[4:6],
                'big'
            )

            chunk_data = data[
                6:6+chunk_size
            ]

        except:

            continue

        if chunk_id in decoded_chunks:
            continue

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
        ) as f:

            f.write(
                chunk_data
            )

        print(
            f"HELPER "
            f"{helper_id} "
            f"Recovered "
            f"{chunk_id}"
        )

        print(
            f"Progress "
            f"{len(decoded_chunks)}"
            f"/"
            f"{TOTAL_CHUNKS}"
        )

        with open(
            CSV_FILE,
            "a",
            newline=""
        ) as f:

            writer = csv.writer(f)

            writer.writerow([
                chunk_id,
                "HELPER",
                helper_id,
                len(decoded_chunks),
                time.time()
            ])

        run_decoder()

    # =================================================
    # COMPLETE
    # =================================================

    if (
        len(decoded_chunks)
        >= TOTAL_CHUNKS
    ):

        total_time = (
            time.time()
            -
            start_time
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
            "\nSending COMPLETE"
        )

        for _ in range(10):

            ser.write(
                b'COMPLETE'
            )

            ser.flush()

            time.sleep(0.2)

        break
