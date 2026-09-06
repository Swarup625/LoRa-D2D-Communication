import spidev
import time
import gpiod

print("\n========== LoRa Diagnostic Test ==========\n")

# -------------------------------------------------
# SPI DEVICE CHECK
# -------------------------------------------------

print("Checking SPI Devices...\n")

for dev in [0, 1]:

    try:
        spi = spidev.SpiDev()
        spi.open(0, dev)
        spi.close()

        print(f"CE{dev} Available")

    except Exception as e:
        print(f"CE{dev} Error:", e)

print("\n------------------------------------------\n")

# -------------------------------------------------
# RESET TEST USING GPIO17 (PHYSICAL PIN 11)
# -------------------------------------------------

print("Testing RESET Pin...\n")

try:

    chip = gpiod.Chip('gpiochip4')

    RESET_PIN = 17

    line = chip.get_line(RESET_PIN)

    line.request(
        consumer="reset",
        type=gpiod.LINE_REQ_DIR_OUT
    )

    print("RESET LOW")
    line.set_value(0)
    time.sleep(1)

    print("RESET HIGH")
    line.set_value(1)
    time.sleep(1)

    print("RESET Sequence Completed")

    line.release()

except Exception as e:
    print("RESET Error:", e)

print("\n------------------------------------------\n")

# -------------------------------------------------
# SX1276 VERSION REGISTER TEST
# -------------------------------------------------

print("Reading SX1276 Version Register...\n")

REG_VERSION = 0x42

try:

    spi = spidev.SpiDev()

    spi.open(0, 0)

    spi.max_speed_hz = 500000

    for i in range(10):

        response = spi.xfer2([REG_VERSION & 0x7F, 0x00])

        print(f"Attempt {i+1}: {response}")

        time.sleep(1)

    spi.close()

except Exception as e:
    print("SPI Error:", e)

print("\n------------------------------------------\n")

# -------------------------------------------------
# FINAL INTERPRETATION
# -------------------------------------------------

print("Diagnostic Interpretation:\n")

print("Expected Working Response:")
print("[66, 18]")
print("or")
print("[66, 0x12]\n")

print("If repeated [0, 0] occurs:")
print("- SPI bus exists")
print("- Chip select exists")
print("- RESET line toggles")
print("- BUT SX1276 never responds")

print("\nThis strongly suggests:")
print("1. Dragino LoRa/GPS HAT v1.4 incompatibility with Raspberry Pi 5")
print("2. Hardware routing/timing incompatibility")
print("3. Legacy SPI interface issue")
print("4. Internal HAT-level communication failure")

print("\n========== End of Diagnostic ==========\n")