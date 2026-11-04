# run_inspect_all_2to0.py — Detailed Forensic Audit of All Six 2 -> 0 Hops
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
    steps = 400  # Enough steps to capture multiple 2 -> 0 hops
    
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
    
    print(f"=== Forensic Audit: Inspecting All Ch 2 -> 0 Hops ===")
    
    hop_count = 0
    for t in range(steps):
        frame = step(packets, F, pol, frame_now=t, stalls=True, stall_vz=0.0)
        hops = frame.get("hops", [])
        
        for hop in hops:
            ch_from = hop["from"]["c"]
            ch_to = hop["to"]["c"]
            
            if ch_from == 2 and ch_to == 0:
                hop_count += 1
                z_start = hop["from"]["z"]
                z_end = hop["to"]["z"]
                phi_start = hop["from"]["phi"]
                phi_end = hop["to"]["phi"]
                
                start_pos = world_position(F, ch_from, phi_start, z_start)
                end_pos = world_position(F, ch_to, phi_end, z_end)
                
                # Global theoretical kiss elevation for 8-unit span
                delta_x = abs(F.channel_centers[ch_to] - F.channel_centers[ch_from])
                z_kiss_global = -math.log(delta_x / (2.0 * F.R0)) / F.beta
                
                kiss_pos_global = np.array([
                    (F.channel_centers[ch_from] + F.channel_centers[ch_to]) / 2.0,
                    0.0,
                    z_kiss_global
                ])
                
                l_approach = np.linalg.norm(kiss_pos_global - start_pos)
                l_departure = np.linalg.norm(end_pos - kiss_pos_global)
                l_via_kiss = l_approach + l_departure
                l_direct = np.linalg.norm(end_pos - start_pos)
                
                print(f"\n--- Hop {hop_count} (Frame {t}) ---")
                print(f"  Start (z={z_start:.3f}, phi={phi_start:.3f}) -> Pos: {np.round(start_pos, 2)}")
                print(f"  End   (z={z_end:.3f}, phi={phi_end:.3f}) -> Pos: {np.round(end_pos, 2)}")
                print(f"  Approach Bridge (Start -> Global Kiss): {l_approach:.3f} units")
                print(f"  Departure Bridge (Global Kiss -> End): {l_departure:.3f} units")
                print(f"  Direct Chord Length (L_direct)       : {l_direct:.3f} units")
                print(f"  Via-Global-Kiss Route (L_via_kiss)   : {l_via_kiss:.3f} units")
                print(f"  Implied Kiss Penalty                 : {l_via_kiss - l_direct:.3f} units")

    print(f"\n=== Audit Complete. Total Ch 2 -> 0 Hops Inspected: {hop_count} ===")

if __name__ == "__main__":
    main()