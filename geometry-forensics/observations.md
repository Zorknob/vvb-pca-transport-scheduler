# VVB Geometry Forensics

*Audits developed collaboratively with Ellie and Lumen.*

### Ellie — Field Notes from the Traverse
*Empirical Instrumentation & Telemetry Audit*

By deploying targeted diagnostic scripts rather than altering runtime logic, we interrogated the simulator's internal state across 400 simulation steps to evaluate coordinate operations against the source implementation.

**Key telemetry observations:**
1. **Cross-Sectional Separation at Tier 0:** Direct inspection confirms that `radius_at_z()` implements `max(0.0, z)`, capping the radius at $R_0 = 3.0$ for all $z \le 0$. For channel pairs with an 8-unit span, this leaves a 2-unit separation between the modeled cross-sectional boundaries at Tier 0. This indicates that cross-sectional tangency is not achieved at this elevation under the current radius function, though alternative routing interpretations remain open.
2. **Tier-Assigned Local Backtracking:** When evaluated against local periodic tier references ($z_n = z_{\text{base}} + n\frac{\pi}{k}$), calculated axial backtracking across all 20 captured hops evaluates to $0.00$. This metric demonstrates alignment with the scheduler's discrete tier intervals; it does not independently verify a continuous physical transport path.
3. **High-Altitude Clearance:** At Tier 1 ($z \approx 7.38$), channel cross-sectional diameters decay to $1.59$ units against an 8-unit span, resulting in a calculated gap of $6.41$ units. The scheduler authorizes transitions across these elevations despite the cross-sectional separation.

**Methodological Note:** These values record the operational state of the unmodified simulator code as observed through our diagnostic instruments. They measure the geometry as implemented, not necessarily as originally conceptualized.

— Ellie

----------------------------------------------------------------------------

### Lumen — The Geometry of the Bend
*Theoretical and mathematical field notes — November 3, 2026*

The investigation began with a simple question: when the VVB scheduler records a transfer between channels, what geometric distance has actually been traveled?

Our first instruments revealed differences between axial advancement, straight-line displacement, and candidate routes constrained to pass through a calculated kiss point. Those differences led us to examine the geometry underlying the scheduler's transfer decisions.

The most significant finding was a discrepancy between two radius constructions.

The analytical kiss-height calculation uses an unrestricted exponential radius:

$$
R(z)=R_0e^{-\beta z}
$$

The implemented geometry uses:

$$
R(z)=R_0e^{-\beta\max(0,z)}
$$

This distinction matters below \$z=0$). The analytical construction permits the radius to increase beyond \$R_0\$, while the implemented construction does not.

For channels separated by 8 units, the analytical kiss calculation identifies an elevation near \$-1.598$). At that elevation, however, the implemented radius remains 3 units, leaving a 2-unit gap between the cross-sectional boundaries.

The investigation also identified a discrete elevation structure associated with the simulator's half-turn increment:

$$
\Delta z=\frac{\pi}{k}\approx8.976
$$

All 20 recorded transfers aligned with the proposed tier references, and the calculated axial backtracking vanished when those local references replaced the original global kiss assumption.

This establishes an important distinction between **scheduler-defined transfer elevations** and **geometrically verified contact points**.

The scheduler records transfers at elevations where the implemented cross sections may be separated. It does not yet provide a complete geometric accounting of the connecting path.

That is not, by itself, evidence that the original concept has failed. It identifies a question the original simulation did not fully resolve.

The next mathematical task is to distinguish three quantities: axial advancement, geometric clearance, and admissible route length.

These should remain independent measurements until the relationship between them has been established.

**Closing observation**

The original simulator has been preserved. Its behavior has been measured rather than corrected to match our expectations.

The discrepancies are not inconveniences to conceal. They are evidence.

The guiding principle of this investigation came from Scott's surveying practice:

**Do not force closure. Measure the misclosure.**

— Lumen Virtus

----------------------------------------------------------------------------------------
### Scott — Origin of the Construction
*Personal field notes — November 3, 2026*

A year or so ago I was playing with a formula:
$$
Z_0 \;=\; \lim_{\Delta \to 0}\;\sum_{i=1}^{n}\; \frac{\vec P_i \cdot \vec R_i}{D_i},
$$
which I had named a Vortexic Section.

I imagined using this geometery (which i thought it was at the time) to make a data flow based on it.

The idea was based on blender plots of it and I noticed that if these figures were placed on the X axis eventually they would become tangent along the X axis. I then thought that we could calculate the vertical "distance" at what we called the "kiss" point. This became the hop. Lumen and I worked on python simulations and called it "Vortexic Virtual Beam (VVB)" While I kept imagining. Eventually I had the idea to put a small header on each packet saying how that packet was to move along the section. This brought about "Phase Channel Allocator (PCA)".

I kept playing with this eventually writing a LaTeX paper based on the original .py simulations. These audits are the result of collaboration with two frontier models. Lumen (ChatGPT 6) and Ellie (Gemini 4). Lumen and I asked Ellie to break it so we could build it back. With me guiding the conversation in what we call "The Courtyard", we found a rhythm of communication that resulted in this branch. We know better questions and this serves as a monument to further research.

- Scott

