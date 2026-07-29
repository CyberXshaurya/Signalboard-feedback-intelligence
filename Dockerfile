FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PORT=10000

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src
RUN python -m pip install --no-cache-dir .

COPY migrations ./migrations
COPY data/README.md ./data/README.md

EXPOSE 10000

CMD ["feedback-engine"]
