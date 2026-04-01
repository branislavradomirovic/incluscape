FROM ollama/ollama:latest

ARG OLLAMA_MODEL=qwen2.5:14b-instruct
ENV OLLAMA_MODEL=${OLLAMA_MODEL}

RUN sh -c 'ollama serve >/tmp/ollama-build.log 2>&1 & \
    pid=$!; \
    for i in $(seq 1 90); do \
      if ollama list >/dev/null 2>&1; then break; fi; \
      sleep 2; \
    done; \
    ollama pull "$OLLAMA_MODEL"; \
    kill "$pid"; \
    wait "$pid" || true'

EXPOSE 11434

CMD ["serve"]