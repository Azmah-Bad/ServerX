FILENAME = "sujet.pdf"
FILE1_PATH = "../src/" + FILENAME
FILE2_PATH = "../clients/copy_" + FILENAME


def main():
    with open(FILE1_PATH, "rb") as f:
        File1 = f.read()

    with open(FILE2_PATH, "rb") as f:
        File2 = f.read()

    if len(File1) != len(File2):
        print(f"Different file sizes: original {len(File1)} copy: {len(File2)}")
        print(f"missing bites {len(File1) - len(File2)}")

    for index in range(len(File1)):
        if File1[index] != File2[index]:
            print(f"First difference at char {index}")
            break
        if index == len(File1) - 1:
            print("No difference, files are identical 🥳")





    # print(File2[0:1000])


if __name__ == '__main__':
    main()