# vvb_min.py — Vortexic Virtual Beam (VVB) + Phase-Channel Allocator (PCA)
# Drop-in, no dependencies. Run: python vvb_min.py --demo

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Iterable, Optional, Dict, Tuple
import math, json, argparse, random

# ---------- Field / Params ----------
@dataclass
class FieldParams:
    R0: float = 3.0
    beta: float = 0.18
    k: float = 0.35
    channel_centers: List[float] = None

    def __post_init__(self):
        if self.channel_centers is None:
            self.channel_centers = [-3.0, 0.0, 3.0]

@dataclass
class Packet:
    pid: int
    payload: bytes

@dataclass
class Particle:
    id: int
    channel: int
    phi: float
    z: float
    ttl: int = 10_000
    priority: int = 1
    allowed_mask: int = 0xFFFFFFFF
    last_switch: int = -10_000
    hop_count: int = 0
    packet: Optional[Packet] = None   # ← safe to check in step()

# ---------- Particles & Policy ----------
@dataclass
class Particle:
    id: int
    channel: int   # ← INDEX (0..N-1)
    phi: float
    z: float
    ttl: int = 10_000
    priority: int = 1
    allowed_mask: int = 0xFFFFFFFF
    last_switch: int = -10_000
    hop_count: int = 0

@dataclass
class SwitchPolicy:
    phi_min: float = 0.6
    z_min: float = 0.25
    hysteresis_frames: int = 6
    golden_nudge: float = (math.pi * (3.0 - math.sqrt(5.0))) * 0.15
    prefer_kiss: bool = True
    phase_smooth: bool = True

# ---------- Geometry ----------
def radius_at_z(F: FieldParams, z: float) -> float:
    return F.R0 * math.exp(-F.beta * max(0.0, z))


def wrap_angle(a: float) -> float:
    return (a + math.pi) % (2 * math.pi) - math.pi


def local_density(packets: List[Particle], ch: int, phi0: float, z0: float,
                  phi_min: float, z_min: float) -> int:
    return sum(
        1 for p in packets
        if p.channel == ch
        and abs(wrap_angle(p.phi - phi0)) <= 1.2 * phi_min
        and abs(p.z - z0) <= 1.2 * z_min
    )

def pick_target_channel(packets: List[Particle], cur_ch: int, phi: float, z: float,
                        allowed: Iterable[int], pol: SwitchPolicy) -> Optional[int]:
    best, best_rho = None, 1e9
    for ch in allowed:
        if ch == cur_ch: 
            continue
        rho = local_density(packets, ch, phi, z, pol.phi_min, pol.z_min)
        if rho < best_rho:
            best_rho, best = rho, ch
    return best

def kiss_height(F, Xa, Xb, eps=1e-6):
    dX = abs(Xa - Xb)

    # Prevent singularity: packets cannot be closer than eps
    dX = max(dX, eps)

    return (1.0 / F.beta) * math.log((2.0 * F.R0) / dX)

def prefer_kiss_height(z_now: float, ch_from: int, ch_to: int, F: FieldParams) -> Optional[float]:
    Xa, Xb = F.channel_centers[min(ch_from, ch_to)], F.channel_centers[max(ch_from, ch_to)]
    zk = kiss_height(F, Xa, Xb)
    if zk is None:
        return None
    dz_phi = math.pi / F.k
    candidates = [zk + n*dz_phi for n in (-1,0,1)]
    best = min(candidates, key=lambda zc: abs(zc - z_now))
    tol = max(0.15, 0.5*dz_phi)
    return best if abs(best - z_now) <= tol else None

def apply_switch(p: Particle, new_channel: int, F: FieldParams, pol: SwitchPolicy, frame_now: int) -> None:
    if pol.phase_smooth:
        dz_phi = math.pi / F.k
        p.z += dz_phi  # smooth upward hop
    p.phi = wrap_angle(p.phi + pol.golden_nudge)
    p.channel = new_channel
    p.last_switch = frame_now
    p.hop_count += 1  # track hops

def renormalize(p: Particle, F: FieldParams, max_hops: int = 8) -> None:
    if p.hop_count >= max_hops:
        r = radius_at_z(F, p.z)
        theta = p.phi  # simplify
        blend_factor = 0.3
        p.phi = wrap_angle((1 - blend_factor) * p.phi + blend_factor * (theta + F.k * p.z))
        p.hop_count = 0

def conflict_mask(packets: List[Particle], phi_min: float, z_min: float) -> List[bool]:
    mask = [False] * len(packets)
    for i, a in enumerate(packets):
        for j, b in enumerate(packets):
            if i == j or b.channel != a.channel:
                continue
            if abs(wrap_angle(b.phi - a.phi)) < phi_min and abs(b.z - a.z) < z_min:
                mask[i] = True
                break
    return mask

def step(packets, F, pol, frame_now,
        omega=0.10, vz=0.03, z_wrap=4.0,
        prefer_kiss_flag=True, stalls=False, stall_vz=0.0):

    conf = conflict_mask(packets, pol.phi_min, pol.z_min) if stalls else [False] * len(packets)

    deliveries = 0
    delivered_packets = []
    for idx, p in enumerate(packets):
        p.phi = wrap_angle(p.phi + omega)
        vzeff = stall_vz if conf[idx] else vz
        p.z += vzeff
        if p.z >= z_wrap:
            if p.packet is not None:
                deliveries += 1
                delivered_packets.append(p.packet)
                p.packet = None
            p.z -= z_wrap

    hop_events = []
    for i, a in enumerate(packets):
        if (frame_now - a.last_switch) < pol.hysteresis_frames:
            continue
        if not any(abs(wrap_angle(b.phi - a.phi)) < pol.phi_min and abs(b.z - a.z) < pol.z_min
                   for j, b in enumerate(packets) if i != j and b.channel == a.channel):
            continue

        allowed = [c for c in range(len(F.channel_centers)) if (a.allowed_mask >> c) & 1]
        tgt = pick_target_channel(packets, a.channel, a.phi, a.z, allowed, pol)
        if tgt is None:
            continue

        if prefer_kiss_flag and pol.prefer_kiss:
            zk = prefer_kiss_height(a.z, a.channel, tgt, F)
            if zk is not None:
                a.z = zk

        before = (a.channel, a.phi, a.z)
        apply_switch(a, tgt, F, pol, frame_now)
        after = (a.channel, a.phi, a.z)

        hop_events.append({
            "t": frame_now,
            "id": a.id,
            "from": {"c": before[0], "phi": before[1], "z": before[2]},
            "to":   {"c": after[0],  "phi": after[1],  "z": after[2]},
            "reason": "collision"
        })

    # Build the state dict in a way that animation code can use
    state = [{"id": p.id, "channel": p.channel, "phi": p.phi, "z": p.z, "hop_count": p.hop_count} for p in packets]

    return {
        "t": frame_now,
        "packets": state,
        "hops": hop_events,
        "deliveries": deliveries,
        "delivered_packets": delivered_packets
    }

# ---------- Demo / CLI ----------
def demo(steps=300, channels=(-4.0,0.0,4.0), R0=3.0, beta=0.18, k=0.35,
         packets_n=60, seed=42, out="-", disable_hops=False,
         stalls=True, stall_vz=0.0, phi_min=None, z_min=None, hyst=None):

    F = FieldParams(R0=R0, beta=beta, k=k, channel_centers=list(channels))
    pol = SwitchPolicy()
    if disable_hops:
        pol.hysteresis_frames = 10**9
        pol.prefer_kiss = False
    if phi_min is not None: pol.phi_min = phi_min
    if z_min is not None:   pol.z_min = z_min
    if hyst is not None:    pol.hysteresis_frames = hyst

    rng = random.Random(seed)
    packets = [Particle(id=i,
                        channel=i % len(F.channel_centers),
                        phi=rng.random()*2*math.pi,
                        z=rng.random()*4.0*0.9)
               for i in range(packets_n)]

    sink = open(out, "w") if out != "-" else None
    total_hops = 0
    hops_by_pair: Dict[Tuple[int,int], int] = {}
    total_deliveries = 0

    for t in range(steps):
        frame = step(packets, F, pol, frame_now=t, stalls=stalls, stall_vz=stall_vz)
        total_deliveries += frame["deliveries"]
        for h in frame["hops"]:
            total_hops += 1
            pair = (h["from"]["c"], h["to"]["c"])
            hops_by_pair[pair] = hops_by_pair.get(pair, 0) + 1
        line = json.dumps(frame)
        if sink: 
            sink.write(line + "\n")
        else:
            print(line)  # NDJSON line
            # Pretty preview
            print(f"Frame {frame['t']}: {len(frame['packets'])} packets, "
                f"{len(frame['hops'])} hops, {frame['deliveries']} deliveries")

    hops_pairs_list = [{"from": a, "to": b, "count": n} for (a,b), n in sorted(hops_by_pair.items())]
    summary = {
        "summary": {
            "steps": steps,
            "packets": packets_n,
            "channels": list(channels),
            "total_hops": total_hops,
            "hops_by_pair": hops_pairs_list,
            "throughput_per_frame": total_deliveries / steps
        }
    }
    summary_line = json.dumps(summary)
    if sink: sink.write(summary_line + "\n")
    else: print(summary_line)
    print(f"# SUMMARY total_hops={total_hops}, throughput_per_frame={total_deliveries/steps:.3f}, "
          f"steps={steps}, packets={packets_n}, channels={list(channels)}")
    if sink: sink.close()

def main():
    ap = argparse.ArgumentParser(description="VVB simulator")
    ap.add_argument("--demo", action="store_true")
    ap.add_argument("--steps", type=int, default=300)
    ap.add_argument("--channels", type=float, nargs="+", default=[-4,0,4])
    ap.add_argument("--R0", type=float, default=3.0)
    ap.add_argument("--beta", type=float, default=0.18)
    ap.add_argument("--k", type=float, default=0.35)
    ap.add_argument("--packets", type=int, default=60)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", type=str, default="-")
    ap.add_argument("--no-hops", action="store_true")
    ap.add_argument("--stalls", action="store_true")
    ap.add_argument("--stall-vz", type=float, default=0.0)
    ap.add_argument("--phi-min", type=float, default=None)
    ap.add_argument("--z-min", type=float, default=None)
    ap.add_argument("--hyst", type=int, default=None)

    args = ap.parse_args()

    if args.demo:
        demo(args.steps, tuple(args.channels), args.R0, args.beta, args.k,
             args.packets, args.seed, args.out,
             disable_hops=args.no_hops,
             stalls=args.stalls, stall_vz=args.stall_vz,
             phi_min=args.phi_min, z_min=args.z_min, hyst=args.hyst)
    else:
        print("Nothing to do. Use --demo")

if __name__ == "__main__":
    main()