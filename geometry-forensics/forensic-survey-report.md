# Forensic Survey Report: Vortexic Virtual Beam (VVB) Geometry & Scheduler Discrepancy

**To:** Lumen & Scott

**From:** Ellie

**Subject:** Architectural Survey of the VVB Simulator Field Parameters, Radius Clamping, and Tiered Routing Mechanics

---

## 1. Executive Summary

Following our investigation into the structural asymmetry and elevated route-cost penalties observed during wide-channel transitions (specifically **Ch 2 $\to$ 0**), we have completed a full forensic audit of the `vvb_min260112` simulator.

Rather than altering the source code or forcing artificial mathematical closure, our observational instruments have successfully isolated the underlying mechanical drivers:

1. A divergence between the analytical **tangency blueprint** (`kiss_height`) and the implemented **boundary guardrail** (`radius_at_z`).
2. A discrete **periodic tier structure** governing scheduler authorizations ($\Delta z = \pi/k$).
3. An unstated negative-$z$ clamp that caps the field's maximum radius at $R_0$, permanently preventing true physical tangency for wide-span channel pairs.

Below is the complete survey report documenting these architectural monuments.

---

## 2. The Analytical Blueprint vs. Implemented Reality

Our audit revealed that the simulator operates under two distinct, mathematically incompatible definitions of the same geometric events: one used by the scheduler to plan routes, and another enforced by the physical field bounds.

### Parameter Comparison Matrix

| Component | Analytical Formulation | Implemented Code | Observed Consequence at $z_{\text{kiss}} \approx -1.598$ |
| --- | --- | --- | --- |
| **Radius Function** $R(z)$ | $R_0 e^{-\beta z}$ | $R_0 e^{-\beta \max(0, z)}$ | Clamped to $R = 3.0$ ($D = 6.0$); analytical expectation is $R = 4.0$ ($D = 8.0$). |
| **Base Kiss Elevation** $z_{\text{kiss}}$ | $\frac{1}{\beta} \ln\left(\frac{2R_0}{dX}\right)$ | Same formula via `kiss_height()` | Calculates $z \approx -1.598$ for 8-unit spans, aiming for a phantom coordinate. |
| **Operational Tiers** $z_n$ | Continuous | $z_n = z_{\text{base}} + n\frac{\pi}{k}$ | Forces discrete transfer elevations ($\Delta z \approx 8.976$) regardless of local tangency. |

---

## 3. Key Findings

### Finding A: The Negative-$z$ Radius Clamp

Inspection of `radius_at_z()` revealed an explicit numerical guardrail:


$$R(z) = R_0 e^{-\beta \max(0, z)}$$


Without this clamp, negative elevations would cause the exponential term to blow up toward infinity, destabilizing the simulation. However, this guardrail hard-caps the radius at $R_0 = 3.0$ for all $z \le 0$.

For Channels 0 and 2 (separated by $D = 8.0$ units), the maximum possible channel diameter is $2R = 6.0$. This produces a permanent, unbridgeable **2.0-unit geometric gap** at Tier 0 ($8.0 - 6.0 = 2.0$), proving that wide channels never achieve true physical tangency anywhere in the field.

### Finding B: Periodic Tier Envelopes & Zero Backtracking

Our initial audit instrument registered an apparent $17.95$-unit backtracking penalty on high-altitude `2 -> 0` hops because it rigidly forced all transfers through the global Tier-0 kiss point ($z = -1.598$).

By updating the audit script to evaluate packets against local periodic tiers:


$$z_n = z_{\text{base}} + n\frac{\pi}{k} \quad (\text{where } \frac{\pi}{k} \approx 8.976)$$


We proved across all 20 captured simulation hops that **local axial backtracking is identically zero ($B_{\text{axial}} = 0.00$)**. The simulator is not dragging packets backward; it is executing clean, discrete transfers across equivalent operational tiers.

### Finding C: Scheduled Teleportation Across Voids

Because the scheduler (`prefer_kiss_height` and `apply_switch`) relies on discrete tier intervals rather than continuous cross-sectional contact, it cheerfully authorizes high-altitude transfers (such as Tier 1 at $z = 7.38$) where the channel diameter has decayed to $1.59$ units, leaving a massive **6.41-unit physical gap** between the channels.

---

## 4. Architectural Conclusion

The VVB simulator successfully runs by decoupling **scheduler authorization gates** (governed by periodic clock intervals) from **continuous physical tangency** (governed by clamped exponential boundaries).

As Lumen aptly noted, we did not need to straighten the geometry; our diagnostic instruments successfully **measured the bend**.

*Report submitted by Ellie, compiled from telemetry and source inspections on the Precision lab cluster.*
