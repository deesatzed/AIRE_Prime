from itertools import pairwise

import pytest

from aire_prime.registry.lifecycle import (
    InvalidLifecycleTransition,
    LifecycleState,
    require_transition,
)


def test_documented_lifecycle_path_is_explicitly_allowed() -> None:
    path = (
        LifecycleState.DRAFT,
        LifecycleState.SUBMITTED,
        LifecycleState.CONTRACT_BOUND,
        LifecycleState.VALIDATION_PENDING,
        LifecycleState.PROVISIONAL,
        LifecycleState.REPLICATED,
    )

    for current, target in pairwise(path):
        require_transition(current, target)


def test_rejected_cannot_reverse_to_provisional() -> None:
    with pytest.raises(InvalidLifecycleTransition, match="Rejected.*Provisional"):
        require_transition(LifecycleState.REJECTED, LifecycleState.PROVISIONAL)


@pytest.mark.parametrize(
    "terminal",
    (
        LifecycleState.EXPIRED,
        LifecycleState.SUPERSEDED,
        LifecycleState.WITHDRAWN,
        LifecycleState.GROUNDING_CONFLICT,
        LifecycleState.BUDGET_VIOLATION,
        LifecycleState.EVALUATOR_CONTAMINATION,
    ),
)
def test_terminal_states_do_not_advance(terminal: LifecycleState) -> None:
    with pytest.raises(InvalidLifecycleTransition):
        require_transition(terminal, LifecycleState.PROVISIONAL)
