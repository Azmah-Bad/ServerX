import socket
import logging
import random
import os 
import progressbar
import time
from func_timeout import func_timeout, FunctionTimedOut

HOST = "127.0.0.2"
PORT = 8081
SEGMENT_SIZE = 1000
SEGMENT_ID_SIZE = 6  # 6 bites for the segment ID according to subject 
RTT = 0.0489288

class Server:
    def __init__(self) -> None:
        self.ServerSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)  # create UDP socket
        self.ServerSocket.bind((HOST, PORT))  # bind the socket to an address
        logging.info("Socket binded with success")

        self.NewPort = random.randint(1000,9999)
        self.DataSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)  # create UDP socket
        self.DataSocket.bind((HOST, self.NewPort))  # bind the socket to an address
    
    
    def send(self, port, data):
        if type(data) == str:
            self.ServerSocket.sendto(str.encode(data), (HOST, port))
        else:
            self.ServerSocket.sendto(data, (HOST, port))

    
    def rcv(self, Socket, bufferSize):
        return Socket.recvfrom(bufferSize)


    def handshake(self):
        handshakeBuffer = 12
        message, address = self.rcv(self.ServerSocket, handshakeBuffer)
        self.clientPort = address[1]
        if b"SYN" in message:
            logging.info( f"SYN Received from {address}")
        else:
            raise ConnectionRefusedError

        self.send(self.clientPort, f"SYN-ACK{self.NewPort}")
        logging.info( f"SYN-ACK sent 🚀")

        message, address = self.rcv(self.ServerSocket, handshakeBuffer)
        print(f"message recieved {message}")
        if b"ACK" in message:
            logging.info(f"Connection with {address} acheived")
        else:
            raise ConnectionRefusedError
    

    def _getSegments(self,data):
        """return: list of segments"""
        return [str(x // SEGMENT_SIZE).zfill(SEGMENT_ID_SIZE).encode() + data[x:x + SEGMENT_SIZE] for x in
            range(0, len(data), SEGMENT_SIZE)]


    def sendFile(self):
        filenameBuffer = 15
        message, _ = self.rcv(self.DataSocket, filenameBuffer)
        logging.debug("message recieved: " + str(message))

        filename = message.decode()[:-1]
        logging.info(f"file name recieved {filename}")

        if not os.path.exists(filename):
            raise FileNotFoundError("file requested couldn't be found")

        with open(filename, "rb") as f:
            file = f.read()
        logging.info(f"file loaded 🥳")

        segments = self._getSegments(file)  # segment the files 
        logging.info(f"File segmented into {len(file) // SEGMENT_SIZE} segment")

        
        CWindow = 1  # Congestion Window
        rtts = []
        index = 0
        LastACK = 0
        CwndLogs = []
        widgets = [
            ' [', progressbar.Timer(), '] ',
            progressbar.Bar("=","[","]"),
            ' (', progressbar.ETA(), ') ',
        ]
        # with progressbar.ProgressBar(max_value=len(segments), redirect_stdout=True,widgets=widgets) as bar:
        while index < len(segments):
            CwndLogs.append(CWindow)
            segment = segments[index]
            remainingSegments = len(segments[index:])
            if remainingSegments < CWindow:
                CWindow = remainingSegments
            start = time.time()
            FlightSize = range(index, index + CWindow)
            for segIG in FlightSize:
                self.send(self.clientPort, segments[segIG])
                # log("SLOW_START" , f"Sending segment {segIG}")
            index += CWindow
            for _ in FlightSize:
                try:
                    LastACK = func_timeout(RTT, self.ackHandler, (self.ServerSocket,))
                    CWindow += 1
                except FunctionTimedOut:  # dropedd a segment
                    logging.info(f"segment {index} not acked 😭")
                    CWindow = 1  # reset the CWindow
                    self.send(self.clientPort, segments[LastACK + 1])  # resend the lost segment

            logging.info(f"CWindow: {CWindow}")
            end = time.time()
            rtts.append(end - start)
            # bar.update(index)
            logging.info(f"Estimated RTT {int((sum(rtts) / len(rtts)) * 1000)} ms")
            logging.info(f"Total time to send file {int(sum(rtts) * 1000)} ms ")
            logging.info(f"Transmission rate: {os.stat(filename).st_size / int(sum(rtts) * 1000)}")
            self.send(self.clientPort, "FIN")

    def ackHandler(self,ServerSocket):
        # check for ACK 
        rcvACK, _ = self.rcv(ServerSocket, 8)
        # log('SEND_FILE', f'ACK: recieved ACK {rcvACK}')
        logging.debug(f"recieved ACK: {int((rcvACK).decode()[3:])}" )

        return int((rcvACK).decode()[3:])



if __name__ == "__main__":
    logging.basicConfig(format='%(asctime)s--[%(levelname)s]: %(message)s',
                        level=logging.DEBUG)
    
    server = Server()
    server.handshake()
    server.sendFile()