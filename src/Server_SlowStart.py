import logging
import time
import socket
from src import BaseServer

INITIAL_CWINDOW = 30


class SlowStartServer(BaseServer):
    RESEND_THRESHOLD = 40

    def engine(self, Segments):
        Index = 0
        CWindow = INITIAL_CWINDOW  # Congestion Window
        CwndLogs = []
        CycleLogs = []

        while Index < len(Segments):
            start = time.time()
            remainingSegments = len(Segments[Index:])
            if remainingSegments < CWindow:  # Last window
                CWindow = remainingSegments

            FlightSize = range(Index, Index + CWindow)

            self.writer(Index, Index + CWindow)
            logging.info(f"sending segments {Index} => {Index + CWindow},Cwnd of {CWindow}")
            isDropped = self.windowInspector(self.Segments, Index + 1, Index + CWindow)
            #CWindow = int(CWindow / 2) if isDropped else int(CWindow * 2)
            #if CWindow < 2:
            #    CWindow = 2
            logging.debug(f"CWindow: {CWindow}")
            CwndLogs.append(CWindow)
            CycleLogs.append(time.time() - start)
            Index += len(FlightSize)

        self.writeLogs("Cwnd", CwndLogs)
        self.writeLogs("Cycle", CycleLogs)

    def windowInspector(self, Segments, StartIndex, EndIndex):
        """
        receives all the ACKs and resend dropped segments if a segment was dropped send the resend of the window
        :param Segments: all the segments
        :param StartIndex: index of the first segment sent in the current window
        :param EndIndex: index of the last segment sent in the current window
        :return: True if no segment was dropped False otherwise
        """
        ACKd = [StartIndex]  # list of segments that were ACK'ed
        ResentACK = {StartIndex: 1}  # list of segments that were resent
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
                logging.warning(f"timed out ⏰, resending {max(ACKd)}...")
                self.writer(max(ACKd) - 1, EndIndex)
                isDropped = True


if __name__ == "__main__":
    server = SlowStartServer()
    server.run()
