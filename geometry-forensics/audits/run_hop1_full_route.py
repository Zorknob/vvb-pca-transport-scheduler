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
# run_route_cost_matrix.py — Observational Route-Cost Matrix Audit
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

def evaluate_candidate_route(hop_event, F: FieldParams):
    """
    Calculates candidate route cost (C_route) using approach and departure 
    bridge vectors through the theoretical kiss point, compared to axial jump.
    """
    ch_from = hop_event["from"]["c"]
    ch_to = hop_event["to"]["c"]
    
    z_start = hop_event["from"]["z"]
    z_end = hop_event["to"]["z"]
    phi_start = hop_event["from"]["phi"]
    phi_end = hop_event["to"]["phi"]
    
    # 1. Actual world positions at start and end
    start_pos = world_position(F, ch_from, phi_start, z_start)
    end_pos = world_position(F, ch_to, phi_end, z_end)
    
    # 2. Theoretical kiss height and position for this channel pair
    delta_x = abs(F.channel_centers[ch_to] - F.channel_centers[ch_from])
    # R0 * exp(-beta * z_kiss) = delta_x / 2 => z_kiss = -ln(delta_x / (2 * R0)) / beta
    z_kiss = -math.log(delta_x / (2.0 * F.R0)) / F.beta
    
    kiss_pos = np.array([
        (F.channel_centers[ch_from] + F.channel_centers[ch_to]) / 2.0,
        0.0,
        z_kiss
    ])
    
    # 3. Route segment costs (Candidate Chords through Kiss)
    l_approach = np.linalg.norm(kiss_pos - start_pos)
    l_departure = np.linalg.norm(end_pos - kiss_pos)
    c_route = l_approach + l_departure
    
    delta_z_sim = z_end - z_start
    
    return {
        "transition": f"Ch {ch_from} -> {ch_to}",
        "delta_x": delta_x,
        "sim_axial_jump": delta_z_sim,
        l_approach: l_approach,
        l_departure: l_departure,
        "c_route": c_route,
        "premium": c_route - delta_z_sim
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
    
    print(f"=== VVB Observational Route-Cost Matrix Audit ({steps} steps) ===")
    
    transition_records = {}
    
    for t in range(steps):
        frame = step(packets, F, pol, frame_now=t, stalls=True, stall_vz=0.0)
        hops = frame.get("hops", [])
        
        for hop in hops:
            metrics = evaluate_candidate_route(hop, F)
            key = metrics["transition"]
            if key not in transition_records:
                transition_records[key] = []
            transition_records[key].append(metrics)
            
    print("\n--- Route-Cost Matrix Summary ---")
    print(f"{'Transition':<15} | {'Count':<6} | {'Sim Jump':<10} | {'Route Cost (C)':<15} | {'Cost Premium':<12}")
    print("-" * 65)
    
    for key, records in sorted(transition_records.items()):
        sim_jumps = [r["sim_axial_jump"] for r in records]
        costs = [r["c_route"] for r in records]
        premiums = [r["premium"] for r in records]
        
        print(f"{key:<15} | {len(records):<6} | {np.mean(sim_jumps):<10.3f} | {np.mean(costs):<15.3f} | {np.mean(premiums):<12.3f}")

if __name__ == "__main__":
    main()
