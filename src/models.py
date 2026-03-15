"""Pydantic data models for A2A protocol messages between Green and Purple agents."""

from typing import Any, Literal, Optional, Dict
from pydantic import BaseModel, Field, model_validator


# Green Agent -> Purple Agent
class InitPayload(BaseModel):
    type: Literal["init"] = "init"
    prompt: str = Field(default="", description="System prompt with action space instructions")
    text: str = Field(..., description="Task description")


class ObservationPayload(BaseModel):
    type: Literal["obs"] = "obs"
    step: int = Field(..., ge=0, description="Current step number")
    obs: str = Field(..., description="Base64 encoded JPEG image (128x128)")


# Purple Agent -> Green Agent
class AckPayload(BaseModel):
    type: Literal["ack"] = "ack"
    success: bool = False
    message: str = ""


class ActionPayload(BaseModel):
    """Action in env format — most readable for LLM output."""
    type: Literal["action"] = "action"
    action_type: Literal["env"] = "env"
    action: Dict[str, Any] = Field(..., description="Action dict with buttons + camera")

    @model_validator(mode="after")
    def fill_defaults(self):
        required_buttons = [
            "forward", "back", "left", "right",
            "jump", "sneak", "sprint",
            "attack", "use", "drop", "inventory",
        ] + [f"hotbar.{i}" for i in range(1, 10)]

        for key in required_buttons:
            if key not in self.action:
                self.action[key] = 0
        if "camera" not in self.action:
            self.action["camera"] = [0.0, 0.0]
        return self


# Helper to create a noop action
NOOP_ACTION = ActionPayload(action={
    "forward": 0, "back": 0, "left": 0, "right": 0,
    "jump": 0, "sneak": 0, "sprint": 0,
    "attack": 0, "use": 0, "drop": 0, "inventory": 0,
    "hotbar.1": 0, "hotbar.2": 0, "hotbar.3": 0, "hotbar.4": 0,
    "hotbar.5": 0, "hotbar.6": 0, "hotbar.7": 0, "hotbar.8": 0, "hotbar.9": 0,
    "camera": [0.0, 0.0],
})
