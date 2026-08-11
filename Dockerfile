FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN groupadd --system mcp \
    && useradd --system --gid mcp --create-home mcp

COPY --chown=mcp:mcp src ./src

USER mcp

EXPOSE 9090

CMD ["python", "-m", "src.server"]
