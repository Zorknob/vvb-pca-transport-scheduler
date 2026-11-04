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
# run_axial_backtrack_audit.py — Measuring Axial Backtracking (B_axial)
import math
import random
import numpy as np
from vvb_min260112 import FieldParams, SwitchPolicy, Particle, step, radius_at_z

def analyze_axial_backtracking(hop_event, F: FieldParams):
    """
    Computes delta_z_kiss and B_axial to separate vertical backtracking 
    from lateral chord geometry.
    """
    ch_from = hop_event["from"]["c"]
    ch_to = hop_event["to"]["c"]
    
    z_start = hop_event["from"]["z"]
    z_end = hop_event["to"]["z"]
    
    # Global theoretical kiss elevation for this channel pair
    delta_x = abs(F.channel_centers[ch_to] - F.channel_centers[ch_from])
    z_kiss = -math.log(delta_x / (2.0 * F.R0)) / F.beta
    
    # 1. Distance from start to kiss elevation
    delta_z_kiss = z_start - z_kiss
    
    # 2. Minimum additional axial travel caused by routing through kiss elevation
    # B_axial = |z_start - z_kiss| + |z_end - z_kiss| - |z_end - z_start|
    b_axial = abs(z_start - z_kiss) + abs(z_end - z_kiss) - abs(z_end - z_start)
    
    return {
        "transition": f"Ch {ch_from} -> {ch_to}",
        "z_start": z_start,
        "z_end": z_end,
        "z_kiss": z_kiss,
        "delta_z_kiss": delta_z_kiss,
        "b_axial": b_axial,
        "is_high_start": z_start > (z_kiss + 1.0)
    }

def main():
    channels = [-4.0, 0.0, 4.0]
    F = FieldParams(R0=3.0, beta=0.18, k=0.35, channel_centers=channels)
    pol = SwitchPolicy()
    
    rng = random.Random(42)
    packets_n = 60
    steps = 400
    
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
    
    print(f"=== VVB Axial Backtracking Audit ({steps} steps) ===")
    
    transition_records = []
    
    for t in range(steps):
        frame = step(packets, F, pol, frame_now=t, stalls=True, stall_vz=0.0)
        hops = frame.get("hops", [])
        
        for hop in hops:
            metrics = analyze_axial_backtracking(hop, F)
            transition_records.append(metrics)
            
    print(f"\nTotal Hops Analyzed: {len(transition_records)}")
    print("-" * 75)
    print(f"{'Transition':<12} | {'Z_start':<8} | {'Z_end':<8} | {'Delta Z_kiss':<12} | {'B_axial (Extra Z)'}")
    print("-" * 75)
    
    for r in transition_records[:15]:  # Print first 15 for inspection
        print(f"{r['transition']:<12} | {r['z_start']:<8.2f} | {r['z_end']:<8.2f} | {r['delta_z_kiss']:<12.2f} | {r['b_axial']:<16.2f}")

if __name__ == "__main__":
    main()
