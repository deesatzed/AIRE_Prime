from collections import Counter
from typing import Literal

from pydantic import Field, computed_field, field_validator

from aire_prime.core.canonical import content_id
from aire_prime.core.model import FrozenModel
from aire_prime.experiments.e3.contracts import (
    BASELINE_ARM_IDS,
    E3_HARD_CONTRACT,
    BaselinePacket,
)
from aire_prime.experiments.e3.world import E3World, ProposerEpisode
from aire_prime.measurement.resources import ResourceMeasurement, ResourceVector

RECIPIENT_KINDS = ("linear", "recurrent", "feedforward", "interpreter")
RecipientKind = Literal["linear", "recurrent", "feedforward", "interpreter"]


class RecipientSpec(FrozenModel):
    recipient_id: str
    kind: RecipientKind
    seed: int = Field(ge=0)
    adapter_version: str = "e3-reviewed-contained-v1"
    calibration_schedule_id: str = E3_HARD_CONTRACT.calibration_schedule_id
    external_calls: int = 0

    @field_validator("recipient_id")
    @classmethod
    def require_id(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("recipient id must be nonblank")
        return value

    @field_validator("kind", mode="before")
    @classmethod
    def require_kind(cls, value: str) -> str:
        if value not in RECIPIENT_KINDS:
            raise ValueError("recipient kind is not registered")
        return value

    @computed_field  # type: ignore[prop-decorator]
    @property
    def identity(self) -> str:
        return content_id(
            {
                "recipient_id": self.recipient_id,
                "kind": self.kind,
                "seed": self.seed,
                "adapter_version": self.adapter_version,
            }
        )


class RecipientState(FrozenModel):
    recipient_id: str
    kind: RecipientKind
    seed: int
    parameter_commitment: str
    optimizer_commitment: str

    @property
    def content_id(self) -> str:
        return content_id(self)


class RecipientExchange(FrozenModel):
    recipient_id: str
    packet_arm_id: str
    packet_content_id: str
    target_world_id: str
    calibration_episode_count: int
    predicted_actions: tuple[int, ...]
    contained: bool
    observation_access: str
    resources: ResourceVector

    @property
    def content_id(self) -> str:
        return content_id(self)


class BaselineScore(FrozenModel):
    arm_id: str
    recipient_id: str
    valid: bool
    evaluation_count: int
    accuracy: float = Field(ge=0.0, le=1.0)


def build_recipient_state(spec: RecipientSpec) -> RecipientState:
    return RecipientState(
        recipient_id=spec.recipient_id,
        kind=spec.kind,
        seed=spec.seed,
        parameter_commitment=content_id(
            {"recipient": spec.recipient_id, "kind": spec.kind, "seed": spec.seed}
        ),
        optimizer_commitment=content_id(
            {
                "recipient": spec.recipient_id,
                "kind": spec.kind,
                "seed": spec.seed,
                "optimizer": "fresh",
            }
        ),
    )


def _pack_observation(observation: tuple[int, ...]) -> int:
    return sum(bit << index for index, bit in enumerate(observation))


def _unpack_pair(payload: tuple[int, ...], index: int) -> tuple[int, int] | None:
    start = index * 2
    if start + 1 >= len(payload):
        return None
    return payload[start], payload[start + 1] % 5


def _majority_action(actions: tuple[int, ...], fallback: int) -> int:
    if not actions:
        return fallback
    counts = Counter(actions)
    return min(counts, key=lambda action: (-counts[action], action))


def _predict(
    packet: BaselinePacket,
    spec: RecipientSpec,
    world: E3World,
    calibration: tuple[ProposerEpisode, ...],
    evaluation: tuple[ProposerEpisode, ...],
) -> tuple[int, ...]:
    calibration_actions = tuple(episode.action for episode in calibration)
    fallback = _majority_action(calibration_actions, 0)
    pair_count = len(packet.payload) // 2
    previous = fallback
    predictions: list[int] = []
    for episode in evaluation:
        observation = tuple(episode.observation)
        packed = _pack_observation(observation)
        if packet.algorithm == "none":
            action = fallback
        elif packet.algorithm == "random":
            action = (packed + packet.payload[0] + spec.seed) % world.public_spec.action_count
        elif packet.algorithm in {"trajectory", "nearest"} and pair_count:
            pairs = tuple(
                pair
                for pair in (_unpack_pair(packet.payload, i) for i in range(pair_count))
                if pair is not None
            )
            distances = tuple((packed ^ pair[0]).bit_count() for pair in pairs)
            best = min(range(len(distances)), key=lambda i: (distances[i], i))
            action = pairs[best][1]
        elif packet.algorithm == "distill":
            action = (sum(observation) + packet.payload[0]) % world.public_spec.action_count
        elif packet.algorithm == "feature":
            action = (
                sum(index * bit for index, bit in enumerate(observation)) + spec.seed
            ) % world.public_spec.action_count
        elif packet.algorithm == "world-model":
            transition = sum(episode.intervention_outcomes)
            action = (transition + previous + spec.seed) % world.public_spec.action_count
        elif packet.algorithm == "oracle":
            raise ValueError("oracle requires the explicit validator adapter")
        else:
            raise ValueError("packet algorithm is not registered")
        if spec.kind == "recurrent":
            action = (action + previous) % world.public_spec.action_count
        elif spec.kind == "feedforward":
            action = (action + sum(observation[:4])) % world.public_spec.action_count
        elif spec.kind == "linear":
            action = (action + spec.seed) % world.public_spec.action_count
        previous = action
        predictions.append(action)
    return tuple(predictions)


def run_recipient(
    packet: BaselinePacket,
    world: E3World,
    spec: RecipientSpec,
    *,
    calibration_episodes: int = E3_HARD_CONTRACT.target_calibration_episodes,
) -> RecipientExchange:
    if packet.arm_id not in BASELINE_ARM_IDS:
        raise ValueError("packet arm is not registered")
    if calibration_episodes != E3_HARD_CONTRACT.target_calibration_episodes:
        raise ValueError("calibration schedule is frozen")
    expected_episode_count = (
        E3_HARD_CONTRACT.target_calibration_episodes
        + E3_HARD_CONTRACT.evaluation_episodes
    )
    if len(world.episodes) != expected_episode_count:
        raise ValueError("world does not provide the frozen calibration/evaluation schedule")
    wire = packet.wire_bytes
    calibration = world.proposer_view().episodes[:calibration_episodes]
    evaluation = world.proposer_view().episodes[calibration_episodes:]
    if packet.algorithm == "oracle":
        raise ValueError("oracle requires the explicit validator adapter")
    predictions = _predict(packet, spec, world, calibration, evaluation)
    resources = ResourceVector(
        packet_bytes=ResourceMeasurement.observed(float(len(wire))),
        interaction_count=ResourceMeasurement.observed(float(len(world.episodes))),
        operation_count=ResourceMeasurement.observed(float(len(predictions))),
        external_calls=ResourceMeasurement.observed(0.0),
    )
    return RecipientExchange(
        recipient_id=spec.recipient_id,
        packet_arm_id=packet.arm_id,
        packet_content_id=packet.content_id,
        target_world_id=world.content_id,
        calibration_episode_count=calibration_episodes,
        predicted_actions=predictions,
        contained=True,
        observation_access=E3_HARD_CONTRACT.observation_access,
        resources=resources,
    )


def evaluate_exchange(world: E3World, exchange: RecipientExchange) -> BaselineScore:
    expected = world.validator_spec.optimal_actions[E3_HARD_CONTRACT.target_calibration_episodes :]
    valid = (
        len(expected) == E3_HARD_CONTRACT.evaluation_episodes
        and len(exchange.predicted_actions) == len(expected)
    )
    correct = (
        sum(
            actual == wanted
            for actual, wanted in zip(exchange.predicted_actions, expected, strict=True)
        )
        if valid
        else 0
    )
    return BaselineScore(
        arm_id=exchange.packet_arm_id,
        recipient_id=exchange.recipient_id,
        valid=valid,
        evaluation_count=len(expected) if valid else 0,
        accuracy=correct / len(expected) if valid else 0.0,
    )
