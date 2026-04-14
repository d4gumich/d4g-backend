from unittest.mock import MagicMock, patch

from src.core.settings import settings
from src.socrates.service import SocratesService


def test_service_graph_registration():
    service = SocratesService()
    # Check if 'refine' node exists in the graph
    assert "refine" in service.builder.nodes
    assert "classify" in service.builder.nodes
    assert "action_draft" in service.builder.nodes


def test_service_initialization_no_db():
    with patch.object(settings, "SOCRATES_DB_URL", None):
        service = SocratesService()
        assert service.graph is not None


def test_service_initialization_with_db_error():
    with patch.object(settings, "SOCRATES_DB_URL", "postgresql://invalid:invalid@localhost:5432/invalid"):
        # Mock sys.modules to avoid triggering real import that fails due to missing psycopg/libpq
        mock_saver = MagicMock()
        mock_saver.from_conn_string.side_effect = Exception("Connection refused")
        
        with patch.dict("sys.modules", {"langgraph.checkpoint.postgres": MagicMock(PostgresSaver=mock_saver)}):
            service = SocratesService()
            assert service.graph is not None
            # Should still compile without checkpointer
