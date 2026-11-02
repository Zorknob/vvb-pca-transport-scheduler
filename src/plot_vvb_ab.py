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
# plot_vvb_ab.py — cumulative throughput (A vs B),
#                   hop-z histogram with Kiss overlays,
#                   conflicts per frame over time (A vs B)
import argparse, json, os, math
from collections import Counter, defaultdict

def read_ndjson(path):
    frames, summary = [], None
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if not line: continue
            obj = json.loads(line)
            if isinstance(obj, dict) and "summary" in obj:
                summary = obj["summary"]
            elif isinstance(obj, dict):
                # keep only frames that have either packets or deliveries (for cum throughput)
                if "packets" in obj or "deliveries" in obj:
                    frames.append(obj)
    return frames, (summary or {})

def infer_channels(frames, summary):
    ch = summary.get("channels")
    if ch is not None:
        return ch
    for fr in frames:
        if "packets" in fr:
            return sorted({p["c"] for p in fr["packets"]})
    return [0,1,2]

def kisses(centers, R0, beta):
    zs = []
    for i in range(len(centers)-1):
        dx = abs(centers[i+1] - centers[i])
        if dx <= 2*R0:
            zk = (1.0/beta) * math.log((2.0*R0)/dx)
            zs.append((f"{i}-{i+1}", zk))
    return zs

def cumulative_deliveries(frames):
    cum, total = [], 0
    for fr in frames:
        total += int(fr.get("deliveries", 0))
        cum.append(total)
    return cum

def wrap_angle(a):
    return (a + math.pi) % (2*math.pi) - math.pi

def conflicts_in_frame(fr, phi_min, z_min):
    if "packets" not in fr:
        return None
    byc = defaultdict(list)
    for p in fr["packets"]:
        byc[p["c"]].append((p["phi"], p["z"]))
    cnt = 0
    for lst in byc.values():
        n = len(lst)
        for i in range(n):
            phi_i, z_i = lst[i]
            for j in range(i+1, n):
                phi_j, z_j = lst[j]
                if abs(wrap_angle(phi_i - phi_j)) < phi_min and abs(z_i - z_j) < z_min:
                    cnt += 1
    return cnt

def conflicts_series(frames, phi_min, z_min):
    out = []
    for fr in frames:
        c = conflicts_in_frame(fr, phi_min, z_min)
        if c is not None:
            out.append(c)
    return out

def moving_avg(xs, w):
    if w <= 1 or not xs: return xs
    out = []
    for i in range(len(xs)):
        lo = max(0, i - w + 1)
        seg = xs[lo:i+1]
        out.append(sum(seg)/len(seg))
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("A", help="NDJSON with hops ON")
    ap.add_argument("B", help="NDJSON with hops OFF")
    ap.add_argument("--outdir", default="figs", help="output folder for PNGs")
    ap.add_argument("--R0", type=float, default=3.0)
    ap.add_argument("--beta", type=float, default=0.18)
    ap.add_argument("--k", type=float, default=0.35)
    ap.add_argument("--zwrap", type=float, default=4.0)
    ap.add_argument("--phi-min", type=float, default=0.60, help="conflict phase threshold (rad)")
    ap.add_argument("--z-min",   type=float, default=0.25, help="conflict axial threshold")
    ap.add_argument("--smooth", type=int, default=1, help="moving average window for conflict plot")
    ap.add_argument("--open", action="store_true", help="open folder after writing")
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    # Load both runs
    FA, SA = read_ndjson(args.A)
    FB, SB = read_ndjson(args.B)
    centers = infer_channels(FA, SA)

    # ---- Figure 1: cumulative throughput ----
    cumA = cumulative_deliveries(FA)
    cumB = cumulative_deliveries(FB)
    plt.figure()
    plt.plot(cumA, label="Hops ON (A)")
    plt.plot(cumB, label="Hops OFF (B)")
    plt.xlabel("frame")
    plt.ylabel("cumulative deliveries")
    plt.title("Cumulative throughput")
    plt.legend()
    plt.tight_layout()
    out1 = os.path.join(args.outdir, "throughput_cumulative_AB.png")
    plt.savefig(out1, dpi=180)

    # ---- Figure 2: hop-z histogram with Kiss overlays (A only) ----
    hop_z = []
    for fr in FA:
        for h in fr.get("hops", []):
            hop_z.append(h["to"]["z"] % args.zwrap)
    plt.figure()
    if hop_z:
        plt.hist(hop_z, bins=16, alpha=0.85)
    plt.xlabel(f"hop height z (wrapped to [0, {args.zwrap}))")
    plt.ylabel("count")
    title = "Hop heights with Kiss overlays"
    if isinstance(centers[0], (int,float)) and len(centers) >= 2:
        for label, zk in kisses(centers, args.R0, args.beta):
            if zk is not None:
                zkN = zk % args.zwrap
                plt.axvline(zkN, linestyle="--", linewidth=1)
                # lightweight label near top
                ymin, ymax = plt.ylim()
                plt.text(zkN, ymax*0.95, f"Kiss {label}", rotation=90,
                         va="top", ha="right", fontsize=8)
                title += f" | Kiss {label} @ z≈{zkN:.2f}"
    plt.title(title)
    plt.tight_layout()
    out2 = os.path.join(args.outdir, "hop_z_hist_with_kiss.png")
    plt.savefig(out2, dpi=180)

    # ---- Figure 3: conflicts per frame over time (A vs B) ----
    confA = conflicts_series(FA, args.phi_min, args.z_min)
    confB = conflicts_series(FB, args.phi_min, args.z_min)
    confA_s = moving_avg(confA, args.smooth)
    confB_s = moving_avg(confB, args.smooth)

    plt.figure()
    plt.plot(confA_s, label=f"Hops ON (A){' — smoothed' if args.smooth>1 else ''}")
    plt.plot(confB_s, label=f"Hops OFF (B){' — smoothed' if args.smooth>1 else ''}")
    plt.xlabel("frame")
    plt.ylabel("conflicts per frame")
    plt.title(f"Conflict pressure over time (φ<{args.phi_min}, z<{args.z_min})")
    plt.legend()
    plt.tight_layout()
    out3 = os.path.join(args.outdir, "conflicts_over_time_AB.png")
    plt.savefig(out3, dpi=180)

    # Console summary
    thA = SA.get("throughput_per_frame")
    thB = SB.get("throughput_per_frame")
    if thA is not None and thB is not None and thB > 0:
        gain = (thA / thB) - 1.0
        print(f"Throughput per frame: A={thA:.3f}, B={thB:.3f}  →  gain = {gain*100:.1f}%")
    if confA and confB:
        mA = sum(confA)/len(confA)
        mB = sum(confB)/len(confB)
        drop = (mB - mA)/mB*100 if mB else 0.0
        print(f"Conflict rate: A={mA:.3f}, B={mB:.3f}  →  drop = {drop:.1f}%")

    print("Wrote:", os.path.abspath(out1))
    print("Wrote:", os.path.abspath(out2))
    print("Wrote:", os.path.abspath(out3))

    if args.open:
        try: os.startfile(os.path.abspath(args.outdir))
        except Exception: pass

if __name__ == "__main__":
    main()
