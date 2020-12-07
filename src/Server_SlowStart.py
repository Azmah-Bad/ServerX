"""
out of 8100 packet client 1 dropped 547
6 % chance of dropping a packet
"""

import logging
import socket
import sys
import argparse
from BaseServer import BaseServer, isDropped

INITIAL_CWINDOW = 1


class Server(BaseServer):

    def engine(self, Segments):
        Index = 0
        CWindow = INITIAL_CWINDOW  # Congestion Window

        while Index < len(Segments):
            remainingSegments = len(Segments[Index:])
            if remainingSegments < CWindow:
                CWindow = remainingSegments

            FlightSize = range(Index, Index + CWindow)

            CWindow = self.sendSegments(FlightSize, Segments, CWindow)

            logging.debug(f"CWindow: {CWindow}")
            Index += len(FlightSize)

    def sendSegments(self, FlightSize, Segments, CWindow):
        LastACK = 0
        ReceivedACK = 0
        # for SegID in FlightSize:
        #     self.send(self.clientPort, Segments[SegID])
        self.writer(Segments[FlightSize[0]:FlightSize[-1] + 1])

        ExpectedACK = FlightSize[-1]
        logging.debug(f"sent Segments {FlightSize[0] + 1} => {FlightSize[-1] + 1}")

        CWindow = self.windowChecker(Segments, FlightSize[0], FlightSize[-1], CWindow)

        # while not ReceivedACK > ExpectedACK:
        #     try:
        #         ReceivedACK = self.ackHandler()
        #         if ReceivedACK == LastACK:
        #             logging.warning(f"Segment {LastACK + 1} dropped RIP 💀")
        #             self.send(self.clientPort, Segments[LastACK])
        #             CWindow = 1
        #         if ReceivedACK >= ExpectedACK:
        #             logging.debug(f"all Segments were ACK'd 🤑")
        #             CWindow = CWindow * 2
        #             LastACK = ReceivedACK
        #             break
        #         LastACK = ReceivedACK
        #     except socket.timeout:
        #         logging.warning(f"Segment {LastACK + 1} dropped RIP 💀 from timeout")
        #         self.send(self.clientPort, Segments[LastACK])
        # 
        #         CWindow = 1  # reset the CWindow

        logging.debug(f"all Segments were ACK'd 🤑")
        # CWindow = CWindow * 2
        # LastACK = ReceivedACK
        return CWindow

    def windowChecker(self, Segments, StartIndex, EndIndex, CWindow):
        ACKs = []
        Index = 0
        isMultipleACKs = False
        while Index < CWindow:
            try:
                ACKs.append(self.ackHandler(True))
                if EndIndex in ACKs:
                    CWindow = CWindow * 2
                    return CWindow  # EndIndex already in list

                if isDropped(ACKs) and not isMultipleACKs:
                    Index += 2
                    isMultipleACKs = True
                    logging.warning(f"a segment has been dropped, skipping last ACK listen")

                Index += 1

            except socket.timeout:
                if ACKs:
                    logging.warning(f"timed out ⏰, dropped segment {ACKs[-1] + 1}")
                    break

        for Ack in ACKs:
            if ACKs.count(Ack) != 1:  # Ack was dropped
                logging.warning(f"dropped segment {Ack + 1} 😭")
                CWindow = INITIAL_CWINDOW
                toBeResent = Ack
                isRecovered = False
                while not isRecovered:
                    self.send(self.clientPort, Segments[toBeResent])
                    self.DroppedSegmentCount += 1
                    try:
                        while True:
                            ReceivedACK = self.ackHandler(True)
                            if ReceivedACK == EndIndex:
                                isRecovered = True
                            else:
                                toBeResent = ReceivedACK

                    except socket.timeout:
                        pass
                break
        return CWindow


if __name__ == "__main__":
    logging.basicConfig(format='%(asctime)s--[%(levelname)s]: %(message)s',
                        level=logging.INFO if 'INFO' in sys.argv else logging.DEBUG)

    server = Server()
    server.handshake()
    server.sendFile()
