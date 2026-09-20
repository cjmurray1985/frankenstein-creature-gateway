FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg ca-certificates && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY scripts/family_encounter/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
COPY creature_runtime /app/creature_runtime
COPY frankenstein_monster_lore_emotion_interactivity.md /app/
COPY scripts/live_audition /app/scripts/live_audition
COPY scripts/family_encounter /app/scripts/family_encounter
COPY analysis/audio/incremental/live-streamed-creature-audition.wav /app/analysis/audio/incremental/
RUN useradd --uid 10001 --create-home creature && mkdir -p /var/lib/creature && chown creature /var/lib/creature
USER creature
ENV GATEWAY_BIND=0.0.0.0 PORT=10000 STATE_DIR=/var/lib/creature PYTHONUNBUFFERED=1
EXPOSE 10000
CMD ["python", "scripts/family_encounter/run.py"]
