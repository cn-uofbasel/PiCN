import gc
from datetime import datetime

import matplotlib.pyplot as plt
import numpy as np
from ThreeLayerStreamingScenario import simulation

time_list = []
time_list_classic = []
plot = True

for i in range (0,20):
    time = simulation(False)
    if time:
        time_list.append(time)
    gc.collect()

# for i in range (0,10):
#     time = simulation(True)
#     if time:
#         time_list_classic.append(time)
#     gc.collect()


print(time_list)
#print(time_list_classic)

if plot:
    plt.plot(list(range(1,21)), time_list, 'ro')
    #plt.plot([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], time_list_classic, 'bo')
    plt.axis([0, 11, 20.2, 20.8])
    plt.xticks(np.arange(0, 21, 1))
    plt.xlabel("run number")
    plt.ylabel("time in s")
    plt.title("Three hop scenario " + datetime.now().strftime("%H:%M:%S"))
    plt.savefig('three_hop_scenario.png')
    plt.show()