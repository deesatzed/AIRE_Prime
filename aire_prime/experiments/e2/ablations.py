from aire_prime.agents import MessageKind
from aire_prime.core.canonical import content_id
from aire_prime.core.model import FrozenModel
from aire_prime.experiments.e2.baselines import correctness_samples
from aire_prime.experiments.e2.discoverer import fixed_size_packet
from aire_prime.experiments.e2.recipient import RecipientExchange, run_recipient
from aire_prime.experiments.e2.world import CausalSplit
from aire_prime.grc.constructor import ConstructorPlan, OperationSpec
from aire_prime.measurement.ablation import AblationKind, AblationReport, AblationResult


class E2AblationEvidence(FrozenModel):
    report: AblationReport
    targeted_drop: float
    sham_drops: tuple[float, ...]
    packet_ids: tuple[str, ...]
    response_ids: tuple[str, ...]
    exchanges: tuple[RecipientExchange, ...]

    @property
    def content_id(self) -> str:
        return content_id(self)


def _changed(constructor: ConstructorPlan, kind: AblationKind) -> ConstructorPlan:
    causal, nuisance = constructor.operations
    causal_table = causal.lookup_table
    nuisance_table = nuisance.lookup_table
    if kind is AblationKind.TARGETED:
        causal_table = ((0.0,), (0.0,))
    elif kind is AblationKind.RANDOM_SUBSPACE:
        nuisance_table = ((0.0,), (0.0,))
    elif kind is AblationKind.ACTIVATION_PERMUTATION:
        nuisance_table = tuple(reversed(nuisance_table))
    else:
        mean = sum(row[0] for row in nuisance_table) / len(nuisance_table)
        nuisance_table = ((mean,), (mean,))
    return ConstructorPlan(
        object_id=content_id({"source": constructor.object_id, "ablation": kind.value}),
        dependencies=constructor.dependencies,
        operations=(
            OperationSpec(
                id=causal.id, primitive="lookup", inputs=causal.inputs, lookup_table=causal_table
            ),
            OperationSpec(
                id=nuisance.id,
                primitive="lookup",
                inputs=nuisance.inputs,
                lookup_table=nuisance_table,
            ),
        ),
        output_ref=constructor.output_ref,
        output_type=constructor.output_type,
    )


def build_ablation_packets(
    *, constructor: ConstructorPlan, packet_bytes: int
) -> tuple[tuple[AblationKind, tuple[int, ...], dict[str, object]], ...]:
    dimensions = {
        AblationKind.TARGETED: (0,),
        AblationKind.RANDOM_SUBSPACE: (1,),
        AblationKind.ACTIVATION_PERMUTATION: (1,),
        AblationKind.REPRESENTATION_REPLACEMENT: (1,),
    }
    return tuple(
        (
            kind,
            dimensions[kind],
            fixed_size_packet(
                constructor=_changed(constructor, kind),
                training_commitment="ablation:frozen",
                variant=kind.value,
                size=packet_bytes,
                method_spec={"intervention": kind.value, "dimension": dimensions[kind][0]},
            ),
        )
        for kind in AblationKind
    )


def evaluate_e2_ablations(
    *,
    packets: tuple[tuple[AblationKind, tuple[int, ...], dict[str, object]], ...],
    operator_packet_id: str,
    seed: int,
    hidden: CausalSplit,
    transformed: CausalSplit,
    task_payload: dict[str, object],
    claim_id: str,
    object_id: str,
    candidate_accuracy: float,
) -> E2AblationEvidence:
    results = []
    response_ids = []
    exchanges = []
    for index, (kind, dimensions, packet) in enumerate(packets):
        exchange = run_recipient(
            operator_payload=packet,
            task_payload=task_payload,
            claim_id=claim_id,
            object_id=object_id,
            receiver_id=f"agent:e2-ablation-{index}",
        )
        if (
            exchange.response.message_kind is not MessageKind.RESPONSE
            or exchange.response.content_ids != (exchange.expected_artifact_id,)
        ):
            raise RuntimeError(f"contained ablation failed: {kind.value}")
        samples = correctness_samples(
            hidden=hidden, transformed=transformed, actions=exchange.expected_actions
        )
        results.append(
            AblationResult(
                kind=kind,
                selected_dimensions=dimensions,
                mean_absolute_effect=candidate_accuracy - sum(samples) / len(samples),
            )
        )
        response_ids.append(exchange.response.content_id)
        exchanges.append(exchange)
    report = AblationReport(
        seed=seed,
        activation_content_id=operator_packet_id,
        target_content_id=content_id({"target": "probe-conditioned-latent-operator"}),
        evaluator_id="aire:e2-contained-heldout-control:v3",
        metric_id="metric:per-episode-control-accuracy:v3",
        replacement_strategy="equal-packet-executable-inert-channel-controls:v3",
        results=tuple(results),
    )
    return E2AblationEvidence(
        report=report,
        targeted_drop=results[0].mean_absolute_effect,
        sham_drops=tuple(result.mean_absolute_effect for result in results[1:]),
        packet_ids=tuple(content_id(packet) for _, _, packet in packets),
        response_ids=tuple(response_ids),
        exchanges=tuple(exchanges),
    )
