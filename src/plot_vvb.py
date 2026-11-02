# plot_vvb.py — normalize hop z and compute |z - z_kiss|
import json, sys, os, argparse
from collections import Counter
import math

def read_frames(path):
    with open(path, "r") as f:
        for line in f:
            line=line.strip()
            if line:
                yield json.loads(line)

def z_kiss(delta_x, R0, beta):
    return (1.0/beta)*math.log((2.0*R0)/delta_x) if delta_x <= 2.0*R0 else None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("log")
    ap.add_argument("--outdir", default="figs")
    ap.add_argument("--open", action="store_true")
    # params so we can compute z_kiss and wrap consistently
    ap.add_argument("--R0", type=float, default=3.0)
    ap.add_argument("--beta", type=float, default=0.18)
    ap.add_argument("--k", type=float, default=0.35)
    ap.add_argument("--zwrap", type=float, default=4.0)
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    frames = list(read_frames(args.log))

    # infer channel centers (e.g., [-4,0,4])
    ch_centers = None
    for obj in reversed(frames):
        if "summary" in obj:
            ch_centers = obj["summary"]["channels"]; break
    if ch_centers is None:
        first = next(x for x in frames if "packets" in x)
        ch_centers = sorted({p["c"] for p in first["packets"]})  # fallback to indices

    # occupancy + hops
    occ_over_time, hop_z_raw, hop_z_norm, dz_from_kiss = [], [], [], []
    for fr in frames:
        if "packets" in fr:
            occ = Counter(p["c"] for p in fr["packets"])
            occ_over_time.append([occ.get(i,0) for i in range(len(ch_centers))])
        for h in fr.get("hops", []):
            z = h["to"]["z"]
            hop_z_raw.append(z)
            zN = z % args.zwrap          # normalize into [0, z_wrap)
            hop_z_norm.append(zN)
            a, b = h["from"]["c"], h["to"]["c"]
            if isinstance(ch_centers[0], (int, float)) and abs(a-b) == 1:
                dx = abs(ch_centers[b] - ch_centers[a])
                zk = z_kiss(dx, args.R0, args.beta)
                if zk is not None:
                    dz_from_kiss.append(abs(zN - zk))

    # occupancy over time
    if occ_over_time:
        plt.figure()
        for i, series in enumerate(zip(*occ_over_time)):
            plt.plot(series, label=f"channel {i}")
        plt.xlabel("frame"); plt.ylabel("occupancy"); plt.legend()
        plt.tight_layout(); plt.savefig(os.path.join(args.outdir, "occupancy_over_time.png"), dpi=160)

    # raw hop-z (shows the ±π/k jumps)
    if hop_z_raw:
        plt.figure()
        plt.hist(hop_z_raw, bins=16)
        plt.xlabel("hop height z (raw)"); plt.ylabel("count")
        plt.tight_layout(); plt.savefig(os.path.join(args.outdir, "hop_z_hist_raw.png"), dpi=160)

    # normalized hop-z in [0, z_wrap)
    if hop_z_norm:
        plt.figure()
        plt.hist(hop_z_norm, bins=16)
        plt.xlabel(f"hop height z (wrapped to [0,{args.zwrap}))"); plt.ylabel("count")
        plt.tight_layout(); plt.savefig(os.path.join(args.outdir, "hop_z_hist.png"), dpi=160)

    # |z - z_kiss| for neighbor hops
    plt.figure()
    if dz_from_kiss:
        plt.hist(dz_from_kiss, bins=16)
    plt.xlabel("|z - z_kiss|"); plt.ylabel("count")
    plt.tight_layout(); plt.savefig(os.path.join(args.outdir, "dz_from_kiss_hist.png"), dpi=160)

    outabs = os.path.abspath(args.outdir)
    print("Wrote figures to:", outabs)
    if args.open:
        try: os.startfile(outabs)
        except Exception: pass

if __name__ == "__main__":
    main()
