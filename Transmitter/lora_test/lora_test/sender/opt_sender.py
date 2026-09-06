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
# AUTOMATIC PARAMETERS
# -------------------------------------------------

MAX_PACKETS = TOTAL_CHUNKS * 7

feedback_start = int(
    3 * TOTAL_CHUNKS
)

feedback_interval = 10

print(
    f"MAX_PACKETS: {MAX_PACKETS}"
)

print(
    f"Feedback starts after: "
    f"{feedback_start} packets"
)

print(
    f"Feedback interval: "
    f"{feedback_interval}"
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

print("\nStarting Wireless Transmission...\n")

# -------------------------------------------------
# MAIN LOOP
# -------------------------------------------------

while packet_id < MAX_PACKETS:

    # -----------------------------------------
    # FEEDBACK WINDOW
    # -----------------------------------------

    if (
        packet_id > feedback_start
        and packet_id % feedback_interval == 0
    ):

        print(
            "\nListening for feedback..."
        )

        # RX stability pause
        time.sleep(0.5)

        incoming = b''

        start_time = time.time()

        # -----------------------------------------
        # RECEIVE WINDOW
        # -----------------------------------------

        while time.time() - start_time < 1:

            if ser.in_waiting:

                incoming += ser.read(
                    ser.in_waiting
                )

            time.sleep(0.05)

        # -----------------------------------------
        # COMPLETE SIGNAL
        # -----------------------------------------

        if incoming.find(b'COMPLETE') != -1:

            print(
                "\nReceiver completed recovery"
            )

            print(
                "Stopping transmission"
            )

            break

        # -----------------------------------------
        # TARGETED RECOVERY
        # -----------------------------------------

        if b'MISSING:' in incoming:

            try:

                msg = incoming.decode()

                missing_part = msg.split(
                    "MISSING:"
                )[1]

                missing_ids = list(
                    map(
                        int,
                        missing_part.split(",")
                    )
                )

                print(
                    "\nTARGETED MODE"
                )

                print(
                    "Missing Chunks:",
                    missing_ids
                )

                # -----------------------------------------
                # SEND ONLY MISSING CHUNKS
                # -----------------------------------------

                for chunk_id in missing_ids:

                    for repeat in range(1):

                        payload_data = chunks[
                            chunk_id
                        ]

                        packet = Packet(
                            packet_id=packet_id,
                            indices=[chunk_id],
                            payload=payload_data
                        )

                        payload_bytes = (
                            packet.to_bytes()
                        )

                        crc = zlib.crc32(
                            payload_bytes
                        )

                        # -----------------------------------------
                        # SEND FRAME
                        # -----------------------------------------

                        ser.write(
                            b'\xAA\x55'
                        )

                        ser.write(
                            len(
                                payload_bytes
                            ).to_bytes(
                                2,
                                'big'
                            )
                        )

                        ser.write(
                            crc.to_bytes(
                                4,
                                'big'
                            )
                        )

                        ser.write(
                            payload_bytes
                        )

                        packet_id += 1

                        time.sleep(0.5)

                # -----------------------------------------
                # WAIT FOR COMPLETE
                # -----------------------------------------

                print(
                    "\nWaiting for COMPLETE..."
                )

                time.sleep(2)

            except Exception as e:

                print(
                    "Targeted Recovery Error:",
                    e
                )

    # -----------------------------------------
    # ADAPTIVE DEGREE DISTRIBUTION
    # -----------------------------------------

    r = random.random()

    # Early Stage
    if packet_id < feedback_start:

        if r < 0.40:
            degree = 1

        elif r < 0.85:
            degree = 2

        else:
            degree = 3

    # Late Stage
    else:

        if r < 0.80:
            degree = 1

        else:
            degree = 2

    # -----------------------------------------
    # RANDOM CHUNK SELECTION
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
        indices=list(selected_indices),
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
        len(payload).to_bytes(
            2,
            'big'
        )
    )

    ser.write(
        crc.to_bytes(
            4,
            'big'
        )
    )

    ser.write(payload)

    if packet_id % 25 == 0:

        print(
            f"Sent Packet {packet_id}"
        )

    packet_id += 1

    # -----------------------------------------
    # TX DELAY
    # -----------------------------------------

    time.sleep(0.7)

print("\nTransmission Complete")
