"""
out of 8100 packet client 1 dropped 547
6 % chance of dropping a packet
"""

import socket
import logging
import random
import os
import progressbar
import time
from func_timeout import func_timeout, FunctionTimedOut
import matplotlib.pyplot as plt
import sys

HOST = "127.0.0.2"  # TODO Change this so all hosts can work
if len(sys.argv) == 2:
    HOST = sys.argv[1]

PORT = 8080
SEGMENT_ID_SIZE = 6  # 6 bites for the segment ID according to subject
SEGMENT_SIZE = 1500 - SEGMENT_ID_SIZE
RTT = 0.015


class Server:
    def __init__(self) -> None:
        self.ServerSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)  # create UDP socket
        self.ServerSocket.bind((HOST, PORT))  # bind the socket to an address
        logging.info("Socket binded with success")

        self.NewPort = random.randint(1000, 9999)
        self.clientPort = None
        self.DataSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)  # create UDP socket
        self.DataSocket.bind((HOST, self.NewPort))  # bind the socket to an address

        logging.info(f"Server listening at {PORT}")

    def send(self, port, data):
        if type(data) == str:
            self.ServerSocket.sendto(str.encode(data), (HOST, port))
        else:
            self.ServerSocket.sendto(data, (HOST, port))

    def rcv(self, Socket, bufferSize):
        return Socket.recvfrom(bufferSize)

    def handshake(self):
        handshakeBuffer = 12
        message, address = self.rcv(self.ServerSocket, handshakeBuffer)
        self.clientPort = address[1]
        if b"SYN" in message:
            logging.info(f"SYN Received from {address}")
        else:
            raise ConnectionRefusedError

        self.send(self.clientPort, f"SYN-ACK{self.NewPort}")
        logging.info(f"SYN-ACK sent 🚀")

        message, address = self.rcv(self.ServerSocket, handshakeBuffer)
        if b"ACK" in message:
            logging.info(f"Connection with {address} achieved")
        else:
            raise ConnectionRefusedError

    def _getSegments(self, data):
        """return: list of segments"""
        return [str((x // SEGMENT_SIZE) + 1).zfill(SEGMENT_ID_SIZE).encode() + data[x:x + SEGMENT_SIZE] for x in
                range(0, len(data), SEGMENT_SIZE)]

    def sendFile(self):
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

        CWindow = 5  # Congestion Window
        rtts = []
        index = 0
        LastACK = 0
        CwndLogs = []
        widgets = [
            ' [', progressbar.Timer(), '] ',
            progressbar.Bar("=", "[", "]"),
            ' (', progressbar.ETA(), ') ',
        ]
        # with progressbar.ProgressBar(max_value=len(segments), redirect_stdout=True,widgets=widgets) as bar:
        while index < len(segments):
            CwndLogs.append(CWindow)
            remainingSegments = len(segments[index:])
            if remainingSegments < CWindow:
                CWindow = remainingSegments
            start = time.time()
            FlightSize = range(index, index + CWindow)

            CWindow = self.sendSegments2(FlightSize, segments, CWindow)

            logging.debug(f"CWindow: {CWindow}")
            index += len(FlightSize)
            end = time.time()
            rtts.append(end - start)
            # bar.update(index)
        self.send(self.clientPort, "FIN")
        logging.info("File send with success 🎉")
        logging.info(f"Estimated RTT {int((sum(rtts) / len(rtts)) * 1000)} ms")
        logging.info(f"Total time to send file {int(sum(rtts) * 1000)} ms ")
        rate = "{:.2f}".format(round(os.stat(filename).st_size / int(sum(rtts) * (10 ** 6)), 2))
        logging.info(f"Transmission rate: {rate} MBps")

        with open("Cwind.log", "w") as LogFile:
            LogFile.write("\n".join([str(Cwnd) for Cwnd in CwndLogs]))
        # plt.plot(CwndLogs)
        # plt.show()

    def sendSegments(self, FlightSize, segments, CWindow):
        ExpectedACKs = []
        for segID in FlightSize:
            self.send(self.clientPort, segments[segID])
            ExpectedACKs.append(segID + 1)
        logging.debug(f"sent segments {ExpectedACKs}")

        while ExpectedACKs:
            try:
                logging.debug(f"Expected ACK: {ExpectedACKs[0] + 1} => {ExpectedACKs[-1] + 1}")
                ReceivedACK = func_timeout(RTT, self.ackHandler)
                if ReceivedACK in ExpectedACKs:
                    for ack in range(min(ExpectedACKs), ReceivedACK + 1):
                        if ack in ExpectedACKs:
                            ExpectedACKs.remove(ack)
                            CWindow += 1
                else:
                    logging.debug(f"received trailing ACK {ReceivedACK}")
                    pass

            except FunctionTimedOut:  # dropped a segment
                logging.warning(f"segment {ExpectedACKs} dropped 😭")
                CWindow = 1  # reset the CWindow
                for droppedSegID in ExpectedACKs:  # TODO MAYBE only send the first dropped segment
                    self.send(self.clientPort, segments[droppedSegID - 1])  # resend the lost segment
                logging.debug(f"sending back {ExpectedACKs}")
        return CWindow

    def ackHandler(self):
        # check for ACK
        rcvACK, _ = self.rcv(self.ServerSocket, 10)
        logging.debug(f"received ACK from client: {rcvACK.decode()}")

        return int(rcvACK.decode()[3:9])

    def sendSegments2(self, FlightSize, segments, CWindow):
        LastACK = 0
        ReceivedACK = 0
        for segID in FlightSize:
            self.send(self.clientPort, segments[segID])

        ExpectedACK = FlightSize[-1] + 1
        logging.debug(f"sent segments {FlightSize[0] + 1} => {FlightSize[-1] + 1}")

        while not ReceivedACK > ExpectedACK:
            try:
                ReceivedACK = func_timeout(RTT, self.ackHandler)
                if ReceivedACK == LastACK:
                    logging.warning(f"Segment {LastACK + 1} dropped RIP 💀")
                    self.send(self.clientPort, segments[LastACK])
                    CWindow = 5
                # if ReceivedACK >= ExpectedACK:
                #     logging.debug(f"all segments were ACK'd 🤑")
                #     CWindow = CWindow * 2
                #     LastACK = ReceivedACK
                #     break
                LastACK = ReceivedACK
            except FunctionTimedOut:
                logging.warning(f"Segment {LastACK + 1} dropped RIP 💀 from timeout")
                self.send(self.clientPort, segments[LastACK])

                CWindow = 5  # reset the CWindow

        logging.debug(f"all segments were ACK'd 🤑")
        CWindow = CWindow * 2
        LastACK = ReceivedACK
        return CWindow

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

    def writer(self, Segments):
        logging.info("sending all segments")
        for Segment in Segments:
            self.send(self.clientPort, Segment)

    def reader(self, Segments):
        LastACK = 0
        ReceivedACKs = []
        for _ in range(len(Segments)):
            try:
                ReceivedACK = func_timeout(RTT, self.ackHandler)
                ReceivedACKs.append(ReceivedACK)
            except:
                logging.warning(f"timed out ⏲")
                break

        if ReceivedACKs[-1] == ReceivedACKs[-2]:
            logging.warning(f"dropped segment {ReceivedACKs[-1] + 1}")
            self.send(self.clientPort, Segments[ReceivedACKs[-1]])

    def sendFileIncrementally(self):
        filenameBuffer = 15
        message, _ = self.rcv(self.DataSocket, filenameBuffer)
        filename = message.decode()[:-1]
        logging.info(f"file name received {filename}")
        DropCount = 0

        if not os.path.exists(filename):
            raise FileNotFoundError("file requested couldn't be found")

        with open(filename, "rb") as f:
            file = f.read()
        logging.info(f"file loaded 🥳")

        segments = self._getSegments(file)  # segment the files
        logging.info(f"File segmented into {len(file) // SEGMENT_SIZE} segments")

        start = time.time()
        for index, segement in enumerate(segments):
            self.send(self.clientPort, segement)
            logging.debug(f"sending segement {index + 1}")
            while True:
                try:
                    logging.debug(f"waiting for segment {index + 1}")
                    ReceivedACK = func_timeout(2, self.ackHandler)
                    if ReceivedACK >= index + 1:
                        break
                    else:
                        self.send(self.clientPort, segement)
                        logging.warning(f"dropped segment {index + 1}")
                        DropCount += 1
                except FunctionTimedOut:
                    self.send(self.clientPort, segement)
                    logging.warning(f"timed out ⏲ dropped segment {index + 1}")
                    break
        end = time.time()

        self.send(self.clientPort, "FIN")
        logging.info("File send with success 🎉")
        logging.info(f"Total time {int((end - start) * 1000)} ms ")
        rate = "{:.2f}".format(round(os.stat(filename).st_size / int((end - start) * (10 ** 6)), 2))  # bytes
        logging.info(f"Transmission rate: {rate} MBps")
        logging.warning(f"Dropped {DropCount} segments  out of {len(segments)}")


if __name__ == "__main__":
    logging.basicConfig(format='%(asctime)s--[%(levelname)s]: %(message)s',
                        level=logging.DEBUG)

    server = Server()
    server.handshake()
    server.sendFileNoSlowStart()
