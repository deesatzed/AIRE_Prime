import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError

from aire_prime.core.canonical import content_id
from aire_prime.grc.graph import GRCGraph, Hyperedge, Node


def test_hyperedge_rejects_unknown_node_reference() -> None:
    with pytest.raises(ValidationError, match="unknown"):
        GRCGraph(
            nodes=(Node(id="n1", type_ref="scalar"),),
            edges=(Hyperedge(id="e1", sources=("n1",), targets=("missing",)),),
        )


def test_hyperedge_requires_sources_and_targets() -> None:
    with pytest.raises(ValidationError, match="at least one"):
        Hyperedge(id="e1", sources=(), targets=("n1",))


def test_graph_rejects_duplicate_ids() -> None:
    with pytest.raises(ValidationError, match="unique"):
        GRCGraph(
            nodes=(
                Node(id="n1", type_ref="scalar"),
                Node(id="n1", type_ref="vector"),
            )
        )


def test_graph_rejects_duplicate_edge_ids() -> None:
    with pytest.raises(ValidationError, match="edge IDs must be unique"):
        GRCGraph(
            nodes=(Node(id="n1", type_ref="scalar"),),
            edges=(
                Hyperedge(id="e1", sources=("n1",), targets=("n1",)),
                Hyperedge(id="e1", sources=("n1",), targets=("n1",)),
            ),
        )


def test_graph_rejects_node_and_edge_id_collision() -> None:
    with pytest.raises(ValidationError, match="unique graph-wide"):
        GRCGraph(
            nodes=(Node(id="shared", type_ref="scalar"),),
            edges=(Hyperedge(id="shared", sources=("shared",), targets=("shared",)),),
        )


@given(st.permutations(("n1", "n2", "n3")))
def test_node_order_does_not_change_graph_content_id(order: list[str]) -> None:
    nodes_by_id = {
        "n1": Node(id="n1", type_ref="scalar"),
        "n2": Node(id="n2", type_ref="vector"),
        "n3": Node(id="n3", type_ref="tensor"),
    }
    graph = GRCGraph(nodes=tuple(nodes_by_id[node_id] for node_id in order))
    reference = GRCGraph(nodes=tuple(nodes_by_id.values()))
    assert content_id(graph) == content_id(reference)


@given(st.permutations(("e1", "e2")))
def test_edge_order_does_not_change_graph_content_id(order: list[str]) -> None:
    nodes = (
        Node(id="n1", type_ref="scalar"),
        Node(id="n2", type_ref="scalar"),
    )
    edges_by_id = {
        "e1": Hyperedge(id="e1", sources=("n1",), targets=("n2",)),
        "e2": Hyperedge(id="e2", sources=("n2",), targets=("n1",)),
    }
    graph = GRCGraph(nodes=nodes, edges=tuple(edges_by_id[edge_id] for edge_id in order))
    reference = GRCGraph(nodes=nodes, edges=tuple(edges_by_id.values()))
    assert content_id(graph) == content_id(reference)
