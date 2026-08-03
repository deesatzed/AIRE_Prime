import math
from collections import deque
from dataclasses import dataclass
from enum import Enum
from typing import Any

import pytest
from pydantic import BaseModel, ConfigDict, ValidationError

from aire_prime.core.canonical import canonical_bytes, content_id
from aire_prime.core.model import FrozenModel


class MutablePayload(FrozenModel):
    items: list[int]


class MutableChild(BaseModel):
    value: int


class NestedMutableModelPayload(FrozenModel):
    child: MutableChild


class UnorderedPayload(FrozenModel):
    values: frozenset[str]


class MutableDequePayload(FrozenModel):
    items: deque[int]


class MappingModel(BaseModel):
    values: dict[Any, str]


class UnfrozenOverride(FrozenModel):
    model_config = ConfigDict(frozen=False)

    value: int


class NestedUnfrozenOverridePayload(FrozenModel):
    child: UnfrozenOverride


@dataclass
class MutableDataclass:
    value: int


class MutableDataclassPayload(FrozenModel):
    child: MutableDataclass


class MutableValueEnum(Enum):
    ITEM = [1]


class MutableEnumPayload(FrozenModel):
    item: MutableValueEnum


def test_canonical_bytes_ignore_mapping_insertion_order() -> None:
    left = {"b": 2, "a": 1}
    right = {"a": 1, "b": 2}
    assert canonical_bytes(left) == canonical_bytes(right)
    assert content_id(left) == content_id(right)


def test_canonical_bytes_reject_non_finite_float() -> None:
    with pytest.raises(ValueError, match="finite"):
        canonical_bytes({"bad": math.nan})


def test_canonical_bytes_reject_non_string_mapping_keys() -> None:
    with pytest.raises(TypeError, match="keys must be strings"):
        canonical_bytes({1: "integer key"})


def test_canonical_bytes_validate_model_keys_before_json_coercion() -> None:
    model = MappingModel(values={1: "integer key", "1": "string key"})
    with pytest.raises(TypeError, match="keys must be strings"):
        canonical_bytes(model)


def test_canonical_identity_has_a_golden_vector() -> None:
    value = {"nested": (True, None, "π"), "a": 1}
    assert canonical_bytes(value) == b'{"a":1,"nested":[true,null,"\xcf\x80"]}'
    assert content_id(value) == (
        "sha256:cad52dcd6759341a85512a16b157ce8e096a7484347afa3b86b399b297dd8777"
    )


def test_frozen_model_rejects_nested_mutable_containers() -> None:
    with pytest.raises(ValidationError, match="mutable or unordered containers"):
        MutablePayload(items=[1])


def test_frozen_model_rejects_mutable_nested_pydantic_model() -> None:
    with pytest.raises(ValidationError, match="genuinely frozen FrozenModel"):
        NestedMutableModelPayload(child=MutableChild(value=1))


def test_frozen_model_rejects_unordered_frozenset() -> None:
    with pytest.raises(ValidationError, match="unordered containers"):
        UnorderedPayload(values=frozenset({"alpha", "beta"}))


def test_frozen_model_rejects_other_mutable_sequences() -> None:
    with pytest.raises(ValidationError, match="mutable or unordered containers"):
        MutableDequePayload(items=deque([1]))


def test_frozen_model_rejects_subclass_that_disables_freezing() -> None:
    with pytest.raises(ValidationError, match="genuinely frozen FrozenModel"):
        NestedUnfrozenOverridePayload(child=UnfrozenOverride(value=1))


def test_frozen_model_rejects_unrecognized_mutable_objects() -> None:
    with pytest.raises(ValidationError, match="unsupported frozen field type"):
        MutableDataclassPayload(child=MutableDataclass(value=1))


def test_frozen_model_recursively_validates_enum_values() -> None:
    with pytest.raises(ValidationError, match="mutable or unordered containers"):
        MutableEnumPayload(item=MutableValueEnum.ITEM)
