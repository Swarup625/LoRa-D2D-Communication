import spidev
import time
import random
import os

# --- Native Linux Pin System to wake up the Dragino module ---
if not os.path.exists("/sys/class/gpio/gpio4"):
    try:
        with open("/sys/class/gpio/export", "w") as f: f.write("4")
        time.sleep(0.1)
    except: pass

try:
    with open("/sys/class/gpio/gpio4/direction", "w") as f: f.write("out")
    with open("/sys/class/gpio/gpio4/value", "w") as f: f.write("1")
except: pass

# --- Continue with normal SPI Initialization ---
spi = spidev.SpiDev()
spi.open(0, 0)
spi.max_speed_hz = 1000000
# [Keep the rest of your original receiver.py decoder classes/loops intact here]

# SX1276 Low-Level Register Addresses
REG_FIFO = 0x00
REG_OP_MODE = 0x01
REG_FRF_MSB = 0x06
REG_FRF_MID = 0x07
REG_FRF_LSB = 0x08
REG_FIFO_ADDR_PTR = 0x0D
REG_FIFO_RX_BASE_ADDR = 0x0F
REG_FIFO_RX_CURRENT_ADDR = 0x10
REG_IRQ_FLAGS = 0x12
REG_MODEM_CONFIG1 = 0x1D
REG_MODEM_CONFIG2 = 0x1E

def write_reg(reg, val):
    spi.xfer2([reg | 0x80, val])

def read_reg(reg):
    return spi.xfer2([reg & 0x7F, 0x00])[1]

# --- Initialize SX1276 Radio Transceiver Engine ---
print("[*] Initializing Dragino Receiver Core...")
write_reg(REG_OP_MODE, 0x00) # Sleep Mode
time.sleep(0.01)
write_reg(REG_OP_MODE, 0x80) # Enable LoRa mode
time.sleep(0.01)
write_reg(REG_OP_MODE, 0x81) # Standby

# Set Frequency to 868.0 MHz (Must match transmitter exactly)
write_reg(REG_FRF_MSB, 0xD9)
write_reg(REG_FRF_MID, 0x00)
write_reg(REG_FRF_LSB, 0x00)

# Modem Config: SF7, BW 125kHz, CR 4/5, Explicit Header
write_reg(REG_MODEM_CONFIG1, 0x72)
write_reg(REG_MODEM_CONFIG2, 0x70)

# Set base pointer address to the beginning of RX FIFO section
write_reg(REG_FIFO_ADDR_PTR, read_reg(REG_FIFO_RX_BASE_ADDR))

# Put chip into Continuous RX Listening Mode
write_reg(REG_OP_MODE, 0x85)

print(f"[✔] Radio system listening on 868MHz. Chip validation ID: {hex(read_reg(0x42))}")

# --- Fountain Decoder Architecture ---
class FountainDecoder:
    def __init__(self, K, block_size):
        self.K = K
        self.block_size = block_size
        self.resolved_blocks = [None] * K
        self.received_droplets = []

    def recover_indices(self, seed):
        random.seed(seed)
        degree = random.randint(1, self.K)
        return set(random.sample(range(self.K), degree))

    def process_packet(self, seed, droplet_data):
        indices = self.recover_indices(seed)
        for idx in list(indices):
            if self.resolved_blocks[idx] is not None:
                droplet_data = bytes(a ^ b for a, b in zip(droplet_data, self.resolved_blocks[idx]))
                indices.remove(idx)
                
        if len(indices) == 1:
            target_idx = list(indices)[0]
            if self.resolved_blocks[target_idx] is None:
                self.resolved_blocks[target_idx] = droplet_data
                print(f"    [✔] Directly Decoded Block Index: {target_idx}")
                self.ripple_decode()
        elif len(indices) > 1:
            self.received_droplets.append((indices, droplet_data))

    def ripple_decode(self):
        progress = True
        while progress:
            progress = False
            for indices, data in list(self.received_droplets):
                for idx in list(indices):
                    if self.resolved_blocks[idx] is not None:
                        data = bytes(a ^ b for a, b in zip(data, self.resolved_blocks[idx]))
                        indices.remove(idx)
                        progress = True
                        
                if len(indices) == 1:
                    target_idx = list(indices)[0]
                    if self.resolved_blocks[target_idx] is None:
                        self.resolved_blocks[target_idx] = data
                        print(f"    [✦] Cascade Ripple Decoded Index: {target_idx}")
                    if (indices, data) in self.received_droplets:
                        self.received_droplets.remove((indices, data))
                        
    def is_complete(self):
        return all(b is not None for b in self.resolved_blocks)

    def get_result(self):
        return b"".join(self.resolved_blocks)

decoder = FountainDecoder(K=4, block_size=4) # Initializing for small message

# --- RX Processing Loop ---
try:
    while not decoder.is_complete():
        irq_flags = read_reg(REG_IRQ_FLAGS)
        
        # Look for Bit 6: RxDone
        if irq_flags & 0x40:
            print("\n[!] Radio packet detected on the antenna!")
            
            # Clear IRQ flags register
            write_reg(REG_IRQ_FLAGS, 0xFF)
            
            # Point physical buffer pointer to start address of current package
            current_packet_addr = read_reg(REG_FIFO_RX_CURRENT_ADDR)
            write_reg(REG_FIFO_ADDR_PTR, current_packet_addr)
            
            # Extract 8-byte frame: [Seed (2B)] [K (2B)] [Payload (4B)]
            raw_payload = spi.xfer2([REG_FIFO & 0x7F] + [0x00] * 8)[1:]
            
            # Deconstruct frame properties
            seed_rx = int.from_bytes(raw_payload[0:2], byteorder='big')
            k_rx = int.from_bytes(raw_payload[2:4], byteorder='big')
            droplet_payload = bytes(raw_payload[4:8])
            
            print(f"    Raw Frame Captured: {raw_payload}")
            print(f"    Parsed Extraction: Seed={seed_rx} | K={k_rx} | Data={list(droplet_payload)}")
            
            decoder.process_packet(seed=seed_rx, droplet_data=droplet_payload)
            
        time.sleep(0.01)

    print("\n===============================================")
    print("[🎉] SUCCESS: Fountain Reconstructed Entire Message!")
    print(f"Decoded Output string: {decoder.get_result().decode('utf-8', errors='ignore')}")
    print("===============================================")

except KeyboardInterrupt:
    print("\nStopped.")
finally:
    spi.close()