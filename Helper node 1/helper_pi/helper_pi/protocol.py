import zlib


# -------------------------------------------------
# PACKET TYPES
# -------------------------------------------------

TYPE_ENCODED = 0x01
TYPE_HELPER = 0x02


# -------------------------------------------------
# START MARKER
# -------------------------------------------------

START_MARKER = b'\xAA\x55'


# -------------------------------------------------
# CREATE FRAME
# -------------------------------------------------

def create_frame(payload):

    crc = zlib.crc32(payload)

    frame = (
        START_MARKER +
        len(payload).to_bytes(
            2,
            'big'
        ) +
        crc.to_bytes(
            4,
            'big'
        ) +
        payload
    )

    return frame


# -------------------------------------------------
# READ FRAME
# -------------------------------------------------

def read_frame(ser):

    # ---------------------------------------------
    # FIND START MARKER
    # ---------------------------------------------

    first = ser.read(1)

    if first != b'\xAA':
        return None

    second = ser.read(1)

    if second != b'\x55':
        return None

    # ---------------------------------------------
    # READ LENGTH
    # ---------------------------------------------

    length_bytes = ser.read(2)

    if len(length_bytes) < 2:
        return None

    length = int.from_bytes(
        length_bytes,
        'big'
    )

    if length < 5 or length > 1024:
        return None

    # ---------------------------------------------
    # READ CRC
    # ---------------------------------------------

    crc_bytes = ser.read(4)

    if len(crc_bytes) < 4:
        return None

    received_crc = int.from_bytes(
        crc_bytes,
        'big'
    )

    # ---------------------------------------------
    # READ PAYLOAD
    # ---------------------------------------------

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

    # ---------------------------------------------
    # CRC VALIDATION
    # ---------------------------------------------

    calculated_crc = zlib.crc32(payload)

    if calculated_crc != received_crc:

        return None

    # ---------------------------------------------
    # RETURN PAYLOAD
    # ---------------------------------------------

    return payload
