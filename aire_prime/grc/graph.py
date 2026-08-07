from typing import Self

from pydantic import field_validator, model_validator

from aire_prime.core.model import FrozenModel


class Node(FrozenModel):
    id: str
    type_ref: str


class Hyperedge(FrozenModel):
    id: str
    sources: tuple[str, ...]
    targets: tuple[str, ...]

    @field_validator("sources", "targets")
    @classmethod
    def require_references(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if not value:
            raise ValueError("hyperedges require at least one source and target")
        return value


class GRCGraph(FrozenModel):
    nodes: tuple[Node, ...]
    edges: tuple[Hyperedge, ...] = ()

    @field_validator("nodes")
    @classmethod
    def sort_nodes(cls, value: tuple[Node, ...]) -> tuple[Node, ...]:
        return tuple(sorted(value, key=lambda node: node.id))

    @field_validator("edges")
    @classmethod
    def sort_edges(cls, value: tuple[Hyperedge, ...]) -> tuple[Hyperedge, ...]:
        return tuple(sorted(value, key=lambda edge: edge.id))

    @model_validator(mode="after")
    def validate_graph(self) -> Self:
        node_ids = [node.id for node in self.nodes]
        if len(node_ids) != len(set(node_ids)):
            raise ValueError("node IDs must be unique")

        edge_ids = [edge.id for edge in self.edges]
        if len(edge_ids) != len(set(edge_ids)):
            raise ValueError("edge IDs must be unique")
        if set(node_ids) & set(edge_ids):
            raise ValueError("node and edge IDs must be unique graph-wide")

        declared_nodes = set(node_ids)
        for edge in self.edges:
            unknown = (set(edge.sources) | set(edge.targets)) - declared_nodes
            if unknown:
                unknown_list = ", ".join(sorted(unknown))
                raise ValueError(f"hyperedge {edge.id} references unknown nodes: {unknown_list}")
        return self
