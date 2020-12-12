"""
this script tests the server's performance with multiple parameter to determine the best and optimal configuration

:param that are going to be tested
 - TIMEOUT
 - WINDOW SIZE
"""
import logging
import csv
from multiRunner import multiRunner
import progressbar
from src import WindowServer
import subprocess
from func_timeout import func_timeout

TIMEOUT_POOL = [x * 0.001 for x in range(5, 20)]
WINDOW_SIZE_POOL = range(5, 200, 10)
LOG_FILE = 'training_data/training.csv'

widgets = [
    ' [', progressbar.Timer(), '] ',
    progressbar.Bar("=", "[", "]"),
    ' (', progressbar.ETA(), ') ',
]
progressbar.streams.wrap_stderr()
Fieldnames = ['Window', 'Timeout', 'Transmission rate', 'time', 'DroppedSegments']

logging.getLogger().disabled = True


def trainer():
    with progressbar.ProgressBar(max_value=len(TIMEOUT_POOL) * len(WINDOW_SIZE_POOL), widgets=widgets,
                                 redirect_stdout=True, redirect_stderr=True) as bar:
        Counter = 0
        Results = []
        with open(LOG_FILE, 'w', newline='') as csvFile:
            writer = csv.DictWriter(csvFile, fieldnames=Fieldnames)
            writer.writeheader()

        for Window in WINDOW_SIZE_POOL:
            for Timeout in TIMEOUT_POOL:
                try:
                    print(f"\nTESTING WITH WINDOW:{Window}, TIMEOUT:{Timeout}...")
                    port = 4200 + Counter
                    Result = func_timeout(30, multiRunner, (WindowServer,),
                                          {"port": port, "TIMEOUT": Timeout, "WINDOW_SIZE": Window})

                    print(
                        f"RESULTS WITH WINDOW:{Window}, TIMEOUT:{Timeout} :: {Result[0]} Mbps {Result[1]} s {Result[2]} dp")
                except:
                    subprocess.run(['sudo', 'killall', 'client1'])
                    Result = (-1, -1, -1)
                    print(f"EXCEPTION OCCURRED WHEN TESTING WITH WINDOW:{Window}, TIMEOUT:{Timeout}...")
                Results.append({
                    'Window': Window,
                    'Timeout': Timeout,
                    'Transmission rate': Result[0],
                    'time': Result[1],
                    'DroppedSegments': Result[2]
                })

                with open(LOG_FILE, 'a', newline='') as csvFile:
                    writer = csv.DictWriter(csvFile, fieldnames=Fieldnames)
                    writer.writerow(Results[-1])

                Counter += 1
                bar.update(Counter)
    BestPerf = Results[0]
    for Result in Results:
        if Result['Transmission rate'] > BestPerf['Transmission rate']:
            BestPerf = Result['Transmission rate']

    print(f"BEST PERFORMANCE...")
    print(BestPerf)


if __name__ == '__main__':
    trainer()
