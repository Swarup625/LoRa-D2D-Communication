import serial
import time

ser = serial.Serial(
    '/dev/ttyAMA0',
    9600,
    timeout=1
)

print("Starting UART Sender...\n")

counter = 0

while True:

    message = f"HELLO {counter}\n"

    ser.write(message.encode())

    print(
        f"Sent: {message.strip()}"
    )

    counter += 1

    time.sleep(1)