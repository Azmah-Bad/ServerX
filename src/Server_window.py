"""
out of 8100 packet client 1 dropped 547
6 % chance of dropping a packet
"""
import logging
import socket
import sys
import time

from .BaseServer import BaseServer


class WindowServer(BaseServer):
    WINDOW_SIZE = 75  # on average we lose 1 segment per 100 segments
    TIMEOUT = 0.006
    rcvLogs = []
    ACKed = []  # we noticed that some acked segments get received at once making the server think they were lost

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
            self.windowInspector(Segments, Index, Index + CurrentWindow)
            logging.debug(f"received all ACKs {Index + 1} => {Index + CurrentWindow}")

            CycleEnd = time.time()
            CycleLogs.append(CycleEnd - CycleStart)

            Index += CurrentWindow
        self.writeLogs("Cycle", CycleLogs)
        self.writeLogs("Ack_rcv_time", self.rcvLogs)

    def windowInspector(self, Segments, StartIndex, EndIndex):
        """
        receives all the ACKs and resend segments
        :param Segments: all the segments
        :param StartIndex: index of the first segment sent in the current window
        :param EndIndex: index of the last segment sent in the current window
        :return: None
        """
        ACKd = []
        ReceivedACK = StartIndex
        ResentACK = []
        
        while True:
            try:
                ReceivedACK = self.ackHandler(True)

                if ReceivedACK == EndIndex:  # received last expected ACK in the Window
                    break

                if ReceivedACK in ACKd and ReceivedACK not in ResentACK:  # received an ACK twice
                    logging.warning(f"segment {ReceivedACK + 1} was dropped 😞 resending it...")
                    ResentACK.append(ReceivedACK)
                    self.sendSegmentThread(ReceivedACK)
                    self.DroppedSegmentCount += 1

                ACKd.append(ReceivedACK)

            except socket.timeout:
                logging.warning(f"timed out ⏰, resending {ReceivedACK +1}...")
                # if ReceivedACK not in ResentACK:
                ResentACK.append(ReceivedACK)
                self.sendSegmentThread(ReceivedACK)
                self.DroppedSegmentCount += 1


if __name__ == "__main__":
    server = WindowServer()
    server.run()
