# run_tiered_kiss_audit.py — Testing Periodic Tiered Kiss Envelopes
import math
import random
import numpy as np
from vvb_min260112 import FieldParams, SwitchPolicy, Particle, step, radius_at_z

def analyze_tiered_backtracking(hop_event, F: FieldParams):
    """
    Evaluates axial backtracking against the local periodic kiss envelope 
    shifted by integer multiples of pi/k.
    """
    ch_from = hop_event["from"]["c"]
    ch_to = hop_event["to"]["c"]
    
    z_start = hop_event["from"]["z"]
    z_end = hop_event["to"]["z"]
    
    # Base tier-0 kiss elevation
    delta_x = abs(F.channel_centers[ch_to] - F.channel_centers[ch_from])
    z_kiss_base = -math.log(delta_x / (2.0 * F.R0)) / F.beta
    tier_interval = math.pi / F.k  # ~8.976
    
    # Find the closest periodic tier kiss elevation to z_start
    tier_offset = round((z_start - z_kiss_base) / tier_interval)
    z_kiss_local = z_kiss_base + tier_offset * tier_interval
    
    # Local backtracking relative to the matched tier kiss
    b_axial_local = abs(z_start - z_kiss_local) + abs(z_end - z_kiss_local) - abs(z_end - z_start)
    
    return {
        "transition": f"Ch {ch_from} -> {ch_to}",
        "z_start": z_start,
        "z_end": z_end,
        "tier_offset": tier_offset,
        "z_kiss_local": z_kiss_local,
        "b_axial_local": b_axial_local
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
    
    print(f"=== Full 20-Hop Tiered Kiss Audit ===")
    
    records = []
    for t in range(steps):
        frame = step(packets, F, pol, frame_now=t, stalls=True, stall_vz=0.0)
        for hop in frame.get("hops", []):
            records.append(analyze_tiered_backtracking(hop, F))
            
    print(f"\nTotal Hops Captured: {len(records)}")
    print("-" * 80)
    print(f"{'#':<3} | {'Transition':<10} | {'Z_start':<8} | {'Tier':<5} | {'Z_kiss_local':<14} | {'B_axial (Local)'}")
    print("-" * 80)
    
    for idx, r in enumerate(records, 1):
        print(f"{idx:<3} | {r['transition']:<10} | {r['z_start']:<8.2f} | {r['tier_offset']:<5} | {r['z_kiss_local']:<14.2f} | {r['b_axial_local']:<16.2f}")

if __name__ == "__main__":
    main()