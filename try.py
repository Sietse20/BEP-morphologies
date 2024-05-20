import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

def gaussian(x, mu, sigma, amplitude=1):
    return amplitude * np.exp(-((x - mu) ** 2) / (2 * sigma ** 2))

# Set up the figure and axis
fig, ax = plt.subplots()
x = np.linspace(-10, 10, 1000)
line, = ax.plot(x, gaussian(x, 0, 1), lw=2)

# Set axis limits
ax.set_xlim(-10, 10)
ax.set_ylim(0, 1)

# Update function for the animation
def update(frame):
    mu = frame / 10.0 - 5  # Move the mean from -5 to 5
    y = gaussian(x, mu, 1)
    line.set_ydata(y)
    return line,

# Create the animation
ani = FuncAnimation(fig, update, frames=np.arange(0, 100), blit=True, interval=50)

# Show the animation
plt.show()
