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
# run_geometry_audit.py — Detailed Hop & Kiss-Point Audit
import math
import random
import numpy as np
from vvb_min260112 import FieldParams, SwitchPolicy, Particle, step, radius_at_z

def world_position(F: FieldParams, channel: int, phi: float, z: float) -> np.ndarray:
    """Calculates true 3D world-space coordinates for a particle on a channel streamline."""
    r = radius_at_z(F, z)
    theta = phi - F.k * z
    return np.array([
        F.channel_centers[channel] + r * np.cos(theta),
        r * np.sin(theta),
        z
    ])

def audit_individual_hops(hop_event, F: FieldParams, hop_index: int):
    """
    Inspects individual hop endpoints, calculates straight-line distance,
    and measures distances relative to the midpoint/kiss approximation.
    """
    ch_from = hop_event["from"]["c"]
    ch_to = hop_event["to"]["c"]
    
    z_initial = hop_event["from"]["z"]
    z_final = hop_event["to"]["z"]
    phi_initial = hop_event["from"]["phi"]
    phi_final = hop_event["to"]["phi"]
    
    # 1. World-space coordinates
    start_pos = world_position(F, ch_from, phi_initial, z_initial)
    end_pos = world_position(F, ch_to, phi_final, z_final)
    
    # 2. Straight-line distance (L_straight)
    l_straight = np.linalg.norm(end_pos - start_pos)
    delta_z_sim = z_final - z_initial
    
    # 3. Midpoint / Kiss-point approximation test
    kiss_approximation = (start_pos + end_pos) / 2.0
    dist_start_to_kiss = np.linalg.norm(kiss_approximation - start_pos)
    dist_kiss_to_end = np.linalg.norm(end_pos - kiss_approximation)
    
    print(f"\n--- Hop {hop_index}: Channel {ch_from} -> {ch_to} ---")
    print(f"  Start Pos (X, Y, Z): {start_pos[0]:.2f}, {start_pos[1]:.2f}, {start_pos[2]:.2f}")
    print(f"  End Pos   (X, Y, Z): {end_pos[0]:.2f}, {end_pos[1]:.2f}, {end_pos[2]:.2f}")
    print(f"  Sim Axial Jump (Delta Z): {delta_z_sim:.3f}")
    print(f"  Straight-Line Distance (L_straight): {l_straight:.3f}")
    print(f"  Distance Start->Kiss: {dist_start_to_kiss:.3f} | Kiss->End: {dist_kiss_to_end:.3f}")

def main():
    channels = [-4.0, 0.0, 4.0]
    F = FieldParams(R0=3.0, beta=0.18, k=0.35, channel_centers=channels)
    pol = SwitchPolicy()
    
    rng = random.Random(42)
    packets_n = 60
    steps = 300
    
    packets = []
    for i in range(packets_n):
        p = Particle(
            id=i, 
            channel=i % len(F.channel_centers),
            phi=rng.random() * 2 * math.pi,
            z=rng.random() * 4.0 * 0.9
        )
        p.packet = None
        packets.append(p)
    
    print(f"=== Detailed VVB Hop & Kiss Audit ({steps} steps, {packets_n} packets) ===")
    
    total_hops = 0
    for t in range(steps):
        frame = step(packets, F, pol, frame_now=t, stalls=True, stall_vz=0.0)
        hops = frame.get("hops", [])
        
        for hop in hops:
            total_hops += 1
            audit_individual_hops(hop, F, total_hops)
            
    print(f"\n=== Audit Complete. Total Hops Inspected: {total_hops} ===")

if __name__ == "__main__":
    main()
