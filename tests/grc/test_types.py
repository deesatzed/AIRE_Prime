import pytest

from aire_prime.grc.types import SpaceKind, StructuralType


def test_structural_type_requires_positive_dimensions() -> None:
    with pytest.raises(ValueError):
        StructuralType(kind=SpaceKind.VECTOR, dimensions=(0,))


def test_human_label_is_not_part_of_structural_identity() -> None:
    left = StructuralType(kind=SpaceKind.VECTOR, dimensions=(4,), label="phase")
    right = StructuralType(kind=SpaceKind.VECTOR, dimensions=(4,), label="unnamed")
    assert left.structural_signature() == right.structural_signature()
