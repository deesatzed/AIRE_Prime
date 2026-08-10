from aire_prime.agents import MessageKind
from aire_prime.core.canonical import canonical_bytes, content_id
from aire_prime.core.model import FrozenModel
from aire_prime.experiments.e2.discoverer import fixed_size_packet
from aire_prime.experiments.e2.recipient import RecipientExchange, run_recipient
from aire_prime.experiments.e2.world import CausalSplit
from aire_prime.grc.constructor import ConstructorPlan, OperationSpec
from aire_prime.grc.types import SpaceKind, StructuralType
from aire_prime.measurement.resources import ResourceMeasurement, ResourceVector

BASELINE_KINDS = (
    "frozen-lookup-policy",
    "bandwidth-matched-opaque-tensor",
    "conventional-feature-schema",
)


class E2BaselineResult(FrozenModel):
    kind: str
    method_id: str
    packet_bytes: int
    packet_digest: str
    response_id: str
    measurement_artifact_id: str
    exchange: RecipientExchange
    samples: tuple[float, ...]
    hidden_accuracy: float
    transformed_accuracy: float
    resources: ResourceVector

    @property
    def content_id(self) -> str:
        return content_id(self)


def baseline_method_ids() -> tuple[str, ...]:
    return tuple(content_id({"E2-baseline-method": kind, "version": 3}) for kind in BASELINE_KINDS)


def _constructor(
    *, kind: str, dependency: str, table: tuple[tuple[float, ...], ...]
) -> ConstructorPlan:
    return ConstructorPlan(
        object_id=content_id(
            {"baseline": kind, "dependency": dependency, "table": table, "version": 3}
        ),
        dependencies=(dependency,),
        operations=(
            OperationSpec(
                id="physical_action", primitive="lookup", inputs=(dependency,), lookup_table=table
            ),
            OperationSpec(
                id="nuisance_signal",
                primitive="lookup",
                inputs=(dependency,),
                lookup_table=((0.25,), (0.75,)),
            ),
        ),
        output_ref="physical_action",
        output_type=StructuralType(kind=SpaceKind.VECTOR, dimensions=(1,)),
    )


def build_baseline_packets(*, packet_bytes: int) -> tuple[tuple[str, dict[str, object]], ...]:
    definitions: tuple[tuple[str, str, tuple[tuple[float, ...], ...], dict[str, object]], ...] = (
        (
            "frozen-lookup-policy",
            "probe_success",
            ((0.0,), (0.0,)),
            {"algorithm": "fixed-action-prior", "fixed_action": 0},
        ),
        (
            "bandwidth-matched-opaque-tensor",
            "probe_success",
            ((1.0,), (1.0,)),
            {
                "algorithm": "opaque-first-byte-parity-control",
                "tensor": ("8f", "31", "c2", "09"),
                "decoded_action": 1,
            },
        ),
        (
            "conventional-feature-schema",
            "raw_observation",
            ((0.0,), (0.0,)),
            {"algorithm": "raw-observation-lookup", "feature": "raw_observation"},
        ),
    )
    return tuple(
        (
            kind,
            fixed_size_packet(
                constructor=_constructor(kind=kind, dependency=dependency, table=table),
                training_commitment="baseline:no-discovery",
                variant=kind,
                size=packet_bytes,
                method_spec=method_spec,
            ),
        )
        for kind, dependency, table, method_spec in definitions
    )


def resources(packet_bytes: int, observations: int) -> ResourceVector:
    """Actual deterministic protocol counts; unavailable host usage remains unknown."""
    return ResourceVector(
        packet_bytes=ResourceMeasurement.observed(float(packet_bytes)),
        peak_resident_bytes=ResourceMeasurement.undetermined(),
        operation_count=ResourceMeasurement.observed(float(observations * 2)),
        interaction_count=ResourceMeasurement.observed(1.0),
        elapsed_time=ResourceMeasurement.undetermined(),
        external_calls=ResourceMeasurement.observed(0.0),
        declared_energy_proxy=ResourceMeasurement.observed(float(observations * 2)),
        declared_bandwidth=ResourceMeasurement.observed(float(packet_bytes)),
    )


def correctness_samples(
    *, hidden: CausalSplit, transformed: CausalSplit, actions: tuple[int, ...]
) -> tuple[float, ...]:
    episodes = hidden.episodes + transformed.episodes
    splits = (hidden,) * len(hidden.episodes) + (transformed,) * len(transformed.episodes)
    return tuple(
        float(action == dict(split.action_label_map)[episode.optimal_physical_action])
        for split, episode, action in zip(splits, episodes, actions, strict=True)
    )


def evaluate_baselines(
    *,
    packets: tuple[tuple[str, dict[str, object]], ...],
    hidden: CausalSplit,
    transformed: CausalSplit,
    task_payload: dict[str, object],
    claim_id: str,
    object_id: str,
) -> tuple[E2BaselineResult, ...]:
    count = len(hidden.episodes) + len(transformed.episodes)
    results = []
    methods = dict(zip(BASELINE_KINDS, baseline_method_ids(), strict=True))
    for index, (kind, packet) in enumerate(packets):
        exchange = run_recipient(
            operator_payload=packet,
            task_payload=task_payload,
            claim_id=claim_id,
            object_id=object_id,
            receiver_id=f"agent:e2-control-{index}",
        )
        if (
            exchange.response.message_kind is not MessageKind.RESPONSE
            or exchange.response.content_ids != (exchange.expected_artifact_id,)
        ):
            raise RuntimeError(f"contained baseline failed: {kind}")
        samples = correctness_samples(
            hidden=hidden, transformed=transformed, actions=exchange.expected_actions
        )
        hidden_count = len(hidden.episodes)
        results.append(
            E2BaselineResult(
                kind=kind,
                method_id=methods[kind],
                packet_bytes=len(canonical_bytes(packet)),
                packet_digest=content_id(packet),
                response_id=exchange.response.content_id,
                measurement_artifact_id=exchange.expected_artifact_id,
                exchange=exchange,
                samples=samples,
                hidden_accuracy=sum(samples[:hidden_count]) / hidden_count,
                transformed_accuracy=sum(samples[hidden_count:]) / len(transformed.episodes),
                resources=resources(len(canonical_bytes(packet)), count),
            )
        )
    return tuple(results)
