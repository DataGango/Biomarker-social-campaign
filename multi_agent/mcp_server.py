"""Run Biomarker's read-only/draft-only agents over MCP stdio."""

from __future__ import annotations

import json
from typing import Any

from mcp.server.mcpserver import MCPServer

from multi_agent.orchestrator import AgentOrchestrator, build_default_orchestrator


def create_mcp_server(orchestrator: AgentOrchestrator | None = None) -> MCPServer:
    orchestrator = orchestrator or build_default_orchestrator()
    server = MCPServer("Biomarker Research Agents")

    @server.tool(name="list_agents", description="List registered Biomarker agents and their bounded skills.")
    def list_agents() -> str:
        return json.dumps(orchestrator.list_agents(), ensure_ascii=False)

    @server.tool(name="run_agent_task", description="Run a bounded research, reviewed-poster, codebase-search, or campaign-draft task. This cannot publish or prescribe.")
    def run_agent_task(task_type: str, payload_json: str) -> str:
        try:
            payload: Any = json.loads(payload_json)
        except json.JSONDecodeError as error:
            raise ValueError("payload_json must be valid JSON.") from error
        if not isinstance(payload, dict):
            raise ValueError("payload_json must encode a JSON object.")
        return json.dumps(orchestrator.run(task_type, payload), ensure_ascii=False)

    @server.tool(name="run_research_campaign_workflow", description="Run source-grounded research then hand citations to a draft-only campaign agent. No publication occurs.")
    def run_research_campaign_workflow(question: str, audience: str = "Families and community members", platform: str = "general") -> str:
        result = orchestrator.run_workflow(
            "research_to_campaign_draft",
            {"question": question, "audience": audience, "platform": platform},
        )
        return json.dumps(result, ensure_ascii=False)

    @server.resource("skills://biomarker/registry", name="Agent skill registry", mime_type="application/json")
    def skill_registry() -> str:
        return json.dumps(orchestrator.list_agents(), ensure_ascii=False, indent=2)

    @server.resource("skills://biomarker/safety", name="Agent safety contract", mime_type="text/markdown")
    def safety_contract() -> str:
        return (
            "# Biomarker agent safety contract\n\n"
            "- Research answers are educational and must retain citations from retrieved sources.\n"
            "- Agents do not diagnose, prescribe, or select treatment for a child.\n"
            "- Poster and campaign outputs are DRAFT / NEEDS REVIEW.\n"
            "- No tool publishes, schedules, sends messages, or invokes social publishers.\n"
            "- Codebase search is read-only, scoped to the configured workspace, and returns evidence excerpts rather than full files.\n"
        )

    return server


def main() -> None:
    create_mcp_server().run(transport="stdio")


if __name__ == "__main__":
    main()