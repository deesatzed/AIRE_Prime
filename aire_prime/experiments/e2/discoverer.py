import tempfile
from pathlib import Path
from typing import cast

from aire_prime.agents import (
    AgentIdentity,
    AgentRequest,
    AgentResponse,
    MessageKind,
    Role,
    SubprocessAdapter,
    TrustedCommand,
)
from aire_prime.agents.protocol import DeclaredInput
from aire_prime.core.canonical import canonical_bytes, content_id
from aire_prime.core.model import FrozenModel
from aire_prime.grc.constructor import ConstructorPlan, OperationSpec
from aire_prime.grc.types import SpaceKind, StructuralType

_DISCOVERER = r"""use strict;
use warnings;
use JSON::PP;
use Digest::SHA qw(sha256_hex);

my $request_line = <STDIN>;
defined $request_line or exit 20;
my $request = decode_json($request_line);
open my $handle, '<', $ARGV[0] or exit 21;
local $/;
my $packet = decode_json(<$handle>);
close $handle;

my @mapping;
for my $probe (0, 1) {
    my %actions;
    for my $episode (@{$packet->{training_episodes}}) {
        next unless $episode->{probe_success} == $probe;
        my @ordered = sort { $b->[1] <=> $a->[1] } @{$episode->{action_outcomes}};
        $ordered[0]->[1] == 1 or exit 22;
        $actions{$ordered[0]->[0]} = 1;
    }
    my @identified = sort { $a <=> $b } keys %actions;
    @identified == 1 or exit 23;
    push @mapping, [$probe, 0 + $identified[0]];
}
my $operator = {
    training_commitment => $packet->{training_commitment},
    probe_success_to_physical_action => \@mapping,
    interface => ['probe-success', 'physical-action', 'action-label-map'],
};
my $encoder = JSON::PP->new->canonical(1);
my $operator_id = 'sha256:' . sha256_hex($encoder->encode($operator));
my $response = {
    schema_version => '0.1.0',
    message_kind => 'response',
    request_content_id => $request->{content_id},
    sender => $request->{receiver},
    receiver => $request->{sender},
    object_ids => $request->{object_ids},
    content_ids => [$operator_id],
    receipt_content_ids => [],
    failures => [],
};
my $identity = $encoder->encode($response);
$response->{content_id} = 'sha256:' . sha256_hex($identity);
print $encoder->encode($response) . "\n";
"""


class LatentOperator(FrozenModel):
    training_commitment: str
    probe_success_to_physical_action: tuple[tuple[int, int], ...]
    interface: tuple[str, ...]

    @property
    def content_id(self) -> str:
        return content_id(self)


class DiscoveryExchange(FrozenModel):
    request: AgentRequest
    response: AgentResponse
    operator: LatentOperator


def discover_operator(training_packet: dict[str, object]) -> LatentOperator:
    """Reference validator for the intervention-derived operator."""
    episodes = cast(tuple[dict[str, object], ...], training_packet["training_episodes"])
    mapping: list[tuple[int, int]] = []
    for probe_success in (0, 1):
        actions = {
            max(
                cast(tuple[tuple[int, int], ...], episode["action_outcomes"]),
                key=lambda action_outcome: action_outcome[1],
            )[0]
            for episode in episodes
            if episode["probe_success"] == probe_success
        }
        if len(actions) != 1:
            raise ValueError("training interventions do not identify a deterministic operator")
        mapping.append((probe_success, actions.pop()))
    return LatentOperator(
        training_commitment=cast(str, training_packet["training_commitment"]),
        probe_success_to_physical_action=tuple(mapping),
        interface=("probe-success", "physical-action", "action-label-map"),
    )


def run_contained_discovery(
    *, training_packet: dict[str, object], claim_id: str
) -> DiscoveryExchange:
    expected = discover_operator(training_packet)
    packet_id = content_id(training_packet)
    request = AgentRequest(
        message_kind=MessageKind.REALIZE_REQUEST,
        sender=AgentIdentity(agent_id="agent:e2-orchestrator", role=Role.PROPOSER),
        receiver=AgentIdentity(agent_id="agent:e2-discoverer-contained", role=Role.RECEIVER),
        claim_id=claim_id,
        object_ids=(expected.training_commitment,),
        content_ids=(packet_id,),
        declared_inputs=(DeclaredInput(name="training-interventions", content_id=packet_id),),
    )
    with tempfile.TemporaryDirectory(prefix="aire-e2-discovery-") as directory:
        working_directory = Path(directory)
        packet_path = working_directory / "training.json"
        script_path = working_directory / "discover.pl"
        packet_path.write_bytes(canonical_bytes(training_packet))
        script_path.write_text(_DISCOVERER, encoding="utf-8")
        response = SubprocessAdapter(
            trusted_command=TrustedCommand.attest(
                ("/usr/bin/perl", str(script_path), str(packet_path))
            ),
            working_directory=working_directory,
            timeout_seconds=2.0,
            max_input_bytes=16_384,
            max_output_bytes=16_384,
        ).run(request)
    if response.message_kind is not MessageKind.RESPONSE or response.content_ids != (
        expected.content_id,
    ):
        raise RuntimeError("contained discovery did not reproduce the validator commitment")
    return DiscoveryExchange(request=request, response=response, operator=expected)


def operator_constructor(operator: LatentOperator) -> ConstructorPlan:
    table = tuple((float(action),) for _, action in operator.probe_success_to_physical_action)
    return ConstructorPlan(
        object_id=operator.content_id,
        dependencies=("probe_success",),
        operations=(
            OperationSpec(
                id="physical_action",
                primitive="lookup",
                inputs=("probe_success",),
                lookup_table=table,
            ),
            OperationSpec(
                id="nuisance_signal",
                primitive="lookup",
                inputs=("probe_success",),
                lookup_table=((0.25,), (0.75,)),
            ),
        ),
        output_ref="physical_action",
        output_type=StructuralType(kind=SpaceKind.VECTOR, dimensions=(1,)),
    )


def fixed_size_packet(
    *,
    constructor: ConstructorPlan,
    training_commitment: str,
    variant: str,
    size: int,
    method_spec: dict[str, object] | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "constructor": constructor.to_wire(),
        "training_commitment": training_commitment,
        "variant": variant,
        "method_spec": {} if method_spec is None else method_spec,
        "padding": "",
    }
    missing = size - len(canonical_bytes(payload))
    if missing < 0:
        raise ValueError("packet budget is smaller than the constructor payload")
    payload["padding"] = "0" * missing
    if len(canonical_bytes(payload)) != size:
        raise AssertionError("fixed-size packet construction failed")
    return payload
