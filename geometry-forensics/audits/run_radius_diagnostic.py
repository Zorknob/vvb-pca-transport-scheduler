# run_radius_diagnostic.py — Comparing radius_at_z() vs. Analytical Formula
import math
from vvb_min260112 import FieldParams, radius_at_z

def main():
    F = FieldParams(R0=3.0, beta=0.18, k=0.35, channel_centers=[-4.0, 0.0, 4.0])
    
    test_elevations = [-1.598, 0.000, 7.378]
    
    print("=== Radius Implementation Diagnostic ===")
    print(f"{'Elevation (z)':<15} | {'Function R(z)':<15} | {'Function Diameter':<18} | {'Analytical R(z)':<18} | {'Analytical Diam'}")
    print("-" * 88)
    
    for z in test_elevations:
        func_r = radius_at_z(F, z)
        func_diam = 2.0 * func_r
        
        analytical_r = F.R0 * math.exp(-F.beta * z)
        analytical_diam = 2.0 * analytical_r
        
        print(f"{z:<15.3f} | {func_r:<15.3f} | {func_diam:<18.3f} | {analytical_r:<18.3f} | {analytical_diam:.3f}")

if __name__ == "__main__":
    main()