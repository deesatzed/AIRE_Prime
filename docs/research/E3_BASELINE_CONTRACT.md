# E3 Frozen Baseline and Resource Contract

**Status:** Design contract; baseline implementations must be frozen before candidate work

## Fair-comparison principle

E3 compares adaptation under a bounded information and interaction channel. Every eligible arm
receives the same target observations, task interface, calibration episodes, evaluation episodes,
packet byte ceiling, recipient update allowance, and containment boundary. Differences are explicit
evidence, not silently normalized away.

The primary comparison is against the strongest eligible baseline. Weak controls are useful for
diagnosis but cannot establish improvement.

## Mandatory baselines

### B0 — No transfer

The fresh recipient receives an empty canonical packet and adapts only from the target calibration
episodes. This measures the value of any transferred artifact.

### B1 — Random packet

A deterministic seed produces a structurally valid but semantically random 2,048-byte packet. This
tests whether packet presence, parser behavior, or recipient branching causes an effect.

### B2 — Compressed source trajectories

The arm selects and compresses source observation/action/reward trajectories into the same packet
budget using a frozen deterministic algorithm. It tests the compression hypothesis directly.

### B3 — Nearest-neighbor policy table

The arm stores as many source observation/action examples as fit in the packet and uses a frozen
distance/tie-breaking rule. It is a strong bounded lookup baseline.

### B4 — Policy distillation

A small typed policy representation is fit to source behavior and serialized under the same byte
ceiling. Training data, optimization steps, and fitting time are recorded.

### B5 — Conventional feature representation

A frozen PCA/random-projection-style feature map plus a linear target adapter is fit under the same
training and packet budgets. The exact method is selected and frozen during the baseline phase.

### B6 — Contrastive/world-model representation

A compact representation is trained to predict or contrast temporal transitions without causal
intervention structure. This is the principal modern noncausal representation baseline.

### B7 — Causal representation baseline

A literature-grounded causal representation method compatible with the discrete interventional
world is implemented or attached. Its assumptions and any privileged information must be declared.
If no method fits without changing the task, the incompatibility is documented; B7 may not be
replaced with a weak proxy and still called state of the art.

### B8 — Symmetry/alignment baseline

A frozen equivalence- or symmetry-discovery method aligns source and target interfaces without the
candidate's causal program. This addresses zero-shot coordination overlap.

### B9 — Oracle upper bound

The validator supplies the true mechanism library and target binding under the same recipient
execution interface. B9 is not eligible for the improvement comparison; it establishes headroom
and detects an impossible benchmark.

## Candidate arm

The first candidate emits a typed sparse causal program containing only:

- abstract variable domains;
- typed mechanism/operator descriptions;
- dependency edges;
- intervention signatures;
- a bounded target-alignment procedure;
- provenance and training commitments.

It may not contain unrestricted source code, model weights, hidden labels, validator names,
target-world identifiers, file paths, environment variables, or external references.

## Recipient families

Every serious arm must be evaluated with at least these independently initialized recipients:

1. linear/tabular adapter;
2. recurrent adapter;
3. small feed-forward or attention-based adapter;
4. typed program interpreter.

An arm may be inapplicable only when incompatibility is declared before scoring. The headline claim
must report the complete arm-by-recipient matrix and cannot select only favorable recipients.

## Resource vector

### Hard-matched dimensions

- transfer packet: at most 2,048 canonical bytes;
- source-world interaction budget;
- target calibration episodes: at most 32 per world;
- scored target episodes: 256 per world by default;
- recipient update steps;
- external calls: zero;
- observation access;
- task requests and interaction count;
- receiver prior and initialization policy.

### Bounded and reported dimensions

- discoverer operation count;
- recipient operation count;
- elapsed time;
- peak resident bytes;
- declared energy proxy;
- artifact count and total persisted bytes.

Elapsed time and peak RSS are measured with paired randomized arm order on a pinned host. They are
not required to be numerically identical. The confirmatory contract must choose one of two claims:

1. **Resource-equivalent claim:** predeclare an equivalence margin and show the complete confidence
   interval lies inside it; or
2. **Resource-envelope claim:** show every arm stayed below hard ceilings and report a performance-
   resource Pareto frontier without claiming equivalence.

The claim type is frozen before confirmatory seeds are derived.

## Eligibility rules

An arm is comparison-eligible only if:

- its packet parses and stays within the exact byte ceiling;
- it executes through the reviewed contained recipient;
- its declared resource and observation access match the frozen contract;
- it produces the complete expected episode set;
- all failures remain in evidence;
- it was frozen before confirmatory seed derivation.

An invalid or failed arm is not assigned zero performance. It is retained as invalid/undetermined
and blocks a superiority claim when it is a mandatory serious baseline.

## Baseline freeze gate

Candidate implementation may begin only after:

- B0 through B6 and B9 pass focused and adversarial tests;
- B7 and B8 are either executable or have a reviewed incompatibility record;
- the recipient matrix and resource contract are canonical objects;
- the maximum-baseline selection rule is tested;
- packet-capacity and leakage audits pass;
- the baseline checkpoint is committed and pushed.
