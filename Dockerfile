FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY reward_bot ./reward_bot

# Run as an unprivileged user; /app/data holds the SQLite file (mounted as a volume).
RUN useradd --create-home --uid 1000 bot && mkdir -p /app/data && chown bot:bot /app/data
USER bot

EXPOSE 8080
CMD ["python", "-m", "reward_bot"]
