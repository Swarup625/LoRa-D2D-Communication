import zlib

START_MARKER = b'\xAA\x55'

TYPE_ENCODED = 0x01
TYPE_DECODED = 0x02
TYPE_COMPLETE = 0x03

BROADCAST_ID = 255

MAX_PAYLOAD_SIZE = 512


# -------------------------------------------------
# CREATE FRAME
# -------------------------------------------------

def create_frame(
    packet_type,
    source_id,
    dest_id,
    payload
):

    length = len(payload)

    header = (
        bytes([packet_type]) +
        bytes([source_id]) +
        bytes([dest_id]) +
        length.to_bytes(2, 'big')
    )

    crc = zlib.crc32(
        header + payload
    )

    frame = (
        START_MARKER +
        header +
        crc.to_bytes(4, 'big') +
        payload
    )

    return frame


# -------------------------------------------------
# READ FRAME
# -------------------------------------------------

def read_frame(ser):

    first = ser.read(1)

    if first != b'\xAA':
        return None

    second = ser.read(1)

    if second != b'\x55':
        return None

    header = ser.read(5)

    if len(header) < 5:
        return None

    packet_type = header[0]
    source_id = header[1]
    dest_id = header[2]

    length = int.from_bytes(
        header[3:5],
        'big'
    )

    if length > MAX_PAYLOAD_SIZE:
        return None

    crc_bytes = ser.read(4)

    if len(crc_bytes) < 4:
        return None

    received_crc = int.from_bytes(
        crc_bytes,
        'big'
    )

    payload = b''

    while len(payload) < length:

        chunk = ser.read(
            length - len(payload)
        )

        if not chunk:
            break

        payload += chunk

    if len(payload) < length:
        return None

    calculated_crc = zlib.crc32(
        header + payload
    )

    if calculated_crc != received_crc:

        print("CRC FAILED")

        return None

    return {
        "type": packet_type,
        "source": source_id,
        "dest": dest_id,
        "payload": payload
    }
