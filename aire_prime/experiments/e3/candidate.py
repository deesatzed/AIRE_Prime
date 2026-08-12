from typing import Literal

from pydantic import Field, computed_field, field_validator

from aire_prime.core.canonical import canonical_bytes, content_id
from aire_prime.core.model import FrozenModel
from aire_prime.experiments.e3.contracts import E3_HARD_CONTRACT
from aire_prime.experiments.e3.recipient import (
    RecipientExchange,
    RecipientSpec,
    _pack_observation,
)
from aire_prime.experiments.e3.world import E3World, ProposerEpisode, ProposerWorld
from aire_prime.measurement.resources import ResourceMeasurement, ResourceVector

ALLOWED_OPERATORS = ("intervention-effect", "parent-gate", "parity", "threshold")


class CausalMechanism(FrozenModel):
    operator: str
    source_index: int = Field(ge=0)
    target_index: int = Field(ge=0)
    parameter: int = Field(ge=0, le=8)
    dependencies: tuple[int, ...] = ()

    @field_validator("operator")
    @classmethod
    def require_allowed_operator(cls, value: str) -> str:
        if value not in ALLOWED_OPERATORS:
            raise ValueError("candidate operator is not in the reviewed typed allow-list")
        return value


class CausalProgramPacket(FrozenModel):
    arm_id: Literal["candidate"] = "candidate"
    version: str = "e3-causal-program-v1"
    mechanisms: tuple[CausalMechanism, ...]
    alignment: tuple[int, ...]
    provenance: str

    @computed_field  # type: ignore[prop-decorator]
    @property
    def operator_count(self) -> int:
        return len(self.mechanisms)

    def _unpadded_wire_bytes(self) -> bytes:
        wire = canonical_bytes(
            {
                "arm_id": self.arm_id,
                "version": self.version,
                "mechanisms": self.mechanisms,
                "alignment": self.alignment,
                "provenance": self.provenance,
            }
        )
        if len(wire) > E3_HARD_CONTRACT.packet_bytes:
            raise ValueError("candidate causal program exceeds the 2,048-byte packet ceiling")
        return wire

    @computed_field  # type: ignore[prop-decorator]
    @property
    def packet_bytes(self) -> int:
        self._unpadded_wire_bytes()
        return E3_HARD_CONTRACT.packet_bytes

    @computed_field  # type: ignore[prop-decorator]
    @property
    def wire_bytes(self) -> bytes:
        wire = self._unpadded_wire_bytes()
        return wire + b"\0" * (E3_HARD_CONTRACT.packet_bytes - len(wire))

    @computed_field  # type: ignore[prop-decorator]
    @property
    def content_id(self) -> str:
        return content_id({"wire": self.wire_bytes.hex(), "arm_id": self.arm_id})


def _summarize_world(world: ProposerWorld) -> tuple[int, int, int]:
    action_counts = [0] * 5
    reward_count = 0
    intervention_signal = 0
    for episode in world.episodes:
        action_counts[episode.action] += 1
        reward_count += episode.reward
        intervention_signal += sum(episode.intervention_outcomes)
    majority = min(range(5), key=lambda action: (-action_counts[action], action))
    return majority, reward_count, intervention_signal % 9


def discover_causal_program(source_worlds: tuple[ProposerWorld, ...]) -> CausalProgramPacket:
    if not source_worlds:
        raise ValueError("candidate requires source interaction evidence")
    summaries = tuple(_summarize_world(world) for world in source_worlds)
    mechanisms = tuple(
        CausalMechanism(
            operator=ALLOWED_OPERATORS[index % len(ALLOWED_OPERATORS)],
            source_index=index,
            target_index=(summary[0] + index) % 6,
            parameter=(summary[1] + summary[2] + index) % 9,
            dependencies=tuple(range(min(index, 2))),
        )
        for index, summary in enumerate(summaries)
    )
    return CausalProgramPacket(
        mechanisms=mechanisms,
        alignment=tuple(summary[0] for summary in summaries),
        provenance="source-interventions-v1",
    )


def _predict_candidate(
    packet: CausalProgramPacket,
    spec: RecipientSpec,
    calibration: tuple[ProposerEpisode, ...],
    evaluation: tuple[ProposerEpisode, ...],
) -> tuple[int, ...]:
    calibration_prior = min(
        range(5),
        key=lambda action: (
            -sum(episode.action == action for episode in calibration),
            action,
        ),
    )
    alignment = packet.alignment or (0,)
    outputs: list[int] = []
    for episode in evaluation:
        packed = _pack_observation(episode.observation)
        mechanism_signal = sum(
            mechanism.parameter * ((packed >> mechanism.source_index) & 1)
            for mechanism in packet.mechanisms
        )
        action = (
            mechanism_signal
            + alignment[episode.action % len(alignment)]
            + calibration_prior
        ) % 5
        if spec.kind == "recurrent" and outputs:
            action = (action + outputs[-1]) % 5
        elif spec.kind == "feedforward":
            action = (action + sum(episode.observation[:4])) % 5
        elif spec.kind == "linear":
            action = (action + spec.seed) % 5
        outputs.append(action)
    return tuple(outputs)


def run_candidate_recipient(
    packet: CausalProgramPacket,
    world: E3World,
    spec: RecipientSpec,
    *,
    calibration_episodes: int = E3_HARD_CONTRACT.target_calibration_episodes,
) -> RecipientExchange:
    if calibration_episodes != E3_HARD_CONTRACT.target_calibration_episodes:
        raise ValueError("calibration schedule is frozen")
    expected = E3_HARD_CONTRACT.target_calibration_episodes + E3_HARD_CONTRACT.evaluation_episodes
    if len(world.episodes) != expected:
        raise ValueError("world does not provide the frozen calibration/evaluation schedule")
    view = world.proposer_view()
    predictions = _predict_candidate(
        packet,
        spec,
        view.episodes[:calibration_episodes],
        view.episodes[calibration_episodes:],
    )
    return RecipientExchange(
        recipient_id=spec.recipient_id,
        packet_arm_id="candidate",
        packet_content_id=packet.content_id,
        target_world_id=world.content_id,
        calibration_episode_count=calibration_episodes,
        predicted_actions=predictions,
        contained=True,
        observation_access="proposer-visible-v1",
        resources=ResourceVector(
            packet_bytes=ResourceMeasurement.observed(float(packet.packet_bytes)),
            interaction_count=ResourceMeasurement.observed(float(expected)),
            operation_count=ResourceMeasurement.observed(
                float(packet.operator_count * len(predictions))
            ),
            external_calls=ResourceMeasurement.observed(0.0),
        ),
    )


__all__ = [
    "ALLOWED_OPERATORS",
    "CausalMechanism",
    "CausalProgramPacket",
    "discover_causal_program",
    "run_candidate_recipient",
]
