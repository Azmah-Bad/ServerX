"""
out of 8100 packet client 1 dropped 547
6 % chance of dropping a packet
"""
import logging
import socket
import sys
import time

from .BaseServer import BaseServer, isDropped


class Server(BaseServer):
    WINDOW_SIZE = 60  # on average we lose 1 segment per 100 segments
    rcvLogs = []
    ACKed = []  # we noticed that some acked segments get received at once making the server think they were lost

    # def ackHandler(self, debug=True):
    #     start = time.time()
    #     value = super().ackHandler(debug)
    #     end = time.time()
    #     self.rcvLogs.append(end - start)
    #     return value

    def engine(self, Segments):
        Index = 0
        CycleLogs = []
        while Index < len(Segments):
            RemainingSegmentsCount = len(Segments[Index:])

            CurrentWindow = self.WINDOW_SIZE
            if RemainingSegmentsCount < self.WINDOW_SIZE:
                CurrentWindow = RemainingSegmentsCount

            logging.debug(f"send segments {Index + 1} => {Index + CurrentWindow}")

            CycleStart = time.time()

            self.writer(Segments[Index:Index + CurrentWindow])  # sending all segments in all Current window
            self.windowChecker(Segments, Index, Index + CurrentWindow)
            logging.debug(f"received all ACKs {Index + 1} => {Index + CurrentWindow}")

            CycleEnd = time.time()
            CycleLogs.append(CycleEnd - CycleStart)

            Index += CurrentWindow
        self.writeLogs("Cycle", CycleLogs)
        self.writeLogs("Ack_rcv_time", self.rcvLogs)

    def checker(self, Segments, StartIndex, EndIndex):
        ReceivedACK = 0
        while ReceivedACK != EndIndex:
            try:
                ReceivedACK = self.ackHandler()
                if ReceivedACK in self.ACKed:
                    logging.warning(f"dropped {ReceivedACK + 1} segment 😭")
                    self.DroppedSegmentCount += 1
                    # flush the socket
                    for _ in range(self.WINDOW_SIZE - ReceivedACK):
                        self.ackHandler()
                    self.send(self.clientPort, Segments[ReceivedACK])
                    logging.debug(f"sending back segment {ReceivedACK + 1}")
                self.ACKed.append(ReceivedACK)
            except socket.timeout:
                logging.warning(f"timed out ⏰, dropped segment {ReceivedACK}")
                self.send(self.clientPort, Segments[ReceivedACK])
                self.DroppedSegmentCount += 1

    def windowChecker(self, Segments, StartIndex, EndIndex):
        ACKs = []
        Index = 0
        isMultipleACKs = False
        TimeoutCountdown = 3
        while Index < self.WINDOW_SIZE:
            try:
                ACKs.append(self.ackHandler(True))
                if EndIndex in ACKs:
                    return  # EndIndex already in list

                if isDropped(ACKs) and not isMultipleACKs:
                    Index += 2
                    isMultipleACKs = True
                    logging.warning(f"a segment has been dropped, skipping last ACK listen")

                Index += 1

            except socket.timeout:
                if ACKs:
                    logging.warning(f"timed out ⏰, dropped segment {ACKs[-1] + 1}")
                    Index += 1
                    TimeoutCountdown -= 1
                    if TimeoutCountdown == 0:
                        break
                    pass

        for Ack in ACKs:
            if ACKs.count(Ack) != 1:  # Ack was dropped
                logging.warning(f"dropped segment {Ack + 1} 😭")
                toBeResent = Ack
                isRecovered = False
                while not isRecovered:
                    self.send(self.clientPort, Segments[toBeResent])
                    self.DroppedSegmentCount += 1
                    try:
                        while True:
                            ReceivedACK = self.ackHandler(True)
                            if ReceivedACK == EndIndex:
                                isRecovered = True
                            else:
                                toBeResent = ReceivedACK

                    except socket.timeout:
                        pass
                break


if __name__ == "__main__":
    server = Server()
    server.run()
