import logging
import os
import random
import socket
import time
import sys
from func_timeout import func_timeout

HOST = "127.0.0.2"  # TODO Change this so all hosts can work
PORT = 8080
SEGMENT_ID_SIZE = 6  # 6 bites for the segment ID according to subject
SEGMENT_SIZE = 1500 - SEGMENT_ID_SIZE
RTT = 0.005
TIMEOUT = 0.01

if "remote" in sys.argv:
    import pydevd_pycharm

    pydevd_pycharm.settrace('192.168.2.1', port=6969, stdoutToServer=True, stderrToServer=True)


class BaseServer:
    def __init__(self) -> None:
        self.ServerSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)  # create UDP socket
        self.ServerSocket.bind((HOST, PORT))  # bind the socket to an address

        self.NewPort = random.randint(1000, 9999)
        self.clientAddr = None
        self.clientPort = None

        self.DataSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)  # create UDP socket
        self.DataSocket.bind((HOST, self.NewPort))  # bind the socket to an address
        logging.info("Socket binded with success")

        self.startTime = None
        self.endTime = None
        self.fileName = None
        self.DroppedSegmentCount = 0

        logging.info(f"Server listening at {PORT} 🙉")

    def send(self, port, data):
        if type(data) == str:
            self.ServerSocket.sendto(str.encode(data), (self.clientAddr, port))
        else:
            self.ServerSocket.sendto(data, (self.clientAddr, port))

    def rcv(self, Socket, bufferSize):
        return Socket.recvfrom(bufferSize)

    def setTimeout(self):
        self.ServerSocket.settimeout(TIMEOUT)
        self.DataSocket.settimeout(TIMEOUT)

    def handshake(self):
        handshakeBuffer = 12
        message, address = self.rcv(self.ServerSocket, handshakeBuffer)
        self.clientAddr, self.clientPort = address
        if b"SYN" in message:
            logging.debug(f"SYN Received from {address}")
        else:
            raise ConnectionRefusedError

        self.send(self.clientPort, f"SYN-ACK{self.NewPort}")
        logging.debug(f"SYN-ACK sent 🚀")

        message, address = self.rcv(self.ServerSocket, handshakeBuffer)
        if b"ACK" in message:
            logging.info(f"handshake with {address} achieved 🤝")
            self.setTimeout()
        else:
            raise ConnectionRefusedError

    def _getSegments(self, data):
        """return: list of segments"""
        return [str((x // SEGMENT_SIZE) + 1).zfill(SEGMENT_ID_SIZE).encode() + data[x:x + SEGMENT_SIZE] for x in
                range(0, len(data), SEGMENT_SIZE)]

    def ackHandler(self):
        # check for ACK
        rcvACK, _ = self.rcv(self.ServerSocket, 10)
        # logging.debug(f"received ACK from client: {rcvACK.decode()}")

        return int(rcvACK.decode()[3:9])

    def writer(self, Segments):
        # logging.info("sending all segments")
        for Segment in Segments:
            self.send(self.clientPort, Segment)

    def reader(self, Segments):
        LastACK = 0
        ReceivedACKs = []
        for _ in range(len(Segments)):
            try:
                ReceivedACK = func_timeout(RTT, self.ackHandler)
                if ReceivedACK == len(Segments):
                    break
                ReceivedACKs.append(ReceivedACK)
            except:
                logging.warning(f"timed out ⏲")
                break

        if ReceivedACKs[-1] == ReceivedACKs[-2]:
            logging.warning(f"dropped segment {ReceivedACKs[-1] + 1} 😭")
            self.send(self.clientPort, Segments[ReceivedACKs[-1]])

    def _preSendFile(self):
        message, _ = self.rcv(self.DataSocket, 15)
        self.fileName = message.decode()[:-1]
        logging.info(f"file name received {self.fileName}")

        if not os.path.exists(self.fileName):
            raise FileNotFoundError("file requested couldn't be found")

        with open(self.fileName, "rb") as f:
            file = f.read()
        logging.info(f"file loaded 🥳")

        segments = self._getSegments(file)  # segment the files
        logging.info(f"File segmented into {len(segments)} segments 🎉")

        self.startTime = time.time()

        return segments

    def _postSendFile(self):
        self.send(self.clientPort, "FIN")
        self.endTime = time.time()
        logging.info(f"File {self.fileName} send with success 🎉")
        logging.info(f"Total time to send file {int((self.endTime - self.startTime) * 1000)} ms 🐢")
        rate = "{:.2f}".format(
            round(os.stat(self.fileName).st_size / int((self.endTime - self.startTime) * (10 ** 6)), 2))
        logging.info(f"Number of dropped segments {self.DroppedSegmentCount}")
        logging.info(f"Transmission rate: {rate} MBps ")

    def engine(self, *args, **kwargs):
        raise NotImplementedError("Base server can't be used on it's own, you need inherit it into your own subclass "
                                  "and provide an engine to handle sending segments and receiving ACKs")

    def sendFile(self):
        segments = self._preSendFile()

        self.engine(segments)

        self._postSendFile()

    def writeLogs(self, Name, Logs):
        with open(Name + ".log", "w") as f:
            for Log in Logs:
                f.write(str(Log*1000) + "\n")
        logging.debug(f"wrote ✍️  logs onto {Name}.log")

    def checkFile(self):
        FilePath1 = self.fileName
        FilePath2 = f"../clients/copy_{self.fileName}"

        with open(FilePath1, "rb") as f:
            File1 = f.read()

        with open(FilePath2, "rb") as f:
            File2 = f.read()

        if len(File1) != len(File2):
            logging.warning(f"Different file sizes: original {len(File1)} copy: {len(File2)}")
            logging.warning(f"missing bites {len(File1) - len(File2)}")

        for index in range(len(File1)):
            if File1[index] != File2[index]:
                logging.warning(f"First difference at segment {index // 15000}")
                break
            if index == len(File1) - 1:
                logging.info("No difference, files are identical 🥳")

