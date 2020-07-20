import matplotlib.pyplot as plt
import numpy as np

def get_measurements(filename: str):
    time_list = []
    with open(filename, 'r') as file:
        line = file.readline()
        while line:
            time_list.append(float(line[:-1]))
            line = file.readline()
    file.close()
    return time_list


three_time_list_stream = get_measurements('threelayerstreamingscenario_combined_stream.txt')
amount_of_runs = len(three_time_list_stream)
three_time_list_classic = get_measurements('threelayerstreamingscenario_combined_classic.txt')

plt.figure(0)
plt.plot(list(range(1, amount_of_runs+1)), three_time_list_stream, 'ro', label="stream")
plt.plot(list(range(1, amount_of_runs+1)), three_time_list_classic, 'bo', label="classic")
plt.legend(loc="upper left")
plt.axis([0, amount_of_runs+1, 39.25, 40.25])
plt.xticks(np.arange(0, amount_of_runs+1, 1))
plt.xlabel("run number")
plt.ylabel("time in s")
plt.title("Three hop scenario combined")
plt.savefig('three_hop_scenario_combined.png')
plt.show()

six_time_list_stream = get_measurements('sixlayerstreamingscenario_combined_stream.txt')
amount_of_runs = len(six_time_list_stream)
six_time_list_classic = get_measurements('sixlayerstreamingscenario_combined_classic.txt')

plt.figure(1)
plt.plot(list(range(1, amount_of_runs+1)), six_time_list_stream, 'ro', label="stream")
plt.plot(list(range(1, amount_of_runs+1)), six_time_list_classic, 'bo', label="classic")
plt.legend(loc="upper left")
plt.axis([0, amount_of_runs+1, 39.4, 40.4])
plt.xticks(np.arange(0, amount_of_runs+1, 1))
plt.xlabel("run number")
plt.ylabel("time in s")
plt.title("Six hop scenario combined")
plt.savefig('six_hop_scenario_combined.png')
plt.show()

# Error bars
three_time_list_stream = np.array(three_time_list_stream)
three_time_list_classic = np.array(three_time_list_classic)
six_time_list_stream = np.array(six_time_list_stream)
six_time_list_classic = np.array(six_time_list_classic)

three_stream_mean = np.mean(three_time_list_stream)
three_classic_mean = np.mean(three_time_list_classic)
six_stream_mean = np.mean(six_time_list_stream)
six_classic_mean = np.mean(six_time_list_classic)

three_stream_median = np.median(three_time_list_stream)
three_classic_median = np.median(three_time_list_classic)
six_stream_median = np.mean(six_time_list_stream)
six_classic_median = np.mean(six_time_list_classic)

three_stream_std = np.std(three_time_list_stream)
three_classic_std = np.std(three_time_list_classic)
six_stream_std = np.std(six_time_list_stream)
six_classic_std = np.std(six_time_list_classic)

labels = ["three stream", "three classic", "six stream", "six classic"]
x_pos = np.arange(len(labels))
means = [three_stream_mean, three_classic_mean, six_stream_mean, six_classic_mean]
print(three_stream_median, three_stream_mean)
print(three_classic_median, three_classic_mean)
print(six_stream_median, six_stream_mean)
print(six_classic_median, six_classic_mean)
medians = [three_stream_median, three_classic_median, six_stream_median, six_classic_median]
error = [three_stream_std, three_classic_std, six_stream_std, six_classic_std]

fig, temp = plt.subplots()
temp.bar(x_pos, medians, yerr=error, align="center", alpha=1, ecolor="black", capsize=30)
temp.set_ylabel("time in s")
temp.set_xticks(x_pos)
temp.set_xticklabels(labels)
temp.set_title('Combined scenario with three and six layer simulations (with median)')
temp.yaxis.grid(True)

plt.ylim(39,40.5)
plt.savefig('combined_errorbar_plot_median.png')
plt.show()