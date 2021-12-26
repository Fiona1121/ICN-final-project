import argparse
from server.server import Server


if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument("-i", "--IPADDRESS", type=str, default="127.0.0.1", help="The RTSP server IP address")
    parser.add_argument("-p", "--PORT", type=int, default=5540, help="The port number")
    parser.add_argument("-s", "--SESSIONID", type=str, default="123456", help="Session IDServer session ID")
    
    args = parser.parse_args()
    # print(args.IPADDRESS, args.PORT, args.SESSIONID)

    while True:
        server = Server(args.IPADDRESS, args.PORT, args.SESSIONID)
        try:
            server.setup()
            server.handle_rtsp_requests()
        except ConnectionError as e:
            server.server_state = server.STATE.TEARDOWN
            print(f"Connection reset: {e}")
