FROM python:3.12-bookworm AS python-builder

ARG BRUNNER_REF=97073876d6bda0bd800e7e347c1effbb10343e98

RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && python -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir \
       "git+https://github.com/cbizon/brunner.git@${BRUNNER_REF}" \
       "pillow==12.3.0" \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build/monkeybench
COPY pyproject.toml README.md ./
COPY src/ src/
RUN /opt/venv/bin/pip install --no-cache-dir --no-deps .


FROM node:22-bookworm-slim AS node-builder
ARG CODEX_VERSION=0.144.1
ARG CLAUDE_VERSION=2.1.110

RUN npm install -g \
       "@openai/codex@${CODEX_VERSION}" \
       "@anthropic-ai/claude-code@${CLAUDE_VERSION}"


FROM python:3.12-slim-bookworm

LABEL org.opencontainers.image.source="https://github.com/cbizon/monkeybench"

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       bubblewrap \
       imagemagick \
       poppler-utils \
       socat \
       util-linux \
    && useradd --create-home --uid 1000 benchmark \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY --from=python-builder /opt/venv /opt/venv
COPY --from=node-builder /usr/local/bin/node /usr/local/bin/node
COPY --from=node-builder /usr/local/lib/node_modules /usr/local/lib/node_modules
RUN ln -s ../lib/node_modules/@openai/codex/bin/codex.js /usr/local/bin/codex \
    && ln -s ../lib/node_modules/@anthropic-ai/claude-code/cli.js /usr/local/bin/claude

ENV PATH=/opt/venv/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PIP_NO_INDEX=1 \
    UV_NO_SYNC=1

USER benchmark
WORKDIR /brunner/trial/workspace

CMD ["brunner-agent", "--help"]
