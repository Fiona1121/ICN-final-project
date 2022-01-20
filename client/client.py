import socket
from threading import Thread, Timer
from typing import Union, Optional, List, Tuple
from time import sleep, time
from PIL import Image
from io import BytesIO
from utils.rtcp_packet import RTCPPacket

from utils.rtsp_packet import RTSPPacket
from utils.rtp_packet import RTPPacket
from utils.video_stream import VideoStream


class Client:
    DEFAULT_CHUNK_SIZE = 4096
    DEFAULT_RECV_DELAY = 20  # in milliseconds

    DEFAULT_LOCAL_HOST = "127.0.0.1"

    RTP_SOFT_TIMEOUT = 5  # in milliseconds
    # for allowing simulated non-blocking operations
    # (useful for keyboard break)
    RTSP_SOFT_TIMEOUT = 100  # in milliseconds
    # if it's present at the end of chunk, client assumes
    # it's the last chunk for current frame (end of frame)
    PACKET_HEADER_LENGTH = 5

    # =================
    # RTCP variables
    # =================
    RTCP_RCV_PORT = 19001  # port where server will receive the RTP packets
    RTCP_PERIOD = 400  # how often to send RTCP packet

    def __init__(
        self,
        file_path: str,
        remote_host_address: str,
        remote_host_port: int,
        rtp_port: int,
    ):
        self._rtsp_connection: Union[None, socket.socket] = None
        self._rtp_socket: Union[None, socket.socket] = None
        self._rtp_receive_thread: Union[None, Thread] = None
        self._frame_buffer: List[Image.Image] = []
        self._current_sequence_number = 0
        self.session_id = ""

        self.current_frame_number = -1

        self.is_rtsp_connected = False
        self.is_receiving_rtp = False

        # ===========================
        # Rtcp variables:
        # ===========================
        self._rtcp_socket: Union[None, socket.socket] = None
        self._rtcp_sender: Union[None, self.RtcpSender()] = None

        # ===========================
        # Statistics variables:
        # ===========================
        self.stat_data_rate = 0  # Rate of video data received in bytes/s
        self.stat_total_bytes = 0  # Total number of bytes received in a session
        self.stat_start_time = 0  # Time in ms when start is pressed
        self.stat_total_play_time = 0  # Time in ms of video playing since beginning
        self.stat_fraction_lost = 0  # Fraction of RTP data packets from sender lost since the prev packet was sent
        self.stat_cumulative_lost = 0  # Number of packets lost
        self.stat_expected_sequence_number = 0  # Expected sequence num in the session
        self.stat_high_sequence_number = 0  # Highest sequence num received in session

        self.file_path = file_path
        self.remote_host_address = remote_host_address
        self.remote_host_port = remote_host_port
        self.rtp_port = rtp_port

    def get_next_frame(self) -> Optional[Tuple[Image.Image, int]]:
        if self._frame_buffer:
            self.current_frame_number += 1
            # skip 5 bytes which contain frame length in bytes
            return self._frame_buffer.pop(0), self.current_frame_number
        return None

    @staticmethod
    def _get_frame_from_packet(packet: RTPPacket) -> Image.Image:
        # the payload is already the jpeg
        raw = packet.payload
        frame = Image.open(BytesIO(raw))
        return frame

    def _recv_rtp_packet(self, size=DEFAULT_CHUNK_SIZE) -> RTPPacket:
        recv = bytes()
        # print("Waiting RTP packet...")
        while True:
            try:
                recv += self._rtp_socket.recv(size)
                if recv.endswith(VideoStream.JPEG_EOF):
                    break
            except socket.timeout:
                continue
        # print(f"Received from server: {repr(recv)}")
        return RTPPacket.from_packet(recv)

    def _start_rtp_receive_thread(self):
        self._rtp_receive_thread = Thread(
            target=self._handle_video_receive, name="rtp_rcv"
        )
        self._rtp_receive_thread.setDaemon(True)
        self._rtp_receive_thread.start()

    def _start_rtcp_send_thread(self):
        self._rtcp_send_thread = Thread(
            target=self._rtcp_sender._send_rtcp_packet, name="rtcp_send"
        )
        self._rtcp_send_thread.setDaemon(True)
        self._rtcp_send_thread.start()

    def _handle_video_receive(self):
        self._rtp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._rtp_socket.bind((self.DEFAULT_LOCAL_HOST, self.rtp_port))
        self._rtp_socket.settimeout(self.RTP_SOFT_TIMEOUT / 1000.0)
        while True:
            if not self.is_receiving_rtp:
                sleep(self.RTP_SOFT_TIMEOUT / 1000.0)  # diminish cpu hogging
                continue

            cur_time = round(time() * 1000)  # Get current time in ms
            self.stat_total_play_time += cur_time - self.stat_start_time
            self.stat_start_time = cur_time

            packet = self._recv_rtp_packet()
            frame = self._get_frame_from_packet(packet)
            self._frame_buffer.append(frame)
            print(f"[RTP] Receive packet #{packet.sequence_number}")

            if packet.sequence_number > self.stat_high_sequence_number:
                self.stat_high_sequence_number = packet.sequence_number
            if packet.sequence_number != self.stat_expected_sequence_number:
                self.stat_cumulative_lost += 1
            self.stat_expected_sequence_number += 1

            self.stat_data_rate = 0.0
            if self.stat_total_play_time != 0:
                self.stat_data_rate = self.stat_total_bytes / (
                    self.stat_total_play_time / 1000
                )
            self.stat_fraction_lost = 0.0
            if self.stat_high_sequence_number != 0:
                self.stat_fraction_lost = float(
                    self.stat_cumulative_lost / self.stat_high_sequence_number
                )
            self.stat_total_bytes += len(packet.payload)

            # todo: update statistics label

    def _setup_rtcp_sender(self):
        print("[RTCP] Setting up RTCP socket...")
        self._rtcp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        print(f"[RTCP] UDP client is up")
        self._rtcp_sender = self.RtcpSender(self, self.RTCP_PERIOD / 1000.0)
        print(f"[RTCP] Finish setting up")

    def establish_rtsp_connection(self):
        if self.is_rtsp_connected:
            print("RTSP is already connected.")
            return
        print(f"Connecting to {self.remote_host_address}:{self.remote_host_port}...")
        self._rtsp_connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._rtsp_connection.connect((self.remote_host_address, self.remote_host_port))
        self._rtsp_connection.settimeout(self.RTSP_SOFT_TIMEOUT / 1000.0)
        self.is_rtsp_connected = True

    def close_rtsp_connection(self):
        if not self.is_rtsp_connected:
            print("RTSP is not connected.")
            return
        self._rtsp_connection.close()
        self.is_rtsp_connected = False

    def _send_request(self, request_type=RTSPPacket.INVALID) -> RTSPPacket:
        if not self.is_rtsp_connected:
            raise Exception(
                "rtsp connection not established. run `setup_rtsp_connection()`"
            )
        request = RTSPPacket(
            request_type,
            self.file_path,
            self._current_sequence_number,
            self.rtp_port,
            self.session_id,
        ).to_request()
        # print(f"Sending request: {repr(request)}")
        self._rtsp_connection.send(request)
        self._current_sequence_number += 1
        return self._get_response()

    def send_setup_request(self) -> RTSPPacket:
        response = self._send_request(RTSPPacket.SETUP)
        self._start_rtp_receive_thread()
        self._setup_rtcp_sender()
        self.session_id = response.session_id
        return response

    def send_play_request(self) -> RTSPPacket:
        response = self._send_request(RTSPPacket.PLAY)
        self._start_rtcp_send_thread()
        self.is_receiving_rtp = True
        return response

    def send_pause_request(self) -> RTSPPacket:
        response = self._send_request(RTSPPacket.PAUSE)
        self.is_receiving_rtp = False
        return response

    def send_teardown_request(self) -> RTSPPacket:
        response = self._send_request(RTSPPacket.TEARDOWN)
        self.is_receiving_rtp = False
        self.is_rtsp_connected = False
        return response

    def _get_response(self, size=DEFAULT_CHUNK_SIZE) -> RTSPPacket:
        rcv = None
        while True:
            try:
                rcv = self._rtsp_connection.recv(size)
                break
            except socket.timeout:
                continue
        # print(f"Received from server: {repr(rcv)}")
        response = RTSPPacket.from_response(rcv)
        return response

    # ===========================
    # Send RTCP control packets for QoS feedback
    # ===========================
    class RtcpSender:
        def __init__(self, client, interval) -> None:
            self.client: Union[None, Client] = client  # Pass in the client instance
            self.interval = interval  # Interval for receiving packets

            self.num_pkts_expected = 0  # Number of RTP pkt expected since last RTCP pkt
            self.num_pkts_lost = 0  # Number of RTP pkt lost since last RTCP pkt
            self.last_high_sequence_number = 0  # The last highest Seq number received
            self.last_cumulative_lost = 0  # The last cumulative packets lost
            self.last_fraction_lost = 0  # The last fraction lost

        def _send_rtcp_packet(self):
            while True:
                if not self.client.is_receiving_rtp:
                    sleep(self.interval)
                    continue
                # Calculate stats for this period
                self.num_pkts_expected = (
                    self.client.stat_high_sequence_number
                    - self.last_high_sequence_number
                )
                self.num_pkts_lost = (
                    self.client.stat_cumulative_lost - self.last_cumulative_lost
                )
                self.last_fraction_lost = float(0)
                if self.num_pkts_expected != 0:
                    self.last_fraction_lost = float(
                        self.num_pkts_lost / self.num_pkts_expected
                    )
                self.last_high_sequence_number = self.client.stat_high_sequence_number
                self.last_cumulative_lost = self.client.stat_cumulative_lost

                try:
                    rtcp_packet = RTCPPacket(
                        self.last_fraction_lost,
                        self.client.stat_cumulative_lost,
                        self.client.stat_high_sequence_number,
                    )
                    datagram = rtcp_packet.get_packet()
                    self.client._rtcp_socket.sendto(
                        datagram,
                        (self.client.remote_host_address, self.client.RTCP_RCV_PORT),
                    )
                    print(
                        f"[RTCP] Send pkt: {self.last_fraction_lost,self.client.stat_cumulative_lost,self.client.stat_high_sequence_number}"
                    )
                except socket.error as e:
                    print("[RTCP] Error sending data %s" % e)
                sleep(self.interval)
