import pytest

from aire_prime.experiments.e2.run import classify_e2
from aire_prime.objects.evidence import OccurrenceMaturity


def test_o4_requires_every_declared_gate() -> None:
    gates = {
        "heldout-gain": True,
        "causal-ablation": True,
        "matched-controls": True,
        "transformed-generalization": True,
        "fresh-recipient": True,
        "independent-reproduction": True,
    }

    passed = classify_e2(gates)
    assert passed[0] is OccurrenceMaturity.TRANSFERRED
    assert passed[1] == ()

    for gate in gates:
        failed = classify_e2({**gates, gate: False})
        assert failed[0] is not OccurrenceMaturity.TRANSFERRED
        assert failed[1] == (gate,)


def test_classification_vocabulary_is_simulated_and_bounded() -> None:
    forbidden = ("physical", "qec", "superintelligence", "new physics")
    classification = "simulated-alien-sense-transfer"

    assert not any(term in classification.lower() for term in forbidden)


@pytest.mark.parametrize("gates", ({}, {"heldout-gain": True}, {"unexpected": True}))
def test_classification_rejects_missing_or_unexpected_gate_sets(gates: dict[str, bool]) -> None:
    with pytest.raises(ValueError, match="exact E2 gate set"):
        classify_e2(gates)
