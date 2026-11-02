# Copyright 2026 James Scott Graber
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# sweep_sensitivity.py — vary phi_min, z_min, hyst; report total hops & occupancy CV
import itertools, json, os, statistics, subprocess, sys, tempfile
from collections import Counter

VVB = os.path.join(os.getcwd(), "vvb_min.py")  # path to your sim

def run_one(phi_min, z_min, hyst, steps=300, packets=60, seed=42,
            channels=("-4","0","4"), stalls=True, stall_vz=0.0):
    out = tempfile.NamedTemporaryFile(delete=False, suffix=".ndjson").name
    cmd = [sys.executable, VVB, "--demo",
           "--steps", str(steps),
           "--channels", *channels,
           "--packets", str(packets),
           "--seed", str(seed),
           "--out", out,
           "--phi-min", str(phi_min),
           "--z-min",   str(z_min),
           "--hyst",    str(hyst)]
    if stalls:
        cmd += ["--stalls", "--stall-vz", str(stall_vz)]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        print("\n--- vvb_min.py FAILED ---")
        print("CMD:", " ".join(cmd))
        print("\nSTDOUT:\n", proc.stdout)
        print("\nSTDERR:\n", proc.stderr)
        raise SystemExit(proc.returncode)


    # run
    subprocess.run(cmd, check=True, capture_output=True, text=True)
    # parse
    frames, summary = [], None
    with open(out, "r") as f:
        for line in f:
            line = line.strip()
            if not line: continue
            obj = json.loads(line)
            if "summary" in obj:
                summary = obj["summary"]
            elif "packets" in obj:
                frames.append(obj)
    os.unlink(out)
    total_hops = int(summary.get("total_hops", 0)) if summary else 0
    # occupancy CV across frames
    if not frames:
        cv = 0.0
    else:
        # infer number of channels from first frame
        chans = sorted({p["c"] for p in frames[0]["packets"]})
        C = len(chans)
        cvs = []
        for fr in frames:
            occ = Counter(p["c"] for p in fr["packets"])
            vec = [occ.get(c, 0) for c in range(C)]
            mu = sum(vec) / C
            cvs.append((statistics.pstdev(vec) / mu) if mu else 0.0)
        cv = sum(cvs)/len(cvs)
    throughput = float(summary.get("throughput_per_frame", 0.0)) if summary else 0.0
    return {"phi_min": phi_min, "z_min": z_min, "hyst": hyst,
            "total_hops": total_hops, "cv": cv, "throughput": throughput}

def main():
    # grids to try — tweak as you like
    PHI = [0.45, 0.60, 0.75]
    Z   = [0.20, 0.25, 0.35]
    H   = [20, 40, 80]

    rows = []
    for phi_min, z_min, hyst in itertools.product(PHI, Z, H):
        r = run_one(phi_min, z_min, hyst)
        print(f"phi_min={phi_min:4.2f}  z_min={z_min:4.2f}  H={hyst:3d}  "
              f"hops={r['total_hops']:4d}  CV={r['cv']:.4f}  thr={r['throughput']:.3f}")
        rows.append(r)

    # write CSV
    csv_path = os.path.join("figs", "sensitivity.csv")
    os.makedirs("figs", exist_ok=True)
    with open(csv_path, "w", newline="") as f:
        f.write("phi_min,z_min,hyst,total_hops,cv,throughput\n")
        for r in rows:
            f.write(f"{r['phi_min']},{r['z_min']},{r['hyst']},"
                    f"{r['total_hops']},{r['cv']:.6f},{r['throughput']:.6f}\n")
    print("CSV:", os.path.abspath(csv_path))

    # write LaTeX table
    tex_path = os.path.join("figs", "sensitivity_table.tex")
    with open(tex_path, "w") as f:
        f.write("\\begin{table}[h]\n\\centering\n")
        f.write("\\begin{tabular}{rrrrrr}\n\\hline\n")
        f.write("$\\phi_{\\min}$ & $z_{\\min}$ & $H$ & hops & CV & thr \\\\\n\\hline\n")
        for r in rows:
            f.write(f"{r['phi_min']:.2f} & {r['z_min']:.2f} & {r['hyst']} & "
                    f"{r['total_hops']} & {r['cv']:.4f} & {r['throughput']:.3f} \\\\\n")
        f.write("\\hline\n\\end{tabular}\n")
        f.write("\\caption{Sensitivity of total hops and occupancy CV to thresholds "
                "$\\phi_{\\min}$, $z_{\\min}$ and hysteresis $H$. "
                "thr = throughput per frame (stall model).}\n")
        f.write("\\label{tab:sensitivity}\n\\end{table}\n")
    print("TeX:", os.path.abspath(tex_path))

if __name__ == "__main__":
    main()
