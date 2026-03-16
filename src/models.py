"""Pydantic data models for A2A protocol messages between Green and Purple agents."""

import math
import itertools
from collections import OrderedDict
from typing import Any, Literal, Optional, Dict, List
from pydantic import BaseModel, Field


# Button order matching MineStudio's Buttons.ALL
BUTTON_KEYS = [
    "forward", "back", "left", "right",
    "jump", "sneak", "sprint",
    "attack", "use", "drop", "inventory",
    "hotbar.1", "hotbar.2", "hotbar.3", "hotbar.4",
    "hotbar.5", "hotbar.6", "hotbar.7", "hotbar.8", "hotbar.9",
]

# === Compact format encoding (matching CameraHierarchicalMapping) ===

# Button groups for joint encoding
_BUTTONS_GROUPS = OrderedDict(
    hotbar=["none"] + [f"hotbar.{i}" for i in range(1, 10)],
    fore_back=["none", "forward", "back"],
    left_right=["none", "left", "right"],
    sprint_sneak=["none", "sprint", "sneak"],
    use=["none", "use"],
    drop=["none", "drop"],
    attack=["none", "attack"],
    jump=["none", "jump"],
    camera=["none", "camera"],
)

_BUTTONS_COMBINATIONS = list(itertools.product(*_BUTTONS_GROUPS.values())) + ["inventory"]
_BUTTONS_COMBO_TO_IDX = {comb: i for i, comb in enumerate(_BUTTONS_COMBINATIONS)}

# Camera encoding constants (matching MineStudio defaults)
_CAMERA_MAXVAL = 10
_CAMERA_BINSIZE = 2
_CAMERA_MU = 10.0
_N_CAMERA_BINS = 11  # (2 * maxval / binsize) + 1
_CAMERA_NULL_BIN = _N_CAMERA_BINS // 2  # = 5


def _mu_law_discretize(value: float) -> int:
    """Discretize a camera delta using mu-law quantization."""
    value = max(-_CAMERA_MAXVAL, min(_CAMERA_MAXVAL, value))
    # mu-law encoding
    normalized = value / _CAMERA_MAXVAL
    encoded = math.copysign(
        math.log(1.0 + _CAMERA_MU * abs(normalized)) / math.log(1.0 + _CAMERA_MU),
        normalized,
    )
    encoded *= _CAMERA_MAXVAL
    # Linear quantization
    return round((encoded + _CAMERA_MAXVAL) / _CAMERA_BINSIZE)


def _encode_compact(env_action: Dict[str, Any]) -> tuple:
    """Encode env-format action dict to compact (buttons_int, camera_int)."""
    # Determine button group choices
    choices = {}
    # hotbar
    hotbar_choice = "none"
    for i in range(1, 10):
        if env_action.get(f"hotbar.{i}", 0) == 1:
            hotbar_choice = f"hotbar.{i}"
            break
    choices["hotbar"] = hotbar_choice

    # fore_back
    fwd = env_action.get("forward", 0)
    back = env_action.get("back", 0)
    if fwd and back:
        choices["fore_back"] = "none"
    elif fwd:
        choices["fore_back"] = "forward"
    elif back:
        choices["fore_back"] = "back"
    else:
        choices["fore_back"] = "none"

    # left_right
    left = env_action.get("left", 0)
    right = env_action.get("right", 0)
    if left and right:
        choices["left_right"] = "none"
    elif left:
        choices["left_right"] = "left"
    elif right:
        choices["left_right"] = "right"
    else:
        choices["left_right"] = "none"

    # sprint_sneak
    sprint = env_action.get("sprint", 0)
    sneak = env_action.get("sneak", 0)
    if sprint:
        choices["sprint_sneak"] = "sprint"
    elif sneak:
        choices["sprint_sneak"] = "sneak"
    else:
        choices["sprint_sneak"] = "none"

    # Simple binary groups
    choices["use"] = "use" if env_action.get("use", 0) else "none"
    choices["drop"] = "drop" if env_action.get("drop", 0) else "none"
    choices["attack"] = "attack" if env_action.get("attack", 0) else "none"
    choices["jump"] = "jump" if env_action.get("jump", 0) else "none"

    # Camera discretization
    cam = env_action.get("camera", [0.0, 0.0])
    pitch_bin = _mu_law_discretize(cam[0])
    yaw_bin = _mu_law_discretize(cam[1])

    # Camera meta action: "camera" if non-null, "none" if center
    is_camera_null = (pitch_bin == _CAMERA_NULL_BIN and yaw_bin == _CAMERA_NULL_BIN)

    # Handle inventory specially
    if env_action.get("inventory", 0) == 1:
        button_idx = _BUTTONS_COMBO_TO_IDX["inventory"]
        camera_idx = _CAMERA_NULL_BIN * _N_CAMERA_BINS + _CAMERA_NULL_BIN
    else:
        choices["camera"] = "none" if is_camera_null else "camera"
        combo = tuple(choices[k] for k in _BUTTONS_GROUPS.keys())
        button_idx = _BUTTONS_COMBO_TO_IDX[combo]
        camera_idx = pitch_bin * _N_CAMERA_BINS + yaw_bin

    return button_idx, camera_idx


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
    """Action in compact agent format (Format 1).

    This is the only format that Green Agent handles without bugs.
    buttons: single int encoding all button states
    camera: single int encoding discretized camera movement
    """
    type: Literal["action"] = "action"
    action_type: Literal["agent"] = "agent"
    buttons: List[int] = Field(default_factory=lambda: [0])
    camera: List[int] = Field(default_factory=lambda: [60])

    @classmethod
    def from_env_dict(cls, action: Dict[str, Any]) -> "ActionPayload":
        """Convert an env-format action dict to compact agent format."""
        button_idx, camera_idx = _encode_compact(action)
        return cls(buttons=[button_idx], camera=[camera_idx])


# Noop: no buttons, camera center (5*11+5=60)
NOOP_ACTION = ActionPayload(buttons=[0], camera=[60])
