"""
this script tests a given server with multiple parameters to optimize them
"""
import subprocess
from src import WindowServer
import threading
import logging
from func_timeout import func_set_timeout

CLIENTS_PATH = "~/Desktop/'Parallels Shared Folders'/Home/Desktop/ServerX/clients/"
CLIENT1 = CLIENTS_PATH + "client1"
CLIENT2 = CLIENTS_PATH + "client2"
CLIENT_ARGUMENTS = ["127.0.0.2", "8080", "10mb.jpg", "0"]

COMMANDS = ["Offset lol 😂"] + ["" + client for client in [CLIENT1, CLIENT2]]
CurrentResult = None


class ClientRunner(threading.Thread):
    def __init__(self, ClientID):
        super().__init__()
        self.name = "ClientRunner"
        self.Subprocess = None
        self.ClientID = ClientID

    # @func_set_timeout(5)
    def run(self) -> None:
        self.Subprocess = subprocess.run([f"clients/client{self.ClientID}"] + CLIENT_ARGUMENTS)

    def kill(self):
        self.Subprocess.terminate()


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

    mClientHandler = ClientRunner(ClientID)
    mServer = Server()
    mServer.isTraining = True
    for key in kwargs:
        setattr(mServer, key, kwargs[key])

    ServerRunner = threading.Thread(target=serverRunner, args=(mServer,), name="ServerRunner")
    try:
        ServerRunner.start()
        mClientHandler.start()
        ServerRunner.join()
        mClientHandler.join()
    finally:
        if mClientHandler.is_alive():
            mClientHandler.kill()  # 😭

    global CurrentResult
    return CurrentResult


def unsafeRunner(Server, ClientID=1, *args, **kwargs):
    try:
        mClientHandler = ClientRunner(ClientID)
        mServer = Server()
        mServer.isTraining = True
        for key in kwargs:
            setattr(mServer, key, kwargs[key])

        ServerRunner = threading.Thread(target=serverRunner, args=(mServer,), name="ServerRunner")
        ServerRunner.start()
        mClientHandler.start()
        ServerRunner.join()
        mClientHandler.join()
        global CurrentResult
    finally:
        return CurrentResult


if __name__ == '__main__':
    logging.getLogger().disabled = True
    runner(WindowServer)
