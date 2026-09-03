FROM node:22-bookworm-slim AS node-runtime


FROM python:3.12-slim-bookworm

COPY --from=node-runtime /usr/local /usr/local

ARG BRUNNER_REF=bb51a9eb048f6f6470fb101124de8958f1fb748b
ARG CODEX_VERSION=0.144.1
ARG CLAUDE_CODE_VERSION=2.1.236

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       ca-certificates \
       git \
       imagemagick \
       poppler-utils \
    && python -m pip install --no-cache-dir \
       "git+https://github.com/cbizon/brunner.git@${BRUNNER_REF}" \
       "pillow==12.3.0" \
    && npm install --global \
       "@openai/codex@${CODEX_VERSION}" \
       "@anthropic-ai/claude-code@${CLAUDE_CODE_VERSION}" \
    && npm cache clean --force \
    && apt-get purge -y --auto-remove git \
    && useradd --uid 1000 --create-home --shell /usr/sbin/nologin brunner \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_INDEX=1 \
    UV_NO_SYNC=1

USER 1000:1000
WORKDIR /tmp

CMD ["python", "-m", "brunner.agent_cli", "--help"]
