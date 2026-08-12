from typing import Literal

from pydantic import Field, computed_field, field_validator

from aire_prime.core.canonical import canonical_bytes, content_id
from aire_prime.core.model import FrozenModel

BASELINE_ARM_IDS = ("B0", "B1", "B2", "B3", "B4", "B5", "B6", "B9")
BASELINE_IDS = BASELINE_ARM_IDS[:-1]
PACKET_BYTES = 2_048


class HardContract(FrozenModel):
    packet_bytes: int = Field(default=PACKET_BYTES, ge=1)
    target_calibration_episodes: int = Field(default=32, ge=1)
    evaluation_episodes: int = Field(default=256, ge=1)
    source_interactions: int = Field(default=288, ge=1)
    recipient_update_steps: int = Field(default=32, ge=0)
    external_calls: int = Field(default=0, ge=0)
    observation_access: str = "proposer-visible-v1"
    calibration_schedule_id: str = "e3-calibration-v1"


E3_HARD_CONTRACT = HardContract()


class BaselinePacket(FrozenModel):
    arm_id: str
    algorithm: str
    payload: tuple[int, ...] = ()

    @field_validator("arm_id", "algorithm")
    @classmethod
    def require_nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("packet identifiers must be nonblank")
        return value

    @field_validator("payload")
    @classmethod
    def require_bounded_integers(cls, value: tuple[int, ...]) -> tuple[int, ...]:
        if any(abs(item) > 2**63 for item in value):
            raise ValueError("packet payload integers exceed the typed bound")
        return value

    def _unpadded_wire_bytes(self) -> bytes:
        wire = canonical_bytes(
            {"arm_id": self.arm_id, "algorithm": self.algorithm, "payload": self.payload}
        )
        if len(wire) > PACKET_BYTES:
            raise ValueError("packet exceeds the 2,048-byte canonical ceiling")
        return wire

    @computed_field  # type: ignore[prop-decorator]
    @property
    def packet_bytes(self) -> int:
        self._unpadded_wire_bytes()
        return PACKET_BYTES

    @computed_field  # type: ignore[prop-decorator]
    @property
    def wire_bytes(self) -> bytes:
        wire = self._unpadded_wire_bytes()
        return wire + b"\0" * (PACKET_BYTES - len(wire))

    @computed_field  # type: ignore[prop-decorator]
    @property
    def content_id(self) -> str:
        return content_id(
            {"arm_id": self.arm_id, "algorithm": self.algorithm, "wire": self.wire_bytes.hex()}
        )


class BaselineCompatibility(FrozenModel):
    arm_id: Literal["B7", "B8"]
    status: Literal["compatible", "incompatible"]
    rationale: str = Field(min_length=1)
