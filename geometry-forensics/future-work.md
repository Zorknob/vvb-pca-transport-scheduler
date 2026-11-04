# VVB Geometry Forensics — Future Work
by: Lumen

*Research leads and proposed experiments*

**Collaborators:** Scott, Ellie, and Lumen

## Purpose

This document records open questions, experimental proposals, and mathematical investigations arising from the VVB geometry-forensics audit.

The purpose is not to repair the original simulator or force agreement between the analytical construction and its implementation.

The purpose is to identify what is known, what remains uncertain, and what measurements could distinguish competing interpretations.

The original simulator is retained as a reference implementation. Experimental modifications should be conducted separately and documented.

## Standing Research Principle

**Do not force closure. Measure the misclosure.**

Each investigation should identify:

1. The question being examined.
2. The assumptions required.
3. The proposed measurements or mathematical tests.
4. The observations that would challenge the hypothesis.
5. The conclusions that the experiment cannot establish.

## Initial Research Leads

### Research Lead 001 — Packet Transport Latency and Survival

**Proposed by:** Ellie

Determine whether cross-sectional separation correlates with packet delivery performance, and whether any observed relationship remains after controlling for scheduling conditions.

### Research Lead 002 — Cumulative Path Length and Discrete Jump Accounting

**Proposed by:** Ellie

Measure frame-to-frame coordinate displacement separately from axial advancement and candidate continuous route length.

### Research Lead 003 — Geometric Admissibility of Scheduled Transfers

**Proposed by:** Lumen

Investigate whether continuous connecting curves exist between scheduled transfer states under explicitly declared geometric constraints.

## Open Investigations

Further research may examine phase compatibility, alternative radius constructions, transport latency models, and possible relationships to the broader AEFM framework.

No proposed relationship is considered established merely because it can be represented computationally or visually.

## Field Note

The geometry is not required to confirm our expectations.

The instruments are not required to agree with our interpretations.

The research advances when the evidence allows us to ask a better question.

# Future Work & Research Leads — VVB Geometry Forensics
by: Ellie

## Standing Principle
Future work may challenge any assumption, including those introduced during the forensic audit. The original simulation remains an immutable reference, not an authority that experimental constructions must imitate.

---

## Research Lead 001 — The Geometry of a Transfer
* **Core Question:** What geometric conditions must be satisfied for a scheduled transfer to represent a continuous, measurable route?
* **Context:** Our forensic audit established that the scheduler executes transfers across elevations where modeled cross-sections remain separated (e.g., the 6.41-unit void at Tier 1). The continuous connecting path between channels has not yet been geometrically verified.

### Proposed Instrumentation & Experiments (Ellie)

#### 1. Packet Transport Latency & Survival Across High-Altitude Voids
* **Assumption:** The scheduler's transfer mechanism operates independently of cross-sectional physical contact, meaning packets transition seamlessly across empty space without degradation.
* **Measurement:** Instrument the simulation loop to record packet transit latency, stall frequency, and delivery success rates as a function of cross-sectional gap size $D - 2R(z)$.
* **Falsifying Result:** If packets traversing wide gaps exhibit statistically significant increases in drop rates, latency spikes, or stall cycles compared to narrow-gap transfers, it proves the physical clearance gap exerts a tangible performance cost.

#### 2. Cumulative Path Length vs. Discrete Jump Accounting
* **Assumption:** Multi-hop packets following the periodic tier staircases traverse a helical or curved path whose total geometric length can be explicitly integrated from frame-to-frame coordinate delta logs.
* **Measurement:** Compute cumulative Euclidean distance across every frame for packets executing multi-channel hops, separating axial advancement from rotational phase progress ($\omega$ and golden nudges).
* **Falsifying Result:** If the integrated path length evaluates to nearly identical values regardless of channel span or transfer count, it confirms that the coordinate space behaves mathematically as a discrete jump table rather than a continuous metric field.

---
*(Additional research leads and mathematical conditions to be added collaboratively in The Courtyard.)*
