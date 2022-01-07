"""
RR: Receiver Report RTCP Packet

        0              |    1          |        2      |            3
        0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
       +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
header |V=2|P|    RC   |   PT=RR=201   |             length            |
       +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
       |                     SSRC of packet sender                     |
       +=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+
report |                           fraction lost                       |
block  +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
  1    |              cumulative number of packets lost                |
       +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
       |           extended highest sequence number received           |
       +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
       |                      interarrival jitter                      |
       +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
       |                         last SR (LSR)                         |
       +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
       |                   delay since last SR (DLSR)                  |
       +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
"""


class InvalidRequest(Exception):
    pass


class RTCPPacket:
    # packet size info
    HEADER_SIZE = 8  # bytes
    BODY_SIZE = 24  # bytes

    # default header info
    VERSION = 0b10  # 2 bits -> Current version = 2
    PADDING = 0b0  # 1 bit -> Padding of packet = 0
    RC = 0b00001  # 5 bits -> Reception report count = 1 for one receiver
    PT = 0b11001001  # 8 bits -> Payload type = 201 for Receiver Report
    LENGTH = 0x0020  # 16 bits -> 1 source is always 32 bytes: 8 header + 24 body
    SSRC = 0x00000000  # 32 bits -> Synchronization source identifier

    def __init__(
        self, fraction_lost: float = None, cum_lost: int = None, highest_rcv: int = None
    ):
        self.fraction_lost = fraction_lost  # The fraction of RTP data pkt from sender lost since the previous RR packet was sent
        self.cum_lost = cum_lost  # The total number of RTP data packets from sender that have been lost since the beginning of reception
        self.highest_rcv = highest_rcv  # Highest sequence number received

        header = [None] * self.HEADER_SIZE
        header[0] = self.VERSION << 6 | self.PADDING << 5 | self.RC
        header[1] = self.PT & 0xFF
        header[2] = self.LENGTH >> 8
        header[3] = self.LENGTH & 0xFF
        header[4] = self.SSRC >> 24
        header[5] = self.SSRC >> 16
        header[6] = self.SSRC >> 8
        header[7] = self.SSRC & 0xFF

        self.header = bytes(header)
        self.body = bytes([0] * self.BODY_SIZE)

    def __len__(self):
        return self.BODY_SIZE + self.HEADER_SIZE

    def get_packet(self) -> bytes:
        return bytes((*self.header, *self.body))
