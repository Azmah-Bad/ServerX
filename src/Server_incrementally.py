"""
out of 8100 packet client 1 dropped 547
6 % chance of dropping a packet
"""

import socket
import logging
from BaseServer import BaseServer


class IncrementalServer(BaseServer):
    TIMEOUT = 1

    def engine(self, Segments, *args, **kwargs):
        LastACK = 0
        Logs = []
        for Index, Segment in enumerate(Segments):
            self.sendSegmentThread(Index)
            Logs.append(1)
            logging.debug(f"sending segment {Index + 1}")
            while LastACK != Index + 1:
                try:
                    ReceivedACK = self.ackHandler()
                    if LastACK == ReceivedACK:
                        self.DroppedSegmentCount += 1
                        Logs[-1] = 0
                        self.send(self.clientPort, Segment)
                        logging.warning(f"dropped segment {Index + 1}")

                    LastACK = ReceivedACK
                except socket.timeout:
                    Logs[-1] = 0
                    self.DroppedSegmentCount += 1
                    logging.warning(f"timed out ⏲ dropped segment {Index + 1}")
                    self.send(self.clientPort, Segment)

        self.writeLogs("segments", Logs)


if __name__ == "__main__":
    server = IncrementalServer()
    server.run()
