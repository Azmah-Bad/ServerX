import socket
import logging
import random

HOST = "127.0.0.2"
PORT = 8080

class Server:
    def __init__(self) -> None:
        self.ServerSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)  # create UDP socket
        self.ServerSocket.bind((HOST, PORT))  # bind the socket to an address
        logging.info("Socket binded with success")

        self.NewPort = random.randint(1000,9999)
    
    
    def send(self, port, data):
        if type(data) == str:
            self.ServerSocket.sendto(str.encode(data), (HOST, port))
        else:
            self.ServerSocket.sendto(data, (HOST, port))


    def rcv(self, bufferSize):
        return self.ServerSocket.recvfrom(bufferSize)


    def handshake(self):
        handshakeBuffer = 12
        message, address = self.rcv(handshakeBuffer)
        clientPort = address[1]
        if message == b"SYN":
            logging.info( f"SYN Received from {address}")
        else:
            raise ConnectionRefusedError

        self.send(clientPort, f"SYNACK{self.NewPort}")
        logging.info( f"SYNACK sent 🚀")

        message, address = self.rcv(handshakeBuffer)
        print(f"message recieved {message}")
        if message == b"ACK":
            logging.info(f"Connection with {address} acheived")
        else:
            raise ConnectionRefusedError



if __name__ == "__main__":
    logging.basicConfig(format='%(asctime)s--[%(levelname)s] :%(message)s',
                        level=logging.DEBUG)
    
    server = Server()
    server.handshake()