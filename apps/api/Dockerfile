FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml ./
RUN uv pip install --system --no-cache -r pyproject.toml

COPY . .

EXPOSE 8000

# --no-access-log: /places?q= carries a place name (ADR-029). FORWARDED_ALLOW_IPS (env) must be the reverse proxy (Caddy) - ADR-029, TASK-15.6
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--no-access-log"]
