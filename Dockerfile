# Portfolio local deployment; build from the repository root.
FROM python:3.11-slim-bookworm AS gpt-researcher

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_ROOT_USER_ACTION=ignore
WORKDIR /usr/src/app

# Chromium supports optional browser scraping; Pango/Cairo support PDF export.
RUN apt-get update && apt-get install -y --no-install-recommends \
    chromium chromium-driver build-essential ca-certificates \
    libpango-1.0-0 libpangoft2-1.0-0 libcairo2 libgdk-pixbuf-2.0-0 libffi-dev

COPY requirements.txt ./requirements.txt
COPY multi_agents/requirements.txt ./multi_agents/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt -r multi_agents/requirements.txt

RUN useradd --create-home gpt-researcher && \
    mkdir -p outputs logs && chown -R gpt-researcher:gpt-researcher /usr/src/app
COPY --chown=gpt-researcher:gpt-researcher . .
USER gpt-researcher
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/enterprise/ready', timeout=4)"
# One worker: startup marks previously running tasks interrupted, without paid replay.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
