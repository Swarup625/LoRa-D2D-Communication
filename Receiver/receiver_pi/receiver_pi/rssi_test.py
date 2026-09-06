from lora_e220 import LoRaE220

import time

# -----------------------------------
# MODULE SETUP
# -----------------------------------

lora = LoRaE220(
    device='/dev/ttyAMA0',
    baudrate=9600
)

print("\nReading RSSI...\n")

while True:

    try:

        # -----------------------------------
        # RECEIVE PACKET
        # -----------------------------------

        message = lora.receiveMessage()

        if message is not None:

            print(
                f"Message: "
                f"{message.message}"
            )

            print(
                f"RSSI: "
                f"{message.rssi}"
            )

            print(
                "----------------"
            )

    except Exception as e:

        print(e)

    time.sleep(0.2)