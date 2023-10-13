import matplotlib.pyplot as plt
import numpy as np

final_distance = 200
distances = list(range(1, final_distance + 1, 10))

# Load rates from the file

rates_Ac_l2r = np.loadtxt('data/rates/network(N=2RoutersMultiChannels.json)(Swapping_order=left_to_right).txt')
rates_Ac_r2l = np.loadtxt('data/rates/network(N=2RoutersMultiChannels.json)(Swapping_order=right_to_left).txt')




#

# Plotting the moving average curve
fig, ax = plt.subplots()
ax.set_xscale('linear')
ax.set_yscale('log')
ax.set_ylim([10 ** (2), 10 ** 5])
#ax.set_yticks([10**-4,10**-2,10**0, 10**2, 10**4])




ax.plot(distances, rates_Ac_l2r, label='rates (case 1)')
ax.plot(distances, rates_Ac_r2l, label='rates (case 2)')



#ax.plot(distances, rates2e6, label='rates 2e6')
#ax.plot(distances, ratesinf, label='rates inf')
# Add labels and titles
ax.set_xlabel('Distance in Km')
ax.set_ylabel('Rate (entanglement per second)')
ax.set_title('Rates vs. Distance')
ax.legend()

# Show the plot
plt.show()
