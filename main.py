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
# "Channel name as written in the .csv file": {
#     "type": (str) variable type orp/pH/temp, TODO: implement use
#     "label": (str) text to display,
#     "unit": (str) unit of the original measurement,
#     "displayUnit": (str) unit to convert the original measurement to TODO: implement conversion
# },


def setupParser():
    print("parsing arguments")
    parser = argparse.ArgumentParser(description="Utility to record samples from the Poseidon")
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


def openFile(path, delimiter: str = ";"):
    print(f"opening {path.split('/')[-1]}")
    with open(path, "r") as f:
        data = f.readlines()
        if "," in data[1]:
            data = [x.replace(",", ".") for x in data]
        data = [x.strip().split(delimiter) for x in data]
        if "" in data[1]:
            data.pop(1)
        if "" in data[-1]:
            data.pop(-1)
        if len(data[-1]) != len(data[-2]):
            data.pop(-1)
        try:
            data = np.array(data).T
        except ValueError:
            if len(data[0]) != len(data[-1]):
                data.pop(-1)
            data = np.array(data).T

    return data


def loadFile(path, args):
    print(f"loading all .csv in {path}")
    files = []

    # Check if the path is a file or a directory
    if os.path.isfile(path):
        # data = openFile(path, args.delimiter)
        files.append(path)

    if os.path.isdir(path):
        # List all the csv files in the directory and subdirectories

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

    loadedfiles = {}
    data = {
        "dataSize": 0,  # the amount of data points in set
        "channels": [],  # the channels in the set
        "files": {
            #   "filename":{
            #       "range":[startindex, endIndex],
            #       "channels":{
            #           channelName: [...],
            #           otherChannelName: [...]
            #       }
            #   }
        },
    }

    # sort the files by name reversed (oldest first)
    files.sort()

    for file in files:
        loadedfiles.update({file: []})
        fileNameShorted = file.split("/")[-1].split(".")[0].split("\\")[1]
        print(f"loading {files.index(file)}: {fileNameShorted}")
        fileData = openFile(file, args.delimiter)

        # check if the file is empty
        if len(fileData) == 0:
            print(f"{file} is empty")
            continue
        # check if the file has more data than just the header
        if len(fileData[1]) < 2:
            print(f"{file} has no data")
            continue

        # check if the file is a duplicate
        # done by checking if first and last timestamps are already in the data
        for serie in data["files"]:
            if (
                data["files"][serie]["channels"]["Time"][0] == fileData[1][1]
                and data["files"][serie]["channels"]["Time"][-1] == fileData[1][-1]
            ):
                print(f"{file} is a duplicate of {serie}")
                continue

        # get the amount of rows in the file
        rows = len(fileData[0]) - 1
        # grab the start and end index of the data
        startindex = data["dataSize"]
        endindex = startindex + rows
        # increment the data size
        data["dataSize"] += rows
        # add the data to the channels dict
        data["files"].update({fileNameShorted: {"range": [startindex, endindex], "channels": {}}})
        for channel in fileData:
            if channel[0] not in data["channels"]:
                data["channels"].append(channel[0])
            data["files"][fileNameShorted]["channels"][channel[0]] = channel[1:]

    return data


def loadChannelConfig(path):
    print(f"loading channel configuration from {path}")
    with open(path, "r") as f:
        data = json.load(f)
    return data


def extractUnit(label: str):
    print(f"extracting unit from {label}")
    if "[" in label:
        unitLabel = label.split("[")[-1].split("]")[0]
    else:
        unitLabel = label.split("(")[-1].split(")")[0]
    return unitLabel


def trimData(data: dict, args):
    NvalidIdx = 0

    if args.start is not None:
        startTime = datetime.strptime(args.start, "%Y-%m-%d %H:%M")
    else:
        startTime = None
    if args.end is not None:
        endTime = datetime.strptime(args.end, "%Y-%m-%d %H:%M")
    else:
        endTime = None

    for serie in data["files"]:
        print(f"Trimming out of range data of serie {serie}")
        time = []

        for timestamp in data["files"][serie]["channels"]["Time"]:
            time.append(datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S:%f"))
        time = np.array(time)

        validIdx = np.where(time != "None")
        startIdx = np.arange(len(time))
        endIdx = np.arange(len(time))

        if startTime is not None:
            startIdx = np.where(time[validIdx] > startTime)
        if endTime is not None:
            endIdx = np.where(time[validIdx] < endTime)

        validIdx = np.intersect1d(startIdx, endIdx)

        NvalidIdx += len(validIdx)
        data["files"][serie]["validIdx"] = validIdx
        data["files"][serie]["channels"]["Time"] = time

    if NvalidIdx == 0:
        print("No valid data in the time range")
        exit()


def plotData(data: dict, args, channelConfig: dict = None):
    print("plotting data")
    labels = data["channels"]

    trimData(data, args)

    concatenatedTime = []
    for serie in data["files"]:
        concatenatedTime += data["files"][serie]["channels"]["Time"].tolist()

    label: str
    plots = {}
    for label in labels:
        # check if the label is in the channel configuration, if not go to the next label
        if label not in channelConfig.keys():
            continue
        elif label != "Time":
            unitLabel = channelConfig[label]["displayUnit"]
            actualUnit = channelConfig[label]["unit"]
            displayLabel = channelConfig[label]["label"]
            if unitLabel not in plots:
                newAxis: plt.Axes
                newfig, newAxis = plt.subplots()
                newAxis.set_xlabel("Time")
                newAxis.set_ylabel(f"{unitLabel}({actualUnit})")
                newAxis.set_title(unitLabel)
                plots.update({unitLabel: (newfig, newAxis)})

        # combine the individual data sets into one easy to index
        indexChain = []
        concatenatedData = []
        for serie in data["files"]:
            if label not in data["files"][serie]["channels"]:
                continue
            serieValidIdx = data["files"][serie]["validIdx"]
            if len(serieValidIdx) == 0:
                continue
            indexChain.append(
                [
                    data["files"][serie]["range"][0] + serieValidIdx[0],
                    data["files"][serie]["range"][0] + serieValidIdx[-1] + 1,
                ]
            )
            concatenatedData += data["files"][serie]["channels"][label][serieValidIdx].tolist()

        # check if the index chain is correct
        for link in range(len(indexChain) - 1):
            if indexChain[link][1] != indexChain[link + 1][0]:
                print("Index chain is broken and sparse data is not supported yet")
                print(f"label: {label}")
                print(f"Broken chain between {indexChain[link][1]} and {indexChain[link + 1][0]}")
                # print the time of the broken chain
                print(
                    f"Time of the broken chain: {data['files'][serie]['channels']['Time'][indexChain[link][1]]} and {data['files'][serie]['channels']['Time'][indexChain[link + 1][0]]}"
                )
                exit()

        # plot the data
        if label != "Time":
            print(f"plotting {len(concatenatedData)} points for {label}")
            if unitLabel == "ORP":
                yData = np.array(concatenatedData, float)*1000
            else:
                yData = np.array(concatenatedData, float)
            plots[unitLabel][1].plot(
                concatenatedTime[indexChain[0][0] : indexChain[-1][1]],
                yData,
                label=f"{label}-{displayLabel}",
            )

    for plot in plots:
        currAxis:plt.Axes = plots[plot][1]
        currAxis.legend()

    plt.show()

def main():
    args = setupParser()
    data = loadFile(args.path, args)
    if args.channelconfig is not None:
        channelConfig = loadChannelConfig(args.channelconfig)

    plotData(data, args, channelConfig)


if __name__ == "__main__":
    main()
