import multiprocessing
import argparse
import logging
from server1_coreDumped import WindowServer


class MultiClientServer(WindowServer):
    """
    SCENARIO 3
    server that can handle multiple connections and client simultaneously
    """

    def run(self):
        Parser = argparse.ArgumentParser()
        Parser.add_argument("port", type=int, default=self.PORT, help='servers public port')
        Parser.add_argument("-v", "--verbose", action="store_true")
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

        self.initServerSockets()

        if Args.remote_debugger:  # FOR DEV AND RESEARCH PURPOSES
            import pydevd_pycharm
            pydevd_pycharm.settrace(Args.remote_debugger, port=6969, stdoutToServer=True, stderrToServer=True)

        while True:
            self.connect()
            mClientHandlerProcess = multiprocessing.Process(target=self.clientHandler, name="ServerHelper (client "
                                                                                            "handler)")
            mClientHandlerProcess.start()
            # mClientHandlerProcess.join()
            if Args.verify:
                self.checkFile()


if __name__ == '__main__':
    mMultiClientServer = MultiClientServer()
    mMultiClientServer.run()
