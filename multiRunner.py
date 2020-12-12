import logging

from runner import runner
import argparse
from src import SlowStartServer, WindowServer, IncrementalServer
from func_timeout import func_set_timeout

RUN_COUNTER = 1
VERBOSE = False


def multiRunner(Server, Client: int = 1, **kwargs):
    if VERBOSE:
        print(f"running tests on {Server.__name__.upper()}...")
    Results = []
    for _ in range(RUN_COUNTER):
        Results.append(runner(Server, Client, **kwargs))

    Rates = []
    Times = []
    DroppedSegments = []

    for Result in Results:
        Rates.append(float(Result[0]))
        Times.append(Result[1])
        DroppedSegments.append(Result[2])

    if VERBOSE:
        print(f"RESULTS OF {type(Server).__name__.upper()}")
        print(f"average Rate {sum(Rates) / len(Rates)}")
        print(f"average time {sum(Times) / len(Times)}")
        print(f"average dropped segments {sum(DroppedSegments) / len(DroppedSegments)}")
    return sum(Rates) / len(Rates), sum(Times) / len(Times), sum(DroppedSegments) / len(DroppedSegments)


if __name__ == '__main__':
    Parser = argparse.ArgumentParser()
    Parser.add_argument("-q", "--quite", action="store_false")
    Parser.add_argument("-d", "--debug", action="store_false")
    Parser.add_argument("-t", "--times", type=int, default=RUN_COUNTER)
    Parser.add_argument("-m", "--mode", type=str, default="window",
                        choices=["all", "slowStart", "window", "incremental",
                                 "ss", "w", "i"])
    Parser.add_argument("-c", "--client", default=1, type=int)

    Args = Parser.parse_args()
    RUN_COUNTER = Args.times
    VERBOSE = Args.quite
    ToBeRun = []
    if Args.debug:
        logging.getLogger().disabled = True
    if Args.mode == "all":
        ToBeRun = [SlowStartServer, WindowServer]
    if Args.mode in ["slowStart", "ss"]:
        ToBeRun = [SlowStartServer]
    if Args.mode in ["window", "W"]:
        ToBeRun = [WindowServer]
    if Args.mode in ["incremental", "i"]:
        ToBeRun = [IncrementalServer]

    for ToBeRunServer in ToBeRun:
        Results = multiRunner(ToBeRunServer, Client=Args.client, TIMEOUT=0.020)
