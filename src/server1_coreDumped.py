"""
out of 8100 packet client 1 dropped 547
6 % chance of dropping a packet
"""
import logging
import socket
import time
from BaseServer import BaseServer


class WindowServer(BaseServer):
    WINDOW_SIZE = 80  # on average we lose 1 segment per 100 segments
    TIMEOUT = 0.006
    RESEND_THRESHOLD = 40
    rcvLogs = []  # Research purposes
    ACKed = []  # we noticed that some acked segments get received at once making the server think they were lost
    SegLog = [1] * 227  # Research Purposes

    def engine(self, Segments):
        Index = 0
        CycleLogs = []
        CurrentWindow = self.WINDOW_SIZE

        while Index < len(Segments):
            RemainingSegmentsCount = len(Segments) - Index

            if RemainingSegmentsCount < self.WINDOW_SIZE:
                CurrentWindow = RemainingSegmentsCount

            CycleStart = time.time()

            self.writer(Index, Index + CurrentWindow)  # sending all segments in all Current window
            isDropped = self.windowInspector(Segments, Index, Index + CurrentWindow)
            logging.debug(f"received all ACKs {Index + 1} => {Index + CurrentWindow}")

            Index += CurrentWindow
            CurrentWindow = int(self.WINDOW_SIZE) if isDropped else int(CurrentWindow * 1.5)

            CycleEnd = time.time()
            CycleLogs.append(CycleEnd - CycleStart)
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
        ACKd = []  # list of segments that were ACK'ed
        ResentACK = {}  # list of segments that were resent
        isDropped = False

        while True:
            try:
                rttStart = time.time()
                ReceivedACK = self.ackHandler(True)
                rttEnd = time.time()
                self.appendRtt(rttEnd - rttStart)
                self.setTimeout(self.getMeanRTT())

                if ReceivedACK == EndIndex:  # received last expected ACK in the Window
                    return isDropped

                if not StartIndex <= ReceivedACK <= EndIndex:
                    continue  # we receive trailing ack from previous window those shall be ignored

                if ACKd.count(ReceivedACK) % self.RESEND_THRESHOLD == 1 and ReceivedACK + 1 not in ACKd:  # received an ACK twice that wasn't resent
                    logging.debug(f"segment {ReceivedACK + 1} was dropped 😞 resending it...")
                    ResentACK[ReceivedACK] = 1
                    self.sendSegmentThread(ReceivedACK)
                    self.DroppedSegmentCount += 1
                    isDropped = True

                ACKd.append(ReceivedACK)

            except socket.timeout:
                if ACKd:
                    toBeResent = max(ACKd)
                    if toBeResent not in ResentACK:
                        logging.debug(f"timed out ⏰, resending {toBeResent + 1}...")
                        self.sendSegmentThread(max(ACKd))
                        ResentACK[toBeResent] = 1
                    else:
                        ResentACK[toBeResent] += 1
                        if ResentACK[toBeResent] == 20:
                            ResentACK.pop(max(ACKd))


if __name__ == "__main__":
    server = WindowServer()
    server.run()
