import logging
import os
import random
import socket
import time
from abc import abstractmethod
import argparse


class BaseServer:
    HOST = ""
    PORT = 8080
    SEGMENT_ID_SIZE = 6  # 6 bites for the segment ID according to subject
    SEGMENT_SIZE = 1500 - SEGMENT_ID_SIZE
    RTT = 0.005
    TIMEOUT = 0.01

    def __init__(self) -> None:
        self.ServerSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)  # create UDP socket
        self.ServerSocket.bind((self.HOST, self.PORT))  # bind the socket to an address

        self.NewPort = random.randint(1000, 9999)
        self.clientAddr = None
        self.clientPort = None

        self.DataSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)  # create UDP socket
        self.DataSocket.bind((self.HOST, self.NewPort))  # bind the socket to an address
        logging.info("Socket binded with success")

        self.startTime = None
        self.endTime = None
        self.fileName = None
        self.DroppedSegmentCount = 0

        logging.info(f"Server listening at {self.PORT} 🙉")

    def send(self, port, data):
        if type(data) == str:
            self.ServerSocket.sendto(str.encode(data), (self.clientAddr, port))
        else:
            self.ServerSocket.sendto(data, (self.clientAddr, port))

    def rcv(self, Socket, bufferSize):
        return Socket.recvfrom(bufferSize)

    def setTimeout(self):
        self.ServerSocket.settimeout(self.TIMEOUT)
        self.DataSocket.settimeout(self.TIMEOUT)

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
        return [str((x // self.SEGMENT_SIZE) + 1).zfill(self.SEGMENT_ID_SIZE).encode() + data[x:x + self.SEGMENT_SIZE]
                for x in
                range(0, len(data), self.SEGMENT_SIZE)]

    def ackHandler(self, debug=True):
        # check for ACK
        rcvACK, _ = self.rcv(self.ServerSocket, 10)
        if debug:
            logging.debug(f"received ACK from client: {rcvACK.decode()}")

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
                ReceivedACK = self.ackHandler()
                if ReceivedACK == len(Segments):
                    break
                ReceivedACKs.append(ReceivedACK)
            except socket.timeout:
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
        TotalTime = int((self.endTime - self.startTime) * 1000)
        logging.info(f"File {self.fileName} send with success 🎉")
        logging.info(f"Total time to send file {TotalTime} ms 🐢")
        rate = "{:.2f}".format(
            round(os.stat(self.fileName).st_size / int((self.endTime - self.startTime) * (10 ** 6)), 2))
        logging.info(f"Number of dropped segments {self.DroppedSegmentCount}")
        logging.info(f"Transmission rate: {rate} MBps ")
        return rate, TotalTime, self.DroppedSegmentCount

    @abstractmethod
    def engine(self, *args, **kwargs):
        raise NotImplementedError("Base server can't be used on it's own, you need inherit it into your own subclass "
                                  "and provide an engine to handle sending segments and receiving ACKs")

    def sendFile(self):
        segments = self._preSendFile()

        self.engine(segments)

        return self._postSendFile()

    def writeLogs(self, Name, Logs):
        with open("logs/" + Name + ".log", "w") as f:
            for Log in Logs:
                f.write(str(Log * 1000) + "\n")
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

    def run(self):
        Parser = argparse.ArgumentParser()
        Parser.add_argument("-v", "--verbose", type=int)
        Parser.add_argument("-p", "--port", type=int, default=self.PORT)
        Parser.add_argument("-t", "--timeout", type=int, default=self.TIMEOUT)
        Parser.add_argument("-h", "--host", type=str, default="")
        Parser.add_argument("--remote_debugger", type=str)
        Parser.add_argument("-q", "--quite", type=int, help="don't write log files")

        Args = Parser.parse_args()

        logging.basicConfig(format='%(asctime)s--[%(levelname)s]: %(message)s',
                            level=logging.DEBUG if Args.verbose else logging.DEBUG)
        self.TIMEOUT = Args.timeout
        self.PORT = Args.PORT
        self.HOST = Args.host

        if Args.remote_debugger:
            import pydevd_pycharm
            pydevd_pycharm.settrace(Args.remote_debugger, port=6969, stdoutToServer=True, stderrToServer=True)

        self.ackHandler()
        self.sendFile()
        self.checkFile()
