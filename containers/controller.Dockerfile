FROM node:22-bookworm-slim AS node-runtime


FROM python:3.12-slim-bookworm

COPY --from=node-runtime /usr/local /usr/local

ARG BRUNNER_REF=0994ab5efeb21b4b2a4f9d022576ad68e34e6299
ARG CODEX_VERSION=0.144.1
ARG KUBECTL_VERSION
ARG TARGETARCH

RUN test -n "${KUBECTL_VERSION}" \
    && test -n "${TARGETARCH}" \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
       ca-certificates \
       curl \
       git \
    && python -m pip install --no-cache-dir \
       "git+https://github.com/cbizon/brunner.git@${BRUNNER_REF}" \
    && npm install --global "@openai/codex@${CODEX_VERSION}" \
    && npm cache clean --force \
    && curl --fail --location --silent --show-error \
       "https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/${TARGETARCH}/kubectl" \
       --output /usr/local/bin/kubectl \
    && chmod 0755 /usr/local/bin/kubectl \
    && apt-get purge -y --auto-remove curl git \
    && useradd --uid 1000 --create-home --shell /usr/sbin/nologin brunner \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md /opt/monkeybench/
COPY src /opt/monkeybench/src
RUN python -m pip install --no-cache-dir --no-deps /opt/monkeybench

COPY output-contract.json /opt/monkeybench/output-contract.json
COPY challenge /opt/monkeybench/challenge
COPY qualitative /opt/monkeybench/qualitative
COPY reference/manifest.json /opt/monkeybench/reference/manifest.json

ENV MONKEYBENCH_ROOT=/opt/monkeybench \
    PYTHONUNBUFFERED=1 \
    PIP_NO_INDEX=1 \
    UV_NO_SYNC=1

USER 1000:1000
WORKDIR /tmp

CMD ["brunner", "--help"]
