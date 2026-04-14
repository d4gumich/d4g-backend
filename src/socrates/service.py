import logging

from langgraph.graph import END, StateGraph

from src.socrates.nodes.action_draft import action_draft_node
from src.socrates.nodes.classify import classify_node
from src.socrates.nodes.dialectic import antithesis_node, synthesis_node, thesis_node
from src.socrates.nodes.evaluator import evaluator_node
from src.socrates.nodes.refine import refine_node
from src.socrates.schemas import SocratesState

logger = logging.getLogger(__name__)


def route_after_eval(state: SocratesState) -> str:
    """Routes based on evaluation result."""
    if state.passed_eval:
        logger.info("Evaluation passed. Ending.")
        return END
    if state.is_paused:
        logger.info("Evaluation failed and reached retry limit. Pausing.")
        return END
    logger.info("Evaluation failed. Retrying synthesis.")
    return "synthesis"


class SocratesService:
    def __init__(self):
        self.builder = StateGraph(SocratesState)
        self._setup_graph()
        self.graph = self.builder.compile()

    def _setup_graph(self):
        """Adds nodes and edges to the LangGraph builder."""
        self.builder.add_node("classify", classify_node)
        self.builder.add_node("refine", refine_node)
        self.builder.add_node("thesis", thesis_node)
        self.builder.add_node("antithesis", antithesis_node)
        self.builder.add_node("synthesis", synthesis_node)
        self.builder.add_node("action_draft", action_draft_node)
        self.builder.add_node("evaluator", evaluator_node)

        self.builder.set_entry_point("classify")

        self.builder.add_edge("classify", "refine")
        self.builder.add_edge("refine", "thesis")
        self.builder.add_edge("thesis", "antithesis")
        self.builder.add_edge("antithesis", "synthesis")
        self.builder.add_edge("synthesis", "action_draft")
        self.builder.add_edge("action_draft", "evaluator")

        self.builder.add_conditional_edges(
            "evaluator",
            route_after_eval,
            {"synthesis": "synthesis", END: END},
        )

    async def run(self, request_data: SocratesState):
        # Entry point for the graph
        pass


socrates_service = SocratesService()
