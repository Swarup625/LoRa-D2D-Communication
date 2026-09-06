import serial

from packet import Packet


ser = serial.Serial(
    '/dev/ttyAMA0',
    9600,
    timeout=1
)

print("Waiting for packets...\n")

while True:

    # Read packet length
    length_bytes = ser.read(2)

    if len(length_bytes) < 2:
        continue

    length = int.from_bytes(
        length_bytes,
        'big'
    )

    # Read packet data
    data = ser.read(length)

    if len(data) < length:
        continue

    # Deserialize
    packet = Packet.from_bytes(data)

    print("\nReceived Packet")

    print(
        f"Packet ID: {packet.packet_id}"
    )

    print(
        f"Indices: {packet.indices}"
    )

    print(
        f"Payload: {packet.payload}"
    )