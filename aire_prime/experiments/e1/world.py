import random
from enum import StrEnum

from pydantic import field_validator

from aire_prime.core.canonical import content_id
from aire_prime.core.model import FrozenModel


class ResourceKind(StrEnum):
    BATTERY = "battery"
    SOLAR = "solar"


class ComponentSpec(FrozenModel):
    name: str
    stage: str
    input_port: str
    output_port: str
    resources: tuple[ResourceKind, ...]
    cost: int

    @property
    def content_id(self) -> str:
        return content_id(self)


class CapabilityContract(FrozenModel):
    name: str
    required_stages: tuple[str, ...]
    input_port: str
    output_port: str
    withheld_tests: tuple[str, ...]

    @property
    def content_id(self) -> str:
        return content_id(self)


class ProceduralWorld(FrozenModel):
    seed: int
    contract: CapabilityContract
    components: tuple[ComponentSpec, ...]
    training_resource: ResourceKind
    transfer_resource: ResourceKind
    hidden_test_ids: tuple[str, ...]

    @field_validator("components")
    @classmethod
    def require_unique_components(
        cls, value: tuple[ComponentSpec, ...]
    ) -> tuple[ComponentSpec, ...]:
        names = [component.name for component in value]
        if len(names) != len(set(names)):
            raise ValueError("world component names must be unique")
        return tuple(sorted(value, key=lambda component: component.name))

    @property
    def content_id(self) -> str:
        return content_id(self)


class ConstructionResult(FrozenModel):
    contract_id: str
    resource: ResourceKind
    component_ids: tuple[str, ...]
    passed_tests: tuple[str, ...]
    failed_tests: tuple[str, ...] = ()

    @property
    def success(self) -> bool:
        return not self.failed_tests

    @property
    def artifact_content_id(self) -> str:
        return content_id({"component_ids": self.component_ids, "resource": self.resource})

    @property
    def content_id(self) -> str:
        return content_id(self)


def generate_world(seed: int) -> ProceduralWorld:
    generator = random.Random(seed)
    contract = CapabilityContract(
        name="resource-to-control-capability",
        required_stages=("source", "adapt", "transform", "emit"),
        input_port="local-resource",
        output_port="control-signal",
        withheld_tests=(
            "resource-substitution",
            "port-continuity",
            "composition",
            "single-component-repair",
        ),
    )

    def cost() -> int:
        return generator.randint(1, 9)

    components = (
        ComponentSpec(
            name="battery-source",
            stage="source",
            input_port="local-resource",
            output_port="raw-power",
            resources=(ResourceKind.BATTERY,),
            cost=cost(),
        ),
        ComponentSpec(
            name="solar-source",
            stage="source",
            input_port="local-resource",
            output_port="raw-power",
            resources=(ResourceKind.SOLAR,),
            cost=cost(),
        ),
        ComponentSpec(
            name="battery-adapter",
            stage="adapt",
            input_port="raw-power",
            output_port="regulated-power",
            resources=(ResourceKind.BATTERY,),
            cost=cost(),
        ),
        ComponentSpec(
            name="solar-adapter",
            stage="adapt",
            input_port="raw-power",
            output_port="regulated-power",
            resources=(ResourceKind.SOLAR,),
            cost=cost(),
        ),
        ComponentSpec(
            name="signal-transform",
            stage="transform",
            input_port="regulated-power",
            output_port="logic-signal",
            resources=(ResourceKind.BATTERY, ResourceKind.SOLAR),
            cost=cost(),
        ),
        ComponentSpec(
            name="signal-transform-spare",
            stage="transform",
            input_port="regulated-power",
            output_port="logic-signal",
            resources=(ResourceKind.BATTERY, ResourceKind.SOLAR),
            cost=cost(),
        ),
        ComponentSpec(
            name="control-emitter",
            stage="emit",
            input_port="logic-signal",
            output_port="control-signal",
            resources=(ResourceKind.BATTERY, ResourceKind.SOLAR),
            cost=cost(),
        ),
        ComponentSpec(
            name="independent-monitor",
            stage="monitor",
            input_port="control-signal",
            output_port="monitor-signal",
            resources=(ResourceKind.BATTERY, ResourceKind.SOLAR),
            cost=cost(),
        ),
    )
    hidden_test_ids = tuple(
        content_id({"seed": seed, "test": test_name}) for test_name in contract.withheld_tests
    )
    return ProceduralWorld(
        seed=seed,
        contract=contract,
        components=components,
        training_resource=ResourceKind.BATTERY,
        transfer_resource=ResourceKind.SOLAR,
        hidden_test_ids=hidden_test_ids,
    )


def realize_capability(
    world: ProceduralWorld,
    *,
    resource: ResourceKind,
    fixed_component_ids: tuple[str, ...] | None = None,
    removed_component_id: str | None = None,
    compose_monitor: bool = False,
) -> ConstructionResult:
    components_by_id = {component.content_id: component for component in world.components}
    if fixed_component_ids is None:
        selected: list[ComponentSpec] = []
        for stage in world.contract.required_stages:
            candidates = sorted(
                (
                    component
                    for component in world.components
                    if component.stage == stage
                    and resource in component.resources
                    and component.content_id != removed_component_id
                ),
                key=lambda component: (component.cost, component.name),
            )
            if not candidates:
                return ConstructionResult(
                    contract_id=world.contract.content_id,
                    resource=resource,
                    component_ids=tuple(component.content_id for component in selected),
                    passed_tests=(),
                    failed_tests=("single-component-repair",),
                )
            selected.append(candidates[0])
    else:
        selected = []
        if len(fixed_component_ids) != len(set(fixed_component_ids)):
            return ConstructionResult(
                contract_id=world.contract.content_id,
                resource=resource,
                component_ids=fixed_component_ids,
                passed_tests=(),
                failed_tests=("duplicate-component",),
            )
        unknown = tuple(
            component_id
            for component_id in fixed_component_ids
            if component_id not in components_by_id
        )
        if unknown:
            return ConstructionResult(
                contract_id=world.contract.content_id,
                resource=resource,
                component_ids=fixed_component_ids,
                passed_tests=(),
                failed_tests=("unknown-component",),
            )
        selected = [components_by_id[component_id] for component_id in fixed_component_ids]

    if compose_monitor:
        monitor = next(
            component
            for component in world.components
            if component.stage == "monitor" and resource in component.resources
        )
        selected.append(monitor)

    failed: list[str] = []
    stages = tuple(component.stage for component in selected)
    expected_stages = world.contract.required_stages + (
        ("monitor",) if compose_monitor else ()
    )
    if stages != expected_stages:
        failed.append("single-component-repair")
    if any(resource not in component.resources for component in selected):
        failed.append("resource-substitution")
    if selected and selected[0].input_port != world.contract.input_port:
        failed.append("port-continuity")
    if (
        selected
        and not compose_monitor
        and selected[-1].output_port != world.contract.output_port
    ):
        failed.append("port-continuity")
    for first, second in zip(selected, selected[1:], strict=False):
        if first.output_port != second.input_port:
            failed.append("port-continuity")
            break
    if compose_monitor and (
        len(selected) < 2 or selected[-2].output_port != selected[-1].input_port
    ):
        failed.append("composition")

    passed = tuple(test for test in world.contract.withheld_tests if test not in failed)
    return ConstructionResult(
        contract_id=world.contract.content_id,
        resource=resource,
        component_ids=tuple(component.content_id for component in selected),
        passed_tests=passed,
        failed_tests=tuple(sorted(set(failed))),
    )
