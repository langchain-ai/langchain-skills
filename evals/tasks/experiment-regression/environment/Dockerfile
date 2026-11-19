FROM node:22-bookworm-slim AS node-runtime
FROM python:3.12-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends jq \
    && rm -rf /var/lib/apt/lists/*
COPY --from=node-runtime /usr/local/bin/node /usr/local/bin/node
COPY langsmith /usr/local/bin/langsmith
RUN chmod 0755 /usr/local/bin/langsmith && node --version && jq --version && langsmith --version
RUN pip install --no-cache-dir "langsmith==0.14.17" "langchain==1.5.2" "openevals==0.2.5"

COPY app/ /app/
WORKDIR /app
RUN LANGSMITH_TRACING=false python support_agent.py > /dev/null
