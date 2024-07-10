import argparse, os, numpy as np
from sys import argv
from matplotlib import pyplot as plt
from datetime import datetime
import json

# design philosophy:
# label the data in the csv file with the unit in the same column
# the unit is in the format of "label (unit)" or "label (measurement unit)[represented unit]"
# add columns in the csv file for math operations and use () to plot to an other figure

# Or

# create a json file with the channel configuration
# the json file should have the following structure:
# "Channel name ass written in the .csv file": {
#     "type": (str) variable type orp/pH/temp, TODO: implement use
#     "label": (str) text to display,
#     "unit": (str) unit of the original measurement,
#     "displayUnit": (str) unit to convert the original measurement to TODO: implement conversion
# },

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

    parser.add_argument(
        "-cc",
        "--channelconfig",
        type=str,
        help="The path to the channel configuration file",
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

def openFile(path, delimiter:str = ";"):
    with open(path, "r") as f:
        data = f.readlines()
        if "," in data[1]:
            data = [x.replace(",",".") for x in data]
        data = [x.strip().split(delimiter) for x in data]
        data = np.array(data).T

    return data

def loadFile(path, args):

    data = None

    # Check if the path is a file or a directory
    if os.path.isfile(path):
        data = openFile(path, args.delimiter)

    if os.path.isdir(path):
        # Check if the directory contains csv files
        for file in os.listdir(path):
            if not file.endswith(".csv"):
                continue
            if file == "config.csv":
                continue
            data = openFile(os.path.join(path, file), args.delimiter)

        # did not find any csv files in the directory
        # looking in the subdirectories

        if data is None:
            # create a list of all the files in the directory
            files = []
            for root, dirs, subfiles in os.walk(path):
                for subfile in subfiles:
                    if not subfile.endswith(".csv"):
                        continue
                    if subfile == "config.csv":
                        continue
                    files.append(os.path.join(root, subfile))

            # if no csv files were found
            if len(files) == 0:
                print("No csv files found in the provided directory")
                exit()

            # if multiple csv files were found
            elif len(files) == 1:
                data = openFile(files[0], args.delimiter)
            else:
                print("TODO: Implement multiple file support")
    return data

def loadChannelConfig(path):
    with open(path, "r") as f:
        data = json.load(f)
    return data

def extractUnit(label:str):
    if "[" in label:
        unitLabel = label.split("[")[-1].split("]")[0]
    else:
        unitLabel = label.split("(")[-1].split(")")[0]
    return unitLabel

def plotData(data, args, channelConfig:dict=None):
    labels = data[:, 0]
    data = data[:, 1:]
    # x = np.array(data[0], dtype=float)
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
    labels: list[str] = labels.tolist()
    label: str
    # linestyle = ["-"]*10 + ["--"]*10 + [":"]*10 + ["-."]*10
    # linestyle_i = iter(linestyle)

    for label in labels:
        if channelConfig is not None:
            if label not in channelConfig.keys():
                continue
            unitLabel = channelConfig[label]["displayUnit"]
            displayLabel = channelConfig[label]["label"]
        else:
            if not "(" in label:
                continue
            unitLabel = extractUnit(label)
            displayLabel = label
        if unitLabel not in plots:
            plots.update({unitLabel: plt.subplots()})

        unit = np.array(data[labels.index(label)], dtype=float)
        plots[unitLabel][1].plot(time[validIdx], unit[validIdx], label=f"{label}-{displayLabel}")
        # plots[unitLabel][1].plot(time[validIdx], unit[validIdx], label=unitLabel, linestyle=next(linestyle_i))

    
    for key in plots:
        plots[key][1].legend()
        plots[key][1].set_xlabel("Time")
        plots[key][1].set_ylabel(key)
        plots[key][1].set_title(args.path.split("/")[-1])
    plt.show()


def main():
    args = setupParser()
    data = loadFile(args.path, args)
    if args.channelconfig is not None:
        channelConfig = loadChannelConfig(args.channelconfig)

    plotData(data, args, channelConfig)


if __name__ == "__main__":
    main()
