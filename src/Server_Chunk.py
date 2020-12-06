"""
out of 8100 packet client 1 dropped 547
6 % chance of dropping a packet
"""
import logging
import socket
import time

from BaseServer import BaseServer

WINDOW_SIZE = 20  # on average we lose 1 segment per 20 segments
DroppedSegmentCount = 0


class Server(BaseServer):
    rcvLogs = []
    
    def ackHandler(self):
        start = time.time()
        value = super().ackHandler()
        end = time.time()
        self.rcvLogs.append(end - start)
        return value
    
    def engine(self, Segments):
        Index = 0
        CycleLogs = []
        while Index < len(Segments):
            RemainingSegmentsCount = len(Segments[Index:])

            CurrentWindow = WINDOW_SIZE
            if RemainingSegmentsCount < WINDOW_SIZE:
                CurrentWindow = RemainingSegmentsCount

            logging.debug(f"send segments {Index} => {Index + CurrentWindow}")

            CycleStart = time.time()

            self.writer(Segments[Index:Index + CurrentWindow])  # sending all segments in all Current window
            self.checker(Segments, Index, Index + CurrentWindow)

            CycleEnd = time.time()
            CycleLogs.append(CycleEnd - CycleStart)

            Index += CurrentWindow
        self.writeLogs("Cycle",CycleLogs)
        self.writeLogs("Ack_rcv_time", self.rcvLogs)

    def checker(self, Segments, StartIndex, EndIndex):
        # StartIndex += 1  # to match the ACKs
        # EndIndex += 1
        LastACK = 0

        while LastACK != EndIndex:
            try:
                ReceivedACK = self.ackHandler()
                if ReceivedACK == LastACK:
                    logging.warning(f"dropped {LastACK} segment 😭")
                    self.DroppedSegmentCount += 1
                    self.send(self.clientPort, Segments[LastACK])
                LastACK = ReceivedACK
            except socket.timeout:
                logging.warning(f"timed out ⏰, dropped segment {LastACK}")
                self.send(self.clientPort, Segments[LastACK])
                self.DroppedSegmentCount += 1

        logging.debug(f"received all ACKs {StartIndex} => {EndIndex}")


if __name__ == "__main__":
    logging.basicConfig(format='%(asctime)s--[%(levelname)s]: %(message)s',
                        level=logging.DEBUG)

    server = Server()
    server.handshake()
    server.sendFile()
    server.checkFile()
