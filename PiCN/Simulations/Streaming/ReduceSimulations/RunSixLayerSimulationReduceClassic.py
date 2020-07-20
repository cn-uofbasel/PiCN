from SixLayerStreamingScenarioReduce import simulation

time_list_classic = []
amount_of_runs = 15
amount_of_parts = 20

for i in range (0, amount_of_runs):
    time = simulation(True, amount_of_parts)
    print("RUN", i + 1)
    if time:
        time_list_classic.append(time)


print("Classic", time_list_classic)

with open('sixlayerstreamingscenario_reduce_classic.txt', 'w') as file:
    for run in time_list_classic:
        file.write("%f\n" % run)
file.close()
