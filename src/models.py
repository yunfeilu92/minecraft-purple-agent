"""Pydantic data models for A2A protocol messages between Green and Purple agents."""

from typing import Any, Literal, Optional, Dict, List
from pydantic import BaseModel, Field, model_validator


# Button order matching MineStudio's Buttons.ALL
BUTTON_KEYS = [
    "forward", "back", "left", "right",
    "jump", "sneak", "sprint",
    "attack", "use", "drop", "inventory",
    "hotbar.1", "hotbar.2", "hotbar.3", "hotbar.4",
    "hotbar.5", "hotbar.6", "hotbar.7", "hotbar.8", "hotbar.9",
]


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
    """Action in expanded agent format (Format 2).

    LLM outputs env-style dict internally, which gets converted to
    expanded agent format: buttons=[0,1,0,...] (20 elements), camera=[pitch, yaw].
    """
    type: Literal["action"] = "action"
    action_type: Literal["agent"] = "agent"
    buttons: List[int] = Field(default_factory=lambda: [0] * 20)
    camera: List[float] = Field(default_factory=lambda: [0.0, 0.0])

    @classmethod
    def from_env_dict(cls, action: Dict[str, Any]) -> "ActionPayload":
        """Convert an env-format action dict to expanded agent format."""
        buttons = [int(action.get(key, 0)) for key in BUTTON_KEYS]
        camera = action.get("camera", [0.0, 0.0])
        return cls(buttons=buttons, camera=[float(camera[0]), float(camera[1])])


# Helper to create a noop action
NOOP_ACTION = ActionPayload(buttons=[0] * 20, camera=[0.0, 0.0])
