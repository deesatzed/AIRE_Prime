import hashlib

from aire_prime.core.canonical import canonical_bytes, content_id
from aire_prime.core.model import FrozenModel
from aire_prime.experiments.e1.world import (
    ProceduralWorld,
    ResourceKind,
    realize_capability,
)

BASELINE_KINDS = (
    "fixed-instance",
    "demonstration-list",
    "lookup-policy",
    "random-opaque-packet",
    "conventional-feature-schema",
)


class FrozenBaselinePacket(FrozenModel):
    kind: str
    packet_json: str
    candidate_component_ids: tuple[str, ...] = ()

    @property
    def packet(self) -> bytes:
        return self.packet_json.encode("utf-8")

    @property
    def content_id(self) -> str:
        return content_id(
            {
                "kind": self.kind,
                "packet_bytes": len(self.packet),
                "packet_digest": "sha256:" + hashlib.sha256(self.packet).hexdigest(),
            }
        )


class FrozenBaselineResult(FrozenModel):
    kind: str
    packet_bytes: int
    packet_digest: str
    construction_ids: tuple[str, ...]
    interactions: int
    transmitted_input_bytes: int
    changed_resource_success: bool
    failed_tests: tuple[str, ...]

    @property
    def content_id(self) -> str:
        return content_id(self)


def _pad_packet(payload: dict[str, object], target_bytes: int) -> bytes:
    with_padding = {**payload, "padding": ""}
    empty = canonical_bytes(with_padding)
    if len(empty) > target_bytes:
        raise ValueError("baseline payload exceeds the matched packet budget")
    with_padding["padding"] = "x" * (target_bytes - len(empty))
    packet = canonical_bytes(with_padding)
    if len(packet) != target_bytes:
        raise AssertionError("baseline packet padding is not byte exact")
    return packet


def bandwidth_matched_baseline_packets(
    world: ProceduralWorld, target_bytes: int
) -> tuple[FrozenBaselinePacket, ...]:
    fixed = realize_capability(world, resource=ResourceKind.BATTERY)
    components = fixed.component_ids
    payloads: tuple[tuple[str, dict[str, object], tuple[str, ...]], ...] = (
        (
            "fixed-instance",
            {"component_ids": components},
            components,
        ),
        (
            "demonstration-list",
            {
                "demonstrations": (
                    {"resource": ResourceKind.BATTERY, "component_ids": components},
                )
            },
            components,
        ),
        (
            "lookup-policy",
            {"lookup_policy": {ResourceKind.BATTERY: components}},
            (),
        ),
        (
            "random-opaque-packet",
            {"opaque": hashlib.sha256(b"E1 random opaque baseline").hexdigest()},
            (),
        ),
        (
            "conventional-feature-schema",
            {
                "features": ("stage", "input_port", "output_port", "cost"),
                "component_ids": components,
            },
            components,
        ),
    )
    return tuple(
        FrozenBaselinePacket(
            kind=kind,
            packet_json=_pad_packet(
                {
                    "representation_kind": kind,
                    "requested_resource": world.transfer_resource,
                    "data": data,
                },
                target_bytes,
            ).decode("utf-8"),
            candidate_component_ids=candidate_ids,
        )
        for kind, data, candidate_ids in payloads
    )
