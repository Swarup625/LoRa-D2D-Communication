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

sent_chunks = set()

helper_queue = []

# -------------------------------------------------
# HELPER LOOP
# -------------------------------------------------

print("\nHelper Node Running...\n")

packet_counter = 0

while True:

    # -----------------------------------------
    # COMPLETE SIGNAL
    # -----------------------------------------

    if ser.in_waiting:

        incoming = ser.read(
            ser.in_waiting
        )

        if b'COMPLETE' in incoming:

            print(
                "\nReceiver completed recovery"
            )

            break

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
        continue

    # -----------------------------------------
    # SOURCE PACKETS ONLY
    # -----------------------------------------

    packet_type = data[0]

    if packet_type != 0x01:
        continue

    actual_payload = data[1:]

    # -----------------------------------------
    # DESERIALIZE
    # -----------------------------------------

    try:

        packet = Packet.from_bytes(
            actual_payload
        )

    except:

        continue

    received_packets.append(packet)

    packet_counter += 1

    # -------------------------------------------------
    # PEELING DECODER
    # -------------------------------------------------

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

                    print(
                        f"Recovered Chunk "
                        f"{chunk_id}"
                    )

                    progress = True

                    # ---------------------------------
                    # SAVE CHUNK
                    # ---------------------------------

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

                    # ---------------------------------
                    # ACTIVATE AFTER 75%
                    # ---------------------------------

                    if len(decoded_chunks) < (
                        (TOTAL_CHUNKS * 3) // 4
                    ):
                        continue

                    # ---------------------------------
                    # SEND FEW CHUNKS
                    # ---------------------------------

                    if chunk_id % 15 != 0:
                        continue

                    if chunk_id in sent_chunks:
                        continue

                    helper_queue.append(
                        (
                            chunk_id,
                            recovered_data
                        )
                    )

                    sent_chunks.add(
                        chunk_id
                    )

        # -------------------------------------
        # REMOVE RESOLVED PACKETS
        # -------------------------------------

        for pkt in removable_packets:

            if pkt in received_packets:

                received_packets.remove(pkt)

    # -------------------------------------------------
    # HELPER PHASE TX
    # -------------------------------------------------

    elapsed = time.time() - start

    if (
        elapsed % 7 >= 6
        and len(helper_queue) > 0
    ):

        chunk_id, recovered_data = (
            helper_queue.pop(0)
        )

        helper_payload = (
            b'\x02' +
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
            f"Helper Sent Chunk "
            f"{chunk_id}"
        )

        time.sleep(0.3)
