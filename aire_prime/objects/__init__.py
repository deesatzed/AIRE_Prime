"""Immutable AIRE exchange objects."""

import math
from collections.abc import Mapping
from datetime import datetime
from typing import Annotated, Any, Self

from pydantic import StringConstraints, computed_field, field_validator

from aire_prime.core.canonical import content_id
from aire_prime.core.model import FrozenModel

ContentID = Annotated[str, StringConstraints(pattern=r"^sha256:[0-9a-f]{64}$")]


def normalize_measurements(
    value: tuple[tuple[str, float], ...], *, field_name: str
) -> tuple[tuple[str, float], ...]:
    keys = [key for key, _ in value]
    if len(keys) != len(set(keys)):
        raise ValueError(f"{field_name} keys must be unique")
    if any(not math.isfinite(measurement) for _, measurement in value):
        raise ValueError(f"{field_name} values must be finite")
    return tuple(sorted(value, key=lambda item: item[0]))


class CanonicalObject(FrozenModel):
    schema_version: str = "0.1.0"
    created_at: datetime
    parents: tuple[ContentID, ...] = ()
    validity_region: tuple[str, ...] = ()

    @field_validator("created_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("created_at must include a timezone")
        return value

    def identity_payload(self) -> dict[str, Any]:
        return self.model_dump(
            mode="python",
            exclude={"content_id"},
            exclude_computed_fields=True,
        )

    @computed_field(return_type=str)  # type: ignore[prop-decorator]
    @property
    def content_id(self) -> str:
        return content_id(self.identity_payload())

    @classmethod
    def from_wire(cls, data: Mapping[str, Any], *, context: Any = None) -> Self:
        payload = dict(data)
        transmitted_id = payload.pop("content_id", None)
        if not isinstance(transmitted_id, str):
            raise ValueError("wire object requires content_id")
        instance = cls.model_validate(payload, context=context)
        if transmitted_id != instance.content_id:
            raise ValueError("wire content_id does not match canonical payload")
        return instance
