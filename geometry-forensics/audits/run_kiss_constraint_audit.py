# run_kiss_constraint_audit.py — Measuring the Kiss Constraint Penalty from Real Telemetry
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

def analyze_kiss_constraint(hop_event, F: FieldParams):
    """
    Compares direct chord distance vs. the detour route passing through the kiss point,
    isolating the geometric cost of the kiss constraint (Delta L_kiss).
    """
    ch_from = hop_event["from"]["c"]
    ch_to = hop_event["to"]["c"]
    
    z_start = hop_event["from"]["z"]
    z_end = hop_event["to"]["z"]
    phi_start = hop_event["from"]["phi"]
    phi_end = hop_event["to"]["phi"]
    
    # 1. Real world positions from telemetry
    start_pos = world_position(F, ch_from, phi_start, z_start)
    end_pos = world_position(F, ch_to, phi_end, z_end)
    
    # 2. Theoretical kiss position for this channel pair
    delta_x = abs(F.channel_centers[ch_to] - F.channel_centers[ch_from])
    z_kiss = -math.log(delta_x / (2.0 * F.R0)) / F.beta
    
    kiss_pos = np.array([
        (F.channel_centers[ch_from] + F.channel_centers[ch_to]) / 2.0,
        0.0,
        z_kiss
    ])
    
    # 3. Geometric comparisons
    l_direct = np.linalg.norm(end_pos - start_pos)
    l_approach = np.linalg.norm(kiss_pos - start_pos)
    l_departure = np.linalg.norm(end_pos - kiss_pos)
    l_via_kiss = l_approach + l_departure
    
    delta_l_kiss = l_via_kiss - l_direct
    delta_z_sim = z_end - z_start
    
    return {
        "transition": f"Ch {ch_from} -> {ch_to}",
        "sim_axial_jump": delta_z_sim,
        "l_direct": l_direct,
        "l_via_kiss": l_via_kiss,
        "delta_l_kiss": delta_l_kiss
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
    
    print(f"=== VVB Kiss Constraint Penalty Audit ({steps} steps) ===")
    
    transition_records = {}
    
    for t in range(steps):
        frame = step(packets, F, pol, frame_now=t, stalls=True, stall_vz=0.0)
        hops = frame.get("hops", [])
        
        for hop in hops:
            metrics = analyze_kiss_constraint(hop, F)
            key = metrics["transition"]
            if key not in transition_records:
                transition_records[key] = []
            transition_records[key].append(metrics)
            
    print("\n--- Kiss Constraint Matrix (Real Telemetry) ---")
    print(f"{'Transition':<15} | {'Count':<6} | {'Direct (L_dir)':<15} | {'Via Kiss (L_kiss)':<18} | {'Kiss Penalty (Delta)'}")
    print("-" * 75)
    
    for key, records in sorted(transition_records.items()):
        directs = [r["l_direct"] for r in records]
        kiss_routes = [r["l_via_kiss"] for r in records]
        penalties = [r["delta_l_kiss"] for r in records]
        
        print(f"{key:<15} | {len(records):<6} | {np.mean(directs):<15.3f} | {np.mean(kiss_routes):<18.3f} | {np.mean(penalties):<18.3f}")

if __name__ == "__main__":
    main()