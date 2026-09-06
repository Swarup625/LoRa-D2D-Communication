import serial

ser = serial.Serial(
    '/dev/ttyAMA0',
    9600,
    timeout=1
)

print("Waiting for packets...\n")

while True:

    data = ser.read(64)

    if len(data) > 0:

        print(data)

        print(
            "Length:",
            len(data)
        )

        print("----------------")