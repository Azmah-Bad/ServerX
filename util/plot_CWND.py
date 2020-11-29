import matplotlib.pyplot as plt

LOG_FILE_PATH = "../src/Cwind.log"


def main():
    with open(LOG_FILE_PATH, "r") as file:
        rawLines = file.readlines()

    Cwnds = list(map(lambda x: int(x), rawLines))
    plt.plot(Cwnds)
    plt.show()


if __name__ == '__main__':
    main()
