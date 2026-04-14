import logging

from langgraph.graph import StateGraph

from src.socrates.nodes.classify import classify_node
from src.socrates.schemas import SocratesState

logger = logging.getLogger(__name__)


class SocratesService:
    def __init__(self):
        self.builder = StateGraph(SocratesState)
        self._setup_graph()
        self.graph = self.builder.compile()

    def _setup_graph(self):
        """Adds nodes and edges to the LangGraph builder."""
        self.builder.add_node("classify", classify_node)
        self.builder.set_entry_point("classify")

    async def run(self, request_data: SocratesState):
        # Entry point for the graph
        pass


socrates_service = SocratesService()
