from enum import StrEnum

from aire_prime.core.model import FrozenModel


class OccurrenceMaturity(StrEnum):
    CLAIMED = "O0"
    ASSOCIATED = "O1"
    CAUSALLY_USED = "O2"
    GENERALIZED = "O3"
    TRANSFERRED = "O4"


class GroundingClass(StrEnum):
    UNGROUNDED = "G-U"
    SIMULATED = "G-S"
    OBSERVED = "G-D"
    COUNTERFACTUAL = "G-C"
    PHYSICAL = "G-P"
    PHYSICALLY_REPLICATED = "G-PR"


class EvidenceState(FrozenModel):
    occurrence: OccurrenceMaturity
    grounding: GroundingClass

    @property
    def display(self) -> str:
        return f"{self.occurrence.value}/{self.grounding.value}"
