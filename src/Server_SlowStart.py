"""
out of 8100 packet client 1 dropped 547
6 % chance of dropping a packet
"""

import logging
import time

from Server_window import WindowServer

INITIAL_CWINDOW = 20


class SlowStartServer(WindowServer):
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
            isDropped = self.windowInspector(self.Segments, Index, Index + CWindow)
            CWindow = int(CWindow/2) if isDropped else int(CWindow + 2)
            logging.debug(f"CWindow: {CWindow}")
            CwndLogs.append(CWindow)
            CycleLogs.append(time.time() - start)
            Index += len(FlightSize)

        self.writeLogs("Cwnd",CwndLogs)
        self.writeLogs("Cycle",CycleLogs)


if __name__ == "__main__":
    server = SlowStartServer()
    server.run()
