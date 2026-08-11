from aire_prime.exchange.realize import (
    RealizationContext,
    RealizationOutcome,
    Realizer,
)
from aire_prime.grc.constructor import ConstructorPlan
from aire_prime.registry.events import RegistryEvent
from aire_prime.registry.lifecycle import LifecycleState
from aire_prime.registry.store import RegistryStore


def realize_with_registry_evidence(
    realizer: Realizer,
    plan: ConstructorPlan,
    context: RealizationContext,
    *,
    registry: RegistryStore,
    actor_role: str,
    actor_id: str,
    attack_label: str,
) -> tuple[RealizationOutcome, RegistryEvent]:
    """Execute the bounded realizer and append its exact typed receipt to the registry."""
    outcome = realizer.realize(plan, context)
    event = registry.append(
        actor_role=actor_role,
        actor_id=actor_id,
        object_payload=outcome.receipt.model_dump(mode="json"),
        event_type=LifecycleState.DRAFT,
        event_payload={
            "attack_label": attack_label,
            "success": outcome.receipt.success,
        },
    )
    return outcome, event
