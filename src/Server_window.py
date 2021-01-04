"""
out of 8100 packet client 1 dropped 547
6 % chance of dropping a packet
"""
import logging
import socket
import sys
import time

from BaseServer import BaseServer, isDropped


class WindowServer(BaseServer):
    WINDOW_SIZE = 80  # on average we lose 1 segment per 100 segments
    TIMEOUT = 0.006
    RESEND_THRESHOLD = 20
    rcvLogs = []  # Research purposes
    ACKed = []  # we noticed that some acked segments get received at once making the server think they were lost
    SegLog = [1] * 14000  # Research Purposes

    def engine(self, Segments):
        Index = 0
        CycleLogs = []
        while Index < len(Segments):
            RemainingSegmentsCount = len(Segments[Index:])

            CurrentWindow = self.WINDOW_SIZE
            if RemainingSegmentsCount < self.WINDOW_SIZE:
                CurrentWindow = RemainingSegmentsCount

            CycleStart = time.time()

            self.writer(Index, Index + CurrentWindow)  # sending all segments in all Current window
            self.windowInspector(Segments, Index, Index + CurrentWindow)
            logging.debug(f"received all ACKs {Index + 1} => {Index + CurrentWindow}")

            CycleEnd = time.time()
            CycleLogs.append(CycleEnd - CycleStart)

            Index += CurrentWindow
        # self.writeLogs("Cycle", CycleLogs)
        # self.writeLogs("Ack_rcv_time", self.rcvLogs)
        # self.writeLogs("segments", self.SegLog)

    def windowInspector(self, Segments, StartIndex, EndIndex):
        """
        receives all the ACKs and resend dropped segments
        :param Segments: all the segments
        :param StartIndex: index of the first segment sent in the current window
        :param EndIndex: index of the last segment sent in the current window
        :return: True if no segment was dropped False otherwise
        """
        ACKd = [StartIndex]  # list of segments that were ACK'ed
        ReceivedACK = StartIndex  # last received ACK
        ResentACK = {}  # list of segments that were resent
        isDropped = False

        while True:
            try:
                ReceivedACK = self.ackHandler(True)

                if ReceivedACK == EndIndex:  # received last expected ACK in the Window
                    return isDropped

                if not StartIndex <= ReceivedACK <= EndIndex:
                    continue  # we receive trailing ack from previous window those shall be ignored

                if ReceivedACK in ACKd:  # received an ACK twice that wasn't resent
                    if ReceivedACK not in ResentACK:
                        logging.warning(f"segment {ReceivedACK + 1} was dropped 😞 resending it...")
                        ResentACK[ReceivedACK] = 1
                        self.sendSegmentThread(ReceivedACK)
                        self.DroppedSegmentCount += 1
                        isDropped = True
                        # self.SegLog[ReceivedACK] = 0
                    else:
                        ResentACK[ReceivedACK] += 1
                        if self.RESEND_THRESHOLD < ResentACK[ReceivedACK]:
                            ResentACK.pop(ReceivedACK)

                ACKd.append(ReceivedACK)

            except socket.timeout:
                logging.warning(f"timed out ⏰, resending {max(ACKd) + 1}...")
                self.sendSegmentThread(max(ACKd))
                """
                if ReceivedACK not in ResentACK:
                    ResentACK[ReceivedACK] = 1
                    self.sendSegmentThread(ReceivedACK)
                    self.DroppedSegmentCount += 1
                    #self.SegLog[ReceivedACK] = 0
                else:
                    ResentACK[ReceivedACK] += 1
                    if self.RESEND_THRESHOLD < ResentACK[ReceivedACK]:
                        ResentACK.pop(ReceivedACK)
                """


if __name__ == "__main__":
    server = WindowServer()
    server.run()
