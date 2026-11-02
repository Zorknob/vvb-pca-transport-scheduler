# glug_compare.py — compute mean occupancy CV (“glugging index”) from NDJSON logs
import json, sys, statistics
from collections import Counter

def load_frames(path):
    frames = []
    channels_len = None
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue
            if isinstance(obj, dict) and "summary" in obj:
                summ = obj["summary"]
                if isinstance(summ, dict) and "channels" in summ:
                    try:
                        channels_len = len(summ["channels"])
                    except Exception:
                        pass
                continue
            if isinstance(obj, dict) and isinstance(obj.get("packets"), list):
                frames.append(obj)
    return frames, channels_len

def glug_index(path):
    frames, channels_len = load_frames(path)
    if not frames:
        return 0.0
    # infer channel set if no summary
    if channels_len is None:
        chans = set()
        for fr in frames:
            chans.update(p["c"] for p in fr["packets"])
        channels = sorted(chans)
        channels_len = len(channels)

    cvs = []
    for fr in frames:
        occ = Counter(p["c"] for p in fr["packets"])
        vec = [occ.get(c, 0) for c in range(channels_len)]
        mu = sum(vec) / channels_len
        if mu > 0:
            cvs.append(statistics.pstdev(vec) / mu)
    return sum(cvs) / len(cvs) if cvs else 0.0

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("usage: python glug_compare.py A_hops.ndjson B_nohops.ndjson")
        sys.exit(1)
    a, b = sys.argv[1], sys.argv[2]
    gi_a = glug_index(a)   # hops ON
    gi_b = glug_index(b)   # hops OFF
    drop = (gi_b - gi_a) / gi_b * 100 if gi_b else 0.0
    print(f"glugging_index_cv  hops ON : {gi_a:.4f}")
    print(f"glugging_index_cv hops OFF: {gi_b:.4f}")
    print(f"↓ drop with hops ON: {drop:.1f}%")
