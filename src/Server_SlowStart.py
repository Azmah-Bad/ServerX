"""
out of 8100 packet client 1 dropped 547
6 % chance of dropping a packet
"""

import logging
import time
import socket
from Server_window import WindowServer

INITIAL_CWINDOW = 15


class SlowStartServer(WindowServer):
    TIMEOUT = 0.05

    def windowInspectorS2(self, Segments, StartIndex, EndIndex):
        """
        receives all the ACKs and resend dropped segments if a segment was dropped send the resend of the window
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
                        logging.warning(f"segment {ReceivedACK + 1} was dropped 😞 resending the tail of the window...")
                        for key in range(ReceivedACK, EndIndex):
                            ResentACK[key] = 1
                        self.writer(ReceivedACK, EndIndex)
                        self.DroppedSegmentCount += EndIndex - ReceivedACK
                        isDropped = True
                        # self.SegLog[ReceivedACK] = 0
                    else:
                        ResentACK[ReceivedACK] += 1
                        if self.RESEND_THRESHOLD < ResentACK[ReceivedACK]:
                            ResentACK.pop(ReceivedACK)

                ACKd.append(ReceivedACK)

            except socket.timeout:
                logging.warning(f"timed out ⏰, resending {max(ACKd) + 1}...")
                self.writer(ReceivedACK, EndIndex)


    def engine(self, Segments):
        Index = 0
        CWindow = INITIAL_CWINDOW  # Congestion Window
        CwndLogs = []
        CycleLogs = []

        while Index < len(Segments):
            start = time.time()
            remainingSegments = len(Segments[Index:])
            if remainingSegments < CWindow:
                CWindow = remainingSegments

            FlightSize = range(Index, Index + CWindow)

            self.writer(Index, Index + CWindow)
            logging.info(f"sending segments {Index} => {Index + CWindow},Cwnd of {CWindow}")
            isDropped = self.windowInspectorS2(self.Segments, Index + 1, Index + CWindow)
            # CWindow = int(CWindow / 2) if isDropped else int(CWindow + 2)
            logging.debug(f"CWindow: {CWindow}")
            CwndLogs.append(CWindow)
            CycleLogs.append(time.time() - start)
            Index += len(FlightSize)

        self.writeLogs("Cwnd", CwndLogs)
        self.writeLogs("Cycle", CycleLogs)


if __name__ == "__main__":
    server = SlowStartServer()
    server.run()
