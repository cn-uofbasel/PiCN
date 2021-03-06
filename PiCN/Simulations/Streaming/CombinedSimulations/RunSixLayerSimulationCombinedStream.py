from SixLayerStreamingScenarioCombined import simulation

time_list = []
amount_of_runs = 15
amount_of_parts = 20

for i in range (0, amount_of_runs):
    time = simulation(False, amount_of_parts)
    print("RUN", i + 1)
    if time:
        time_list.append(time)


print("Improved", time_list)

with open('sixlayerstreamingscenario_combined_stream.txt', 'w') as file:
    for run in time_list:
        file.write("%f\n" % run)
file.close()

raise KeyboardInterrupt