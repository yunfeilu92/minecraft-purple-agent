"""A2A server entry point for the Minecraft purple agent."""

import argparse
import logging
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

import uvicorn
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentSkill

from executor import MCUPurpleExecutor

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)


def build_agent_card(url: str) -> AgentCard:
    skill = AgentSkill(
        id="minecraft_tasks",
        name="Minecraft Task Solver",
        description="LLM-powered agent that solves Minecraft benchmark tasks using vision models",
        tags=["minecraft", "benchmark", "mcu", "game-agent"],
        examples=["build a wall using stone bricks", "craft a furnace from cobblestone"],
    )
    return AgentCard(
        name="minecraft-llm-agent",
        description="Vision-LLM Minecraft agent for AgentBeats MCU benchmark. "
                    "Uses Claude/GPT-4o to analyze game screenshots and output actions.",
        url=url,
        version="1.0.0",
        default_input_modes=["text/plain"],
        default_output_modes=["text/plain"],
        capabilities=AgentCapabilities(),
        skills=[skill],
    )


def main():
    parser = argparse.ArgumentParser(description="Minecraft LLM Purple Agent")
    parser.add_argument("--host", type=str, default="0.0.0.0")
    parser.add_argument("--port", type=int, default=9019)
    parser.add_argument("--card-url", type=str, help="External URL for agent card")
    args = parser.parse_args()

    card_url = args.card_url or f"http://{args.host}:{args.port}/"
    card = build_agent_card(card_url)

    request_handler = DefaultRequestHandler(
        agent_executor=MCUPurpleExecutor(),
        task_store=InMemoryTaskStore(),
    )

    app = A2AStarletteApplication(
        agent_card=card,
        http_handler=request_handler,
    )

    logger.info(f"Starting Minecraft LLM Purple Agent on {args.host}:{args.port}")
    uvicorn.run(
        app.build(),
        host=args.host,
        port=args.port,
        timeout_keep_alive=300,
    )


if __name__ == "__main__":
    main()
