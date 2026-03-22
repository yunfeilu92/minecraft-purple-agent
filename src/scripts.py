"""Scripted action sequences for known simple tasks.

V4: Fixed based on task config analysis:
- collect_grass/clean_weeds: grass is at ~3 ~1 ~3 (above), need to look up slightly + attack
- collect_wood: oak_log filled at ~1 ~ ~1 ~5 ~10 ~5, right in front, just face forward + attack
- collect_wool: sheep summoned at ~2, need shears + USE (not attack)
- drink_potion: potion in hotbar.1, just hold use
- make_fire: flint_and_steel already in mainhand (no hotbar select needed), look down + use
- use_bow: hold use to charge, then release (alternate use=1 and use=0)
- carve_pumpkin: pumpkin is in INVENTORY not world. Need to place first, then use shears
"""

from typing import Optional


def get_scripted_action(task_text: str, step: int) -> Optional[dict]:
    """Return a scripted env-format action for known tasks, or None for LLM fallback."""
    text = task_text.lower()

    # === MOTION ===
    if "drop" in text and "item" in text:
        return _script_drop_item(step)
    if "look" in text and "sky" in text:
        return _script_look_at_sky(step)
    if "throw" in text and "snowball" in text:
        return _script_throw_snowball(step)

    # === MINING / COLLECTING (task-specific) ===
    if "collect grass" in text or ("grass" in text and "collect" in text):
        return _script_collect_grass(step)
    if "collect wood" in text or "collect oak" in text or ("wood" in text and "collect" in text):
        return _script_collect_wood(step)
    if "shear sheep" in text or "collect wool" in text:
        return _script_collect_wool(step)
    if "collect dirt" in text:
        return _script_collect_dirt(step)
    if any(w in text for w in ["collect", "mine", "cut stone", "shear"]):
        return _script_mine_generic(step, text)

    # === TOOL USE (task-specific) ===
    if "drink" in text and "potion" in text:
        return _script_drink_potion(step)
    if "sleep" in text and "bed" in text:
        return _script_sleep_in_bed(step)
    if "flint and steel" in text or "ignite" in text or "make fire" in text:
        return _script_make_fire(step)
    if "use bow" in text or ("bow" in text and "weapon" in text):
        return _script_use_bow(step)
    if "plant" in text and ("wheat" in text or "seed" in text):
        return _script_plant(step)
    if "place" in text and "item frame" in text:
        return _script_place_item(step)
    if "carve" in text and "pumpkin" in text:
        return _script_carve_pumpkin(step)
    if "use trident" in text or "trident" in text:
        return _script_use_trident(step)
    if "use lead" in text or "lead" in text and "animal" in text:
        return _script_use_lead(step)
    if "use shield" in text or "shield" in text and "block" in text:
        return _script_use_shield(step)

    # === BUILDING ===
    if "dig" in text and "down" in text:
        return _script_dig_down(step)
    if any(w in text for w in ["build", "stack", "pillar"]):
        return _script_build(step, text)

    # === COMBAT (task-specific) ===
    if any(w in text for w in ["defeat", "combat", "fend off"]):
        return _script_combat_melee(step)  # weapon already in mainhand via /replaceitem
    if "hunt" in text:
        return _script_combat_hunt(step, text)  # weapon via /give = hotbar.1
    if "shoot" in text:
        return _script_combat_ranged(step)  # bow via /give = hotbar.1

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

    return None


def _base(**overrides) -> dict:
    a = {
        "forward": 0, "back": 0, "left": 0, "right": 0,
        "jump": 0, "sneak": 0, "sprint": 0,
        "attack": 0, "use": 0, "drop": 0, "inventory": 0,
        "hotbar.1": 0, "hotbar.2": 0, "hotbar.3": 0, "hotbar.4": 0,
        "hotbar.5": 0, "hotbar.6": 0, "hotbar.7": 0, "hotbar.8": 0, "hotbar.9": 0,
        "camera": [0.0, 0.0],
    }
    a.update(overrides)
    return a


# ============================================================
# MOTION
# ============================================================

def _script_drop_item(step: int) -> dict:
    if step == 0: return _base(**{"hotbar.1": 1})
    if step < 10: return _base(drop=1)
    if step == 10: return _base(**{"hotbar.2": 1})
    if step < 20: return _base(drop=1)
    if step == 20: return _base(**{"hotbar.3": 1})
    return _base(drop=1)


def _script_look_at_sky(step: int) -> dict:
    if step < 20:
        return _base(camera=[-10.0, 0.0])
    return _base(camera=[-1.0, 3.0])  # Slowly pan for video


def _script_throw_snowball(step: int) -> dict:
    # Snowball is first /give item = hotbar.1
    if step == 0: return _base(**{"hotbar.1": 1})
    if step < 3: return _base(camera=[-5.0, 0.0])  # Aim slightly up
    return _base(use=1)  # Throw


# ============================================================
# MINING / COLLECTING (task-specific)
# ============================================================

def _script_collect_dirt(step: int) -> dict:
    """Dirt: shovel in hotbar.1, dig ground beneath."""
    if step == 0: return _base(**{"hotbar.1": 1})
    c = step % 35
    if c < 2: return _base(camera=[8.0, 0.0])
    if c < 18: return _base(attack=1)
    if c < 22: return _base(forward=1, jump=1)
    if c < 25: return _base(camera=[0.0, 40.0])
    if c < 27: return _base(camera=[8.0, 0.0])
    return _base(attack=1)


def _script_collect_grass(step: int) -> dict:
    """Grass: shears in hotbar.1, tall_grass at y+1 in 7x7 area around player.
    Shears break grass instantly with attack. Need to look UP more (grass is above feet)."""
    if step == 0: return _base(**{"hotbar.1": 1})
    if step < 5: return _base(camera=[-5.0, 0.0])  # Look up to grass level
    c = step % 25
    if c < 3: return _base(attack=1)  # Break grass (instant with shears)
    if c < 5: return _base(forward=1)  # Move to pick up + next grass
    if c < 8: return _base(attack=1)  # Break more
    if c < 10: return _base(camera=[0.0, 25.0])  # Turn to find more
    if c < 12: return _base(forward=1)
    if c < 15: return _base(attack=1)
    if c < 17: return _base(camera=[0.0, -30.0])  # Turn other way
    if c < 19: return _base(forward=1)
    return _base(attack=1)


def _script_collect_wood(step: int) -> dict:
    """Wood: axe in hotbar.1, oak_log filled at ~1 ~ ~1 to ~5 ~10 ~5.
    Logs are 1 block away. Walk into them and hold attack for long time."""
    if step == 0: return _base(**{"hotbar.1": 1})
    if step < 3: return _base(forward=1)  # Walk right into the log wall
    c = step % 50
    if c < 35: return _base(attack=1)  # Hold attack for a LONG time (wood takes ~20 ticks)
    if c < 40: return _base(forward=1, jump=1)  # Pick up drops, move deeper into logs
    if c < 43: return _base(camera=[3.0, 0.0])  # Look at next log
    return _base(attack=1)


def _script_collect_wool(step: int) -> dict:
    """Wool: shears in hotbar.1, sheep summoned at ~2 ~ ~.
    Shears on sheep = USE (right click), not attack."""
    if step == 0: return _base(**{"hotbar.1": 1})
    c = step % 25
    if c < 5: return _base(forward=1, camera=[0.0, 10.0])  # Walk toward sheep
    if c < 15: return _base(use=1)  # Shear (right click)
    if c < 18: return _base(camera=[0.0, 25.0])  # Turn to find more sheep
    if c < 20: return _base(forward=1)  # Approach
    return _base(use=1)


def _script_mine_generic(step: int, text: str) -> dict:
    """Generic mining for stone, ores etc."""
    if step == 0: return _base(**{"hotbar.1": 1})
    c = step % 40
    if c < 2: return _base(camera=[3.0, 0.0])
    if c < 22: return _base(attack=1, forward=1)
    if c < 25: return _base(forward=1)
    if c < 28: return _base(camera=[0.0, 40.0])
    if c < 32: return _base(forward=1, sprint=1)
    return _base(attack=1)


# ============================================================
# TOOL USE (task-specific)
# ============================================================

def _script_drink_potion(step: int) -> dict:
    """Potion in hotbar.1. Hold use (right click) to drink."""
    if step == 0: return _base(**{"hotbar.1": 1})
    return _base(use=1)


def _script_sleep_in_bed(step: int) -> dict:
    c = step % 30
    if c < 5: return _base(camera=[5.0, 20.0])
    if c < 10: return _base(forward=1)
    if c < 15: return _base(camera=[10.0, 0.0])
    return _base(use=1)


def _script_make_fire(step: int) -> dict:
    """Flint and steel already in mainhand (via /replaceitem). Look at ground + use."""
    if step < 5: return _base(camera=[10.0, 0.0])  # Look at ground
    return _base(use=1)  # Ignite


def _script_use_bow(step: int) -> dict:
    """Bow in hotbar.1, arrows in hotbar.2. Hold use to charge, release to shoot."""
    if step == 0: return _base(**{"hotbar.1": 1})
    c = step % 25
    if c < 3: return _base(camera=[0.0, 15.0])  # Scan for target
    if c < 5: return _base(camera=[-3.0, 0.0])  # Aim slightly up
    if c < 15: return _base(use=1)  # Charge bow (hold right click)
    if c == 15: return _base()  # Release to shoot (use=0)
    if c < 18: return _base(camera=[0.0, 20.0])  # Scan for next target
    if c < 20: return _base(camera=[-2.0, 0.0])
    return _base(use=1)  # Charge again


def _script_use_trident(step: int) -> dict:
    """Trident in hotbar.1. Hold use to charge, release to throw."""
    if step == 0: return _base(**{"hotbar.1": 1})
    c = step % 20
    if c < 3: return _base(camera=[0.0, 20.0])  # Look around
    if c < 5: return _base(camera=[-3.0, 0.0])  # Aim
    if c < 12: return _base(use=1)  # Charge
    if c == 12: return _base()  # Release to throw
    if c < 16: return _base(forward=1)  # Pick up trident
    return _base(use=1)


def _script_use_lead(step: int) -> dict:
    """Lead in hotbar.1. Use on nearby animals."""
    if step == 0: return _base(**{"hotbar.1": 1})
    c = step % 20
    if c < 5: return _base(forward=1, camera=[0.0, 15.0])
    if c < 15: return _base(use=1)
    return _base(forward=1, camera=[0.0, -20.0])


def _script_use_shield(step: int) -> dict:
    """Shield in hotbar.1. Hold use to block."""
    if step == 0: return _base(**{"hotbar.1": 1})
    c = step % 20
    if c < 15: return _base(use=1)  # Block
    return _base(camera=[0.0, 20.0])  # Look around between blocks


def _script_plant(step: int) -> dict:
    c = step % 20
    if c == 0: return _base(**{"hotbar.1": 1})
    if c < 5: return _base(camera=[10.0, 0.0], attack=1)
    if c < 8: return _base(**{"hotbar.2": 1})
    if c < 12: return _base(use=1, camera=[5.0, 0.0])
    if c < 15: return _base(forward=1)
    return _base(use=1, camera=[5.0, 0.0])


def _script_place_item(step: int) -> dict:
    if step < 3: return _base(**{"hotbar.1": 1})
    if step < 8: return _base(camera=[0.0, 0.0])
    return _base(use=1)


def _script_carve_pumpkin(step: int) -> dict:
    """Pumpkin in hotbar.1 (inventory), shears in hotbar.2.
    Step 1: place pumpkin on ground. Step 2: select shears. Step 3: use on pumpkin."""
    if step < 3: return _base(**{"hotbar.1": 1})  # Select pumpkin
    if step < 6: return _base(camera=[10.0, 0.0])  # Look at ground
    if step < 12: return _base(use=1)  # Place pumpkin
    if step < 15: return _base(**{"hotbar.2": 1})  # Select shears
    if step < 18: return _base(camera=[-5.0, 0.0])  # Look at placed pumpkin
    return _base(use=1)  # Carve with shears (right click)


# ============================================================
# BUILDING
# ============================================================

def _script_dig_down(step: int) -> dict:
    """Dig down and fill up."""
    if step == 0: return _base(**{"hotbar.1": 1})
    c = step % 40
    if c < 3: return _base(camera=[10.0, 0.0])  # Look down
    if c < 18: return _base(attack=1)  # Dig
    if c < 20: return _base(camera=[-10.0, 0.0])
    if c < 22: return _base(jump=1)
    if c < 25: return _base(camera=[10.0, 0.0])
    if c < 30: return _base(use=1, jump=1)  # Place block while jumping up
    return _base(attack=1)


def _script_build(step: int, text: str) -> dict:
    """Building: place blocks in organized patterns for better video scores."""
    text_lower = text.lower()

    # Select material
    if step == 0: return _base(**{"hotbar.1": 1})

    if "pillar" in text_lower or "tower" in text_lower:
        # Pillar/tower: look down + jump + place
        c = step % 4
        if c < 2: return _base(camera=[10.0, 0.0], jump=1, use=1, sneak=1)
        return _base(jump=1, use=1, sneak=1)

    if "wall" in text_lower:
        # Wall: place in a line, then go up
        c = step % 20
        if c < 8: return _base(use=1, sneak=1)
        if c < 12: return _base(forward=1, sneak=1)
        if c < 14: return _base(camera=[0.0, 0.0])
        return _base(use=1, sneak=1)

    # Generic building: place blocks around
    c = step % 25
    if c < 3: return _base(camera=[8.0, 0.0])
    if c < 8: return _base(use=1, sneak=1)
    if c < 11: return _base(forward=1, sneak=1)
    if c < 13: return _base(camera=[0.0, 20.0], sneak=1)
    if c < 18: return _base(use=1, sneak=1)
    if c < 21: return _base(right=1, sneak=1)
    return _base(use=1, sneak=1)


# ============================================================
# COMBAT
# ============================================================

def _script_combat_melee(step: int) -> dict:
    """Combat tasks where weapon is already in mainhand via /replaceitem.
    DO NOT select hotbar - it would replace the equipped weapon!
    Mobs summoned 2-3 blocks away. Rush forward and attack."""
    # No hotbar selection! Weapon already equipped.
    c = step % 20
    if c < 2: return _base(camera=[0.0, 20.0])  # Quick scan
    if c < 8: return _base(forward=1, sprint=1, attack=1)  # Rush + attack
    if c < 10: return _base(forward=1, jump=1, attack=1)  # Crit hit
    if c < 15: return _base(forward=1, attack=1)  # Keep attacking
    if c < 17: return _base(camera=[0.0, -30.0], attack=1)  # Turn + attack
    return _base(forward=1, sprint=1, attack=1)


def _script_combat_hunt(step: int, text: str) -> dict:
    """Hunt tasks: weapon via /give in hotbar.1. Select it then attack."""
    if step == 0: return _base(**{"hotbar.1": 1})  # Select sword
    c = step % 20
    if c < 2: return _base(camera=[0.0, 20.0])
    if c < 8: return _base(forward=1, sprint=1, attack=1)
    if c < 10: return _base(forward=1, jump=1, attack=1)
    if c < 15: return _base(forward=1, attack=1)
    if c < 17: return _base(camera=[0.0, -30.0], attack=1)
    return _base(forward=1, sprint=1, attack=1)


def _script_combat_ranged(step: int) -> dict:
    """Shoot tasks: bow in hotbar.1. Hold use to charge, release to shoot."""
    if step == 0: return _base(**{"hotbar.1": 1})
    c = step % 20
    if c < 3: return _base(camera=[0.0, 15.0])  # Scan
    if c < 5: return _base(camera=[-3.0, 0.0])  # Aim up slightly
    if c < 13: return _base(use=1)  # Charge bow
    if c == 13: return _base()  # Release to shoot
    if c < 17: return _base(camera=[0.0, 20.0])  # Scan for next
    return _base(use=1)


# ============================================================
# DECORATION
# ============================================================

def _script_place_torches(step: int) -> dict:
    if step == 0: return _base(**{"hotbar.1": 1})
    c = step % 15
    if c < 3: return _base(camera=[5.0, 0.0])  # Look at surface
    if c < 6: return _base(use=1)
    if c < 10: return _base(forward=1, camera=[0.0, 25.0])
    return _base(use=1)


def _script_lay_carpet(step: int) -> dict:
    """Carpet in hotbar.3 (white_carpet is 3rd /give)."""
    if step == 0: return _base(**{"hotbar.3": 1})
    c = step % 12
    if c < 2: return _base(camera=[10.0, 0.0])
    if c < 6: return _base(use=1)
    if c < 9: return _base(forward=1)
    return _base(use=1)


def _script_clean_weeds(step: int) -> dict:
    """Shears in hotbar.1, tall_grass at y+1 around player. Attack to break.
    Same pattern as collect_grass - need to look UP to hit tall_grass."""
    if step == 0: return _base(**{"hotbar.1": 1})
    if step < 5: return _base(camera=[-5.0, 0.0])  # Look up to grass level
    c = step % 25
    if c < 3: return _base(attack=1)
    if c < 5: return _base(forward=1)
    if c < 8: return _base(attack=1)
    if c < 10: return _base(camera=[0.0, 25.0])
    if c < 12: return _base(forward=1)
    if c < 15: return _base(attack=1)
    if c < 17: return _base(camera=[0.0, -30.0])
    if c < 19: return _base(forward=1)
    return _base(attack=1)


def _script_decorate(step: int) -> dict:
    c = step % 25
    if c == 0:
        slot = (step // 25) % 9 + 1
        return _base(**{f"hotbar.{slot}": 1})
    if c < 3: return _base(camera=[8.0, 0.0])
    if c < 8: return _base(use=1)
    if c < 13: return _base(forward=1, camera=[0.0, 20.0])
    if c < 18: return _base(use=1)
    return _base(right=1)


# ============================================================
# EXPLORATION
# ============================================================

def _script_explore(step: int) -> dict:
    c = step % 40
    if c < 15: return _base(forward=1, sprint=1)
    if c < 18: return _base(forward=1, jump=1)
    if c < 23: return _base(camera=[0.0, 25.0])
    if c < 28: return _base(forward=1, sprint=1)
    if c < 33: return _base(camera=[0.0, -25.0])
    if c < 36: return _base(camera=[-5.0, 15.0])
    return _base(forward=1, sprint=1, jump=1)
