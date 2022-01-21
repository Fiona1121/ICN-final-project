from PyQt5.QtWidgets import QApplication
import os

from client.client_gui import ClientWindow


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 5:
        print(
            f"Usage: {sys.argv[0].split('/')[-1]} <file name> <host address> <host port> <RTP port>"
        )
        exit(-1)

    file_name, host_address, host_port, rtp_port = (*sys.argv[1:],)

    try:
        host_port = int(host_port)
        rtp_port = int(rtp_port)
    except ValueError:
        raise ValueError("port values should be integer")
    except ConnectionRefusedError:
        raise ValueError("failed to connect server")

    app = QApplication(sys.argv)
    if os.path.isfile(file_name):
        client = ClientWindow(file_name, host_address, host_port, rtp_port)
    else:
        client = ClientWindow(
            file_name, host_address, host_port, rtp_port, add_obj_detect=False
        )
    client.resize(400, 300)
    client.show()
    sys.exit(app.exec_())
