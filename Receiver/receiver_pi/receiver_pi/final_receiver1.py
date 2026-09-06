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

# -------------------------------------------------
# TIMER
# -------------------------------------------------

start_time = time.time()

phase_start = time.time()

print(
    "\nFinal Receiver Running...\n"
)

# -------------------------------------------------
# PEELING DECODER
# -------------------------------------------------

def run_decoder():

    global received_packets
    global decoded_chunks

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
                        f"Recovered Chunk "
                        f"{chunk_id}"
                    )

                    print(
                        f"Progress: "
                        f"{len(decoded_chunks)}/"
                        f"{TOTAL_CHUNKS}"
                    )

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

    if length < 5 or length > 1024:
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
    # READ PAYLOAD
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

        print("CRC FAILED")

        continue

    # -----------------------------------------
    # PHASE SCHEDULING
    # -----------------------------------------

    elapsed = time.time() - phase_start

    if elapsed % 7 < 6:

        current_phase = "SOURCE"

    else:

        current_phase = "HELPER"

    # -----------------------------------------
    # PACKET TYPE
    # -----------------------------------------

    packet_type = data[0]

    # -----------------------------------------
    # SOURCE PHASE
    # -----------------------------------------

    if packet_type == 0x01:

        if current_phase != "SOURCE":
            continue

        print("FROM SOURCE")

        actual_payload = data[1:]

        try:

            packet = Packet.from_bytes(
                actual_payload
            )

        except:

            continue

        received_packets.append(packet)

        run_decoder()

    # -----------------------------------------
    # HELPER PHASE
    # -----------------------------------------

    elif packet_type == 0x02:

        if current_phase != "HELPER":
            continue

        print("FROM HELPER")

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

        if chunk_id not in decoded_chunks:

            decoded_chunks[
                chunk_id
            ] = chunk_data

            print(
                f"Helper Provided "
                f"Chunk {chunk_id}"
            )

            print(
                f"Progress: "
                f"{len(decoded_chunks)}/"
                f"{TOTAL_CHUNKS}"
            )

            run_decoder()

    # -----------------------------------------
    # COMPLETION CHECK
    # -----------------------------------------

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

        time.sleep(1)

        for _ in range(5):

            ser.write(b'COMPLETE')

            ser.flush()

            time.sleep(0.3)

        print(
            "Reception Complete"
        )

        break
