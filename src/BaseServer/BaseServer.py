import logging
import os
import random
import socket
import time
from abc import abstractmethod
import argparse
import threading


class BaseServer:
    """
    An abstract class with useful methods to create servers for the multiple clients
    to use it you will have to implement an engine that sends segment to client and then create an instance of it and
    use the self.run() method
    """
    HOST = ""  # empty string = all available interfaces in the host machine (Advised)
    PORT = 8080
    SEGMENT_ID_SIZE = 6  # 6 bites for the segment ID according to subject
    SEGMENT_SIZE = 1500 - SEGMENT_ID_SIZE
    RTT = 0.005
    TIMEOUT = 0.007
    MAX_RTT_COUNT = 10
    isTraining = False
    RTTs = [RTT]

    def __init__(self) -> None:
        self.ServerSocket = None  # public socket
        self.DataSocket = None  # private socket (dedicated client port)

        self.DataPort = None
        self.clientAddr = None  # these will be set on connection with client
        self.clientPort = None

        self.startTime = None
        self.endTime = None
        self.fileName = None
        self.DroppedSegmentCount = 0
        self.Segments = []

    def initServerSockets(self):
        """
        initialize the sockets
        """
        self.ServerSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)  # create UDP socket
        self.ServerSocket.bind((self.HOST, self.PORT))  # bind the socket to an address
        logging.info(f"Server listening at {self.HOST} public port {self.PORT} 🙉")

    def initDataSocket(self):
        while True:  # to assure that socket is binded and if the random port is already in use switch to another ome
            try:
                self.DataPort = random.randint(1000, 9999)
                self.DataSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)  # create UDP socket
                self.DataSocket.bind((self.HOST, self.DataPort))  # bind the socket to an address
                logging.info(f"Server listening at {self.HOST} private port {self.DataPort} 🙉")
                break
            except OSError:  # port already in use
                logging.warning(f"Port {self.DataPort} already in use, switch to another port")

    def closeDataSocket(self):
        self.DataSocket.close()

    def appendRtt(self, newRTT: int):
        self.RTTs.append(newRTT)
        if len(self.RTTs) >= self.MAX_RTT_COUNT:
            self.RTTs = self.RTTs[-self.MAX_RTT_COUNT:]

    def getMeanRTT(self) -> int:
        return (sum(self.RTTs) / len(self.RTTs)) * 1.2

    def send(self, port, data):
        """
        send to a port
        :param port:
        :param data: str or bytes
        :return:
        """
        if type(data) == str:
            self.ServerSocket.sendto(str.encode(data), (self.clientAddr, port))
        else:
            self.ServerSocket.sendto(data, (self.clientAddr, port))

    def rcv(self, Socket, bufferSize):
        """
        listen to a socket and receive a data from it
        :param Socket: socket that will listened to (ServerSocket for public port and DataSocket for private)
        :param bufferSize:
        :return: (bytes) data received from socket
        """
        return Socket.recvfrom(bufferSize)

    def sendSegment(self, index: int) -> None:
        """
        send a segment
        :param index: to be sent segment's index
        """
        self.DataSocket.sendto(self.Segments[index], (self.clientAddr, self.clientPort))

    def sendSegmentThread(self, index: int):
        """
        send a segment in a separate thread
        :param index: index of the segment that is going to be sent
        :return: The thread that os sending the segment
        """
        mSenderThread = threading.Thread(target=self.sendSegment, name=f"sender{index + 1}", args=(index,))
        mSenderThread.start()
        return mSenderThread

    def setTimeout(self):
        self.DataSocket.settimeout(self.TIMEOUT)

    def unsetTimeout(self):
        self.ServerSocket.settimeout(None)

    def connect(self):
        """
        listen for a SYN message on the public port
        """
        while True:
            message, address = self.rcv(self.ServerSocket, bufferSize=12)
            self.clientAddr, self.clientPort = address
            if b"SYN" in message:
                logging.debug(f"SYN Received from {address}")
                break
        self.handshake()

    def handshake(self):
        """
        handles the initial handshake with the client
        """
        self.initDataSocket()
        self.send(self.clientPort, f"SYN-ACK{self.DataPort}")  # sending data port
        logging.debug(f"SYN-ACK sent 🚀")

        message, address = self.rcv(self.ServerSocket, 12)
        if b"ACK" in message:
            logging.info(f"handshake with {address} achieved 🤝")
        else:
            logging.error(f"received message from client {message} expected ACK")
            raise ConnectionRefusedError

    def _getSegments(self, data):
        """
        :return: list of segments
        """
        self.Segments = [
            str((x // self.SEGMENT_SIZE) + 1).zfill(self.SEGMENT_ID_SIZE).encode() + data[x:x + self.SEGMENT_SIZE]
            for x in range(0, len(data), self.SEGMENT_SIZE)]
        return self.Segments

    def ackHandler(self, debug=True):
        """
        listen to the (it suppose to be private port) public port for ACK and parse it
        :param debug: debug logs, set to False to not get spammed
        :return: int received ACK
        :raises: ValueError if received data can't be parsed into an ACKXXXX
        """
        rcvACK, _ = self.rcv(self.DataSocket, 10)
        if debug:  # spams a lot
            logging.debug(f"received ACK from client: {rcvACK.decode()}")
        try:
            return int(rcvACK.decode()[3:9])
        except:
            print(rcvACK.decode())
            raise ValueError(rcvACK.decode())

    def writer(self, Start: int, End: int):
        """
        a launch a thread that will send all the Segments
        :param Segments: list of to be sent segments
        :return: None
        """
        if len(self.Segments) < End:
            Last = len(self.Segments)
        else:
            Last = End

        def massSender(_Start, _End):
            logging.debug(f"send segments {_Start + 1} => {_End}")
            for index in range(_Start, _End):
                self.sendSegment(index)

        # massSender(Start, End)
        threading.Thread(target=massSender, args=(Start, Last), name="writerThread").start()

    def reader(self, Segments):
        """
        DEPRECIATED
        :param Segments:
        :return:
        """
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
        """
        prepare for sending the file
        receive the file name and parse it then turn the file into segments
        """
        while True:
            message, _ = self.rcv(self.DataSocket, 15)  # receive filename from the data port
            if b"ACK" not in message:  # ignore trailing ACK from last conection
                break
        self.fileName = message.decode()[:-1]  # parse filename
        logging.info(f"file name received {self.fileName}")

        if self.isTraining:
            self.fileName = "src/10mb.jpg"

        if not os.path.exists(self.fileName):  # File requested doesn't exists
            raise FileNotFoundError(f"file {self.fileName} requested couldn't be found")

        with open(self.fileName, "rb") as f:
            file = f.read()
        logging.info(f"file loaded 🥳")

        segments = self._getSegments(file)  # segment the files
        logging.info(f"File segmented into {len(segments)} segments 🎉")

        self.setTimeout()  # start setting timeouts on the received ACK
        self.startTime = time.time()

        return segments

    def _postSendFile(self):
        """
        send to client FIN and computes transmission rates and other valuable data
        :return:
        """
        self.send(self.clientPort, "FIN")
        self.endTime = time.time()
        TotalTime = int((self.endTime - self.startTime) * 1000)
        logging.info(f"File {self.fileName} send with success 🎉")
        logging.info(f"Total time to send file {TotalTime} ms 🐢")
        rate = "{:.2f}".format(
            round(os.stat(self.fileName).st_size / int((self.endTime - self.startTime) * (10 ** 6)), 2))
        logging.info(f"Number of dropped segments {self.DroppedSegmentCount}")
        logging.info(f"Transmission rate of {type(self).__name__}: {rate} MBps ")
        return rate, TotalTime

    @abstractmethod
    def engine(self, *args, **kwargs):
        raise NotImplementedError("Base server can't be used on it's own, you need inherit it into your own subclass "
                                  "and provide an engine to handle sending segments and receiving ACKs")

    def sendFile(self):
        """
        well it's in the name, send the file
        :return:
        """
        segments = self._preSendFile()

        self.engine(segments)

        return self._postSendFile()

    def writeLogs(self, Name, Logs):
        """
        DEBUG AND RESEARCH PURPOSES
        write logs into a file to be ploted by another script
        """
        if self.isTraining:
            return
        with open("logs/" + Name + ".log", "w") as f:
            for Log in Logs:
                f.write(str(Log) + "\n")
        logging.debug(f"wrote ✍️  logs onto {Name}.log")

    def checkFile(self):
        """
        DEBUG AND RESEARCH PURPOSES
        check if the file received and sent are the same
        """
        FilePath1 = self.fileName
        FilePath2 = f"../clients/copy_{self.fileName}"
        if self.isTraining:
            FilePath2 = "clients/copy_10mb.jpg"

        with open(FilePath1, "rb") as f:
            File1 = f.read()

        with open(FilePath2, "rb") as f:
            File2 = f.read()

        if len(File1) != len(File2):
            logging.warning(f"Different file sizes: original {len(File1)} copy: {len(File2)}")
            logging.warning(f"missing bites {len(File1) - len(File2)}")
            return False

        for index in range(len(File1)):
            if File1[index] != File2[index]:
                logging.warning(f"First difference at segment {index // 15000}")
                return False
            if index == len(File1) - 1:
                logging.info("No difference, files are identical 🥳")
                return True

    def train(self):
        """
        RESEARCH PURPOSES
        test the current config and returns performance's  stats
        """
        self.initServerSockets()
        self.connect()
        Rate, TotalTime = self.sendFile()
        # isCorrect = self.checkFile()
        self.unsetTimeout()
        return Rate, TotalTime, self.DroppedSegmentCount, True

    def clientHandler(self):
        """
        handles the connection with a single client
        this will be the target function of a separate process to solve the 3rd scenario (multiclient)
        """
        self.sendFile()
        self.closeDataSocket()

    def run(self):
        """
        runs the server
        :return:
        """
        Parser = argparse.ArgumentParser()
        Parser.add_argument("-v", "--verbose", action="store_true")
        Parser.add_argument("-p", "--port", type=int, default=self.PORT)
        Parser.add_argument("-t", "--timeout", type=int, default=self.TIMEOUT)
        Parser.add_argument("--host", type=str, default="")
        Parser.add_argument("--remote_debugger", type=str)
        Parser.add_argument("-q", "--quite", type=int, help="don't write log files")
        Parser.add_argument("--verify", action="store_true")

        Args = Parser.parse_args()

        logging.basicConfig(format='%(asctime)s--[%(levelname)s]: %(message)s',
                            level=logging.DEBUG if Args.verbose else logging.INFO)
        self.TIMEOUT = Args.timeout
        self.PORT = Args.port
        self.HOST = Args.host

        self.initServerSockets()

        if Args.remote_debugger:
            import pydevd_pycharm
            pydevd_pycharm.settrace(Args.remote_debugger, port=4200, stdoutToServer=True, stderrToServer=True)

        while True:
            self.connect()
            self.clientHandler()
            if Args.verify:
                self.checkFile()
