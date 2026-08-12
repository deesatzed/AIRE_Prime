# E3 Evidence Matrix

| Gate | Evidence | Identity/status |
| --- | --- | --- |
| Benchmark freeze before candidate | `E3_BENCHMARK_FREEZE.md` | pushed `1e782b2` |
| Confirmatory freeze before seed | `E3_CONFIRMATORY_FREEZE.md` | pushed `5ab0dfc` |
| Commit-bound seed | `SHA256("AIRE-E3-CONFIRMATORY-V1" || 5ab0dfc)` | `f1622631…0211ea` |
| World scale | 180 worlds, 30 per family | complete |
| Arm matrix | candidate, B0--B6, B9 | 6,480 complete blocks |
| Recipient matrix | four fresh recipient families | complete |
| Primary effect | candidate `0.1991808` vs B0 `0.2006727` | point `-0.001492`, negative |
| Bootstrap | 100,000 world-level replicates | interval `[-0.0202854, 0.0050564]` |
| Causal ablation | three targeted, three controls | margin failed |
| Family noninferiority | six shift families | failed |
| Resource evidence | hard dimensions observed; host RSS/time absent | undetermined |
| Independent confirmation | no external recipient | failed/open |
| Grounding | simulated procedural worlds | `G-S` |
| Final report | `e3_report.json` | `sha256:38fd545187aaac308215979f6037831aea58dd59e229abf9a7bc4e53c3612f9f` |

Raw generated artifacts are retained outside Git at
`/private/tmp/aire-e3-confirmatory-5ab0dfc` with manifest, result, report, and ablation summary
hashes recorded in the handoff. The report inspector validates the three canonical JSON artifacts.
