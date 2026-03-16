"""LLM-powered Minecraft agent that uses vision models to play the game."""

import os
import json
import logging
from typing import Optional
from collections import Counter

from models import ActionPayload, NOOP_ACTION
from prompts import SYSTEM_PROMPT, TASK_PROMPT_TEMPLATE, PLAN_PROMPT_TEMPLATE, get_task_strategy

logger = logging.getLogger(__name__)


class MinecraftAgent:
    """Vision-LLM based Minecraft agent."""

    def __init__(self):
        self.backend = os.getenv("LLM_BACKEND", "bedrock")
        self.model = os.getenv("LLM_MODEL", "us.anthropic.claude-opus-4-6-v1")
        self.call_interval = int(os.getenv("LLM_CALL_INTERVAL", "1"))

        self.task_text: str = ""
        self.green_prompt: str = ""  # prompt from Green Agent
        self.plan: list[str] = []
        self.current_subgoal_idx: int = 0
        self.step_count: int = 0
        self.max_steps: int = 1200
        self.last_action: Optional[ActionPayload] = None
        self.action_history: list[str] = []
        self.recent_action_hashes: list[str] = []  # for stuck detection
        self.stuck_counter: int = 0
        self.task_strategy: str = ""

        self.client = self._create_client()

    def _create_client(self):
        """Create the appropriate Anthropic client based on backend config."""
        if self.backend == "bedrock":
            from anthropic import AnthropicBedrock
            return AnthropicBedrock(
                aws_access_key=os.getenv("AWS_ACCESS_KEY_ID"),
                aws_secret_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
                aws_session_token=os.getenv("AWS_SESSION_TOKEN"),
                aws_region=os.getenv("AWS_REGION", "us-east-1"),
            )
        elif self.backend == "claude":
            from anthropic import Anthropic
            return Anthropic()
        else:
            from openai import OpenAI
            return OpenAI()

    def init_task(self, text: str, prompt: str = "") -> None:
        """Initialize with task description and create a plan."""
        self.task_text = text
        self.green_prompt = prompt
        self.step_count = 0
        self.last_action = None
        self.action_history = []
        self.recent_action_hashes = []
        self.stuck_counter = 0
        self.current_subgoal_idx = 0

        # Determine max steps based on task complexity
        long_tasks = {"ender_dragon", "mine_diamond_from_scratch"}
        if any(t in text.lower() for t in long_tasks):
            self.max_steps = 12000

        # Get task-specific strategy
        self.task_strategy = get_task_strategy(text)

        # Generate plan via LLM
        self.plan = self._generate_plan(text)
        logger.info(f"Task: {text}")
        logger.info(f"Plan: {self.plan}")

    def get_action(self, step: int, obs_b64: str) -> ActionPayload:
        """Given a step and base64-encoded observation image, return an action."""
        self.step_count = step

        # Skip LLM call if not on interval (repeat last action)
        if self.call_interval > 1 and step % self.call_interval != 0 and self.last_action:
            return self.last_action

        try:
            action = self._call_vision_llm(obs_b64)
            action = self._validate_action(action)
            self._update_history(step, action)
            self.last_action = action
            return action
        except Exception as e:
            logger.error(f"LLM call failed at step {step}: {e}")
            return self.last_action or NOOP_ACTION

    @property
    def _is_anthropic(self) -> bool:
        return self.backend in ("claude", "bedrock")

    def _generate_plan(self, task_text: str) -> list[str]:
        """Use LLM to decompose the task into sub-goals."""
        prompt = PLAN_PROMPT_TEMPLATE.format(task_text=task_text)
        try:
            if self._is_anthropic:
                resp = self.client.messages.create(
                    model=self.model,
                    max_tokens=1024,
                    messages=[{"role": "user", "content": prompt}],
                )
                text = resp.content[0].text
            else:
                resp = self.client.chat.completions.create(
                    model=self.model,
                    max_tokens=1024,
                    messages=[{"role": "user", "content": prompt}],
                )
                text = resp.choices[0].message.content

            return json.loads(self._extract_json(text))
        except Exception as e:
            logger.warning(f"Plan generation failed: {e}")
            return [task_text]

    def _build_system_prompt(self) -> str:
        """Build the full system prompt, incorporating Green Agent's prompt if available."""
        # Use the Green Agent's official prompt if provided (it has the exact action space spec)
        if self.green_prompt:
            base = self.green_prompt
        else:
            base = SYSTEM_PROMPT

        # Append task-specific strategy
        if self.task_strategy:
            base += f"\n\n# Task-Specific Strategy\n{self.task_strategy}"

        return base

    def _detect_stuck(self) -> str:
        """Detect if agent is stuck repeating the same action."""
        if len(self.recent_action_hashes) < 6:
            return ""

        last_6 = self.recent_action_hashes[-6:]
        counts = Counter(last_6)
        most_common_count = counts.most_common(1)[0][1]

        if most_common_count >= 5:
            self.stuck_counter += 1
            if self.stuck_counter >= 2:
                # Advance sub-goal if repeatedly stuck
                if self.current_subgoal_idx < len(self.plan) - 1:
                    self.current_subgoal_idx += 1
                    self.stuck_counter = 0
                    return (
                        "WARNING: You appear STUCK repeating the same action with no progress. "
                        "Moving to next sub-goal. Try a COMPLETELY DIFFERENT approach: "
                        "turn around (camera [0, 90]), move in a new direction, or try a different item/tool."
                    )
            return (
                "CAUTION: You may be stuck. The last several actions were identical. "
                "Try something different: look around, move elsewhere, or change your approach."
            )

        self.stuck_counter = max(0, self.stuck_counter - 1)
        return ""

    def _call_vision_llm(self, obs_b64: str) -> ActionPayload:
        """Send screenshot to vision LLM and parse action response."""
        system_prompt = self._build_system_prompt()

        # Build state summary
        state_lines = []
        if self.plan:
            idx = min(self.current_subgoal_idx, len(self.plan) - 1)
            current = self.plan[idx]
            state_lines.append(f"Current sub-goal ({self.current_subgoal_idx + 1}/{len(self.plan)}): {current}")
            remaining = self.plan[idx + 1:idx + 3]
            if remaining:
                state_lines.append(f"Next sub-goals: {', '.join(remaining)}")

        if self.action_history:
            recent = self.action_history[-5:]
            state_lines.append(f"Recent actions: {'; '.join(recent)}")

        # Add stuck warning if detected
        stuck_warning = self._detect_stuck()
        if stuck_warning:
            state_lines.append(stuck_warning)

        user_text = TASK_PROMPT_TEMPLATE.format(
            task_text=self.task_text,
            step=self.step_count,
            max_steps=self.max_steps,
            state_summary="\n".join(state_lines) if state_lines else "Starting fresh.",
        )

        if self._is_anthropic:
            resp = self.client.messages.create(
                model=self.model,
                max_tokens=512,
                system=system_prompt,
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": obs_b64,
                            },
                        },
                        {"type": "text", "text": user_text},
                    ],
                }],
            )
            raw = resp.content[0].text
        else:
            resp = self.client.chat.completions.create(
                model=self.model,
                max_tokens=512,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/jpeg;base64,{obs_b64}"},
                            },
                            {"type": "text", "text": user_text},
                        ],
                    },
                ],
            )
            raw = resp.choices[0].message.content

        action_dict = json.loads(self._extract_json(raw))
        return ActionPayload.from_env_dict(action_dict)

    def _validate_action(self, action: ActionPayload) -> ActionPayload:
        """Validate compact action — constraints are handled during encoding."""
        # Compact format encoding already handles mutual exclusion.
        # Just clamp to valid ranges.
        action.buttons[0] = max(0, action.buttons[0])
        action.camera[0] = max(0, min(120, action.camera[0]))
        return action

    def _update_history(self, step: int, action: ActionPayload) -> None:
        """Update action history and stuck detection state."""
        action_brief = self._summarize_action(action)
        self.action_history.append(f"Step {step}: {action_brief}")
        if len(self.action_history) > 15:
            self.action_history.pop(0)

        # Track action hashes for stuck detection
        self.recent_action_hashes.append(action_brief)
        if len(self.recent_action_hashes) > 10:
            self.recent_action_hashes.pop(0)

    @staticmethod
    def _extract_json(text: str) -> str:
        """Extract JSON from LLM response, stripping markdown fences if present."""
        text = text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            start = 1 if lines[0].startswith("```") else 0
            end = -1 if lines[-1].strip() == "```" else len(lines)
            text = "\n".join(lines[start:end])
        # Also try to find JSON object if there's extra text
        text = text.strip()
        if not text.startswith("{"):
            start_idx = text.find("{")
            if start_idx != -1:
                # Find matching closing brace
                depth = 0
                for i in range(start_idx, len(text)):
                    if text[i] == "{":
                        depth += 1
                    elif text[i] == "}":
                        depth -= 1
                        if depth == 0:
                            text = text[start_idx:i + 1]
                            break
        return text.strip()

    @staticmethod
    def _summarize_action(action: ActionPayload) -> str:
        """Create a brief text summary of a compact action for history."""
        btn = action.buttons[0]
        cam = action.camera[0]
        if btn == 0 and cam == 60:
            return "noop"
        return f"b{btn}c{cam}"
