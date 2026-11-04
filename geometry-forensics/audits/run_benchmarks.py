# run_benchmarks.py — Parameter sweep and log parser for VVB+PCA
import io
import json
from contextlib import redirect_stdout
from vvb_min260112 import demo

def run_single_config(phi_min: float, z_min: float, hyst: int, steps: int = 200, packets: int = 60):
    """Executes a simulation run programmatically and extracts the summary metrics."""
    f = io.StringIO()
    with redirect_stdout(f):
        demo(
            steps=steps,
            channels=(-4.0, 0.0, 4.0),
            packets_n=packets,
            seed=42,
            disable_hops=False,
            stalls=True,
            stall_vz=0.0,
            phi_min=phi_min,
            z_min=z_min,
            hyst=hyst,
            out="-"
        )
    output = f.getvalue()
    
    # Parse the NDJSON stream to find the final summary JSON block
    lines = [line.strip() for line in output.split('\n') if line.strip()]
    for line in reversed(lines):
        if line.startswith('{') and '"summary":' in line:
            return json.loads(line)["summary"]
    return None

def main():
    # Define sweep ranges mirroring your sensitivity tables
    phi_values = [0.45, 0.60, 0.75]
    z_values = [0.20, 0.25, 0.35]
    hyst_values = [20, 40]

    print("=== VVB+PCA Parameter Sensitivity Benchmark ===")
    header = f"{'phi_min':<8} | {'z_min':<8} | {'Hyst':<6} | {'Throughput (del/frm)':<22} | {'Total Hops':<10}"
    print(header)
    print("-" * len(header))

    for phi in phi_values:
        for z in z_values:
            for h in hyst_values:
                summary = run_single_config(phi_min=phi, z_min=z, hyst=h)
                if summary:
                    tput = summary["throughput_per_frame"]
                    hops = summary["total_hops"]
                    print(f"{phi:<8.2f} | {z:<8.2f} | {h:<6d} | {tput:<22.3f} | {hops:<10d}")

    print("\nBenchmark complete.")

if __name__ == "__main__":
    main()