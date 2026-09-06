import serial
import time

from packet import Packet


ser = serial.Serial(
    '/dev/ttyAMA0',
    9600,
    timeout=1
)

print("Starting Packet Sender...\n")

packet_id = 0

while True:

    packet = Packet(
        packet_id=packet_id,
        indices=[1, 3, 5],
        payload=b'HELLO_LORA'
    )

    packet_bytes = packet.to_bytes()

    # Send length first
    length = len(packet_bytes)

    ser.write(
        length.to_bytes(2, 'big')
    )

    # Send packet
    ser.write(packet_bytes)

    print(
        f"Sent Packet {packet_id}"
    )

    packet_id += 1

    time.sleep(1)