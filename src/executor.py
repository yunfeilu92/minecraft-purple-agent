"""A2A executor that bridges the AgentBeats protocol with the Minecraft agent."""

import json
import logging

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.utils import new_agent_text_message

from models import AckPayload, ActionPayload, NOOP_ACTION
from agent import MinecraftAgent

logger = logging.getLogger(__name__)


class MCUPurpleExecutor(AgentExecutor):
    """A2A executor for the Minecraft purple agent."""

    def __init__(self):
        # One agent per context (task session)
        self.agents: dict[str, MinecraftAgent] = {}

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        ctx_id = context.context_id
        user_input = context.get_user_input()

        try:
            payload = json.loads(user_input)
        except Exception as e:
            logger.error(f"Failed to parse input: {e}")
            ack = AckPayload(success=False, message=f"Invalid JSON: {e}")
            await event_queue.enqueue_event(
                new_agent_text_message(ack.model_dump_json(), context_id=ctx_id)
            )
            return

        msg_type = payload.get("type")

        if msg_type == "init":
            # Create a fresh agent for this task session
            agent = MinecraftAgent()
            agent.init_task(
                text=payload.get("text", ""),
                prompt=payload.get("prompt", ""),
            )
            self.agents[ctx_id] = agent

            ack = AckPayload(success=True, message="Agent initialized with LLM planner.")
            await event_queue.enqueue_event(
                new_agent_text_message(ack.model_dump_json(), context_id=ctx_id)
            )

        elif msg_type == "obs":
            agent = self.agents.get(ctx_id)
            if agent is None:
                ack = AckPayload(success=False, message="No active session. Send init first.")
                await event_queue.enqueue_event(
                    new_agent_text_message(ack.model_dump_json(), context_id=ctx_id)
                )
                return

            obs_b64 = payload.get("obs")
            step = payload.get("step", 0)

            if not obs_b64:
                ack = AckPayload(success=False, message="No observation provided.")
                await event_queue.enqueue_event(
                    new_agent_text_message(ack.model_dump_json(), context_id=ctx_id)
                )
                return

            action = agent.get_action(step, obs_b64)
            await event_queue.enqueue_event(
                new_agent_text_message(action.model_dump_json(), context_id=ctx_id)
            )

        else:
            logger.warning(f"Unknown message type: {msg_type}")
            ack = AckPayload(success=False, message=f"Unknown message type: {msg_type}")
            await event_queue.enqueue_event(
                new_agent_text_message(ack.model_dump_json(), context_id=ctx_id)
            )

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        ctx_id = context.context_id
        if ctx_id in self.agents:
            del self.agents[ctx_id]
