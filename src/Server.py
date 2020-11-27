import socket
import logging
import random
import os 

HOST = "127.0.0.2"
PORT = 8080
SEGMENT_SIZE = 1000

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
        return self.Socket.recvfrom(bufferSize)


    def handshake(self):
        handshakeBuffer = 12
        message, address = self.rcv(self.ServerSocket, handshakeBuffer)
        clientPort = address[1]
        if b"SYN" in message:
            logging.info( f"SYN Received from {address}")
        else:
            raise ConnectionRefusedError

        self.send(clientPort, f"SYNACK{self.NewPort}")
        logging.info( f"SYNACK sent 🚀")

        message, address = self.rcv(self.ServerSocket, handshakeBuffer)
        print(f"message recieved {message}")
        if b"ACK" in message:
            logging.info(f"Connection with {address} acheived")
        else:
            raise ConnectionRefusedError
    

    def _getSegments(self,data):
        """return: list of segments"""
        return [str(x // SEGMENT_SIZE).zfill(20).encode() + data[x:x + SEGMENT_SIZE] for x in
            range(0, len(data), SEGMENT_SIZE)]


    def sendFile(self):
        filenameBuffer = 15
        message, _ = self.rcv(self.DataSocket, filenameBuffer)
        logging.debug("message recieved: " + message)

        filename = str(message)[:-3]
        logging.info(f"file name recieved {filename}")

        if not os.path.exists(filename):
            raise FileNotFoundError("file requested couldn't be found")

        with open(filename, "rb") as f:
            file = f.read()
        logging.info(f"file loaded 🥳")

        segments = self._getSegments(file)  # segment the files 
        logging.info(f"File segmented into {len(file) // SEGMENT_SIZE} segment")




if __name__ == "__main__":
    logging.basicConfig(format='%(asctime)s--[%(levelname)s] :%(message)s',
                        level=logging.DEBUG)
    
    server = Server()
    server.handshake()
    server.sendFile()