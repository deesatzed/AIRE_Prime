# E3 Baseline/Oracle-Only Development Pilot

**Status:** completed before candidate implementation; development evidence only

**Pilot seed:** `301`

**Pilot result ID:** `sha256:9d13a8a2748279fcc762474699ee36a5b5846d86c5b504b952cf830491ac0d58`

**Manifest ID:** `sha256:1285e86ed46ff4df012c0f5efc8570f6c2028b347c93b79e60605c988f8d0eca`

## Purpose and boundary

This run contains only the predeclared baselines B0--B6 and validator-only oracle B9 on the public
source and visible development worlds. It cannot import or construct a candidate, and it has no
confirmatory seed derivation path. The pilot validates benchmark headroom, packet capacity, leakage
boundaries, hard-budget matching, and world-level variance. It is not confirmatory evidence and does
not establish a transfer effect.

## Frozen pilot matrix

- 6 development worlds, one from each shift family;
- 8 arms: B0, B1, B2, B3, B4, B5, B6, B9;
- 4 independently seeded recipients: linear, recurrent, feed-forward, and typed interpreter;
- 32 calibration episodes and 256 scored episodes per world;
- 2,048 canonical packet bytes, 288 total target interactions, zero external calls;
- 192 complete arm/world/recipient blocks; no invalid blocks or missing resource fields.

The resulting arm-level scored accuracy (used only as a pilot diagnostic) was:

| Arm | Mean scored accuracy | Range |
| --- | ---: | ---: |
| B0 | 0.16699 | 0.00--0.66797 |
| B1 | 0.23633 | 0.00--0.50 |
| B2 | 0.17367 | 0.00--0.33594 |
| B3 | 0.18734 | 0.00--0.50 |
| B4 | 0.19515 | 0.00--0.66406 |
| B5 | 0.21533 | 0.00--0.66406 |
| B6 | 0.17415 | 0.00--0.25391 |
| B9 | 1.00000 | 1.00--1.00 |

The oracle-minus-strongest-baseline headroom diagnostic was `0.33203125`; between-world variance
of the baseline diagnostic was `0.0008625865252920828`. These values justify retaining the task
scale and oracle headroom, but do not tune or select the candidate.

## Integrity checks

- Source suite ID: `sha256:c23956bf1041f3c0426512c39aacb76dbc448c5f815ca28b4a6cd24a23b97d1c`.
- Development suite ID: `sha256:61d65314a81b050a2954826fe45b2d831f25080cb8f742150ebed4596463a2c2`.
- Exact source policy lower-bound serialization: `366337` bytes, exceeding the 2,048-byte packet
  ceiling.
- Every development proposer view passed the forbidden-token audit; no validator-only field was
  present in proposer bytes.
- Every packet was exactly 2,048 bytes and every recipient used the same calibration schedule and
  observed interaction count. B9's validator-only observation access is retained as headroom and
  is not comparison eligible.

## Pilot decisions

The benchmark remains viable and has nontrivial oracle headroom. The following are now frozen for
E3 v1 before candidate implementation: the six shift families, 32/256 episode schedule, 2,048-byte
packet ceiling, four recipient families, B0--B6 eligible baseline set, B9 oracle exclusion, zero
external calls, world-level resampling unit, and the resource-envelope claim type. B7 and B8 remain
explicit incompatibilities, not silent weak proxies; their reviewed rationale is in the benchmark
freeze and decision log.

The pilot does not authorize changing the primary endpoint, confirmatory margins, candidate
representation, or hidden seed domain based on candidate outcomes. Any later material change creates
E3 v2.
