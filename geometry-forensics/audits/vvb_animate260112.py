# Copyright 2026 James Scott Graber and Lumen Virtus
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# vvb_animate_ready.py — 5-channel VVB + PCA demo with logging
import math, random
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import json
import time

from dataclasses import dataclass
from typing import Optional, List
from matplotlib.widgets import Slider

LOG_EVERY = 20   # print every 20th frame
current_interval_ms = 50

# ---------- Simulation Classes ----------
@dataclass
class Packet:
    pid: int
    payload: bytes = b''

@dataclass
class Particle:
    id: int
    channel: int
    phi: float
    z: float
    ttl: int = 10_000
    priority: int = 1
    allowed_mask: int = 0xFFFFFFFF
    last_switch: int = -10_000
    hop_count: int = 0
    packet: Optional[Packet] = None

@dataclass
class FieldParams:
    R0: float
    beta: float
    k: float
    channel_centers: List[int]
    channel_gain: dict = None

@dataclass
class SwitchPolicy:
    phi_min: float = 0.2
    z_min: float = 0.2
    prefer_kiss: bool = False
    hysteresis_frames: int = 5

# ---------- Simulation Utilities ----------
def wrap_angle(phi):
    while phi < 0: phi += 2*math.pi
    while phi >= 2*math.pi: phi -= 2*math.pi
    return phi

def radius_at_z(F, z):
    return F.R0 * math.exp(-F.beta * z)

def step(packets, F, pol, frame_now, omega=0.1, vz=0.03, stalls=False):
    deliveries = 0
    delivered_packets = []

    for p in packets:
        p.phi = wrap_angle(p.phi + omega)
        p.z += vz
        if p.z >= 4.0:
            if p.packet is not None:
                deliveries += 1
                delivered_packets.append(p.packet)
                p.packet = None
            p.z -= 4.0
    # Build frame state
    state = [{"id": p.id, "channel": p.channel, "phi": p.phi,
              "z": p.z, "hop_count": p.hop_count,
              "packet": p.packet.pid if p.packet else None}
             for p in packets]

    return {
        "t": frame_now,
        "packets": state,
        "deliveries": deliveries,
        "delivered_packets": [p.pid for p in delivered_packets]
    }

# ---------- Simulation Parameters ----------
CHANNELS = [-4, -2, 0, 2, 4]
PACKETS_N = 40
STEPS = 200
R0, BETA, K = 3.0, 0.18, 0.35
omega, vz, stalls = 0.1, 0.03, True

# ---------- Field and Policy ----------
F = FieldParams(R0=R0, beta=BETA, k=K, channel_centers=CHANNELS)
F.channel_gain = {i: 1.0 for i in range(len(F.channel_centers))}
pol = SwitchPolicy()
rng = random.Random(42)

# ---------- Initialize packets ----------
packets = [
    Particle(id=i,
             channel=i % len(F.channel_centers),
             phi=rng.random()*2*math.pi,
             z=rng.random()*3.6,
             hop_count=0,
             packet=None)
    for i in range(PACKETS_N)
]

# ---------- Visualization ----------
fig, ax = plt.subplots(figsize=(9,6))
plt.subplots_adjust(bottom=0.12)  # give room for slider

ax.set_xlim(-8, 8)
ax.set_ylim(0, 4.0)
ax.set_xlabel("Channels")
ax.set_ylabel("Z / axial position")
ax.set_title("VVB Demo — Packets + Logging")

channel_color_map = {
    -4: (1.0, 0.0, 0.0),
    -2: (1.0, 0.5, 0.0),
     0: (0.0, 1.0, 0.0),
     2: (0.0, 0.5, 1.0),
     4: (0.0, 0.0, 1.0),
}

def init_scatter():
    xs, ys, cs = [], [], []
    for p in packets:
        Xc = F.channel_centers[p.channel]
        r = radius_at_z(F, p.z)
        theta = p.phi - F.k*p.z
        xs.append(Xc + r*math.cos(theta))
        ys.append(p.z)
        cs.append(channel_color_map[CHANNELS[p.channel]][:3])
    return xs, ys, cs

xs, ys, cs = init_scatter()
scat = ax.scatter(xs, ys, s=40, c=cs)
annotations = [ax.text(xs[i], ys[i]+0.05, str(p.hop_count), fontsize=6)
               for i, p in enumerate(packets)]

# ---------- Animation Function ----------
def animate(frame):
    xs, ys, cs, sizes = [], [], [], []

    t0 = time.perf_counter()

    # Step the particles
    step(
        packets,
        F,
        pol,
        frame_now=frame,
        omega=omega,
        vz=vz,
        stalls=stalls
    )

    # ---------- Columnar console output (throttled) ----------
    if frame % LOG_EVERY == 0:
        if frame == 0:
            header = f"{'Frame':>5} | {'ID':>4} | {'Ch':>2} | {'Phi':>7} | {'Z':>6} | {'Hop':>3} | {'Pkt':>3}"
            print(header)
            print("-" * len(header))

        for p in packets:
            pid = p.packet.pid if p.packet else "N"
            print(
                f"{frame:5d} | "
                f"{p.id:4d} | "
                f"{p.channel:2d} | "
                f"{p.phi:7.3f} | "
                f"{p.z:6.3f} | "
                f"{p.hop_count:3d} | "
                f"{str(pid):>3}"
            )

    # ---------- Depth scaling for visualization ----------
    depths = []
    for p in packets:
        r = radius_at_z(F, p.z)
        theta = p.phi - F.k*p.z
        depths.append(r * math.sin(theta))

    min_depth, max_depth = min(depths), max(depths)
    MIN_SIZE, MAX_SIZE = 20, 80

    # ---------- Build plotting arrays ----------
    for p in packets:
        Xc = F.channel_centers[p.channel]
        r = radius_at_z(F, p.z)
        theta = p.phi - F.k*p.z
        x = Xc + r*math.cos(theta)
        y = p.z

        xs.append(x)
        ys.append(y)
        cs.append(channel_color_map[CHANNELS[p.channel]][:3])

        depth = r * math.sin(theta)
        t = (depth - min_depth) / (max_depth - min_depth) if max_depth != min_depth else 0.5
        t = max(0.0, min(1.0, t))
        sizes.append(MIN_SIZE + (1 - t)**1.5 * (MAX_SIZE - MIN_SIZE))

    # ---------- Update scatter plot ----------
    scat.set_offsets(list(zip(xs, ys)))
    scat.set_color(cs)
    scat.set_sizes(sizes)

    # ---------- Update hop annotations ----------
    for i, p in enumerate(packets):
        annotations[i].set_position((xs[i], ys[i]+0.05))
        annotations[i].set_text(str(p.hop_count))

    dt = (time.perf_counter() - t0) * 1000.0
    if frame % 10 == 0:
        print(f"[frame {frame}] render+log time: {dt:.1f} ms  (interval: {current_interval_ms} ms)")

    return scat, *annotations

# ---------- Run Animation ----------
ani = animation.FuncAnimation(
    fig,
    animate,
    frames=STEPS,
    interval=50,  # milliseconds between frames
    blit=True
)

# ---------- Speed Slider ----------
ax_speed = fig.add_axes([0.1, 0.02, 0.6, 0.03])
s_speed = Slider(ax_speed, 'Speed (ms/frame)', 10, 1000, valinit=50)

def update_speed(val):
    global current_interval_ms
    interval = int(s_speed.val)
    current_interval_ms = interval
    print("slider interval =", interval)
    if getattr(ani, "event_source", None) is not None:
        ani.event_source.interval = interval
        ani.event_source.stop()
        ani.event_source.start()

s_speed.on_changed(update_speed)

def on_close(event):
    try:
        if ani and getattr(ani, "event_source", None):
            ani.event_source.stop()
    except Exception:
        pass

fig.canvas.mpl_connect("close_event", on_close)

plt.show()
