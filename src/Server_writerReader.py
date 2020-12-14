import logging
import socket
import sys
import time
import threading

from BaseServer import BaseServer, isDropped


class Writer(threading.Thread):
    """
    Sends all the segments
    """

    def __init__(self, Server, Segments):
        super().__init__()
        self.Server = Server
        self.Segments = Segments
        self.name = "writerThread"

    def run(self) -> None:
        logging.debug(f"sending all {len(self.Segments)}...")
        for Segment in self.Segments:
            self.Server.send(self.Server.clientPort, Segment)
            if int(Segment[:6].decode()) % 70 == 0:
                time.sleep(1)
            print(f"sending segment {str(Segment[:6])}")


class Reader(threading.Thread):
    def __init__(self, Server, Segments):
        super().__init__()
        self.Server = Server
        self.Segments = Segments
        self.name = "readerThread"

    def run(self) -> None:
        LastReceivedACK = 0
        LastExpectedACK = len(self.Segments)
        ACKd = []
        Resent = {}
        while True:
            try:
                LastReceivedACK = self.Server.ackHandler(True)
                if LastReceivedACK == LastExpectedACK:
                    break

                # check if there are
                if LastReceivedACK not in ACKd:  # received a new ACK
                    ACKd.append(LastReceivedACK)
                    continue
                else:  # A Segment has been dropped
                    if LastReceivedACK not in Resent:
                        logging.warning(f"segment {max(ACKd) + 1} has been dropped, resending it...")
            except:
                logging.warning(f"timed out ⏰, resending segment {max(ACKd) + 1}")
                self.Server.send(self.Server.clientPort, self.Segments[LastReceivedACK])


class WriterReaderServer(BaseServer):
    """
    compose of 2 threads:
    Writer : sends all the segments
    Reader : rcv Acks and resend dropped segments
    """
    TIMEOUT = 2

    def engine(self, Segments, *args, **kwargs):
        mReader = Reader(self, Segments)
        mWriter = Writer(self, Segments)

        mWriter.start()
        mReader.start()

        mWriter.join()
        logging.info(f"finished sending all {len(Segments)} segments")
        mReader.join()


if __name__ == '__main__':
    mServer = WriterReaderServer()
    mServer.run()
