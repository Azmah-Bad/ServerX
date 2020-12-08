"""
this script tests a given server with multiple parameters to optimize them
"""
import subprocess
from src import WindowServer
import threading
import logging

CLIENTS_PATH = "~/Desktop/'Parallels Shared Folders'/Home/Desktop/ServerX/clients/"
CLIENT1 = CLIENTS_PATH + "client1"
CLIENT2 = CLIENTS_PATH + "client2"
CLIENT_ARGUMENTS = ["127.0.0.2", "8080", "10mb.jpg", "0"]

COMMANDS = ["Offset lol 😂"] + ["" + client for client in [CLIENT1, CLIENT2]]
CurrentResult = None


def clientRunner(ClientID=1):
    subprocess.run([f"clients/client{ClientID}"] + CLIENT_ARGUMENTS)


def serverRunner(Server):
    global CurrentResult
    CurrentResult = Server.train()


def runner(Server, ClientID=1, *args, **kwargs):
    """
    runs server and client
    :param ClientID: client's ID either 1 or 2
    :param Server: the server
    :param args:
    :param kwargs server's params
    :return server's performance
    """

    ClientHandler = threading.Thread(target=clientRunner, args=(ClientID,), name="ClientRunner")
    mServer = Server()
    mServer.isTraining = True
    for key in kwargs:
        setattr(mServer, key, kwargs[key])

    ServerRunner = threading.Thread(target=serverRunner, args=(mServer,), name="ServerRunner")
    ServerRunner.start()
    ClientHandler.start()
    ServerRunner.join()
    global CurrentResult
    return CurrentResult


if __name__ == '__main__':
    logging.getLogger().disabled = True
    runner(WindowServer)
