import spidev
import time

spi = spidev.SpiDev()
spi.open(0, 0)              # Target /dev/spidev0.0
spi.max_speed_hz = 1000000  # Set to a safe 1MHz for Pi 5

# Send dummy test array to read version register from Semtech chip
# (Usually register 0x42 for SX1276)
try:
    while True:
        response = spi.xfer2([0x42, 0x00])
        print(f"Response from Dragino LoRa: {response}")
        time.sleep(1)
except KeyboardInterrupt:
    spi.close()