FROM python:3.13
WORKDIR /app
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

RUN pip install uv
COPY uv.lock .
COPY pyproject.toml .
RUN uv lock && uv sync

COPY . .
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
CMD ["/app/.venv/bin/gunicorn", "Exkursijos.wsgi:application", "--bind", "0.0.0.0:8000"]