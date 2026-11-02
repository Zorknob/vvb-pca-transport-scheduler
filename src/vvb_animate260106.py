# vvb_animate.py — 5-channel VVB + PCA demo with visualization
import math, random
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from vvb_min import FieldParams, Particle, SwitchPolicy, step, wrap_angle, radius_at_z, apply_switch, prefer_kiss_height

# ---------- Simulation Parameters ----------
CHANNELS = [-4, -2, 0, 2, 4]   # 5 channels
PACKETS_N = 60
STEPS = 300
R0 = 3.0
BETA = 0.18
K = 0.35
MAX_HOPS_BEFORE_RENORM = 8
MIN_SIZE = 10
MAX_SIZE = 120
min_depth = -R0
max_depth =  R0

# ---------- Initialize Field and Packets ----------
F = FieldParams(R0=R0, beta=BETA, k=K, channel_centers=CHANNELS)
pol = SwitchPolicy()
rng = random.Random(42)

packets = []
for i in range(PACKETS_N):
    ch = i % len(F.channel_centers)
    phi = rng.random() * 2*math.pi
    z = rng.random() * 4.0 * 0.9
    packets.append(Particle(id=i, channel=ch, phi=phi, z=z, hop_count=0))

# ---------- Renormalization Function ----------
def renormalize(p: Particle):
    if p.hop_count >= MAX_HOPS_BEFORE_RENORM:
        # Snap phi to ideal phase
        theta = math.atan2(math.sin(p.phi), math.cos(p.phi))
        p.phi = wrap_angle(theta + F.k*p.z)
        p.hop_count = 0

# ---------- Visualization Setup ----------
fig, ax = plt.subplots(figsize=(8,6))
ax.set_xlim(-8, 8)  # full vortex view
ax.set_ylim(0, 4.0)
ax.set_xlabel("Channels")
ax.set_ylabel("Z / axial position")
ax.set_title("VVB Phase-Channel Allocator — 5-Channel Demo")

# ---------- Assign Colors by Channel ----------
channel_colors = plt.cm.tab10(range(len(CHANNELS)))
channel_color_map = {ch: channel_colors[i] for i, ch in enumerate(CHANNELS)}

# ---------- Depth bounds for sizing ----------
min_depth = -R0   # r * sin(theta) can swing from -R0 to +R0
max_depth = R0

# ---------- Initial positions & colors ----------
xs, ys, cs = [], [], []
for p in packets:
    Xc = F.channel_centers[p.channel]
    r = radius_at_z(F, p.z)
    theta = p.phi - F.k*p.z
    xs.append(Xc + r * math.cos(theta))
    ys.append(p.z)
    cs.append(channel_color_map[F.channel_centers[p.channel]])

# ---------- Scatter plot ----------
scat = ax.scatter(xs, ys, s=40, c=cs)

# ---------- Hop count annotations ----------
annotations = [ax.text(xs[i], ys[i]+0.1, str(p.hop_count), fontsize=6)
               for i, p in enumerate(packets)]

# ---------- Draw channel lines ----------
for ch, col in channel_color_map.items():
    ax.axvline(x=ch, color=col, linestyle='--', alpha=0.3)

# ---------- Animation Step ----------
def animate(frame_num):
    global packets

    # advance simulation
    step(packets, F, pol, frame_now=frame_num, stalls=True, stall_vz=0.0)

    xs, ys, cs, sizes = [], [], [], []
    for p in packets:
        renormalize(p)

        Xc = F.channel_centers[p.channel]
        r = radius_at_z(F, p.z)
        theta = p.phi - F.k*p.z
        x = Xc + r * math.cos(theta)
        y = p.z

        xs.append(x)
        ys.append(y)
        cs.append(channel_color_map[F.channel_centers[p.channel]])

        # virtual depth (toward / away from viewer)
        depth = r * math.sin(theta)   # or cos(theta)

        # Normalize depth to 0–1
        t = (depth - min_depth) / (max_depth - min_depth)
        t = max(0.0, min(1.0, t))  # clamp for safety

        # Invert so closer = larger
        size = MIN_SIZE + (1 - t)**1.5 * (MAX_SIZE - MIN_SIZE)

        sizes.append(size)    

    # Update scatter
    scat.set_offsets(np.c_[xs, ys])
    scat.set_color(cs)
    scat.set_sizes(sizes)

    # Update hop annotations
    for idx, p in enumerate(packets):
        annotations[idx].set_position((xs[idx], ys[idx]+0.1))
        annotations[idx].set_text(str(p.hop_count))

    return scat, *annotations

def on_close(event):
    try:
        ani.event_source.stop()
    except Exception:
        pass
    plt.close(event.canvas.figure)

# ---------- Run Animation ----------
ani = animation.FuncAnimation(
    fig,
    animate,
    frames=STEPS,
    interval=50,
    blit=True
)

plt.show()
