FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /opt

COPY brunner /opt/brunner
COPY monkeybench/pyproject.toml monkeybench/uv.lock monkeybench/README.md /opt/monkeybench/
COPY monkeybench/src /opt/monkeybench/src

WORKDIR /opt/monkeybench
RUN uv sync --frozen --no-dev

ENV PATH="/opt/monkeybench/.venv/bin:${PATH}"
WORKDIR /trial
ENTRYPOINT []
