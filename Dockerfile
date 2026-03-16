FROM ghcr.io/astral-sh/uv:python3.12-bookworm

ENV UV_HTTP_TIMEOUT=300

RUN adduser agentbeats
USER agentbeats
WORKDIR /home/agentbeats/agent

COPY pyproject.toml ./
RUN --mount=type=cache,target=/home/agentbeats/.cache/uv,uid=1000 \
    uv sync --no-dev --no-install-project

COPY README.md ./
COPY src src

ENTRYPOINT ["uv", "run", "src/server.py"]
CMD ["--host", "0.0.0.0", "--port", "9019"]
EXPOSE 9019
