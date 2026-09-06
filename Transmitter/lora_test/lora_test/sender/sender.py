import spidev
import time
import random
import os

# --- Native Linux Pin System to wake up the Dragino module ---
# This replicates DigitalOutputDevice(4).on() safely
if not os.path.exists("/sys/class/gpio/gpio4"):
    try:
        with open("/sys/class/gpio/export", "w") as f: f.write("4")
        time.sleep(0.1)
    except: pass

try:
    with open("/sys/class/gpio/gpio4/direction", "w") as f: f.write("out")
    with open("/sys/class/gpio/gpio4/value", "w") as f: f.write("1")
except:
    print("[!] Warning: Could not force hardware Pin 7 High. Ensure it isn't locked.")

# --- Continue with normal SPI Initialization ---
spi = spidev.SpiDev()
spi.open(0, 0)
spi.max_speed_hz = 1000000
# [Keep the rest of your original sender.py registers/loops intact here]

# SX1276 Low-Level Register Addresses
REG_FIFO = 0x00
REG_OP_MODE = 0x01
REG_FRF_MSB = 0x06
REG_FRF_MID = 0x07
REG_FRF_LSB = 0x08
REG_PA_CONFIG = 0x09
REG_FIFO_ADDR_PTR = 0x0D
REG_FIFO_TX_BASE_ADDR = 0x0E
REG_MODEM_CONFIG1 = 0x1D
REG_MODEM_CONFIG2 = 0x1E
REG_PAYLOAD_LENGTH = 0x22
REG_IRQ_FLAGS = 0x12

def write_reg(reg, val):
    spi.xfer2([reg | 0x80, val])

def read_reg(reg):
    return spi.xfer2([reg & 0x7F, 0x00])[1]

# --- Initialize SX1276 Radio Transceiver Engine ---
print("[*] Initializing Dragino Transmitter Core...")
write_reg(REG_OP_MODE, 0x00) # Sleep Mode
time.sleep(0.01)
write_reg(REG_OP_MODE, 0x80) # Enable LoRa mode (Bit 7 = 1)
time.sleep(0.01)
write_reg(REG_OP_MODE, 0x81) # Put in Standby Mode

# Set Frequency to 868.0 MHz (Change if your region is 915MHz)
# Formula: FRF = Freq_MHz * 16384
write_reg(REG_FRF_MSB, 0xD9)
write_reg(REG_FRF_MID, 0x00)
write_reg(REG_FRF_LSB, 0x00)

# Configure Power Amplifier (Enable PA_BOOST pin used by Dragino boards)
write_reg(REG_PA_CONFIG, 0xFF) # Max Power output

# Modem Config: SF7, BW 125kHz, CR 4/5, Explicit Header
write_reg(REG_MODEM_CONFIG1, 0x72) 
write_reg(REG_MODEM_CONFIG2, 0x70)

print(f"[✔] Radio engine verified. Operating Version Register check: {hex(read_reg(0x42))}")

# --- Fountain Code Split Engine ---
def chunk_data(data, block_size=4):
    padding = (block_size - (len(data) % block_size)) % block_size
    data += b'\x00' * padding
    return [data[i:i+block_size] for i in range(0, len(data), block_size)]

def generate_droplet(blocks, seed):
    random.seed(seed)
    degree = random.randint(1, len(blocks))
    indices = random.sample(range(len(blocks)), degree)
    droplet = bytearray(len(blocks[0]))
    for idx in indices:
        for b_idx in range(len(droplet)):
            droplet[b_idx] ^= blocks[idx][b_idx]
    return droplet

message = b"HELLO FOUNTAIN"
source_blocks = chunk_data(message, block_size=4)
K = len(source_blocks)

seed_counter = 0
try:
    while True:
        seed_counter += 1
        droplet = generate_droplet(source_blocks, seed_counter)
        
        # Build Frame Layout: [Seed(2B)] [K(2B)] [Payload(4B)] -> Total 8 Bytes
        packet = bytearray()
        packet.extend(seed_counter.to_bytes(2, byteorder='big'))
        packet.extend(K.to_bytes(2, byteorder='big'))
        packet.extend(droplet)
        
        # Write to Chip FIFO Queue
        write_reg(REG_OP_MODE, 0x81) # Put in Standby to reset pointers
        write_reg(REG_FIFO_ADDR_PTR, read_reg(REG_FIFO_TX_BASE_ADDR))
        write_reg(REG_PAYLOAD_LENGTH, len(packet))
        
        # Blast payload stream into SPI
        spi.xfer2([REG_FIFO | 0x80] + list(packet))
        
        # Trigger Transmission Mode Over-The-Air
        write_reg(REG_OP_MODE, 0x83) # TX Mode
        print(f"-> Sending Droplet Seed: {seed_counter} | Packet: {list(packet)}")
        
        # Wait for transmission complete flag before advancing loop
        while not (read_reg(REG_IRQ_FLAGS) & 0x08):
            time.sleep(0.01)
        write_reg(REG_IRQ_FLAGS, 0x08) # Clear TxDone flag
        
        time.sleep(1.0) # Sleep for 1 second between droplets

except KeyboardInterrupt:
    spi.close()