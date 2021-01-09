import socket
from src import BaseServer
import logging

class SlidingWindowServer(BaseServer):
    """
    Sliding window engine
    start by sending a window of segments then reads the ACK recieved
    if the segment is received sends the next segment
    if a segment was dropped
    # Perf
    5.9 MBps for small files
    1 MBps for large files
    """
    WINDOW_SIZE = 80

    def engine(self, *args, **kwargs):
        index = self.WINDOW_SIZE - 1
        ACKd = []
        self.writer(0, self.WINDOW_SIZE)

        while index < len(self.Segments):
            try:
                ReceivedACK = self.ackHandler()
            except socket.timeout:
                logging.warning(f"timed out...")
                if ACKd:
                    self.sendSegmentThread(max(ACKd))
                continue
            if ReceivedACK == len(self.Segments):
                break

            # if ReceivedACK in ACKd:  # TODO maybe if a seg is dropped resend a window
            if ACKd.count(ReceivedACK) == 1:
                logging.warning(f"segment {ReceivedACK + 1} was dropped, resending it...")
                self.writer(ReceivedACK, ReceivedACK + self.WINDOW_SIZE)
                self.DroppedSegmentCount += 1
            if ReceivedACK not in ACKd:  # Segment received with success
                index += 1
                if index == len(self.Segments):
                    break
                self.sendSegmentThread(index)
                logging.debug(f"segment received with success, sending in segment {index + 1}...")

            ACKd.append(ReceivedACK)


if __name__ == '__main__':
    mServer = SlidingWindowServer()
    mServer.run()