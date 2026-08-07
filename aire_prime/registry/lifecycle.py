from enum import StrEnum


class LifecycleState(StrEnum):
    DRAFT = "Draft"
    SUBMITTED = "Submitted"
    CONTRACT_BOUND = "Contract-bound"
    VALIDATION_PENDING = "Validation pending"
    PROVISIONAL = "Provisional"
    RESTRICTED = "Restricted"
    REPLICATED = "Replicated"
    EXPIRED = "Expired"
    SUPERSEDED = "Superseded"
    REJECTED = "Rejected"
    WITHDRAWN = "Withdrawn"
    GROUNDING_CONFLICT = "Grounding Conflict"
    BUDGET_VIOLATION = "Budget Violation"
    EVALUATOR_CONTAMINATION = "Evaluator Contamination"


ALLOWED_TRANSITIONS: dict[LifecycleState, frozenset[LifecycleState]] = {
    LifecycleState.DRAFT: frozenset(
        {LifecycleState.SUBMITTED, LifecycleState.WITHDRAWN}
    ),
    LifecycleState.SUBMITTED: frozenset(
        {
            LifecycleState.CONTRACT_BOUND,
            LifecycleState.REJECTED,
            LifecycleState.WITHDRAWN,
        }
    ),
    LifecycleState.CONTRACT_BOUND: frozenset(
        {
            LifecycleState.VALIDATION_PENDING,
            LifecycleState.REJECTED,
            LifecycleState.WITHDRAWN,
        }
    ),
    LifecycleState.VALIDATION_PENDING: frozenset(
        {
            LifecycleState.PROVISIONAL,
            LifecycleState.RESTRICTED,
            LifecycleState.REJECTED,
            LifecycleState.WITHDRAWN,
            LifecycleState.GROUNDING_CONFLICT,
            LifecycleState.BUDGET_VIOLATION,
            LifecycleState.EVALUATOR_CONTAMINATION,
        }
    ),
    LifecycleState.PROVISIONAL: frozenset(
        {
            LifecycleState.RESTRICTED,
            LifecycleState.REPLICATED,
            LifecycleState.EXPIRED,
            LifecycleState.SUPERSEDED,
        }
    ),
    LifecycleState.RESTRICTED: frozenset(
        {
            LifecycleState.REPLICATED,
            LifecycleState.EXPIRED,
            LifecycleState.SUPERSEDED,
        }
    ),
    LifecycleState.REPLICATED: frozenset(
        {
            LifecycleState.EXPIRED,
            LifecycleState.SUPERSEDED,
            LifecycleState.GROUNDING_CONFLICT,
        }
    ),
    LifecycleState.EXPIRED: frozenset(),
    LifecycleState.SUPERSEDED: frozenset(),
    LifecycleState.REJECTED: frozenset(),
    LifecycleState.WITHDRAWN: frozenset(),
    LifecycleState.GROUNDING_CONFLICT: frozenset(),
    LifecycleState.BUDGET_VIOLATION: frozenset(),
    LifecycleState.EVALUATOR_CONTAMINATION: frozenset(),
}


class InvalidLifecycleTransition(ValueError):
    pass


def require_transition(current: LifecycleState, target: LifecycleState) -> None:
    if target not in ALLOWED_TRANSITIONS[current]:
        raise InvalidLifecycleTransition(
            f"invalid lifecycle transition: {current.value} -> {target.value}"
        )
