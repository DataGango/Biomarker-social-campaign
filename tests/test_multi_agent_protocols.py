import unittest

from fastapi.testclient import TestClient

from multi_agent.a2a_server import create_a2a_app
from multi_agent.mcp_server import create_mcp_server
from multi_agent.orchestrator import AgentOrchestrator, AgentSkill, AgentSpec


class ProtocolAdapterTests(unittest.TestCase):
    def setUp(self):
        skill = AgentSkill("research_question", "Source-grounded test Q&A.", ("question",), (), ())
        self.orchestrator = AgentOrchestrator(
            [
                AgentSpec(
                    "Test Research Agent",
                    "Returns a fixed source-grounded test response.",
                    skill,
                    lambda payload: {
                        "answer": "Test answer [S1].",
                        "sources": [{"id": "S1", "url": "https://example.test/source"}],
                    },
                )
            ]
        )

    def test_mcp_server_registers(self):
        server = create_mcp_server(self.orchestrator)
        self.assertEqual(type(server).__name__, "MCPServer")

    def test_a2a_agent_card_is_discoverable(self):
        app = create_a2a_app(self.orchestrator)
        with TestClient(app) as client:
            response = client.get("/.well-known/agent-card.json")
        self.assertEqual(response.status_code, 200)
        self.assertIn("research_question", response.text)

    def test_a2a_jsonrpc_route_is_mounted(self):
        app = create_a2a_app(self.orchestrator)
        paths = {route.path for route in app.routes}
        self.assertIn("/", paths)


if __name__ == "__main__":
    unittest.main()
