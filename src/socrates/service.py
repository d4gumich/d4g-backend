import logging

from langgraph.graph import END, StateGraph

from src.core.settings import settings
from src.socrates.nodes.action_draft import action_draft_node
from src.socrates.nodes.classify import classify_node
from src.socrates.nodes.dialectic import antithesis_node, synthesis_node, thesis_node
from src.socrates.nodes.evaluator import evaluator_node
from src.socrates.nodes.refine import refine_node
from src.socrates.schemas import SocratesState

logger = logging.getLogger(__name__)


def route_after_action(state: SocratesState) -> str:
    """Routes based on whether evaluation is needed."""
    if state.route == "light":
        logger.info("Light path detected. Skipping evaluation.")
        return END
    logger.info("Evaluation required. Routing to evaluator.")
    return "evaluator"


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


def route_after_classify(state: SocratesState) -> str:
    """Routes based on risk level from classification."""
    route = state.route or "standard"
    if route == "light":
        logger.info("Low risk detected. Routing to Light path (action_draft).")
        return "action_draft"
    logger.info(f"{route.capitalize()} path selected. Routing to refine.")
    return "refine"


class SocratesService:
    def __init__(self):
        self.builder = StateGraph(SocratesState)
        self._setup_graph()

        # Configure checkpointer if DB URL is provided
        if settings.SOCRATES_DB_URL:
            try:
                from langgraph.checkpoint.postgres import PostgresSaver
                # Use PostgresSaver for persistence
                self.checkpointer = PostgresSaver.from_conn_string(settings.SOCRATES_DB_URL)
                # Ensure the checkpoints table is created
                self.checkpointer.setup()
                self.graph = self.builder.compile(checkpointer=self.checkpointer)
                logger.info("SocratesService: Postgres checkpointer initialized.")
            except Exception as e:
                logger.error(f"SocratesService: Failed to initialize Postgres checkpointer: {e}")
                # Fallback to no persistence if DB connection fails
                self.graph = self.builder.compile()
        else:
            logger.warning("SocratesService: SOCRATES_DB_URL not set. Persistence disabled.")
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

        # Branching logic from classify
        self.builder.add_conditional_edges(
            "classify",
            route_after_classify,
            {"refine": "refine", "action_draft": "action_draft"},
        )

        self.builder.add_edge("refine", "thesis")
        self.builder.add_edge("thesis", "antithesis")
        self.builder.add_edge("antithesis", "synthesis")
        self.builder.add_edge("synthesis", "action_draft")

        self.builder.add_conditional_edges(
            "action_draft",
            route_after_action,
            {"evaluator": "evaluator", END: END},
        )

        self.builder.add_conditional_edges(
            "evaluator",
            route_after_eval,
            {"synthesis": "synthesis", END: END},
        )

    async def run(self, request_data: SocratesState):
        # Entry point for the graph
        pass


socrates_service = SocratesService()
