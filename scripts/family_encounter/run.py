"""Supervise both loopback voice engine and public authenticated gateway."""
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

root = Path(__file__).resolve().parents[2]
children = []

def stop(*_):
    for child in children:
        if child.poll() is None:
            child.terminate()
    for child in children:
        try:
            child.wait(timeout=10)
        except subprocess.TimeoutExpired:
            child.kill()

try:
    for name in ('OPENAI_API_KEY', 'ELEVENLABS_API_KEY', 'PUBLIC_ORIGIN'):
        if not os.environ.get(name):
            raise RuntimeError(f'Missing required runtime secret/configuration: {name}')
    os.environ.setdefault('AUDITION_MAX_SESSIONS', '60')
    os.environ.setdefault('AUDITION_WINDOW_SECONDS', '86400')
    os.environ.setdefault('AUDITION_SESSION_SECONDS', '1200')
    os.environ.setdefault('AUDITION_MAX_SPEECH_STREAMS', '60')
    os.environ['PYTHONPATH'] = str(root)
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    signal.signal(signal.SIGINT, lambda *_: sys.exit(0))
    children.append(subprocess.Popen([sys.executable, str(root/'scripts/live_audition/server.py')], cwd=root))
    children.append(subprocess.Popen([sys.executable, str(Path(__file__).with_name('gateway.py'))], cwd=root))
    while all(child.poll() is None for child in children):
        time.sleep(.5)
    raise SystemExit(1)
finally:
    stop()
