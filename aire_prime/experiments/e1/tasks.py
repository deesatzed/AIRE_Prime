from aire_prime.core.canonical import content_id
from aire_prime.core.model import FrozenModel
from aire_prime.experiments.e1.world import (
    ConstructionResult,
    ProceduralWorld,
    realize_capability,
)


class TransferTaskResult(FrozenModel):
    receiver_id: str
    transfer: ConstructionResult
    composition: ConstructionResult
    repair: ConstructionResult
    withheld_conformance_passed: bool

    @property
    def content_id(self) -> str:
        return content_id(self)


def execute_transfer_tasks(
    world: ProceduralWorld,
    *,
    receiver_id: str = "agent:e1-recipient-fresh",
) -> TransferTaskResult:
    transfer = realize_capability(world, resource=world.transfer_resource)
    composition = realize_capability(
        world,
        resource=world.transfer_resource,
        compose_monitor=True,
    )
    transform_id = next(
        component_id
        for component_id in transfer.component_ids
        if next(
            component for component in world.components if component.content_id == component_id
        ).stage
        == "transform"
    )
    repair = realize_capability(
        world,
        resource=world.transfer_resource,
        removed_component_id=transform_id,
    )
    return TransferTaskResult(
        receiver_id=receiver_id,
        transfer=transfer,
        composition=composition,
        repair=repair,
        withheld_conformance_passed=all(
            result.success for result in (transfer, composition, repair)
        ),
    )
