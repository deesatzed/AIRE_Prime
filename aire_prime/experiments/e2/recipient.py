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
from aire_prime.grc.constructor import ConstructorPlan
from aire_prime.objects import ContentID

_RECIPIENT = r"""use strict;
use warnings;
use JSON::PP;
use Digest::SHA qw(sha256_hex);
my $request_line = <STDIN>; defined $request_line or exit 20;
my $request = decode_json($request_line);
open my $oh, '<', $ARGV[0] or exit 21; local $/; my $packet = decode_json(<$oh>); close $oh;
open my $th, '<', $ARGV[1] or exit 22; my $task = decode_json(<$th>); close $th;
my $constructor = $packet->{constructor};
@{$constructor->{operations}} == 2 or exit 23;
@{$constructor->{dependencies}} == 1 or exit 24;
$constructor->{output_ref} eq 'physical_action' or exit 25;
$constructor->{output_type}->{kind} eq 'vector' or exit 26;
$constructor->{output_type}->{dimensions}->[0] == 1 or exit 27;
my %operations = map { $_->{id} => $_ } @{$constructor->{operations}};
exists $operations{physical_action} && exists $operations{nuisance_signal} or exit 28;
my $dependency = $constructor->{dependencies}->[0];
($dependency eq 'probe_success' || $dependency eq 'raw_observation') or exit 29;
for my $operation (values %operations) {
    $operation->{primitive} eq 'lookup' or exit 30;
    @{$operation->{inputs}} == 1 && $operation->{inputs}->[0] eq $dependency or exit 31;
    @{$operation->{lookup_table}} == 2 or exit 32;
    for my $row (@{$operation->{lookup_table}}) { @$row == 1 or exit 33; }
}
my @actions;
for my $episode (@{$task->{episodes}}) {
    my %labels = map { $_->[0] => $_->[1] } @{$episode->{physical_to_external}};
    my $input = $dependency eq 'probe_success'
        ? $episode->{probe_success} : $episode->{raw_observation}->[0];
    my %values;
    for my $name (qw(physical_action nuisance_signal)) {
        $values{$name} = 0 + $operations{$name}->{lookup_table}->[$input]->[0];
    }
    my $physical = $values{$constructor->{output_ref}};
    defined $labels{$physical} or exit 34;
    push @actions, $labels{$physical};
}
my $encoder = JSON::PP->new->canonical(1);
my $artifact_id = 'sha256:' . sha256_hex($encoder->encode({actions => \@actions}));
my $response = {
    schema_version => '0.1.0',
    message_kind => 'response',
    request_content_id => $request->{content_id},
    sender => $request->{receiver},
    receiver => $request->{sender},
    object_ids => $request->{object_ids},
    content_ids => [$artifact_id],
    receipt_content_ids => [],
    failures => [],
};
my $identity = $encoder->encode($response); $response->{content_id}='sha256:'.sha256_hex($identity);
print $encoder->encode($response)."\n";
"""


class RecipientExchange(FrozenModel):
    request: AgentRequest
    response: AgentResponse
    expected_actions: tuple[int, ...]
    expected_artifact_id: ContentID


def _actions(
    operator_payload: dict[str, object], task_payload: dict[str, object]
) -> tuple[int, ...]:
    constructor = ConstructorPlan.from_wire(
        cast(dict[str, object], operator_payload["constructor"])
    )
    if (
        constructor.dependencies not in (("probe_success",), ("raw_observation",))
        or constructor.output_ref != "physical_action"
        or tuple(operation.id for operation in constructor.operations)
        != ("physical_action", "nuisance_signal")
        or any(
            operation.primitive != "lookup"
            or operation.inputs != constructor.dependencies
            or len(operation.lookup_table) != 2
            or any(len(row) != 1 for row in operation.lookup_table)
            for operation in constructor.operations
        )
    ):
        raise ValueError("E2 recipient requires the complete constrained lookup constructor")
    operation = constructor.operations[0]
    table = operation.lookup_table
    episodes = cast(tuple[dict[str, object], ...], task_payload["episodes"])
    return tuple(
        dict(cast(tuple[tuple[int, int], ...], episode["physical_to_external"]))[
            int(
                table[
                    cast(int, episode["probe_success"])
                    if constructor.dependencies == ("probe_success",)
                    else cast(tuple[int, ...], episode["raw_observation"])[0]
                ][0]
            )
        ]
        for episode in episodes
    )


def run_recipient(
    *,
    operator_payload: dict[str, object],
    task_payload: dict[str, object],
    claim_id: str,
    object_id: str,
    receiver_id: str,
) -> RecipientExchange:
    expected_actions = _actions(operator_payload, task_payload)
    expected_artifact_id = content_id({"actions": expected_actions})
    with tempfile.TemporaryDirectory(prefix="aire-e2-recipient-") as directory:
        wd = Path(directory)
        operator_path = wd / "operator.json"
        task_path = wd / "task.json"
        script_path = wd / "recipient.pl"
        operator_path.write_bytes(canonical_bytes(operator_payload))
        task_path.write_bytes(canonical_bytes(task_payload))
        script_path.write_text(_RECIPIENT, encoding="utf-8")
        operator_id = content_id(operator_payload)
        task_id = content_id(task_payload)
        request = AgentRequest(
            message_kind=MessageKind.REALIZE_REQUEST,
            sender=AgentIdentity(agent_id="agent:e2-validator", role=Role.VALIDATOR),
            receiver=AgentIdentity(agent_id=receiver_id, role=Role.RECEIVER),
            claim_id=claim_id,
            object_ids=(object_id,),
            content_ids=(operator_id, task_id),
            declared_inputs=(
                DeclaredInput(name="operator", content_id=operator_id),
                DeclaredInput(name="task", content_id=task_id),
            ),
        )
        response = SubprocessAdapter(
            trusted_command=TrustedCommand.attest(
                ("/usr/bin/perl", str(script_path), str(operator_path), str(task_path))
            ),
            working_directory=wd,
            timeout_seconds=2.0,
            max_input_bytes=16_384,
            max_output_bytes=16_384,
        ).run(request)
    return RecipientExchange(
        request=request,
        response=response,
        expected_actions=expected_actions,
        expected_artifact_id=expected_artifact_id,
    )
