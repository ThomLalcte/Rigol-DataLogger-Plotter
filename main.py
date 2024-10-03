import argparse, os, numpy as np, json
from sys import argv
from matplotlib import pyplot as plt
from datetime import datetime, timedelta


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
    # create a list with M300 replaced with nothing
    # templateFiles = [file.replace("M300", "") for file in files]
    # # get the sort index
    # sortIndex = np.argsort(templateFiles)[::-1]
    # # sort the files
    # files = np.array(files)[sortIndex].tolist()
    files.sort()

    for file in files:
        fileNameShorted = file.split("/")[-1].split(".")[0].split("\\")[1]
        # check if the file name is already in the data, if so add a number to the name in the format of filename_00X
        while fileNameShorted in data["files"]:
            # 'C:/Users/tlalancette/OneDrive - Gecko Alliance Group Inc/OPJ-44/4_Solution Development/XX_RD Hardware/Bug ORP/2e test/data\\goldRef\\20240726_124734\\dat00002.csv'
            fileNameShorted = f"{file.split('/')[-1].split('.')[0].split('\\')[1]}_{file.split('/')[-1].split('.')[0].split('\\')[2]}_{file.split('/')[-1].split('.')[0].split('\\')[-1]}"

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


def packageData(data: dict, args, channelConfig: dict = None):
    # create a new dict to store the data so that one may simply add a data set to a plot using only the name of the data set
    packaged_Data = {}

    labels = data["channels"]

    trimData(data, args)

    concatenatedTime = []
    for serie in data["files"]:
        concatenatedTime += data["files"][serie]["channels"]["Time"].tolist()

    label: str
    for label in labels:
        # check if the label is in the channel configuration, if not go to the next label
        if label not in channelConfig.keys():
            continue

        # combine the individual data sets into one easy to index
        indexChain = []
        concatenatedData = np.array([], float)
        for serie in data["files"]:
            print(f"indexing {label} in {serie}")
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
            # concatenatedData += data["files"][serie]["channels"][label][serieValidIdx]
            concatenatedData = np.concatenate(
                (concatenatedData, data["files"][serie]["channels"][label][serieValidIdx])
            )
            concatenatedData[-1] = np.nan

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

        concatenatedData = np.array(concatenatedData, float)

        packaged_Data.update({label: (concatenatedTime, concatenatedData, indexChain)})

    return packaged_Data


def plotData(dataSeries: dict, args, channelConfig: dict, saveDir: str = "plots"):
    print("plotting data")

    # create the desired plots
    plots = {}

    # generic plot for each display units
    for label in dataSeries:
        unitLabel = channelConfig[label]["displayUnit"]
        if unitLabel not in plots:
            newAxis: plt.Axes
            newfig, newAxis = plt.subplots()
            newAxis.set_xlabel("Time")
            newAxis.set_ylabel(f"{unitLabel} ({channelConfig[label]["unit"]})")
            newAxis.set_title(f"General view of variable {unitLabel}")
            # set the figure margins to the minimum
            newfig.subplots_adjust(left=0.075, right=0.925, top=0.925, bottom=0.075)
            # set the figure window size to the maximum
            newfig.set_size_inches(18.5, 10.5)
            # add verical lines to seperate the different test conditions
            newAxis.axvline(datetime(2024, 7, 8, 14, 30), c="black", ls="--")
            newAxis.axvline(datetime(2024, 7, 11, 15, 40), c="black", ls="--")
            newAxis.axvline(datetime(2024, 7, 22, 16, 41), c="black", ls="--")
            newAxis.axvline(datetime(2024, 7, 24, 13, 37), c="black", ls="--")
            newAxis.axvline(datetime(2024, 7, 26, 11, 6), c="black", ls="--")

            vPos = {"pH": -0.1, "ORP": 100, "thermistor Temperature": 0.5, "tC": 18}[unitLabel]
            offset = 1.0
            offsetStep = 0
            newAxis.text(datetime(2024, 7, 5, 12, 5), vPos * offset, "Test setup assembly")
            offset += offsetStep
            newAxis.text(datetime(2024, 7, 8, 14, 35), vPos * offset, "Air temperature\nincrease")
            offset += offsetStep
            newAxis.text(
                datetime(2024, 7, 11, 15, 45),
                vPos * offset,
                "Water temperature increase 1st attempt\n(setup has broken down)",
            )
            offset += offsetStep
            newAxis.text(datetime(2024, 7, 22, 16, 46), vPos * offset, "Test setup\nreassembly")
            offset += offsetStep
            newAxis.text(datetime(2024, 7, 24, 13, 42), vPos * offset, "Water\ntemperature\nincrease\n2nd attempt")
            offset += offsetStep
            newAxis.text(
                datetime(2024, 7, 26, 11, 11),
                vPos * offset,
                "Test left running at\ntemperature limits\nand using gold reference\nprobe",
            )

            plots.update({unitLabel: (newfig, newAxis)})

    # linestyleDict = {"pH": "--", "ORP": ":", "C": "-", "tC": "-"}
    markerDict = {"pH": "o", "ORP": "s", "C": "D", "tC": "x"}
    timeRanges = {
        "Test setup assembly": [datetime(2024, 7, 5, 12, 5), datetime(2024, 7, 8, 14, 30)],
        "Air temperature increase": [datetime(2024, 7, 8, 14, 35), datetime(2024, 7, 11, 15, 40)],
        "Water temperature increase 1st attempt": [datetime(2024, 7, 11, 15, 45), datetime(2024, 7, 15, 13)],
        "Test setup reassembly": [datetime(2024, 7, 22, 16, 46), datetime(2024, 7, 24, 13, 37)],
        "Water temperature increase 2nd attempt": [datetime(2024, 7, 25, 12, 0), datetime(2024, 7, 26, 11, 6)],
        "Test left running at temperature limits and using gold reference probe": [
            datetime(2024, 7, 26, 11, 11),
            dataSeries[label][0][-1] + timedelta(hours=2),
        ],
    }

    for label in dataSeries:
        unitLabel = channelConfig[label]["displayUnit"]
        displayLabel = channelConfig[label]["label"]
        concatenatedTime, concatenatedData, indexChain = dataSeries[label]

        # plot the data
        if unitLabel == "ORP":
            yData = concatenatedData * 1000
        else:
            yData = concatenatedData
        plots[unitLabel][1].plot(
            concatenatedTime[indexChain[0][0] : indexChain[-1][1]],
            yData,
            label=f"{displayLabel}",
            # linestyle=linestyleDict[unitLabel],
            # marker=markerDict[unitLabel],
        )
        
    # save the plots
    for plot in plots:
        plots[plot][0].savefig(f"{saveDir}/general view {plot}.png")

    for timeRange in timeRanges:
        print(f"plotting {timeRange}")

        for plot in plots:
            currAxis: plt.Axes = plots[plot][1]
            currFigure: plt.Figure = plots[plot][0]
            currAxis.set_title(f"Focused view of variable {plot} during \"{timeRange}\" period")
            currAxis.legend(title=plot)
            currAxis.set_xlim(timeRanges[timeRange])

        # plt.show()

        # save the plots
        for plot in plots:
            plots[plot][0].savefig(f"{saveDir}/{timeRange}-{plot}.png")

    # plot twinx for the temperature and ORP
    fig: plt.Figure
    ax1: plt.Axes
    ax2: plt.Axes
    fig, ax1 = plt.subplots()
    ax2 = ax1.twinx()
    ax1.set_xlabel("Time")
    ax1.set_ylabel("Temperature (°C)")
    ax2.set_ylabel("ORP (mV)")
    ax1.set_title("Temperature and ORP")

    for label in dataSeries:
        unitLabel = channelConfig[label]["displayUnit"]
        displayLabel = channelConfig[label]["label"]
        concatenatedTime, concatenatedData, indexChain = dataSeries[label]

        if unitLabel == "ORP":
            yData = concatenatedData * 1000
        else:
            yData = concatenatedData

        if unitLabel == "tC":
            ax1.plot(
                concatenatedTime[indexChain[0][0] : indexChain[-1][1]],
                yData,
                label=f"{displayLabel}",
                linestyle="-",
            )
        if unitLabel == "ORP":
            ax2.plot(
                concatenatedTime[indexChain[0][0] : indexChain[-1][1]],
                yData,
                label=f"{displayLabel}",
                linestyle="--",
            )

    ax1.legend(title="Temperature")
    ax2.legend(title="ORP")
    # set the figure margins to the minimum
    fig.subplots_adjust(left=0.075, right=0.925, top=0.925, bottom=0.075)
    # set the figure window size to the maximum
    fig.set_size_inches(18.5, 10.5)

    ax1.set_xlim(timeRanges["Air temperature increase"])
    fig.savefig(f"{saveDir}/Temperature and ORP air increase.png")

    # plt.show()

    ax1.set_xlim(timeRanges["Water temperature increase 1st attempt"])
    fig.savefig(f"{saveDir}/Temperature and ORP water increase 1st attempt.png")

    ax1.set_xlim(timeRanges["Water temperature increase 2nd attempt"])
    fig.savefig(f"{saveDir}/Temperature and ORP water increase 2nd attempt.png")



def main():
    args = setupParser()
    data = loadFile(args.path, args)
    if args.channelconfig is not None:
        channelConfig = loadChannelConfig(args.channelconfig)

    pckData = packageData(data, args, channelConfig)
    plotData(pckData, args, channelConfig)


if __name__ == "__main__":
    main()
