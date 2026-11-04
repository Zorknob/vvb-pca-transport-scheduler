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
# run_inspect_2to0_hop.py — Detailed Breakdown of a Ch 2 -> 0 Hop Event
import math
import random
import numpy as np
from vvb_min260112 import FieldParams, SwitchPolicy, Particle, step, radius_at_z

def world_position(F: FieldParams, channel: int, phi: float, z: float) -> np.ndarray:
    r = radius_at_z(F, z)
    theta = phi - F.k * z
    return np.array([
        F.channel_centers[channel] + r * np.cos(theta),
        r * np.sin(theta),
        z
    ])

def main():
    channels = [-4.0, 0.0, 4.0]
    F = FieldParams(R0=3.0, beta=0.18, k=0.35, channel_centers=channels)
    pol = SwitchPolicy()
    
    rng = random.Random(42)
    packets_n = 60
    steps = 100  # Just enough steps to catch a 2 -> 0 transition
    
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
    
    inspected = False
    for t in range(steps):
        frame = step(packets, F, pol, frame_now=t, stalls=True, stall_vz=0.0)
        hops = frame.get("hops", [])
        
        for hop in hops:
            ch_from = hop["from"]["c"]
            ch_to = hop["to"]["c"]
            
            if ch_from == 2 and ch_to == 0 and not inspected:
                z_start = hop["from"]["z"]
                z_end = hop["to"]["z"]
                phi_start = hop["from"]["phi"]
                phi_end = hop["to"]["phi"]
                
                start_pos = world_position(F, ch_from, phi_start, z_start)
                end_pos = world_position(F, ch_to, phi_end, z_end)
                
                # Channel separation & theoretical kiss elevation
                delta_x = abs(F.channel_centers[ch_to] - F.channel_centers[ch_from])
                z_kiss_theoretical = -math.log(delta_x / (2.0 * F.R0)) / F.beta
                
                kiss_pos = np.array([
                    (F.channel_centers[ch_from] + F.channel_centers[ch_to]) / 2.0,
                    0.0,
                    z_kiss_theoretical
                ])
                
                l_direct = np.linalg.norm(end_pos - start_pos)
                l_approach = np.linalg.norm(kiss_pos - start_pos)
                l_departure = np.linalg.norm(end_pos - kiss_pos)
                l_via_kiss = l_approach + l_departure
                delta_l = l_via_kiss - l_direct
                
                print("=== Detailed Ch 2 -> 0 Hop Inspection ===")
                print(f"  Start Coordinates (P_A) : {start_pos} (z_start = {z_start:.3f})")
                print(f"  End Coordinates   (P_B) : {end_pos} (z_end = {z_end:.3f})")
                print(f"  Delta X between channels: {delta_x:.1f}")
                print(f"  Theoretical Kiss Z      : {z_kiss_theoretical:.3f}")
                print(f"  Kiss Position (P_K)     : {kiss_pos}")
                print("--------------------------------------------------")
                print(f"  Approach Bridge (P_A -> P_K) : {l_approach:.3f} units")
                print(f"  Departure Bridge (P_K -> P_B): {l_departure:.3f} units")
                print(f"  Direct Chord (L_direct)      : {l_direct:.3f} units")
                print(f"  Via-Kiss Route (L_via_kiss)  : {l_via_kiss:.3f} units")
                print(f"  Calculated Kiss Penalty      : {delta_l:.3f} units")
                
                inspected = True
                break
        if inspected:
            break

if __name__ == "__main__":
    main()
