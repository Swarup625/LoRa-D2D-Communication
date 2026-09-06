import struct


class Packet:

    def __init__(
        self,
        packet_id,
        indices,
        payload
    ):

        self.packet_id = packet_id
        self.indices = indices
        self.payload = payload

    # -------------------------------------------------
    # SERIALIZE
    # -------------------------------------------------

    def to_bytes(self):

        header = struct.pack(
            "!IB",
            self.packet_id,
            len(self.indices)
        )

        indices_bytes = struct.pack(
            f"!{len(self.indices)}H",
            *self.indices
        )

        return (
            header
            + indices_bytes
            + self.payload
        )

    # -------------------------------------------------
    # DESERIALIZE
    # -------------------------------------------------

    @classmethod
    def from_bytes(cls, data):

        packet_id, num_indices = struct.unpack(
            "!IB",
            data[:5]
        )

        index_start = 5

        index_end = (
            index_start
            + num_indices * 2
        )

        indices = list(
            struct.unpack(
                f"!{num_indices}H",
                data[index_start:index_end]
            )
        )

        payload = data[index_end:]

        return cls(
            packet_id,
            indices,
            payload
        )