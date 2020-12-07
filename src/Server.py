"""
out of 8100 packet client 1 dropped 547
6 % chance of dropping a packet
"""

# DEBUG
# import pydevd_pycharm
# pydevd_pycharm.settrace('192.168.2.1', port=6969, stdoutToServer=True, stderrToServer=True)

import socket
import logging
import random
import os
import time
import sys
from BaseServer import BaseServer


HOST = "127.0.0.2"  # TODO Change this so all hosts can work
if len(sys.argv) == 2:
    HOST = sys.argv[1]

PORT = 8080
SEGMENT_ID_SIZE = 6  # 6 bites for the segment ID according to subject
SEGMENT_SIZE = 1500 - SEGMENT_ID_SIZE
RTT = 0.015


class Server(BaseServer):
    def __init__(self) -> None:
        self.ServerSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)  # create UDP socket
        self.ServerSocket.bind((HOST, PORT))  # bind the socket to an address
        logging.info("Socket binded with success")

        self.NewPort = random.randint(1000, 9999)
        self.clientPort = None
        self.DataSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)  # create UDP socket
        self.DataSocket.bind((HOST, self.NewPort))  # bind the socket to an address

        logging.info(f"Server listening at {PORT}")
    def sendFileNoSlowStart(self):
        filenameBuffer = 15
        message, _ = self.rcv(self.DataSocket, filenameBuffer)
        filename = message.decode()[:-1]
        logging.info(f"file name received {filename}")

        if not os.path.exists(filename):
            raise FileNotFoundError("file requested couldn't be found")

        with open(filename, "rb") as f:
            file = f.read()
        logging.info(f"file loaded 🥳")

        segments = self._getSegments(file)  # segment the files
        logging.info(f"File segmented into {len(file) // SEGMENT_SIZE} segments")

        start = time.time()
        self.writer(segments)
        mid = time.time()
        self.reader(segments)
        end = time.time()

        self.send(self.clientPort, "FIN")
        logging.info("File send with success 🎉")
        logging.info(f"Total time {int((end - start) * 1000)} ms ")
        logging.info(f"Total time to send file {int((mid - start) * 1000)} ms ")
        logging.info(f"Total time to rcv acks {int((end - mid) * 1000)} ms ")
        rate = "{:.2f}".format(round(os.stat(filename).st_size / int((end - start) * (10 ** 6)), 2))
        logging.info(f"Transmission rate: {rate} MBps")


if __name__ == "__main__":
    logging.basicConfig(format='%(asctime)s--[%(levelname)s]: %(message)s',
                        level=logging.DEBUG)

    server = Server()
    server.handshake()
    server.sendFileNoSlowStart()
