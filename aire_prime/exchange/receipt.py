from enum import StrEnum

from pydantic import Field, field_validator

from aire_prime.core.model import FrozenModel
from aire_prime.objects import ContentID


class FailureCode(StrEnum):
    TYPE_MISMATCH = "TypeMismatch"
    UNSUPPORTED_PRIMITIVE = "UnsupportedPrimitive"
    MISSING_DEPENDENCY = "MissingDependency"
    RESOURCE_INFEASIBLE = "ResourceInfeasible"
    OUTSIDE_VALIDITY_REGION = "OutsideValidityRegion"
    CONSTRUCTOR_FAILURE = "ConstructorFailure"
    INVARIANT_VIOLATION = "InvariantViolation"
    VERIFICATION_FAILURE = "VerificationFailure"
    GROUNDING_CONFLICT = "GroundingConflict"
    PERMISSION_DENIED = "PermissionDenied"
    UNDETERMINED = "Undetermined"


class RealizationFailure(FrozenModel):
    code: FailureCode
    message: str
    counterexample: str | None = None


class ResourceUse(FrozenModel):
    operation_count: int = Field(ge=0)
    max_elements: int = Field(ge=0)
    max_tensor_bytes: int = Field(default=0, ge=0)
    output_bytes: int = Field(ge=0)
    elapsed_seconds: float = Field(ge=0, allow_inf_nan=False)


class RealizationReceipt(FrozenModel):
    object_id: ContentID
    receiver_id: str
    local_realization_id: str
    contract_tests: tuple[str, ...] = ()
    resources: ResourceUse
    deviations: tuple[str, ...] = ()
    failures: tuple[RealizationFailure, ...] = ()

    @field_validator("receiver_id", "local_realization_id")
    @classmethod
    def require_attribution_id(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("receipt attribution IDs must be nonblank")
        return value

    @property
    def success(self) -> bool:
        return not self.failures
