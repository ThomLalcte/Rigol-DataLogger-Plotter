import argparse, os, numpy as np
from sys import argv
from matplotlib import pyplot as plt
from datetime import datetime

# design philosophy:
# label the data in the csv file with the unit in the same column
# the unit is in the format of "label (unit)" or "label (measurement unit)[represented unit]"
# add columns in the csv file for math operations and use () to plot to an other figure


def setupParser():
    parser = argparse.ArgumentParser(
        description="Utility to record samples from the Poseidon"
    )
    parser.add_argument(
        "-p",
        "--path",
        type=str,
        help="The location of the data folder",
    )
    parser.add_argument(
        "-d",
        "--delimiter",
        type=str,
        help="The delimiter used in the file",
        default=";",
    )
    parser.add_argument(
        "-s",
        "--start",
        type=str,
        help="The start time of the plot (format: YYYY-MM-DD HH:MM)",
    )
    parser.add_argument(
        "-e",
        "--end",
        type=str,
        help="The end time of the plot (format: YYYY-MM-DD HH:MM)",
    )

    if len(argv) == 1:
        parser.parse_args(["-h"])
    elif len(argv) == 2:
        args = parser.parse_args(argv[1].split(" "))
    else:
        args = parser.parse_args(argv[1:])

    # Check if the path is valid
    if args.path is not None:
        if not os.path.exists(args.path):
            print("The path provided does not exist")
            exit()
    else:
        args.path = os.getcwd()

    return args


def loadFile(path, args):
    if os.path.isdir(path):
        for file in os.listdir(path):
            if not file.endswith(".csv"):
                continue
            if file == "config.csv":
                continue
            with open(os.path.join(path, file), "r") as f:
                data = f.readlines()
                if "," in data[1]:
                    data = [x.replace(",",".") for x in data]
                data = [x.strip().split(args.delimiter) for x in data]
                data = np.array(data).T
    return data

def extractUnit(label:str):
    if "[" in label:
        unitLabel = label.split("[")[-1].split("]")[0]
    else:
        unitLabel = label.split("(")[-1].split(")")[0]
    return unitLabel

def plotData(data, args):
    labels = data[:, 0]
    data = data[:, 1:]
    x = np.array(data[0], dtype=float)
    time = []
    for timestamp in data[1]:
        time.append(datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S:%f"))
    time = np.array(time)

    validIdx = np.where(time != "None")
    startIdx = np.arange(len(time))
    endIdx = np.arange(len(time))
    # list points outside the time range
    if args.start is not None:
        startTime = datetime.strptime(args.start, "%Y-%m-%d %H:%M")
        startIdx = np.where(time[validIdx] > startTime)


    if args.end is not None:
        endTime = datetime.strptime(args.end, "%Y-%m-%d %H:%M")
        endIdx = np.where(time[validIdx] < endTime)

    validIdx = np.intersect1d(startIdx, endIdx)

    if len(validIdx) == 0:
        print("No valid data in the time range")
        exit()

    plots = {}
    for label in labels:
        if not "(" in label:
            continue
        unitLabel = extractUnit(label)
        if unitLabel not in plots:
            plots.update({unitLabel: plt.subplots()})

    linestyle = ["-"]*10 + ["--"]*10 + [":"]*10 + ["-."]*10
    linestyle_i = iter(linestyle)

    for i in range(2, len(labels)):
        try:
            unit = np.array(data[i], dtype=float)
            unitLabel = extractUnit(labels[i])
            plots[unitLabel][1].plot(time[validIdx], unit[validIdx], label=labels[i], linestyle=next(linestyle_i))
        except:
            continue
    
    for key in plots:
        plots[key][1].legend()
        plots[key][1].set_xlabel("Time")
        plots[key][1].set_ylabel(key)
        plots[key][1].set_title(args.path.split("/")[-1])
    plt.show()


def main():
    args = setupParser()
    data = loadFile(args.path, args)

    plotData(data, args)


if __name__ == "__main__":
    main()
