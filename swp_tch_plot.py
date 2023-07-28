import matplotlib.pyplot as plt
import numpy as np

final_distance = 200
distances = list(range(1, final_distance + 1, 10))

# Load rates from the file

rates1ms = np.loadtxt('data/rates/network(N=2Routers.json)(cohTime=1.000ms).txt')
rates10ms = np.loadtxt('data/rates/network(N=2Routers.json)(cohTime=10.000ms).txt')
rates100ms = np.loadtxt('data/rates/network(N=2Routers.json)(cohTime=100.000ms).txt')
rates1s= np.loadtxt('data/rates/network(N=2Routers.json)(cohTime=1000.000ms).txt')
ratesinf = np.loadtxt('data/rates/network(N=2Routers.json)(cohTime=inf).txt')



#

# Plotting the moving average curve
fig, ax = plt.subplots()
ax.set_xscale('linear')
ax.set_yscale('log')
ax.set_ylim([10 ** (0), 10 ** 5])
ax.set_yticks([10**-4,10**-2,10**0, 10**2, 10**4])




#ax.plot(distances, rates100ms, label='rates100ms')
#ax.plot(distances, rates900ms, label='rates900ms')
#ax.plot(distances, rates1s, label='rates1s')
#ax.plot(distances, rates10s, label='rates10s')
# Plot each line with different colors, line styles, and markers
ax.plot(distances, rates1ms, linestyle='--', marker='o', label='rates cohTime = 1ms')
ax.plot(distances, rates10ms, linestyle='-.', marker='D', label='rates cohTime = 10ms')
ax.plot(distances, rates100ms, linestyle=':', marker='s', label='rates cohTime = 100ms')
ax.plot(distances, rates1s, linestyle=':', marker='^', label='rates cohTime = 1s')
ax.plot(distances, ratesinf, linestyle='--', marker='x', label='rates cohTime = inf')


#ax.plot(distances, rates2e6, label='rates 2e6')
#ax.plot(distances, ratesinf, label='rates inf')
# Add labels and titles
ax.set_xlabel('Distance in Km')
ax.set_ylabel('Rate (entanglement per second)')
ax.set_title('Rates vs. Distance')
ax.legend()

# Show the plot
plt.show()
