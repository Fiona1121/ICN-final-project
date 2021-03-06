from logging import info
from PyQt5.QtWidgets import QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout
from PyQt5.QtWidgets import QMainWindow, QWidget, QPushButton
from PyQt5.QtGui import QPixmap, QIcon
from PyQt5.QtCore import pyqtSignal, QTimer
from PIL.ImageQt import ImageQt

from client.client import Client
from utils.video_stream import VideoStream
from utils.inference import inference


class ClientWindow(QMainWindow):
    _update_image_signal = pyqtSignal()

    def __init__(
        self,
        file_name: str,
        host_address: str,
        host_port: int,
        rtp_port: int,
        parent=None,
        add_obj_detect: bool = True,
    ):
        super(ClientWindow, self).__init__(parent)

        self.counter = 0
        self.add_obj_detect = add_obj_detect

        self.video_player = QLabel()
        self.setup_button = QPushButton()
        self.play_button = QPushButton()
        self.pause_button = QPushButton()
        self.tear_button = QPushButton()
        self.error_label = QLabel()

        self.data_rate_label = QLabel()  # Rate of video data received in bytes/s
        self.total_bytes_label = QLabel()  # Total number of bytes received in a session
        self.total_play_time_label = (
            QLabel()
        )  # Time in ms of video playing since beginning
        self.fraction_lost_label = (
            QLabel()
        )  # Fraction of RTP data packets from sender lost since the prev packet was sent
        self.cumulative_lost_label = QLabel()  # Number of packets lost
        self.expected_sequence_number_label = (
            QLabel()
        )  # Expected sequence num in the session
        self.high_sequence_number_label = (
            QLabel()
        )  # Highest sequence num received in session

        self._media_client = Client(file_name, host_address, host_port, rtp_port)
        self._update_image_signal.connect(self.update_image)
        self._update_image_timer = QTimer()
        self._update_image_timer.timeout.connect(self._update_image_signal.emit)

        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Real Time Streaming - Client")
        self.setFixedWidth(1000)
        self.setFixedHeight(400)

        button_style = """
            QPushButton {
                border-style: solid;
                border-width:1px;
                border-radius:5px;
                border-color: black;
                max-width:75px;
                max-height:90px;
                min-width:75px;
                min-height:90px;
            }

            QPushButton:hover {
                border-width:2px;
            }

            QPushButton:pressed {
                background-color: grey;
                color: #000000;
                font: bold 14px;
            }
        """

        self.setup_button.setEnabled(True)
        self.setup_button.setText("Setup")
        self.setup_button.setStyleSheet(button_style)
        self.setup_button.clicked.connect(self.handle_setup)

        self.play_button.setEnabled(False)
        self.play_button.setText("Play")
        self.play_button.setStyleSheet(button_style)
        self.play_button.clicked.connect(self.handle_play)

        self.pause_button.setEnabled(False)
        self.pause_button.setText("Pause")
        self.pause_button.setStyleSheet(button_style)
        self.pause_button.clicked.connect(self.handle_pause)

        self.tear_button.setEnabled(False)
        self.tear_button.setText("Teardown")
        self.tear_button.setStyleSheet(button_style)
        self.tear_button.clicked.connect(self.handle_teardown)

        self.error_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)

        self.data_rate_label.setText(
            f"Data rate: {str(self._media_client.stat_data_rate)} bytes/s"
        )
        self.total_bytes_label.setText(
            f"Total received: {str(self._media_client.stat_total_bytes)} bytes"
        )
        self.total_play_time_label.setText(
            f"Total time playing: {str(self._media_client.stat_total_play_time*1000)} s"
        )

        self.fraction_lost_label.setText(
            f"Fraction lost: {str(self._media_client.stat_fraction_lost)}"
        )
        self.cumulative_lost_label.setText(
            f"Number of packets lost: {str(self._media_client.stat_cumulative_lost)}"
        )
        self.expected_sequence_number_label.setText(
            f"Expected sequence num: {str(self._media_client.stat_expected_sequence_number)}"
        )
        self.high_sequence_number_label.setText(
            f"Highest sequence num received: {str(self._media_client.stat_high_sequence_number)}"
        )

        central_widget = QWidget(self)
        # central_widget.resize(600, 400)
        self.setCentralWidget(central_widget)

        control_layout = QVBoxLayout()
        control_layout.setContentsMargins(0, 0, 0, 0)
        control_layout.addWidget(self.setup_button)
        control_layout.addWidget(self.play_button)
        control_layout.addWidget(self.pause_button)
        control_layout.addWidget(self.tear_button)

        information_layout = QVBoxLayout()
        information_layout.addWidget(self.data_rate_label)
        information_layout.addWidget(self.total_bytes_label)
        information_layout.addWidget(self.total_play_time_label)
        information_layout.addWidget(self.fraction_lost_label)
        information_layout.addWidget(self.cumulative_lost_label)
        information_layout.addWidget(self.expected_sequence_number_label)
        information_layout.addWidget(self.high_sequence_number_label)

        layout = QHBoxLayout()
        layout.addLayout(control_layout, 2)
        layout.addWidget(self.video_player, 8)
        layout.addLayout(information_layout, 5)

        central_widget.setLayout(layout)

    def update_information(self):
        self.counter %= 30
        if self.counter == 0:
            self.data_rate_label.setText(
                f"Data rate: {str(round(self._media_client.stat_data_rate, 2))}  bytes/s"
            )
            self.total_bytes_label.setText(
                f"Total received: {str(round(self._media_client.stat_total_bytes))} bytes"
            )
            self.total_play_time_label.setText(
                f"Total time playing: {str(round(self._media_client.stat_total_play_time*1000))} s"
            )
            self.fraction_lost_label.setText(
                f"Fraction lost: {str(round(self._media_client.stat_fraction_lost,2))}"
            )
            self.cumulative_lost_label.setText(
                f"Number of packets lost: {str(round(self._media_client.stat_cumulative_lost))}"
            )
            self.expected_sequence_number_label.setText(
                f"Expected sequence num: {str(round(self._media_client.stat_expected_sequence_number))}"
            )
            self.high_sequence_number_label.setText(
                f"Highest sequence num received: {str(round(self._media_client.stat_high_sequence_number))}"
            )
        self.counter += 1

    def update_image(self):
        self.update_information()
        if not self._media_client.is_receiving_rtp:
            return
        frame = self._media_client.get_next_frame()
        if (not isinstance(frame, type(None))) and self.add_obj_detect:
            frame = (inference(frame[0]), frame[1])
        if frame is not None:
            pix = QPixmap.fromImage(ImageQt(frame[0]).copy()).scaledToWidth(500)
            self.video_player.setPixmap(pix)

    def handle_setup(self):
        self._media_client.establish_rtsp_connection()
        self._media_client.send_setup_request()
        self.setup_button.setEnabled(False)
        self.play_button.setEnabled(True)
        self.tear_button.setEnabled(True)
        self._update_image_timer.start(1000 // VideoStream.DEFAULT_FPS)

    def handle_play(self):
        self._media_client.send_play_request()
        self.play_button.setEnabled(False)
        self.pause_button.setEnabled(True)

    def handle_pause(self):
        self._media_client.send_pause_request()
        self.pause_button.setEnabled(False)
        self.play_button.setEnabled(True)

    def handle_teardown(self):
        self._media_client.send_teardown_request()
        self.setup_button.setEnabled(True)
        self.play_button.setEnabled(False)
        self.pause_button.setEnabled(False)
        exit(0)

    def handle_error(self):
        self.play_button.setEnabled(False)
        self.pause_button.setEnabled(False)
        self.tear_button.setEnabled(False)
        self.error_label.setText(f"Error: {self.media_player.errorString()}")
