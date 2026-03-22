"""Scripted action sequences for known simple tasks.

Instead of relying on LLM vision for every step, these scripts
execute pre-defined action sequences that are known to work for
specific task types. Much more reliable than LLM frame-by-frame control.
"""

from typing import Optional


def get_scripted_action(task_text: str, step: int) -> Optional[dict]:
    """Return a scripted env-format action for known tasks, or None to fall back to LLM.

    Args:
        task_text: The task description text
        step: Current step number (0-indexed)

    Returns:
        An env-format action dict, or None if no script matches.
    """
    text = task_text.lower()

    # === MOTION TASKS ===
    if "drop" in text and "item" in text:
        return _script_drop_item(step)

    if "look" in text and "sky" in text:
        return _script_look_at_sky(step)

    if "throw" in text and "snowball" in text:
        return _script_throw_snowball(step)

    # === MINING / COLLECTING ===
    if any(w in text for w in ["collect", "mine", "cut stone", "shear"]):
        return _script_mine_or_collect(step, text)

    # === BUILDING ===
    if any(w in text for w in ["build", "stack", "pillar"]):
        return _script_build(step, text)

    # === COMBAT ===
    if any(w in text for w in ["defeat", "combat", "hunt", "shoot", "fend off"]):
        return _script_combat(step, text)

    # === TOOL USE - simple ones ===
    if "drink" in text and "potion" in text:
        return _script_drink_potion(step)

    if "sleep" in text and "bed" in text:
        return _script_sleep_in_bed(step)

    if "flint and steel" in text or "ignite" in text or "make fire" in text:
        return _script_use_flint(step)

    if "plant" in text and ("wheat" in text or "seed" in text):
        return _script_plant(step)

    if "place" in text and "item frame" in text:
        return _script_place_item(step)

    if "carve" in text and "pumpkin" in text:
        return _script_carve_pumpkin(step)

    # === DECORATION ===
    if "light up" in text or "torch" in text:
        return _script_place_torches(step)

    if "lay" in text and "carpet" in text:
        return _script_lay_carpet(step)

    if "clean" in text and "weed" in text:
        return _script_clean_weeds(step)

    if "decorate" in text:
        return _script_decorate(step)

    # === EXPLORATION ===
    if "explore" in text or "find" in text or "locate" in text:
        return _script_explore(step)

    # No script match — fall back to LLM
    return None


def _base_action(**overrides) -> dict:
    """Create a base action with all zeros, then apply overrides."""
    action = {
        "forward": 0, "back": 0, "left": 0, "right": 0,
        "jump": 0, "sneak": 0, "sprint": 0,
        "attack": 0, "use": 0, "drop": 0, "inventory": 0,
        "hotbar.1": 0, "hotbar.2": 0, "hotbar.3": 0, "hotbar.4": 0,
        "hotbar.5": 0, "hotbar.6": 0, "hotbar.7": 0, "hotbar.8": 0, "hotbar.9": 0,
        "camera": [0.0, 0.0],
    }
    action.update(overrides)
    return action


# === MOTION SCRIPTS ===

def _script_drop_item(step: int) -> dict:
    """Drop items from inventory. Cycle through hotbar slots and drop."""
    cycle = step % 20
    if cycle < 2:
        # Select hotbar slot (cycle through them)
        slot = (step // 20) % 9 + 1
        return _base_action(**{f"hotbar.{slot}": 1})
    else:
        return _base_action(drop=1)


def _script_look_at_sky(step: int) -> dict:
    """Look up at the sky progressively."""
    if step < 30:
        return _base_action(camera=[-8.0, 0.0])  # Look up
    else:
        # Keep looking up and slowly rotate to show sky panorama
        return _base_action(camera=[-2.0, 5.0])


def _script_throw_snowball(step: int) -> dict:
    """Find snowball in hotbar and throw it."""
    cycle = step % 15
    if cycle < 3:
        # Try different hotbar slots to find snowball
        slot = (step // 15) % 9 + 1
        return _base_action(**{f"hotbar.{slot}": 1})
    elif cycle < 5:
        # Look slightly up for throwing
        return _base_action(camera=[-5.0, 0.0])
    else:
        # Throw (use = right click)
        return _base_action(use=1)


# === MINING / COLLECTING ===

def _script_mine_or_collect(step: int, text: str) -> dict:
    """Generic mining/collecting: select tool, face block, hold attack."""
    phase = step % 60

    if phase == 0:
        # Select tool from hotbar.1 (usually the tool)
        return _base_action(**{"hotbar.1": 1})
    elif phase < 3:
        # Look slightly down toward blocks
        return _base_action(camera=[5.0, 0.0])
    elif phase < 30:
        # Hold attack to mine
        return _base_action(attack=1)
    elif phase < 33:
        # Walk forward to pick up drops and find next block
        return _base_action(forward=1)
    elif phase < 36:
        # Look around for more blocks
        return _base_action(camera=[0.0, 20.0])
    elif phase < 39:
        return _base_action(camera=[-3.0, 0.0])
    else:
        # Continue mining
        return _base_action(attack=1)


# === BUILDING ===

def _script_build(step: int, text: str) -> dict:
    """Generic building: select material, look at surface, place blocks."""
    phase = step % 30

    if phase == 0:
        return _base_action(**{"hotbar.1": 1})  # Select building material
    elif phase < 3:
        # Look down at ground to place
        return _base_action(camera=[8.0, 0.0])
    elif phase < 8:
        # Place blocks
        return _base_action(use=1, sneak=1)
    elif phase < 11:
        # Move slightly to place next block
        return _base_action(forward=1, sneak=1)
    elif phase < 13:
        # Turn slightly
        return _base_action(camera=[0.0, 15.0], sneak=1)
    elif phase < 18:
        # Place more blocks
        return _base_action(use=1, sneak=1)
    elif phase < 21:
        # Move again
        return _base_action(right=1, sneak=1)
    elif phase < 23:
        return _base_action(camera=[0.0, -15.0], sneak=1)
    else:
        # Place blocks
        return _base_action(use=1, sneak=1)


# === COMBAT ===

def _script_combat(step: int, text: str) -> dict:
    """Generic combat: select weapon, approach enemy, attack."""
    phase = step % 40

    if phase == 0:
        return _base_action(**{"hotbar.1": 1})  # Select weapon (usually sword in slot 1)
    elif phase < 5:
        # Scan for enemy by turning
        return _base_action(camera=[0.0, 25.0])
    elif phase < 20:
        # Sprint toward enemy and attack
        return _base_action(forward=1, sprint=1, attack=1)
    elif phase < 22:
        # Jump for critical hit
        return _base_action(forward=1, jump=1, attack=1)
    elif phase < 30:
        # Continue attacking
        return _base_action(forward=1, attack=1)
    elif phase < 35:
        # Strafe and turn to reposition
        return _base_action(left=1, camera=[0.0, 15.0], attack=1)
    else:
        # Attack more
        return _base_action(forward=1, sprint=1, attack=1)


# === TOOL USE ===

def _script_drink_potion(step: int) -> dict:
    """Select potion from hotbar and drink it."""
    cycle = step % 20
    if cycle < 3:
        slot = (step // 20) % 9 + 1
        return _base_action(**{f"hotbar.{slot}": 1})
    else:
        return _base_action(use=1)  # Hold right click to drink


def _script_sleep_in_bed(step: int) -> dict:
    """Find bed and sleep in it."""
    phase = step % 30
    if phase < 5:
        # Look around for bed
        return _base_action(camera=[5.0, 20.0])
    elif phase < 10:
        # Move toward bed
        return _base_action(forward=1)
    elif phase < 15:
        # Look down at bed
        return _base_action(camera=[10.0, 0.0])
    else:
        # Right click to sleep
        return _base_action(use=1)


def _script_use_flint(step: int) -> dict:
    """Select flint and steel and use it."""
    if step < 5:
        return _base_action(**{"hotbar.1": 1})
    elif step < 10:
        return _base_action(camera=[10.0, 0.0])  # Look at ground
    else:
        return _base_action(use=1)


def _script_plant(step: int) -> dict:
    """Select seeds/hoe and plant."""
    phase = step % 20
    if phase == 0:
        return _base_action(**{"hotbar.1": 1})  # Select hoe
    elif phase < 5:
        return _base_action(camera=[10.0, 0.0], attack=1)  # Till soil
    elif phase < 8:
        return _base_action(**{"hotbar.2": 1})  # Select seeds
    elif phase < 12:
        return _base_action(use=1, camera=[5.0, 0.0])  # Plant
    elif phase < 15:
        return _base_action(forward=1)  # Move to next spot
    else:
        return _base_action(use=1, camera=[5.0, 0.0])  # Plant more


def _script_place_item(step: int) -> dict:
    """Place an item frame or similar item on a surface."""
    if step < 3:
        return _base_action(**{"hotbar.1": 1})
    elif step < 8:
        return _base_action(camera=[0.0, 0.0])  # Look straight
    else:
        return _base_action(use=1)


def _script_carve_pumpkin(step: int) -> dict:
    """Use shears on a pumpkin to carve it."""
    phase = step % 30
    if phase < 3:
        return _base_action(**{"hotbar.1": 1})  # Select shears
    elif phase < 8:
        return _base_action(camera=[0.0, 15.0])  # Look around for pumpkin
    elif phase < 15:
        return _base_action(forward=1)  # Walk to pumpkin
    elif phase < 20:
        return _base_action(camera=[5.0, 0.0])  # Look at pumpkin
    else:
        return _base_action(use=1)  # Carve


# === DECORATION ===

def _script_place_torches(step: int) -> dict:
    """Place torches around."""
    phase = step % 20
    if phase == 0:
        return _base_action(**{"hotbar.1": 1})  # Select torch
    elif phase < 5:
        return _base_action(use=1)  # Place torch
    elif phase < 10:
        return _base_action(forward=1, camera=[0.0, 30.0])  # Move and turn
    elif phase < 15:
        return _base_action(use=1)  # Place another torch
    else:
        return _base_action(forward=1, camera=[0.0, -20.0])


def _script_lay_carpet(step: int) -> dict:
    """Place carpet blocks on ground."""
    phase = step % 15
    if phase == 0:
        return _base_action(**{"hotbar.1": 1})  # Select carpet/wool
    elif phase < 3:
        return _base_action(camera=[10.0, 0.0])  # Look at ground
    elif phase < 8:
        return _base_action(use=1)  # Place
    elif phase < 11:
        return _base_action(forward=1)  # Move
    else:
        return _base_action(use=1)  # Place more


def _script_clean_weeds(step: int) -> dict:
    """Break grass/weeds by attacking them."""
    phase = step % 20
    if phase < 5:
        return _base_action(attack=1)  # Break weed
    elif phase < 8:
        return _base_action(forward=1, camera=[0.0, 15.0])  # Move to next
    elif phase < 10:
        return _base_action(camera=[3.0, 0.0])  # Look at ground
    else:
        return _base_action(attack=1)  # Break more


def _script_decorate(step: int) -> dict:
    """Place decorative items from hotbar."""
    phase = step % 25
    if phase == 0:
        slot = (step // 25) % 9 + 1
        return _base_action(**{f"hotbar.{slot}": 1})  # Cycle through items
    elif phase < 5:
        return _base_action(camera=[8.0, 0.0])  # Look at placement spot
    elif phase < 10:
        return _base_action(use=1)  # Place
    elif phase < 15:
        return _base_action(forward=1, camera=[0.0, 20.0])  # Move and turn
    elif phase < 20:
        return _base_action(use=1)  # Place more
    else:
        return _base_action(right=1)  # Move sideways


# === EXPLORATION ===

def _script_explore(step: int) -> dict:
    """Move around, look around, sprint to explore."""
    phase = step % 40

    if phase < 15:
        # Sprint forward
        return _base_action(forward=1, sprint=1)
    elif phase < 18:
        # Jump over obstacles
        return _base_action(forward=1, jump=1)
    elif phase < 23:
        # Scan right
        return _base_action(camera=[0.0, 25.0])
    elif phase < 28:
        # Sprint forward again
        return _base_action(forward=1, sprint=1)
    elif phase < 33:
        # Scan left
        return _base_action(camera=[0.0, -25.0])
    elif phase < 36:
        # Look around
        return _base_action(camera=[-5.0, 15.0])
    else:
        # Continue forward
        return _base_action(forward=1, sprint=1, jump=1)
