# glug_compare_conflicts.py — compares collision pressure between two runs
import json, sys, math, statistics
from collections import Counter, defaultdict

def load_frames(path):
    frames = []
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            if isinstance(obj, dict) and isinstance(obj.get("packets"), list):
                frames.append(obj)
    return frames

def wrap(a):  # wrap to (-pi, pi]
    return (a + math.pi) % (2*math.pi) - math.pi

def conflicts_in_frame(fr, phi_min, z_min):
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
                if abs(wrap(phi_i - phi_j)) < phi_min and abs(z_i - z_j) < z_min:
                    cnt += 1
    return cnt

def conflict_rate(frames, phi_min, z_min):
    if not frames:
        return 0.0
    total = sum(conflicts_in_frame(fr, phi_min, z_min) for fr in frames)
    return total / len(frames)

def occ_cv(frames):
    if not frames:
        return 0.0
    cvs = []
    # infer channel count from first frame
    chans = sorted({p["c"] for p in frames[0]["packets"]})
    C = len(chans)
    for fr in frames:
        occ = Counter(p["c"] for p in fr["packets"])
        vec = [occ.get(c, 0) for c in range(C)]
        mu = sum(vec) / C
        cvs.append((statistics.pstdev(vec) / mu) if mu else 0.0)
    return sum(cvs)/len(cvs)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("usage: python glug_compare_conflicts.py A_hops.ndjson B_nohops.ndjson [phi_min] [z_min]")
        sys.exit(1)
    A, B = sys.argv[1], sys.argv[2]
    phi_min = float(sys.argv[3]) if len(sys.argv) > 3 else 0.60  # match your sim thresholds
    z_min   = float(sys.argv[4]) if len(sys.argv) > 4 else 0.25

    FA, FB = load_frames(A), load_frames(B)
    rA = conflict_rate(FA, phi_min, z_min)
    rB = conflict_rate(FB, phi_min, z_min)
    drop = (rB - rA) / rB * 100 if rB else 0.0

    print(f"conflict_rate  hops ON : {rA:.3f} pairs/frame")
    print(f"conflict_rate hops OFF: {rB:.3f} pairs/frame")
    print(f"↓ drop with hops ON: {drop:.1f}%")
    # (bonus) show the occupancy CVs too
    print(f"occupancy_cv  hops ON : {occ_cv(FA):.4f}")
    print(f"occupancy_cv hops OFF: {occ_cv(FB):.4f}")
