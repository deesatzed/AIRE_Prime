from pydantic import Field

from aire_prime.grc.types import StructuralType
from aire_prime.objects import CanonicalObject
from aire_prime.objects.evidence import GroundingClass


class SenseProposal(CanonicalObject):
    distinction: str
    domain: str
    probe: str
    transformations: tuple[str, ...] = ()
    expected_utility: tuple[str, ...] = ()
    grounding_claim: GroundingClass = GroundingClass.UNGROUNDED
    label: str | None = Field(default=None, exclude=True)


class RealityObject(CanonicalObject):
    state_space: StructuralType
    interfaces: tuple[str, ...]
    transformations: tuple[str, ...] = ()
    invariants: tuple[str, ...] = ()
    constructor_id: str
    uncertainty: str | None = None
    tests: tuple[str, ...] = ()
    resource_requirements: tuple[str, ...] = ()
    label: str | None = Field(default=None, exclude=True)


class MetricProposal(CanonicalObject):
    dimension: str
    measurement_procedure: str
    ordering: str
    baseline_ids: tuple[str, ...]
    invariances: tuple[str, ...] = ()
    consequence: str
    falsifiers: tuple[str, ...]
    anti_gaming_tests: tuple[str, ...]
    complexity_cost: float = Field(ge=0, allow_inf_nan=False)
    expiration_conditions: tuple[str, ...]
    label: str | None = Field(default=None, exclude=True)
