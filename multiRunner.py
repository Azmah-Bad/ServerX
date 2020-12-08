import logging

from runner import runner
import argparse
from src import SlowStartServer, WindowServer

RUN_COUNTER = 3
VERBOSE = True


def multiRunner(Server, Client: int = 1, **kwargs):
    if VERBOSE:
        print(f"running tests on {Server.__name__.upper()}...")
    Results = []
    for _ in range(RUN_COUNTER):
        Results.append(runner(Server, Client, kwargs))

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
    Parser.add_argument("-v", "--verbose", action="store_false")
    Parser.add_argument("-d", "--debug", action="store_false")
    Parser.add_argument("-c", "--count", type=int, default=RUN_COUNTER)
    Parser.add_argument("-m", "--mode", type=str, default="all", choices=["all", "slowStart", "Window"])

    Args = Parser.parse_args()
    RUN_COUNTER = Args.count
    VERBOSE = Args.verbose
    ToBeRun = []
    if Args.debug:
        logging.getLogger().disabled = True
    if Args.mode == "all":
        ToBeRun = [SlowStartServer, WindowServer]
    if Args.mode == "slowStart":
        ToBeRun = [SlowStartServer]
    if Args.mode == "Window":
        ToBeRun = [WindowServer]

    for ToBeRunServer in ToBeRun:
        Results = multiRunner(ToBeRunServer)
