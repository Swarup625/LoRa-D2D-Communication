import serial

ser = serial.Serial(
    '/dev/ttyAMA0',
    9600,
    timeout=1
)

print("Waiting for UART messages...\n")

while True:

    data = ser.readline()

    if data:

        print(
            "Received:",
            data.decode().strip()
        )