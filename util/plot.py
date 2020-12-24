import matplotlib.pyplot as plt
import os

LOG_FILES_PATH = "../src/logs/"


def main():

    for logFilePath in [LOG_FILES_PATH + file for file in os.listdir(LOG_FILES_PATH) if file[-4:] == ".log"]:
        with open(logFilePath, "r") as file:
            rawLines = file.readlines()
        Cwnds = []
        for value in rawLines:
            try:
                Cwnds.append(float(value[:-1]))
            except ValueError:
                Cwnds.append(0)
                pass
        plt.plot(Cwnds)
        plt.title(logFilePath)
        plt.show()


if __name__ == '__main__':
    main()
