from src.socrates.service import SocratesService


def test_service_graph_registration():
    service = SocratesService()
    # Check if 'refine' node exists in the graph
    assert "refine" in service.builder.nodes
    # Check if there is an edge from 'classify' to 'refine'
    # In LangGraph, edges can be checked via service.builder.edges or compiled graph
    # For now, let's just check if it's added to the builder

    # We can also check if the edge exists by looking at the compiled graph's representation
    # but simplest is to check the builder.

    # Actually, let's check the edges in the builder
    # LangGraph StateGraph builder has an internal representation of edges
    found_edge = False
    for start, end in service.builder.edges:
        if start == "classify" and end == "refine":
            found_edge = True
            break
    assert found_edge, "Edge from classify to refine not found"
