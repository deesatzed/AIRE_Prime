from collections.abc import MutableMapping, MutableSequence, MutableSet
from datetime import date, datetime, time
from enum import Enum
from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, model_validator


def _assert_deeply_immutable(value: object) -> None:
    if isinstance(value, BaseModel):
        if not isinstance(value, FrozenModel) or type(value).model_config.get("frozen") is not True:
            raise ValueError(
                "frozen models can contain only genuinely frozen FrozenModel instances"
            )
        for field_name in type(value).model_fields:
            _assert_deeply_immutable(getattr(value, field_name))
        return
    if isinstance(value, (MutableMapping, MutableSequence, MutableSet, frozenset)):
        raise ValueError(
            "frozen models cannot contain mutable or unordered containers; use tuples"
        )
    if isinstance(value, tuple):
        for item in value:
            _assert_deeply_immutable(item)
        return
    if isinstance(value, Enum):
        _assert_deeply_immutable(value.value)
        return
    canonical_scalars = (str, int, float, bool, datetime, date, time, UUID)
    if value is None or isinstance(value, canonical_scalars):
        return
    raise ValueError(f"unsupported frozen field type: {type(value).__name__}")


class FrozenModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        validate_assignment=True,
    )

    @model_validator(mode="after")
    def require_deeply_immutable_fields(self) -> Self:
        _assert_deeply_immutable(self)
        return self
