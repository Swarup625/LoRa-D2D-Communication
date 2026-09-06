import pickle


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

        data = {
            "packet_id": self.packet_id,
            "indices": self.indices,
            "payload": self.payload
        }

        return pickle.dumps(data)

    # -------------------------------------------------
    # DESERIALIZE
    # -------------------------------------------------

    @staticmethod
    def from_bytes(data):

        obj = pickle.loads(data)

        return Packet(
            packet_id=obj["packet_id"],
            indices=obj["indices"],
            payload=obj["payload"]
        )
