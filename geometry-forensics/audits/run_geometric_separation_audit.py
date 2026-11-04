# run_geometric_separation_audit.py — Measuring Actual Channel Clearance at Transfer Elevations
import math
import random
import numpy as np
from vvb_min260112 import FieldParams, SwitchPolicy, Particle, step, radius_at_z

def analyze_geometric_clearance(hop_event, F: FieldParams):
    """
    Computes channel separation D and diameter 2*R(z) at the exact transfer elevation z_start,
    evaluating whether the channels touch (gap = 0), overlap (gap < 0), or have a gap (gap > 0).
    """
    ch_from = hop_event["from"]["c"]
    ch_to = hop_event["to"]["c"]
    z_start = hop_event["from"]["z"]
    
    # 1. Channel span (Distance between centers)
    d_centers = abs(F.channel_centers[ch_to] - F.channel_centers[ch_from])
    
    # 2. Local channel radius and diameter at this transfer elevation
    r_local = radius_at_z(F, z_start)
    diameter_local = 2.0 * r_local
    
    # 3. Geometric gap / clearance
    # gap == 0 -> True Tangency (Kiss)
    # gap >  0 -> Gap between channels (No physical touch)
    # gap <  0 -> Overlap penetration
    gap = d_centers - diameter_local
    
    # Determine tier
    delta_x = d_centers
    z_kiss_base = -math.log(delta_x / (2.0 * F.R0)) / F.beta
    tier_interval = math.pi / F.k
    tier_offset = round((z_start - z_kiss_base) / tier_interval) if tier_interval > 0 else 0
    
    return {
        "transition": f"Ch {ch_from} -> {ch_to}",
        "z_start": z_start,
        "tier": tier_offset,
        "d_centers": d_centers,
        "diameter": diameter_local,
        "gap": gap,
        "status": "Tanget (Kiss)" if abs(gap) < 0.01 else ("Gap" if gap > 0 else "Overlap")
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
    
    print(f"=== Geometric Separation Audit across 20 Hops ===")
    
    records = []
    for t in range(steps):
        frame = step(packets, F, pol, frame_now=t, stalls=True, stall_vz=0.0)
        for hop in frame.get("hops", []):
            records.append(analyze_geometric_clearance(hop, F))
            
    print(f"\nTotal Hops Analyzed: {len(records)}")
    print("-" * 85)
    print(f"{'#':<3} | {'Transition':<10} | {'Z_start':<8} | {'Tier':<5} | {'Span (D)':<8} | {'2*R(z)':<8} | {'Gap (D - 2R)':<12} | {'State'}")
    print("-" * 85)
    
    for idx, r in enumerate(records, 1):
        print(f"{idx:<3} | {r['transition']:<10} | {r['z_start']:<8.2f} | {r['tier']:<5} | {r['d_centers']:<8.1f} | {r['diameter']:<8.2f} | {r['gap']:<12.2f} | {r['status']}")

if __name__ == "__main__":
    main()