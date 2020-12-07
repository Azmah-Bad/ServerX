"""
out of 8100 packet client 1 dropped 547
6 % chance of dropping a packet
"""

import socket
import logging
from BaseServer import BaseServer


class Server(BaseServer):
    def engine(self, Segments, *args, **kwargs):
        LastACK = 0
        for Index, Segment in enumerate(Segments):
            self.send(self.clientPort, Segment)
            logging.debug(f"sending segment {Index + 1}")
            while LastACK != Index + 1:
                try:
                    ReceivedACK = self.ackHandler()
                    if LastACK == ReceivedACK:
                        self.DroppedSegmentCount += 1
                        self.send(self.clientPort, Segment)
                        logging.warning(f"dropped segment {Index + 1}")

                    LastACK = ReceivedACK
                except socket.timeout:
                    self.DroppedSegmentCount += 1
                    logging.warning(f"timed out ⏲ dropped segment {Index + 1}")
                    self.send(self.clientPort, Segment)


if __name__ == "__main__":
    server = Server()
    server.run()