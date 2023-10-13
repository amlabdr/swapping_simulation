import matplotlib.pyplot as plt
import numpy as np

final_distance = 200
distances = list(range(1, final_distance + 1, 10))

# Load rates from the file

rates_left_to_right_eff_dec = np.loadtxt('data/rates/network(N=2Routers.json)(Swapping_order=left_to_right)(memo_eff=decreasing).txt')
rates_left_to_right_eff_inc = np.loadtxt('data/rates/network(N=2Routers.json)(Swapping_order=left_to_right)(memo_eff=increasing).txt')
rates_right_to_left_eff_dec = np.loadtxt('data/rates/network(N=2Routers.json)(Swapping_order=right_to_left)(memo_eff=decreasing).txt')
rates_right_to_left_eff_inc = np.loadtxt('data/rates/network(N=2Routers.json)(Swapping_order=right_to_left)(memo_eff=increasing).txt')


# Plotting the moving average curve
fig, ax = plt.subplots()
ax.set_xscale('linear')
ax.set_yscale('log')
ax.set_ylim([10 ** (0), 10 ** 5])
#ax.set_yticks([10**-4,10**-2,10**0, 10**2, 10**4])
ax.set_yticks([10**0, 10**2, 10**4])




#ax.plot(distances, rates100ms, label='rates100ms')
#ax.plot(distances, rates900ms, label='rates900ms')
#ax.plot(distances, rates1s, label='rates1s')
#ax.plot(distances, rates10s, label='rates10s')
# Plot each line with different colors, line styles, and markers

ax.plot(distances, rates_left_to_right_eff_dec, linestyle='--', marker='o', label='rates order = left_to_right eff = decreasing')
ax.plot(distances, rates_right_to_left_eff_dec, linestyle='--', marker='o', label='rates order = right_to_left eff = decreasing')

ax.plot(distances, rates_left_to_right_eff_inc, linestyle='--', marker='o', label='rates order = left_to_right eff = increasing')
ax.plot(distances, rates_right_to_left_eff_inc, linestyle='--', marker='o', label='rates order = right_to_left eff = increasing')




#ax.plot(distances, rates2e6, label='rates 2e6')
#ax.plot(distances, ratesinf, label='rates inf')
# Add labels and titles
ax.set_xlabel('Distance in Km')
ax.set_ylabel('Rate (entanglement per second)')
ax.set_title('Rates vs. Distance')
ax.legend()

# Show the plot
plt.show()
