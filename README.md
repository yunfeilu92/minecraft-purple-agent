# Minecraft LLM Purple Agent

Vision-LLM powered Minecraft agent for the [AgentBeats MCU Benchmark](https://rdi.berkeley.edu/agentx-agentbeats.html).

## Overview

This agent uses Claude (or GPT-4o) vision models to analyze Minecraft game screenshots and output optimal actions. It implements the A2A protocol to communicate with the MCU Green Agent evaluator.

### Key Features

- **Vision-based decision making**: Analyzes 128x128 game screenshots each step
- **LLM-powered planning**: Decomposes tasks into sub-goals before execution
- **Task-specific strategies**: Injects domain knowledge for crafting, building, combat, exploration, etc.
- **Stuck detection**: Detects repeated actions and automatically adjusts approach
- **Action validation**: Enforces Minecraft control constraints (mutually exclusive buttons, etc.)
- **Green Agent prompt integration**: Uses the official action space specification from the evaluator

## Architecture

```
Purple Agent (this repo)
├── server.py      # A2A server entry point
├── executor.py    # A2A executor bridging protocol ↔ agent
├── agent.py       # Core LLM agent with planning + vision
├── models.py      # Pydantic models for A2A messages
└── prompts.py     # System prompts + task-specific strategies
```

### Protocol Flow

1. **Init**: Green Agent sends task description → Agent creates plan → responds with ACK
2. **Step Loop**: Green Agent sends screenshot → Agent analyzes + decides action → responds with action JSON
3. **Termination**: Task completed or step limit reached

## Setup

```bash
# Install dependencies
uv sync

# Configure environment
cp .env.example .env
# Edit .env with your API keys
```

## Running

```bash
# Start the Purple Agent server (default port 9019)
uv run python src/server.py

# With custom settings
uv run python src/server.py --host 127.0.0.1 --port 9019
```

## Configuration

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `LLM_BACKEND` | `claude` | LLM provider: `claude` or `openai` |
| `LLM_MODEL` | `claude-sonnet-4-20250514` | Model name |
| `LLM_CALL_INTERVAL` | `1` | Call LLM every N steps |
| `ANTHROPIC_API_KEY` | - | Anthropic API key |
| `OPENAI_API_KEY` | - | OpenAI API key |

## Docker

```bash
docker build -t minecraft-purple-agent .
docker run -p 9019:9019 --env-file .env minecraft-purple-agent
```
