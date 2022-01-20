from logging import info
from PyQt5.QtWidgets import QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout
from PyQt5.QtWidgets import QMainWindow, QWidget, QPushButton
from PyQt5.QtGui import QPixmap, QIcon
from PyQt5.QtCore import pyqtSignal, QTimer
from PIL.ImageQt import ImageQt

from client.client import Client
from utils.video_stream import VideoStream


class ClientWindow(QMainWindow):
    _update_image_signal = pyqtSignal()

    def __init__(
            self,
            file_name: str,
            host_address: str,
            host_port: int,
            rtp_port: int,
            parent=None):
        super(ClientWindow, self).__init__(parent)
        
        self.counter = 0
        
        self.video_player = QLabel()
        self.setup_button = QPushButton()
        self.play_button = QPushButton()
        self.pause_button = QPushButton()
        self.tear_button = QPushButton()
        self.error_label = QLabel()
        
        self.data_rate_label = QLabel()  # Rate of video data received in bytes/s
        self.data_rate_label_num = QLabel()
        self.total_bytes_label = QLabel()  # Total number of bytes received in a session
        self.total_bytes_label_num = QLabel()
        self.start_time_label = QLabel()  # Time in ms when start is pressed
        self.start_time_label_num = QLabel()
        self.total_play_time_label = QLabel()  # Time in ms of video playing since beginning
        self.total_play_time_label_num = QLabel()
        self.fraction_lost_label = QLabel()  # Fraction of RTP data packets from sender lost since the prev packet was sent
        self.fraction_lost_label_num = QLabel()
        self.cumulative_lost_label = QLabel()  # Number of packets lost
        self.cumulative_lost_label_num = QLabel()
        self.expected_sequence_number_label = QLabel()  # Expected sequence num in the session
        self.expected_sequence_number_label_num = QLabel()
        self.high_sequence_number_label = QLabel()  # Highest sequence num received in session
        self.high_sequence_number_label_num = QLabel()

        self._media_client = Client(file_name, host_address, host_port, rtp_port)
        self._update_image_signal.connect(self.update_image)
        self._update_image_timer = QTimer()
        self._update_image_timer.timeout.connect(self._update_image_signal.emit)

        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Client")
        self.setFixedWidth(900)
        self.setFixedHeight(400)
        
        button_style = """
            QPushButton {
                background-color: white;
                border-style: solid;
                border-width:1px;
                border-radius:30px;
                border-color: black;
                max-width:60px;
                max-height:60px;
                min-width:60px;
                min-height:60px;
            }

            QPushButton:hover {
                border-width:3px;
            }

            QPushButton:pressed {
                background-color: #FFA823;
                color: #000000;
                font: bold 14px;
            }
        """
        
        self.setup_button.setEnabled(True)
        self.setup_button.setText('Setup')
        self.setup_button.setStyleSheet(button_style)
        self.setup_button.clicked.connect(self.handle_setup)

        self.play_button.setEnabled(False)
        self.play_button.setText('Play')
        self.play_button.setStyleSheet(button_style)
        self.play_button.clicked.connect(self.handle_play)

        self.pause_button.setEnabled(False)
        self.pause_button.setText('Pause')
        self.pause_button.setStyleSheet(button_style)
        self.pause_button.clicked.connect(self.handle_pause)

        self.tear_button.setEnabled(False)
        self.tear_button.setText('Teardown')
        self.tear_button.setStyleSheet(button_style)
        self.tear_button.clicked.connect(self.handle_teardown)

        self.error_label.setSizePolicy(
            QSizePolicy.Preferred,
            QSizePolicy.Maximum)

        self.data_rate_label.setText('Data rate (bytes/s):')
        self.data_rate_label_num.setText(str(self._media_client.stat_data_rate))
        self.total_bytes_label.setText('Total number of bytes received:')
        self.total_bytes_label_num.setText(str(self._media_client.stat_total_bytes))
        self.start_time_label.setText('Time in ms when start is pressed:')
        self.start_time_label_num.setText(str(self._media_client.stat_start_time))
        self.total_play_time_label.setText('Time in ms of video playing:')
        self.total_play_time_label_num.setText(str(self._media_client.stat_total_play_time))
        self.fraction_lost_label.setText('Fraction lost:')
        self.fraction_lost_label_num.setText(str(self._media_client.stat_fraction_lost))
        self.cumulative_lost_label.setText('Number of packets lost:')
        self.cumulative_lost_label_num.setText(str(self._media_client.stat_cumulative_lost))
        self.expected_sequence_number_label.setText('Expected sequence num :')
        self.expected_sequence_number_label_num.setText(str(self._media_client.stat_expected_sequence_number))
        self.high_sequence_number_label.setText('Highest sequence num received:')
        self.high_sequence_number_label_num.setText(str(self._media_client.stat_high_sequence_number))
        
        central_widget = QWidget(self)
        # central_widget.geomertry(500, 200)
        self.setCentralWidget(central_widget)

        control_layout = QVBoxLayout()
        control_layout.setContentsMargins(0, 0, 0, 0)
        control_layout.addWidget(self.setup_button)
        control_layout.addWidget(self.play_button)
        control_layout.addWidget(self.pause_button)
        control_layout.addWidget(self.tear_button)

        information_layout = QVBoxLayout()
        information_layout.addWidget(self.data_rate_label)
        information_layout.addWidget(self.data_rate_label_num)
        information_layout.addWidget(self.total_bytes_label)
        information_layout.addWidget(self.total_bytes_label_num)
        information_layout.addWidget(self.start_time_label)
        information_layout.addWidget(self.start_time_label_num)
        information_layout.addWidget(self.total_play_time_label)
        information_layout.addWidget(self.total_play_time_label_num)
        information_layout.addWidget(self.fraction_lost_label)
        information_layout.addWidget(self.fraction_lost_label_num)
        information_layout.addWidget(self.cumulative_lost_label)
        information_layout.addWidget(self.cumulative_lost_label_num)
        information_layout.addWidget(self.expected_sequence_number_label)
        information_layout.addWidget(self.expected_sequence_number_label_num)
        information_layout.addWidget(self.high_sequence_number_label)
        information_layout.addWidget(self.high_sequence_number_label_num)
        
        layout = QHBoxLayout()
        layout.addLayout(control_layout, 1)
        layout.addWidget(self.video_player, 8)
        layout.addLayout(information_layout, 6)
        # layout.addWidget(self.error_label)

        central_widget.setLayout(layout)

    def update_information(self):
        self.counter %= 30
        if self.counter == 0:
            self.data_rate_label_num.setText(str(round(self._media_client.stat_data_rate, 5)))
            self.data_rate_label_num.setText(str(round(self._media_client.stat_data_rate)))
            self.total_bytes_label_num.setText(str(round(self._media_client.stat_total_bytes)))
            self.start_time_label_num.setText(str(round(self._media_client.stat_start_time)))
            self.total_play_time_label_num.setText(str(round(self._media_client.stat_total_play_time)))
            self.fraction_lost_label_num.setText(str(round(self._media_client.stat_fraction_lost)))
            self.cumulative_lost_label_num.setText(str(round(self._media_client.stat_cumulative_lost)))
            self.expected_sequence_number_label_num.setText(str(round(self._media_client.stat_expected_sequence_number)))
            self.high_sequence_number_label_num.setText(str(round(self._media_client.stat_high_sequence_number)))
        self.counter += 1

    def update_image(self):
        self.update_information()
        if not self._media_client.is_receiving_rtp:
            return
        frame = self._media_client.get_next_frame()
        if frame is not None:
            pix = QPixmap.fromImage(ImageQt(frame[0]).copy())
            self.video_player.setPixmap(pix)

    def handle_setup(self):
        self._media_client.establish_rtsp_connection()
        self._media_client.send_setup_request()
        self.setup_button.setEnabled(False)
        self.play_button.setEnabled(True)
        self.tear_button.setEnabled(True)
        self._update_image_timer.start(1000//VideoStream.DEFAULT_FPS)

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
