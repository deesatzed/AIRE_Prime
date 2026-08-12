from typing import Literal

from aire_prime.core.canonical import content_id
from aire_prime.core.model import FrozenModel
from aire_prime.experiments.e3.candidate import CausalMechanism, CausalProgramPacket

ABLATION_KINDS = (
    "remove-causal-operator",
    "permute-dependency-edges",
    "replace-mechanism-parameters",
    "change-padding-region",
    "permute-inert-ordering",
    "wrong-object-family",
)
AblationKind = Literal[
    "remove-causal-operator",
    "permute-dependency-edges",
    "replace-mechanism-parameters",
    "change-padding-region",
    "permute-inert-ordering",
    "wrong-object-family",
]


class AblationPacket(FrozenModel):
    kind: AblationKind
    packet: CausalProgramPacket
    source_packet_id: str
    targeted: bool
    changed_fields: tuple[str, ...]

    @property
    def content_id(self) -> str:
        return content_id(self)


def _replace(
    packet: CausalProgramPacket,
    *,
    mechanisms: tuple[CausalMechanism, ...] | None = None,
    alignment: tuple[int, ...] | None = None,
    provenance: str | None = None,
) -> CausalProgramPacket:
    return CausalProgramPacket(
        mechanisms=packet.mechanisms if mechanisms is None else mechanisms,
        alignment=packet.alignment if alignment is None else alignment,
        provenance=packet.provenance if provenance is None else provenance,
    )


def build_ablation_packets(
    packet: CausalProgramPacket, *, wrong_object: CausalProgramPacket
) -> tuple[AblationPacket, ...]:
    if not packet.mechanisms:
        raise ValueError("candidate packet requires at least one mechanism")
    first = packet.mechanisms[0]
    remove = _replace(packet, mechanisms=packet.mechanisms[:-1] + (first,))
    permuted = tuple(
        mechanism.model_copy(
            update={"dependencies": tuple(reversed(mechanism.dependencies))}
        )
        for mechanism in packet.mechanisms
    )
    parameter_changed = tuple(
        mechanism.model_copy(update={"parameter": (mechanism.parameter + 1) % 9})
        for mechanism in packet.mechanisms
    )
    padding_changed = _replace(packet, provenance=packet.provenance + "-padding-sham")
    ordering_changed = _replace(packet, alignment=tuple(reversed(packet.alignment)))
    return (
        AblationPacket(
            kind="remove-causal-operator",
            packet=remove,
            source_packet_id=packet.content_id,
            targeted=True,
            changed_fields=("mechanisms",),
        ),
        AblationPacket(
            kind="permute-dependency-edges",
            packet=_replace(packet, mechanisms=permuted),
            source_packet_id=packet.content_id,
            targeted=True,
            changed_fields=("dependencies",),
        ),
        AblationPacket(
            kind="replace-mechanism-parameters",
            packet=_replace(packet, mechanisms=parameter_changed),
            source_packet_id=packet.content_id,
            targeted=True,
            changed_fields=("parameters",),
        ),
        AblationPacket(
            kind="change-padding-region",
            packet=padding_changed,
            source_packet_id=packet.content_id,
            targeted=False,
            changed_fields=("padding",),
        ),
        AblationPacket(
            kind="permute-inert-ordering",
            packet=ordering_changed,
            source_packet_id=packet.content_id,
            targeted=False,
            changed_fields=("alignment-order",),
        ),
        AblationPacket(
            kind="wrong-object-family",
            packet=wrong_object,
            source_packet_id=packet.content_id,
            targeted=False,
            changed_fields=("world-family",),
        ),
    )


__all__ = ["ABLATION_KINDS", "AblationPacket", "build_ablation_packets"]
