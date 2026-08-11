# E3 Related-Work and Novelty Audit

**Status:** Direction-selection survey, not a novelty claim

**Survey date:** 2026-08-11

## Survey boundary

This survey asks whether the proposed E3 conjunction—intervention-derived causal structure,
bounded artifact transfer, unseen causal worlds, non-co-trained recipients, executable causal
ablations, and matched resource accounting—has already been demonstrated.

It does not claim exhaustive coverage. A manuscript-facing novelty claim requires a subsequent
citation search, backward/forward citation review, and comparison against results published after
this date.

## Reused local evidence

- E1 already demonstrates bounded simulated capability transfer to a fresh recipient.
- E2 already demonstrates contained intervention-based discovery, a fresh recipient, transformed
  evaluation, causal and sham ablations, matched alternatives, evidence lineage, and an honest
  negative/undetermined decision.
- Measurement Layer Zero already supplies fail-undetermined resource comparison, frozen control
  contracts, protected dimensions, and deterministic bootstrap evidence.

E3 should reuse these governance and evidence mechanisms while replacing E2's trivial binary
scientific task.

## Primary literature checked for this pass

| Work | Directly relevant result | Consequence for E3 |
| --- | --- | --- |
| Foerster et al., [Learning to Communicate with Deep Multi-Agent Reinforcement Learning](https://arxiv.org/abs/1605.06676), 2016 | End-to-end learned communication can support cooperative partially observed tasks. | Emergent communication itself is not novel; E3 must prove cross-recipient and cross-world transfer. |
| Unger and Bruni, [Generalizing Emergent Communication](https://arxiv.org/abs/2001.01772), 2020 | Environmental incentives can yield grounded discrete protocols and some transfer. | E3 needs stronger shifts, matched noncommunication baselines, and causal mechanism tests. |
| Chaabouni et al., [Compositionality and Generalization in Emergent Languages](https://arxiv.org/abs/2004.09124), 2020 | Compositionality was not correlated with generalization, although it aided transmission to new learners. | Topographic or compositional scores cannot be the primary E3 endpoint. |
| Kharitonov and Baroni, [Emergent Language Generalization and Acquisition Speed Are Not Tied to Compositionality](https://arxiv.org/abs/2004.03420), 2020 | Noncompositional languages can match or exceed compositional ones on generalization and acquisition. | E3 must measure causal utility and adaptation, not human-looking language structure. |
| Bullard et al., [Exploring Zero-Shot Emergent Communication in Embodied Multi-Agent Populations](https://arxiv.org/abs/2010.15896), 2020 | Costly embodied signals and population training can support novel-partner communication. | New-partner transfer is an established research target; E3 must differentiate its causal artifact and evidence contract. |
| Bullard et al., [Quasi-Equivalence Discovery for Zero-Shot Emergent Communication](https://arxiv.org/abs/2103.08067), 2021 | QED discovers protocol symmetries for zero-shot coordination without prespecified symmetries. | Symmetry discovery is a strong baseline or adjacent mechanism, not evidence unique to E3. |
| Galke et al., [Emergent Communication for Understanding Human Language Evolution: What's Missing?](https://arxiv.org/abs/2204.10590), 2022 | Neural-agent studies often fail to reproduce human generalization and group-size effects; memory and alternating roles may matter. | E3 should include population and role-variation analyses only after the main causal-transfer gate. |
| Schölkopf et al., [Towards Causal Representation Learning](https://arxiv.org/abs/2102.11107), 2021 | Discovering high-level causal variables from low-level observations is a central transfer and generalization problem. | E3 must state its intervention and identifiability assumptions explicitly. |
| Buchholz et al., [Learning Linear Causal Representations from Interventions under General Nonlinear Mixing](https://arxiv.org/abs/2306.02235), 2023 | Unknown single-node interventions can provide identifiability under stated distributional assumptions. | E3's world family should expose controlled interventions and avoid universal-identifiability claims. |
| Ahmed et al., [CausalWorld: A Robotic Manipulation Benchmark for Causal Structure and Transfer Learning](https://arxiv.org/abs/2010.04296), 2020 | A combinatorial intervention-rich manipulation benchmark supports controlled transfer studies and possible sim-to-real work. | CausalWorld is the preferred later grounding bridge; E3 should first prove the method in a cheaper sealed generator. |
| Carmeli et al., [Concept-Best-Matching](https://arxiv.org/abs/2403.14705), 2024 | Emergent-message compositionality can be mapped to human concepts with a global score and translation map. | Interpretability is useful secondary analysis but cannot substitute for behavioral and causal proof. |

## Differentiation matrix

| Property | Typical emergent-communication work | Typical causal-representation work | Proposed E3 |
| --- | --- | --- | --- |
| Intervention-derived hidden mechanisms | Sometimes | Central | Required |
| Explicit bounded transferable artifact | Messages/protocol | Usually internal representation | Required |
| Recipient never co-trained with discoverer | Sometimes in zero-shot coordination | Usually not the task | Required |
| Unseen causal compositions and surface encodings | Variable | Often evaluated | Required |
| Executable targeted and sham ablations | Infrequent | Variable | Required |
| Byte, interaction, compute, and host-resource evidence | Infrequent | Infrequent | Required |
| Append-only content-addressed evidence | Not typical | Not typical | Required |

This matrix identifies a plausible research gap, not proof of novelty. The conjunction may still be
anticipated by work outside the current survey.

## Candidate novelty statement

The defensible candidate claim is not “agents invent language” or “causal representations improve
generalization.” It is:

> A compact intervention-derived causal object can be bound and used by independently initialized,
> non-co-trained recipient architectures to improve adaptation to sealed causal shifts under frozen
> evidence and resource contracts.

This statement must be weakened or rejected if a close prior result is found.

## Unresolved overlap searches

Before candidate promotion, extend the survey in these areas:

1. machine teaching and teaching dimension for new-agent policy acquisition;
2. program synthesis and executable world-model transfer;
3. object-centric and identifiable causal representation learning after 2023;
4. cross-architecture representation alignment;
5. information-theoretic lower bounds for message-limited transfer;
6. independent-agent protocol acquisition and iterated learning;
7. causal abstraction and homomorphism transfer in reinforcement learning.

## Promotion gate

The sparse causal-program direction may enter confirmatory experimentation only if:

- at least five directly usable papers remain in the final survey;
- no checked work already demonstrates the complete E3 conjunction;
- every close overlap has a written difference in task, assumptions, baseline, or evidence;
- the proposed effect is useful even if the representation is not human-interpretable;
- the experiment can falsify causal transfer rather than merely score protocol regularity.
