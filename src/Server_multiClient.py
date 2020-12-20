from Server_window import WindowServer
import multiprocessing
import argparse
import logging


class MultiClientServer(WindowServer):
    """
    server that can handle multiple connections and client simultaneously
    """
    def run(self):
        Parser = argparse.ArgumentParser()
        Parser.add_argument("-v", "--verbose", action="store_true")
        Parser.add_argument("-p", "--port", type=int, default=self.PORT)
        Parser.add_argument("-t", "--timeout", type=int, default=self.TIMEOUT)
        Parser.add_argument("--host", type=str, default="")
        Parser.add_argument("--remote_debugger", type=str)
        Parser.add_argument("-q", "--quite", type=int, help="don't write log files")
        Parser.add_argument("--verify", action="store_true")

        Args = Parser.parse_args()

        logging.basicConfig(format='%(asctime)s--[%(levelname)s]: %(message)s',
                            level=logging.DEBUG if Args.verbose else logging.INFO)
        self.TIMEOUT = Args.timeout
        self.PORT = Args.port
        self.HOST = Args.host

        self.initSockets()

        if Args.remote_debugger:
            import pydevd_pycharm
            pydevd_pycharm.settrace(Args.remote_debugger, port=6969, stdoutToServer=True, stderrToServer=True)

        while True:
            self.connect()
            mClientHandlerProcess = multiprocessing.Process(target=self.clientHandler, name="ServerHelper (client "
                                                                                            "handler)")
            mClientHandlerProcess.start()
            mClientHandlerProcess.join()
            if Args.verify:
                self.checkFile()


if __name__ == '__main__':
    mMultiClientServer = MultiClientServer()
    mMultiClientServer.run()