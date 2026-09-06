import serial
import time

ser = serial.Serial(
    '/dev/ttyAMA0',
    9600
)

while True:

    ser.write(b'HELLO\n')

    print("Sent")

    time.sleep(1)
