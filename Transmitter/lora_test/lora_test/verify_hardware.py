import gpiod
import time

# --- UNLOCKED ALTERNATIVE PINS MAP ---
CHIP_PATH = "/dev/gpiochip4"
PIN_RESET = 17 # Physical Pin 11
PIN_NSS = 6    # Physical Pin 31
PIN_SCK = 26   # Physical Pin 37
PIN_MOSI = 13  # Physical Pin 33
PIN_MISO = 19  # Physical Pin 35

print("[*] Accessing unallocated GPIO block...")
chip = gpiod.Chip(CHIP_PATH)

# Request all control lines manually
lines = chip.request_lines(consumer="lora-unlocked-bitbang", config={
    PIN_RESET: gpiod.LineSettings(direction=gpiod.line.Direction.OUTPUT, output_value=gpiod.line.Value.ACTIVE),
    PIN_NSS: gpiod.LineSettings(direction=gpiod.line.Direction.OUTPUT, output_value=gpiod.line.Value.ACTIVE),
    PIN_SCK: gpiod.LineSettings(direction=gpiod.line.Direction.OUTPUT, output_value=gpiod.line.Value.INACTIVE),
    PIN_MOSI: gpiod.LineSettings(direction=gpiod.line.Direction.OUTPUT, output_value=gpiod.line.Value.INACTIVE),
    PIN_MISO: gpiod.LineSettings(direction=gpiod.line.Direction.INPUT)
})

def hardware_pulse_reset():
    print("[*] Pulsing Reset Line on Pin 11 to awaken transceiver chip...")
    # Drive Low to reset
    lines.set_value(PIN_RESET, gpiod.line.Value.INACTIVE)
    time.sleep(0.15)
    # Drive High to wake up
    lines.set_value(PIN_RESET, gpiod.line.Value.ACTIVE)
    time.sleep(0.15)

def bitbang_transfer(byte_to_send):
    read_byte = 0
    for i in range(8):
        bit_out = (byte_to_send >> (7 - i)) & 0x01
        lines.set_value(PIN_MOSI, gpiod.line.Value.ACTIVE if bit_out else gpiod.line.Value.INACTIVE)
        
        lines.set_value(PIN_SCK, gpiod.line.Value.ACTIVE)
        time.sleep(0.0001) 
        
        bit_in = 1 if lines.get_value(PIN_MISO) == gpiod.line.Value.ACTIVE else 0
        read_byte |= (bit_in << (7 - i))
        
        lines.set_value(PIN_SCK, gpiod.line.Value.INACTIVE)
        time.sleep(0.0001)
        
    return read_byte

try:
    # 1. Wake up the transceiver engine
    hardware_pulse_reset()
    
    print("[*] Directly pulsing SX1276 registers over software SPI...")
    
    # Pull NSS LOW to begin SPI frame
    lines.set_value(PIN_NSS, gpiod.line.Value.INACTIVE)
    time.sleep(0.01)
    
    # Send RegOpVersion address (0x42)
    bitbang_transfer(0x42)
    
    # Clock out the register value
    received_version = bitbang_transfer(0x00)
    
    # Pull NSS HIGH to end SPI frame
    lines.set_value(PIN_NSS, gpiod.line.Value.ACTIVE)
    
    print(f"--> Extracted Version Byte: {hex(received_version)} (Decimal: {received_version})")
    
    if received_version == 0x12:
        print("\n==================================================")
        print("[SUCCESS] SX1276 Compatibility Confirmed on Pi 5!")
        print("Hardware response matched target key 0x12!")
        print("==================================================")
    else:
        print("\n[!] Bitbang executed but returned incorrect data.")
        print("-> Make sure the Dragino's black jumper caps are on vertically!")

finally:
    lines.release()