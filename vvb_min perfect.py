# vvb_min.py  — Vortexic Virtual Beam (VVB) + Phase-Channel Allocator (PCA)
# Drop-in, no dependencies. Run:  python vvb_min.py --demo

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Iterable, Optional, Dict
import math, json, argparse, random

# ---------- Field / Params ----------
@dataclass
class FieldParams:
    R0: float = 3.0          # radius at z=0
    beta: float = 0.18       # radial decay along z
    k: float = 0.35          # axial twist (phase pitch)
    channel_centers: List[float] = None  # X positions of channels

    def __post_init__(self):
        if self.channel_centers is None:
            self.channel_centers = [-3.0, 0.0, 3.0]

# ---------- Particles & Policy ----------
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

@dataclass
class SwitchPolicy:
    phi_min: float = 0.22            # min phase separation to avoid collision
    z_min: float = 0.12              # min axial separation
    hysteresis_frames: int = 12      # min frames between hops
    golden_nudge: float = (math.pi*(3.0 - math.sqrt(5.0))) * 0.15  # golden-angle-ish
    prefer_kiss: bool = True         # prefer “kiss” heights when hopping
    phase_smooth: bool = True        # apply Δz = π/k on hop

# ---------- Geometry ----------
def radius_at_z(F: FieldParams, z: float) -> float:
    return F.R0 * math.exp(-F.beta * max(0.0, z))

def world_from_params(F: FieldParams, channel: int, phi: float, z: float) -> tuple[float,float,float]:
    Xc = F.channel_centers[channel]
    theta = phi - F.k * z
    r = radius_at_z(F, z)
    return (r*math.cos(theta) + Xc, r*math.sin(theta), z)

def phase_from_world(F: FieldParams, x: float, y: float, z: float, Xc: float) -> float:
    return math.atan2(y, x - Xc) + F.k * z

def kiss_height(F: FieldParams, Xa: float, Xb: float) -> Optional[float]:
    """Projected x–z ‘kiss’ height where Xa+r(z) == Xb-r(z). Returns None if channels too far."""
    dX = Xb - Xa
    if dX > 2.0 * F.R0:
        return None
    return (1.0 / F.beta) * math.log((2.0 * F.R0) / dX)

def kiss_ladder(z_kiss: float, k: float, m_range: Iterable[int]) -> List[float]:
    """Phase-smooth rungs separated by Δz = π/k."""
    dz = math.pi / k
    return [z_kiss + m*dz for m in m_range]

# ---------- Scheduler ----------
def wrap_angle(a: float) -> float:
    return (a + math.pi) % (2*math.pi) - math.pi

def local_density(packets: List[Particle], ch: int, phi0: float, z0: float,
                  phi_min: float, z_min: float) -> int:
    cnt = 0
    for q in packets:
        if q.channel != ch: 
            continue
        dphi = abs(wrap_angle(q.phi - phi0))
        dz   = abs(q.z - z0)
        if dphi <= 1.2*phi_min and dz <= 1.2*z_min:
            cnt += 1
    return cnt

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

def prefer_kiss_height(z_now: float, ch_from: int, ch_to: int, F: FieldParams) -> Optional[float]:
    Xa = F.channel_centers[min(ch_from, ch_to)]
    Xb = F.channel_centers[max(ch_from, ch_to)]
    zk = kiss_height(F, Xa, Xb)
    if zk is None:
        return None
    dz_phi = math.pi / F.k
    # pick nearest rung among zk, zk±dz_phi
    cands = [zk, zk + dz_phi, zk - dz_phi]
    best = min(cands, key=lambda zc: abs(zc - z_now))
    tol = max(0.15, 0.5*dz_phi)
    return best if abs(best - z_now) <= tol else None

def apply_switch(p: Particle, new_channel: int, F: FieldParams, pol: SwitchPolicy, frame_now: int) -> None:
    # Minimal phase-smooth hop: adjust z by ±π/k (choose smaller move), then golden-angle nudge on phi.
    if pol.phase_smooth:
        dz_phi = math.pi / F.k
        cand_up   = p.z + dz_phi
        cand_down = p.z - dz_phi
        p.z = cand_up if abs(cand_up - p.z) < abs(cand_down - p.z) else cand_down
    p.phi = wrap_angle(p.phi + pol.golden_nudge)
    p.channel = new_channel
    p.last_switch = frame_now

def step(packets: List[Particle], F: FieldParams, pol: SwitchPolicy, frame_now: int,
         omega: float=0.10, vz: float=0.03, z_wrap: float=4.0, prefer_kiss_flag: bool=True) -> Dict:
    """Advance one frame: advect, detect conflicts, hop with kiss/phase-smooth policy, return frame state."""
    # 1) Advect
    for p in packets:
        p.phi = wrap_angle(p.phi + omega)
        z = p.z + vz
        p.z = z if z < z_wrap else (z - z_wrap)

    # 2) Hop on conflicts
    hop_events = []
    for i, a in enumerate(packets):
        # check same-channel neighbors
        conflict = False
        for j, b in enumerate(packets):
            if i == j or b.channel != a.channel:
                continue
            if abs(wrap_angle(b.phi - a.phi)) < pol.phi_min and abs(b.z - a.z) < pol.z_min:
                conflict = True
                break
        if not conflict:
            continue
        if frame_now - a.last_switch < pol.hysteresis_frames:
            continue

        allowed = [c for c in range(len(F.channel_centers)) if (a.allowed_mask >> c) & 1]
        tgt = pick_target_channel(packets, a.channel, a.phi, a.z, allowed, pol)
        if tgt is None:
            continue

        # bias to kiss rung if near
        if prefer_kiss_flag and pol.prefer_kiss:
            zk = prefer_kiss_height(a.z, a.channel, tgt, F)
            if zk is not None:
                a.z = zk

        before = (a.channel, a.phi, a.z)
        apply_switch(a, tgt, F, pol, frame_now)
        after  = (a.channel, a.phi, a.z)

        hop_events.append({
            "t": frame_now,
            "id": a.id,
            "from": {"c": before[0], "phi": before[1], "z": before[2]},
            "to":   {"c": after[0],  "phi": after[1],  "z": after[2]},
            "reason": "collision"
        })

    # 3) Emit light state for logging/visualization
    state = [{"id": p.id, "c": p.channel, "phi": p.phi, "z": p.z} for p in packets]
    return {"t": frame_now, "packets": state, "hops": hop_events}

# ---------- Tiny demo / CLI ----------
def demo(steps=300, channels=(-3.0, 0.0, 3.0), R0=3.0, beta=0.18, k=0.35,
         packets_n=24, seed=42, out="-"):
    F = FieldParams(R0=R0, beta=beta, k=k, channel_centers=list(channels))
    pol = SwitchPolicy()
    rng = random.Random(seed)
    Z_MAX = 4.0

    packets: List[Particle] = []
    for i in range(packets_n):
        ch  = i % len(F.channel_centers)
        phi = rng.random() * 2*math.pi
        z   = rng.random() * Z_MAX * 0.9
        packets.append(Particle(id=i, channel=ch, phi=phi, z=z))

    sink = open(out, "w") if out != "-" else None
    for t in range(steps):
        frame = step(packets, F, pol, frame_now=t)
        line = json.dumps(frame)
        (sink.write(line + "\n") if sink else print(line))
    if sink:
        sink.close()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", action="store_true", help="run a simple NDJSON demo")
    ap.add_argument("--steps", type=int, default=300)
    ap.add_argument("--channels", type=float, nargs="+", default=[-3,0,3])
    ap.add_argument("--R0", type=float, default=3.0)
    ap.add_argument("--beta", type=float, default=0.18)
    ap.add_argument("--k", type=float, default=0.35)
    ap.add_argument("--packets", type=int, default=24)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", type=str, default="-")
    args = ap.parse_args()
    if args.demo:
        demo(args.steps, tuple(args.channels), args.R0, args.beta, args.k, args.packets, args.seed, args.out)

if __name__ == "__main__":
    main()
