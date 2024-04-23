import matplotlib as plb
import matplotlib.pyplot as plt
import numpy as np
import csv

filename = 'grace_drive.csv'
with open(filename, mode='r') as csvfile:
    reader = csv.reader(csvfile)
    position_x = [0.0]
    position_y = [0.0]
    position_z = [0.0]
    index = 0
    pre_time = 0
    for row in reader:
        if "time" in row:
            continue
        if index == 0:
            index = index + 1
            continue
        new_x = position_x[-1] + float(row[4]) * (float(row[0]) - pre_time)
        new_y = position_y[-1] + float(row[5]) * (float(row[0]) - pre_time)
        new_z = position_z[-1] + float(row[6]) * (float(row[0]) - pre_time)
        pre_time = float(row[0])
        position_x.append(new_x)
        position_y.append(new_y)
        position_z.append(new_z)
    fig = plt.figure()
    ax1 = plt.axes(projection='3d')
    xd = np.array(position_x)
    yd = np.array(position_y)
    zd = np.array(position_z)
    # print(zd)
    ax1.set_ylim3d(-100, 100)
    ax1.set_zlim3d(-100, 100)
    ax1.scatter(xd, yd, zd, c='r')
    plt.savefig("111.jpg")
    plt.show(block=False)

    #
    # fig = plt.figure()
    # ax1 = plt.axes()
    # xd = np.array(position_x)
    # yd = np.array(position_y)
    # plt.ylim((-100, 100))
    # ax1.scatter(xd, yd, c='r')
    # plt.show(block=False)
