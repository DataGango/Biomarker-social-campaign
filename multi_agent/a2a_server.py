"""A2A 1.0 JSON-RPC server for the bounded Biomarker orchestrator."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes.agent_card_routes import create_agent_card_routes
from a2a.server.routes.fastapi_routes import add_a2a_routes_to_fastapi
from a2a.server.routes.jsonrpc_routes import create_jsonrpc_routes
from a2a.server.tasks import InMemoryTaskStore, TaskUpdater
from a2a.types import AgentCapabilities, AgentCard, AgentSkill, Message, Part
from fastapi import FastAPI

from multi_agent.orchestrator import AgentOrchestrator, build_default_orchestrator


class BiomarkerAgentExecutor(AgentExecutor):
    """Accept JSON task text, dispatch one allowlisted task, and return an artifact."""

    def __init__(self, orchestrator: AgentOrchestrator):
        self.orchestrator = orchestrator

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        updater = TaskUpdater(event_queue, context.task_id, context.context_id)
        await updater.start_work()
        try:
            request: Any = json.loads(context.get_user_input())
            if not isinstance(request, dict) or not isinstance(request.get("payload"), dict):
                raise ValueError("A2A message text must be JSON with task_type and payload fields.")
            task_type = request.get("task_type")
            if not isinstance(task_type, str):
                raise ValueError("task_type must be a string.")
            result = await asyncio.to_thread(self.orchestrator.run, task_type, request["payload"])
            await updater.add_artifact(
                name="biomarker-agent-result.json",
                parts=[Part(text=json.dumps(result, ensure_ascii=False))],
            )
            await updater.complete()
        except Exception as error:
            error_message = Message(
                role="ROLE_AGENT",
                parts=[Part(text=json.dumps({"error": str(error)}))],
            )
            await updater.failed(error_message)

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        updater = TaskUpdater(event_queue, context.task_id, context.context_id)
        await updater.cancel()


def _agent_card(base_url: str) -> AgentCard:
    skills = [
        AgentSkill(
            id=skill["skill"]["name"],
            name=skill["name"],
            description=skill["description"],
            tags=[skill["skill"]["name"]],
            examples=["Send a JSON task with task_type and payload fields."],
            input_modes=["text"],
            output_modes=["text"],
        )
        for skill in build_default_orchestrator().list_agents()
    ]
    return AgentCard(
        name="Biomarker Research Agents",
        description="Source-grounded childhood-cancer research, read-only codebase search, and review-only campaign/poster drafts.",
        supported_interfaces=[
            {
                "url": base_url.rstrip("/") + "/",
                "protocol_binding": "JSONRPC",
                "protocol_version": "1.0",
            }
        ],
        version="1.0.0",
        capabilities=AgentCapabilities(streaming=False, push_notifications=False),
        default_input_modes=["text"],
        default_output_modes=["text"],
        skills=skills,
    )


def create_a2a_app(
    orchestrator: AgentOrchestrator | None = None,
    base_url: str = "http://127.0.0.1:8767",
) -> FastAPI:
    orchestrator = orchestrator or build_default_orchestrator()
    card = _agent_card(base_url)
    handler = DefaultRequestHandler(
        agent_executor=BiomarkerAgentExecutor(orchestrator),
        task_store=InMemoryTaskStore(),
        agent_card=card,
    )
    app = FastAPI(title="Biomarker A2A Agent", version="1.0.0")
    add_a2a_routes_to_fastapi(
        app,
        agent_card_routes=create_agent_card_routes(card),
        jsonrpc_routes=create_jsonrpc_routes(handler, rpc_url="/"),
    )
    return app


def main() -> None:
    import uvicorn

    app = create_a2a_app()
    uvicorn.run(app, host="127.0.0.1", port=8767)


if __name__ == "__main__":
    main()