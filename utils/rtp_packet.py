"""
RTP Packet format is defined as: (per RFC 3550, section 5.1)
	
	   0                   1                   2                   3
	   0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
	  +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
	  |V=2|P|X|  CC   |M|     PT      |       sequence number         |
	  +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
	  |                           timestamp                           |
	  +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
	  |           synchronization source (SSRC) identifier            |
	  +=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+
	  |            contributing source (CSRC) identifiers             |
	  |                             ....                              |
	  +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

	  Optional extension header - if X flag == true: (as per RFC 3550, section 5.3.1)
	
	   0                   1                   2                   3
	   0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
	  +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
	  |      defined by profile       |           length              |
	  +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
	  |                        header extension                       |
	  |                             ....                              |
	
	NB: Maximum possible size of the full header is
	  = 4 + 4 (timestamp) + 4(ssrc) + 15 * 4(csrc) + 4(estension top) + 0xFFFF(extension)
	  = 12 + 60 + 4 + 0xFFFF
	  = 76 + 0xFFFF
	  = 65611 (0x1004B) bytes
"""
class InvalidPacketException(Exception):
    pass

class RTPPacket:
    # default header info
    HEADER_SIZE = 12   # bytes
    VERSION = 0b10     # 2 bits -> current version 2
    PADDING = 0b0      # 1 bit
    EXTENSION = 0b0    # 1 bit
    CC = 0x0           # 4 bits
    MARKER = 0b0       # 1 bit
    SSRC = 0x00000000  # 32 bits

    class TYPE:
        MJPEG = 26

    def __init__(
            self,
            payload_type: int = None,
            sequence_number: int = None,
            timestamp: int = None,
            payload: bytes = None
        ):

        self.payload = payload
        self.payload_type = payload_type
        self.sequence_number = sequence_number
        self.timestamp = timestamp


        header = [None] * self.HEADER_SIZE
        header[0]  = (self.VERSION << 6) | (self.PADDING << 5) | (self.EXTENSION << 4) | self.CC
        header[1]  = (self.MARKER << 7) | self.payload_type
        header[2]  = self.sequence_number >> 8
        header[3]  = self.sequence_number & 0xFF
        header[4]  = (self.timestamp >> 24) & 0xFF
        header[5]  = (self.timestamp >> 16) & 0xFF
        header[6]  = (self.timestamp >>  8) & 0xFF
        header[7]  = (self.timestamp >>  0) & 0xFF
        header[8]  = (self.SSRC >> 24) & 0xFF
        header[9]  = (self.SSRC >> 16) & 0xFF
        header[10] = (self.SSRC >>  8) & 0xFF
        header[11] = (self.SSRC >>  0) & 0xFF


        self.header = bytes(header)


    @classmethod
    def from_packet(cls, packet: bytes):
        if len(packet) < cls.HEADER_SIZE:
            raise InvalidPacketException(f"[Invalid packet]: {repr(packet)}")

        header = packet[:cls.HEADER_SIZE]
        payload = packet[cls.HEADER_SIZE:]

        payload_type = header[1] & 0x7F
        
        sequence_number = header[2] << 8 | header[3]
        
        timestamp = header[4] << 24 | header[5] << 16 | header[6] << 8 | header[7] << 0


        return cls(
            payload_type,
            sequence_number,
            timestamp,
            payload
        )

    def get_packet(self) -> bytes:
        return bytes((*self.header, *self.payload))
    
    def print_header(self):
        # print header without SSRC
        for i, by in enumerate(self.header[:8]):
            s = ' '.join(f"{by:08b}")
            # break line after the third and seventh bytes
            print(s, end=' ' if i not in (3, 7) else '\n')

    

