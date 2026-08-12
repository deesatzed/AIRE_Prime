# E3 Confirmatory Results

**Experiment:** AIRE E3 intervention-discovered causal language

**Frozen commit:** `5ab0dfcd13185b6cc2dc0b70057084e84cc4c85a`

**Confirmatory seed:** `f162263141d8887eec42861fab8070d56e1a66199cddcfe539ffaedc000211ea`

**Result report ID:** `sha256:38fd545187aaac308215979f6037831aea58dd59e229abf9a7bc4e53c3612f9f`

**Result artifact ID:** `sha256:ac08ab93b90c47e88ec01db7ccd7d36e149862691b043e9163f47c30475b58c4`

**Raw artifact hashes:** `e3_manifest.json` `7e69908a903ecc35f3ff83247a4c141794a79008a2d2abf0692222b434d310fa`;
`e3_result.json` `0f9e928d54170d6efcf378b40803345b790f43d6bb28419dbaf976164106d900`;
`e3_report.json` `7a95b5645fbabce464c2c9ef579ecc2826ff7d069101bea02a51f86b43b90ade`.

The ablation-summary sidecar SHA-256 is
`8184ae1db7e3bb52d4dce755cd4318ca928f5ae64704d20154ea261d5a66e5bc`.

**Classification:** negative behavioral result; overall superiority claim remains undetermined
because the frozen resource-envelope gate lacks host RSS/timing observations and independent
external reproduction.

## What was tested

The one-shot run evaluated 180 sealed worlds (30 per shift family), 32 calibration episodes, 256
scored episodes, eight eligible arms (candidate plus B0--B6), the B9 oracle headroom arm, and four
independently seeded recipient families. The raw result contains 6,480 complete arm/world/recipient
blocks; no block was silently dropped.

## Primary endpoint

The candidate mean scored accuracy was `0.1991807726`. The strongest eligible baseline was B0 at
`0.2006727431`, giving a point effect of `-0.0014919705`. The frozen 100,000-replicate world-level
bootstrap interval is approximately `[-0.0202854, 0.0050564]`. The primary `+0.05` superiority
margin therefore failed. The oracle mean was `1.0`, leaving substantial headroom, so the benchmark
was not impossible.

## Family and recipient pattern

Candidate mean accuracy by shift family:

| Family | Mean |
| --- | ---: |
| surface | 0.19284 |
| nuisance | 0.20007 |
| parameter | 0.21100 |
| composition | 0.19850 |
| topology | 0.19574 |
| sensor-loss | 0.19694 |

Candidate mean accuracy by recipient:

| Recipient | Mean |
| --- | ---: |
| linear | 0.20740 |
| recurrent | 0.19980 |
| feed-forward | 0.18522 |
| interpreter | 0.20430 |

The candidate did not clear the preregistered family noninferiority or recipient-positive gates.

## Causal and sham checks

The equal-size transformation evidence was retained in `ablation_summary.json` alongside the raw
run. Candidate mean was `0.1991807726`; targeted drops were `0.0004612` (remove operator), `0.0`
(edge permutation), and `-0.0088542` (parameter replacement). The maximum sham drop was `0.0080241`
(wrong-object control), so the targeted-minus-sham causal margin failed. This is not evidence that
the candidate's causal mechanism was behaviorally used.

## Resource and confirmation limits

Hard packet bytes, interaction counts, operation counts, and external-call counts were recorded.
Host elapsed time and peak RSS were not observed by this run, so the resource-equivalent claim was
not available; the resource-envelope gate remains open/undetermined. No independent external
recipient reproduction was available. These are retained failures, not imputed zeros.

## Claim boundary

E3 v1 does not support transferred causal-language improvement. The supported behavioral conclusion
is a negative result against the preregistered primary margin, with failed causal and family gates.
It is a simulated `G-S` result only; it says nothing about physical systems, QEC, consciousness,
general intelligence, superintelligence, or new physics.
