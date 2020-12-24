"""
out of 8100 packet client 1 dropped 547
6 % chance of dropping a packet
"""

import logging
from Server_window import WindowServer

INITIAL_CWINDOW = 5


class SlowStartServer(WindowServer):
    def engine(self, Segments):
        Index = 0
        CWindow = INITIAL_CWINDOW  # Congestion Window
        CwndLogs = []

        while Index < len(Segments):
            remainingSegments = len(Segments[Index:])
            if remainingSegments < CWindow:
                CWindow = remainingSegments

            FlightSize = range(Index, Index + CWindow)

            self.writer(Segments[Index: Index + CWindow])
            logging.info(f"sending segments {Index} => {Index + CWindow},Cwnd of {CWindow}")
            isDropped = self.windowInspector(self.Segments, Index, Index + CWindow)
            CWindow = int(CWindow/2) if isDropped else int(CWindow * 2)
            logging.debug(f"CWindow: {CWindow}")
            CwndLogs.append(CWindow)
            Index += len(FlightSize)

        self.writeLogs("Cwnd",CwndLogs)


if __name__ == "__main__":
    server = SlowStartServer()
    server.run()
