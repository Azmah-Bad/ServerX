import matplotlib.pyplot as plt

LOG_FILE_PATH = "../src/Cycle.log"


def main():
    with open(LOG_FILE_PATH, "r") as file:
        rawLines = file.readlines()

    Cwnds = list(map(lambda x: float(x[:-2]), rawLines))
    plt.plot(Cwnds)
    plt.show()


if __name__ == '__main__':
    main()
