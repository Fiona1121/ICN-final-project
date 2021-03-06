import os
from pickletools import optimize
from random import random
import socket
from io import BytesIO

from PIL import Image
from time import sleep
from threading import Thread
from typing import Union, Tuple

import cv2
import numpy as np
import math
import struct

from utils.video_stream import VideoStream
from utils.rtsp_packet import RTSPPacket
from utils.rtp_packet import RTPPacket
from utils.rtcp_packet import RTCPPacket


class Server:
    FRAME_PERIOD = 1000 // VideoStream.DEFAULT_FPS  # in milliseconds
    DEFAULT_CHUNK_SIZE = 4096

    # for allowing simulated non-blocking operations
    # (useful for keyboard break)
    RTSP_SOFT_TIMEOUT = 100  # in milliseconds

    # =================
    # RTCP variables
    # =================
    RTCP_RCV_PORT = 19001  # port where the client will receive the RTP packets
    RTCP_PERIOD = 400  # how often to check for control events
    CONGESTION_PERIOD = 600

    class STATE:
        INIT = 0
        PAUSED = 1
        PLAYING = 2
        FINISHED = 3
        TEARDOWN = 4

    def __init__(
        self, rtsp_ip: str, rtsp_port: int, sessionID: str, lost_probability: float = 0
    ):
        self._video_stream: Union[None, VideoStream] = None
        self._rtp_send_thread: Union[None, Thread] = None
        self._rtsp_connection: Union[None, socket.socket] = None
        self._rtp_socket: Union[None, socket.socket] = None
        self._client_address: Tuple[str, int] = None
        self.server_state: int = self.STATE.INIT

        self._rtcp_rcv_thread: Union[None, Thread] = None
        self._congestion_control_thread: Union[None, Thread] = None
        self._rtcp_socket: Union[None, socket.socket] = None
        self._rtcp_receiver: Union[None, self.RtcpReceiver()] = None
        self._image_translator: Union[None, self.ImageTranslator()] = None
        self._congestion_controller: Union[None, self.CongestionController()] = None
        self.congestion_level: int = 0

        self.lost_probability = lost_probability
        self.send_delay = self.FRAME_PERIOD
        self.rtsp_host = rtsp_ip
        self.rtsp_port = rtsp_port
        self.sessionID = sessionID

    def _rtsp_recv(self, size=DEFAULT_CHUNK_SIZE) -> bytes:
        recv = None
        while True:
            try:
                recv = self._rtsp_connection.recv(size)
                break
            except socket.timeout:
                continue
        # print(f"Received from client: {repr(recv)}")
        return recv

    def _rtsp_send(self, data: bytes) -> int:
        # print(f"Sending to client: {repr(data)}")
        return self._rtsp_connection.send(data)  # might be the number of bytes sent

    def _get_rtsp_packet(self) -> RTSPPacket:
        return RTSPPacket.from_request(self._rtsp_recv())

    def _wait_connection(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        address = self.rtsp_host, self.rtsp_port
        s.bind(address)
        print(f"Listening on {address[0]}:{address[1]}...")
        s.listen(1)
        print("Waiting for connection...")
        self._rtsp_connection, self._client_address = s.accept()
        self._rtsp_connection.settimeout(self.RTSP_SOFT_TIMEOUT / 1000.0)
        print(
            f"Accepted connection from {self._client_address[0]}:{self._client_address[1]}"
        )

    def _wait_setup(self):
        if self.server_state != self.STATE.INIT:
            raise Exception("server is already setup")
        while True:
            packet = self._get_rtsp_packet()
            if packet.request_type == RTSPPacket.SETUP:
                self.server_state = self.STATE.PAUSED
                print("State set to PAUSED")
                self._client_address = self._client_address[0], packet.rtp_dst_port
                self._setup_rtp(packet.video_file_path)
                self._setup_rtcp()
                self._send_rtsp_response(packet.sequence_number)
                break

    def setup(self):
        self._wait_connection()
        self._wait_setup()

    def _start_rtp_send_thread(self):
        self._rtp_send_thread = Thread(target=self._handle_video_send, name="rtp")
        self._rtp_send_thread.setDaemon(
            True
        )  # this thread will be killed when the main thread ended
        self._rtp_send_thread.start()

    def _start_rtcp_rcv_thread(self):
        self._rtcp_rcv_thread = Thread(
            target=self._rtcp_receiver._receive_rtcp_packet, name="rtcp_rcv"
        )
        self._rtcp_rcv_thread.setDaemon(True)
        self._rtcp_rcv_thread.start()

    def _start_congestion_control_thread(self):
        self._congestion_control_thread = Thread(
            target=self._congestion_controller._congestion_control,
            name="congestion_control",
        )
        self._congestion_control_thread.setDaemon(True)
        self._congestion_control_thread.start()

    def _setup_rtp(self, video_file_path: str):
        print(f"Opening up video stream for file {video_file_path}")
        self._video_stream = VideoStream(video_file_path)
        print("Setting up RTP socket...")
        self._rtp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._start_rtp_send_thread()

    def _setup_rtcp(self):
        print("[RTCP] Setting up RTCP socket...")
        self._rtcp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        address = self.rtsp_host, self.RTCP_RCV_PORT
        self._rtcp_socket.bind(address)
        print(f"[RTCP] UDP server is up and listening on {address[0]}:{address[1]}")

        self._rtcp_receiver = self.RtcpReceiver(self, self.RTCP_PERIOD / 1000.0)
        self._congestion_controller = self.CongestionController(
            self, self.CONGESTION_PERIOD / 1000.0
        )
        self._image_translator = self.ImageTranslator(self, 80)
        # print("[RTCP] Finish setting up")

    def handle_rtsp_requests(self):
        print("Waiting for RTSP requests...")
        # main thread will be running here most of the time
        while True:
            packet = self._get_rtsp_packet()
            # assuming state will only ever be PAUSED or PLAYING at this point
            if packet.request_type == RTSPPacket.PLAY:
                if self.server_state == self.STATE.PLAYING:
                    print("Current state is already PLAYING.")
                    continue
                self.server_state = self.STATE.PLAYING
                self._start_rtcp_rcv_thread()
                self._start_congestion_control_thread()
                print("State set to PLAYING.")
            elif packet.request_type == RTSPPacket.PAUSE:
                if self.server_state == self.STATE.PAUSED:
                    print("Current state is already PAUSED.")
                    continue
                self.server_state = self.STATE.PAUSED
                print("State set to PAUSED.")
            elif packet.request_type == RTSPPacket.TEARDOWN:
                print("Received TEARDOWN request, shutting down...")
                self._send_rtsp_response(packet.sequence_number)
                self._rtsp_connection.close()
                self._video_stream.close()
                self._rtp_socket.close()
                self._rtcp_socket.close()
                self.server_state = self.STATE.TEARDOWN
                # for simplicity's sake, caught on main_server
                raise ConnectionError("teardown requested")
            else:
                # will never happen, since exception is raised inside `parse_rtsp_request()`
                # raise InvalidRTSPRequest()
                pass
            self._send_rtsp_response(packet.sequence_number)

    def _send_rtp_packet(self, packet: bytes):

        to_send = packet[:]
        size = len(to_send)
        count = math.ceil(size / (VideoStream.MAX_IMAGE_DGRAM))
        array_pos_start = 0

        while count:

            array_pos_end = min(size, array_pos_start + VideoStream.MAX_IMAGE_DGRAM)
            try:
                self._rtp_socket.sendto(
                    struct.pack("B", count) + to_send[array_pos_start:array_pos_end],
                    self._client_address,
                )
                array_pos_start = array_pos_end
                count -= 1
            except socket.error as e:
                print(f"failed to send rtp packet: {e}")
                return

    def _handle_video_send(self):
        print(f"Sending video to {self._client_address[0]}:{self._client_address[1]}")
        while True:
            if self.server_state == self.STATE.TEARDOWN:
                return
            if self.server_state != self.STATE.PLAYING:
                sleep(0.5)  # diminish cpu hogging
                continue
            if (
                self._video_stream.current_frame_number >= VideoStream.VIDEO_LENGTH - 1
            ):  # frames are 0-indexed
                print("Reached end of file.")
                self.server_state = self.STATE.FINISHED
                return
            frame = self._video_stream.get_next_frame()
            if random() < self.lost_probability:
                print(f"[RTP] Packet lost")
                sleep(self.send_delay / 1000.0)
                continue
            if self.congestion_level > 0:
                print(f"[RTCP] Congestion control: {self.congestion_level}")
                self._image_translator.set_compression_quality(
                    int(100 - self.congestion_level * 20)
                )
                frame = self._image_translator.compress(frame)
            frame_number = self._video_stream.current_frame_number
            rtp_packet = RTPPacket(
                payload_type=RTPPacket.TYPE.MJPEG,
                sequence_number=frame_number,
                timestamp=frame_number * self.FRAME_PERIOD,
                payload=frame,
            )
            print(f"Sending packet #{frame_number}")
            print("Packet header:")
            # rtp_packet.print_header()
            packet = rtp_packet.get_packet()
            self._send_rtp_packet(packet)
            sleep(self.send_delay / 1000.0)

    def _send_rtsp_response(self, sequence_number: int):
        response = RTSPPacket.build_response(sequence_number, self.sessionID)
        self._rtsp_send(response.encode())
        print("Sent response to client.")

    # ===========================
    # Controls RTP sending rate based on traffic
    # ===========================
    class CongestionController:
        def __init__(self, server, interval) -> None:
            # pass in the server instance
            self.server: Union[None, Server] = server

            # set timer with interval for congestion control
            self.interval = interval
            self.prelevel = -1
            print("[RTCP] Congestion controller instance is created")

        def _congestion_control(self):
            # adjust the send rate
            while True:
                if self.server.server_state == self.server.STATE.TEARDOWN:
                    return
                if self.server.server_state != self.server.STATE.PLAYING:
                    sleep(self.interval)  # diminish cpu hogging
                    continue
                if self.prelevel != self.server.congestion_level:
                    self.server.send_delay = (
                        self.server.FRAME_PERIOD
                        + self.server.congestion_level * self.server.FRAME_PERIOD * 0.1
                    )
                    self.prelevel = self.server.congestion_level
                    print(f"Send delay changed to: {self.server.send_delay}")
                sleep(self.interval)

    # ===========================
    # Listener for RTCP packets sent from client
    # ===========================
    class RtcpReceiver:
        BUFFERSIZE = 512

        def __init__(self, server, interval) -> None:
            # pass in the server instance
            self.server: Union[None, Server] = server

            # set timer with interval for receiving packets
            self.interval = interval
            print("[RTCP] RTCP receiver instance is created")

        def _receive_rtcp_packet(self):
            while True:
                if self.server.server_state == self.server.STATE.TEARDOWN:
                    return
                if self.server.server_state != self.server.STATE.PLAYING:
                    sleep(self.interval)  # diminish cpu hogging
                    continue
                try:
                    datagram = self.server._rtcp_socket.recvfrom(self.BUFFERSIZE)[0]
                    rtcp_pkt = RTCPPacket.from_bitstream(datagram)
                    # print(
                    #     f"[RTCP] Receive pkt: {rtcp_pkt.fraction_lost, rtcp_pkt.cum_lost, rtcp_pkt.highest_rcv}"
                    # )
                    fraction_lost = rtcp_pkt.fraction_lost
                    if fraction_lost >= 0 and fraction_lost <= 0.01:
                        self.server.congestion_level = 0
                    elif fraction_lost > 0.01 and fraction_lost <= 0.25:
                        self.server.congestion_level = 1
                    elif fraction_lost > 0.25 and fraction_lost <= 0.5:
                        self.server.congestion_level = 2
                    elif fraction_lost > 0.5 and fraction_lost <= 0.75:
                        self.server.congestion_level = 3
                    else:
                        self.server.congestion_level = 4
                except socket.error as e:
                    print("[RTCP] Error receiving data %s" % e)
                sleep(self.interval)

    # ===========================
    # Translate an image to different encoding or quality
    # ===========================
    class ImageTranslator:
        def __init__(self, server, cp) -> None:
            # pass in the server instance
            self.server: Union[None, Server] = server

            # assign video quality
            self.compression_quailty = cp
            print("[RTCP] Image translator instance is created")

        def compress(self, image_byte):

            img = cv2.imdecode(np.frombuffer(image_byte, dtype=np.uint8), 1)
            image = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
            image.save(
                "output.jpeg",
                format="JPEG",
                optiimize=True,
                quality=self.compression_quality,
            )
            with open("output.jpeg", "rb") as image:
                f = image.read()
            os.remove("output.jpeg")
            return f

        def set_compression_quality(self, cp):
            self.compression_quality = cp
