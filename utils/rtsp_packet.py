from typing import Optional


def KMP_String(pattern, text):
    a = len(text)
    b = len(pattern)
    prefix_arr = get_prefix_arr(pattern, b)
  
    initial_point = []
    m = 0
    n = 0
  
    while m != a:
       
        if text[m] == pattern[n]:
            m += 1
            n += 1
      
        else:
            n = prefix_arr[n-1]
       
        if n == b:
            initial_point.append(m-n)
            n = prefix_arr[n-1]
        elif n == 0:
            m += 1
   
    return initial_point
def get_prefix_arr(pattern, b):
    prefix_arr = [0] * b
    n = 0
    m = 1
    while m != b:
        if pattern[m] == pattern[n]:
            n += 1
            prefix_arr[m] = n
            m += 1
        elif n != 0:
                n = prefix_arr[n-1]
        else:
            prefix_arr[m] = 0
            m += 1
    return prefix_arr





class InvalidRTSPRequest(Exception):
    pass


class RTSPPacket:
    RTSP_VERSION = 'RTSP/1.0'

    INVALID = -1
    SETUP = 'SETUP'
    PLAY = 'PLAY'
    PAUSE = 'PAUSE'
    TEARDOWN = 'TEARDOWN'
    RESPONSE = 'RESPONSE'

    def __init__(
            self,
            request_type,
            video_file_path: Optional[str] = None,
            sequence_number: Optional[int] = None,
            dst_port: Optional[int] = None,
            session_id: Optional[str] = None
        ):
        self.request_type = request_type
        self.video_file_path = video_file_path
        self.sequence_number = sequence_number
        self.session_id = session_id

        # if request_type SETUP
        self.rtp_dst_port = dst_port

    def __str__(self):
        return (f"RTSPPacket({self.request_type}, "
                f"{self.video_file_path}, "
                f"{self.sequence_number}, "
                f"{self.rtp_dst_port}, "
                f"{self.session_id})")

    @classmethod
    def from_response(cls, response: bytes):
        # only response format implemented, taken from server class:
        # """
        #   <RTSP_VERSION> 200 OK\r\n
        #   CSeq: <SEQUENCE_NUMBER>\r\n
        #   Session: <SESSION_ID>\r\n
        # """

        
        RTSP_index =  KMP_String(b"RTSP", response) 
        status_index =  KMP_String(b"200 OK\r\n", response)
        CSeq_index =  KMP_String(b"CSeq: ", response)
        CSeq_end_index = KMP_String(b"\r\nSession: ", response)

        Session_index =  KMP_String(b"Session: ", response) 
        Sessionend_index =  KMP_String(b"\r\n", response) 

        if (len(RTSP_index) * len(status_index) * len(CSeq_index) * len(Session_index) == 0 ):
            raise Exception(f"[RTSP response] parsing fail: {response}")

    
        sequence_number = response[CSeq_index[0]+6 : CSeq_end_index[0]].decode()
        session_id = response[Session_index[0]+9 : Sessionend_index[len(Sessionend_index)-1]].decode()





        try:
            sequence_number = int(sequence_number)
        except (ValueError, TypeError):
            raise Exception(f"[sequence number] parsing fail: {response}")

        if session_id is None:
            raise Exception(f"[session id] parsing fail: {response}")

        return cls(
            request_type=RTSPPacket.RESPONSE,
            sequence_number=sequence_number,
            session_id=session_id
        )

    @classmethod
    def build_response(cls, sequence_number: int, session_id: str):
        response = '\r\n'.join((
            f"{cls.RTSP_VERSION} 200 OK",
            f"CSeq: {sequence_number}",
            f"Session: {session_id}",
        )) + '\r\n'
        return response

    @classmethod
    def from_request(cls, request: bytes):

        request_type_endindex =  KMP_String(b" rtsp://", request)      
        RTSP_index =  KMP_String(b"RTSP", request)  
        CSeq_index =  KMP_String(b"CSeq: ", request) 
        endindex = KMP_String(b"\r\n", request)

        if (len(request_type_endindex) * len(RTSP_index) * len(CSeq_index) * len(endindex) == 0 ):
            raise InvalidRTSPRequest(f"[request] parsing fail: {request}")

        request_type = request[    : request_type_endindex[0] ].decode()


        if request_type not in (RTSPPacket.SETUP,
                                RTSPPacket.PLAY,
                                RTSPPacket.PAUSE,
                                RTSPPacket.TEARDOWN):
            raise InvalidRTSPRequest(f"[invalid request type]: {request}")


        video_file_path = request[request_type_endindex[0]+8 : RTSP_index[0] -1 ].decode()
        sequence_number = request[CSeq_index[0]+6 : endindex[1] ].decode()

        

        Session_index =  KMP_String(b"Session: ", request)
        client_port_index = KMP_String(b"client_port", request)

    

        session_id = None
        dst_port = None

        if ( len(Session_index) != 0):
            session_id = request[ Session_index[0]+9 : endindex[2] ].decode()
        if ( len(client_port_index) != 0):
            dst_port = request[ client_port_index[0]+12 : endindex[2] ].decode()








        if request_type == RTSPPacket.SETUP:
            try:
                dst_port = int(dst_port)
            except (ValueError, TypeError):
                raise InvalidRTSPRequest(f"[RTP port] parsing fail")
        try:
            sequence_number = int(sequence_number)
        except (ValueError, TypeError):
            raise InvalidRTSPRequest(f"[sequence number] parsing fail: {request}")

        return cls(
            request_type,
            video_file_path,
            sequence_number,
            dst_port,
            session_id
        )

    def to_request(self) -> bytes:

        if any((attr is None for attr in (self.request_type,
                                          self.sequence_number,
                                          self.session_id))):
            raise InvalidRTSPRequest('[attribute missing]: check -> request_type, sequence_number, session_id')

        if self.request_type in (self.INVALID, self.RESPONSE):
            raise InvalidRTSPRequest(f"[invalid request type]: {self}")

        request_lines = [
            f"{self.request_type} rtsp://{self.video_file_path} {self.RTSP_VERSION}",
            f"CSeq: {self.sequence_number}",
        ]
        if self.request_type == self.SETUP:
            if self.rtp_dst_port is None:
                raise InvalidRTSPRequest(f"[RTP destination port missing]: {self}")
            request_lines.append(
                f"Transport: RTP/UDP;client_port={self.rtp_dst_port}"
            )
        else:
            request_lines.append(
                f"Session: {self.session_id}"
            )
        request = '\r\n'.join(request_lines) + '\r\n'
        return request.encode()
