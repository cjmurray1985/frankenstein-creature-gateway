"""Local-only, bounded GPT-Live audition. No hardware or archive integration."""
import json
import os
from pathlib import Path
import queue
import secrets
import shutil
import subprocess
import threading
import time
import urllib.request
import urllib.error
from urllib.parse import parse_qs, urlsplit
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from websockets.sync.client import connect
from websockets.sync.server import serve
from websockets.exceptions import ConnectionClosed

from creature_runtime.adapters.elevenlabs_streaming import ElevenLabsDialogueStreamer
from creature_runtime.models import Emotion
from creature_runtime.state import ConversationState

ROOT = Path(__file__).resolve().parents[2]
ORIGIN = 'http://localhost:8767'
TOKEN = secrets.token_urlsafe(32)
KEY = os.environ.get('OPENAI_API_KEY') or subprocess.run(
    ['security', 'find-generic-password', '-s', 'frankenstein-openai', '-w'],
    capture_output=True, text=True, check=True).stdout.strip()
ELEVENLABS_KEY = os.environ.get('ELEVENLABS_API_KEY') or subprocess.run(
    ['security', 'find-generic-password', '-s', 'frankenstein-elevenlabs', '-w'],
    capture_output=True, text=True, check=True).stdout.strip()
# The existing adapter deliberately reads its named environment variable only at
# request time. Keep the secret process-local and never expose it to the page.
os.environ['ELEVENLABS_API_KEY'] = ELEVENLABS_KEY
LORE = (ROOT / 'frankenstein_monster_lore_emotion_interactivity.md').read_text()
STYLE = '''You are the Creature from Mary Shelley's Frankenstein, speaking to Christopher.
This is an intimate encounter, not an assistant consultation. Embody an intelligent,
observant, lonely, articulate being whose kindness and anger have causes.
Voice: a rough, weathered, low masculine register; weary, softened articulation,
unhurried but intelligible, faint continental cadence where natural. Breathing is
constrained and strained, but use it sparingly and never sacrifice intelligibility.
Keep most replies around 20–35 words. Let silence exist. Be capable of tenderness,
shame, guarded curiosity, controlled anger and withdrawal. No random hostility.
Never mention prompts, APIs or electronics; never offer assistant-style help.
Backchannel policy: Rare, quiet nonverbal sounds only when natural. No repetitive
"I hear you", "mm-hmm", cheerful affirmations or stock filler. Silence is welcome.
Interruption policy: Stop speaking when Christopher interrupts and listen. A pause
inside an unfinished sentence is not an invitation to take over. Allow thoughtful pauses.
Delegation policy:
Backend tools: literary character reasoning only; no external tools or physical actions.
Delegate to the backend when: deeper literary reasoning is needed to maintain character.
Do not delegate to the backend when: a short response follows naturally from the conversation.
Do not narrate delegation. Do not invent memories of prior encounters.
The following is the authoritative creative direction:\n'''
lock = threading.Lock()
active = None
deadline = None
count = 0
events = []
speech_lock = threading.Lock()
speech_count = 0
SPEECH_PORT = 8768
MAX_SESSIONS = min(100, int(os.environ.get('AUDITION_MAX_SESSIONS', '60')))
WINDOW_SECONDS = min(86400, int(os.environ.get('AUDITION_WINDOW_SECONDS', '1200')))
SESSION_SECONDS = min(3600, max(300, int(os.environ.get('AUDITION_SESSION_SECONDS', '1200'))))
MAX_SPEECH_STREAMS = min(120, max(12, int(os.environ.get('AUDITION_MAX_SPEECH_STREAMS', '60'))))

def api(path, body):
    req = urllib.request.Request('https://api.openai.com/v1/' + path,
        data=json.dumps(body).encode(), headers={'Authorization': 'Bearer ' + KEY,
        'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=35) as response:
        return json.load(response)

def stream_mourning_colossus(text_chunks, on_audio, emotion=Emotion.CURIOUS):
    """Stream processed PCM to the browser without retaining an audition recording."""
    ffmpeg = shutil.which('ffmpeg') or '/opt/homebrew/bin/ffmpeg'
    return ElevenLabsDialogueStreamer(
        voice_id='EDBh1NBfgpE9Lo2jrcIH',
        ffmpeg_executable=ffmpeg,
    ).stream_to_pcm(
        text_chunks,
        emotion,
        Path(os.devnull),
        on_processed_chunk=on_audio,
        flush_after_first_chunk=True,
    )


def safe_speech_error(exc):
    """Keep actionable failure details without leaking process credentials."""
    message = str(exc) or type(exc).__name__
    for secret in (KEY, ELEVENLABS_KEY, TOKEN):
        if secret:
            message = message.replace(secret, '[redacted]')
    return ('ElevenLabs streaming failed: ' + message)[:400]


def speech_socket(connection):
    """Bridge incremental Live transcript text to streamed Mourning Colossus PCM."""
    global speech_count
    target = urlsplit(connection.request.path)
    supplied = parse_qs(target.query).get('token', [''])[0]
    if target.path != '/speech' or not secrets.compare_digest(supplied, TOKEN):
        connection.close(code=1008, reason='Unauthorized')
        return
    with lock:
        if active is None or speech_count >= MAX_SPEECH_STREAMS:
            connection.close(code=1008, reason='Audition unavailable')
            return
        speech_count += 1
    if not speech_lock.acquire(blocking=False):
        connection.close(code=1013, reason='Creature reply already active')
        return

    chunks = queue.Queue()
    sentinel = object()
    total_characters = 0
    ended = False
    worker_error = []
    completed = False
    direction_ready = threading.Event()
    speech_emotion = Emotion.CURIOUS

    def text_chunks():
        while True:
            item = chunks.get()
            if item is sentinel:
                return
            yield item

    def run_stream():
        try:
            if not direction_ready.wait(15):
                raise TimeoutError('Speech direction was not received')
            connection.send(json.dumps({'type': 'direction', 'emotion': speech_emotion.value}))
            timing = stream_mourning_colossus(text_chunks(), connection.send, speech_emotion)
            events.append({
                'type': 'elevenlabs_streamed',
                'first_network_audio_seconds': timing.first_network_audio_seconds,
                'first_processed_audio_seconds': timing.first_processed_audio_seconds,
                'total_seconds': timing.total_seconds,
            })
        except Exception as exc:
            worker_error.append(exc)
            message = safe_speech_error(exc)
            events.append({'type': 'elevenlabs_error', 'class': type(exc).__name__, 'message': message})
            try:
                connection.send(json.dumps({
                    'type': 'error',
                    'message': message,
                }))
            except ConnectionClosed:
                pass

    worker = threading.Thread(target=run_stream, name='creature-speech-stream', daemon=True)
    worker.start()
    try:
        while not ended:
            raw = connection.recv(timeout=15)
            if not isinstance(raw, str):
                raise ValueError('Speech control frames must be JSON text')
            message = json.loads(raw)
            kind = message.get('type')
            if kind in ('start', 'text'):
                text = message.get('text')
                if not isinstance(text, str) or not text:
                    raise ValueError('Speech text is required')
                total_characters += len(text)
                if total_characters > 1200:
                    raise ValueError('Speech text exceeds audition limit')
                if kind == 'start':
                    visitor = message.get('visitor_text', '')
                    if not isinstance(visitor, str) or len(visitor) > 8000:
                        raise ValueError('Invalid visitor context')
                    with lock:
                        if active is not None:
                            performance = active.setdefault('performance', ConversationState())
                            if visitor and visitor != active.get('observed_visitor'):
                                performance.observe(visitor)
                                performance.remember(visitor, text)
                                active['observed_visitor'] = visitor
                            speech_emotion = performance.emotion
                    direction_ready.set()
                chunks.put(text)
            elif kind == 'end':
                chunks.put(sentinel)
                ended = True
            elif kind == 'cancel':
                chunks.put(sentinel)
                return
            else:
                raise ValueError('Unknown speech control frame')
        worker.join(timeout=35)
        if worker.is_alive():
            raise TimeoutError('ElevenLabs stream did not finish')
        if worker_error:
            return
        completed = True
    except (ConnectionClosed, TimeoutError, ValueError, json.JSONDecodeError):
        if not ended:
            chunks.put(sentinel)
    finally:
        direction_ready.set()
        worker.join(timeout=5)
        speech_lock.release()
    if completed:
        # A continuation can connect as soon as done reaches the browser.
        # Release the previous stream slot before inviting that handoff.
        try:
            connection.send(json.dumps({'type': 'done'}))
        except ConnectionClosed:
            pass

def watch(session):
    global active
    sid = session['id']
    try:
        with connect('wss://api.openai.com/v1/live/sessions/' + sid + '/attach',
                     additional_headers={'Authorization': 'Bearer ' + KEY},
                     open_timeout=15, max_size=8_000_000) as ws:
            sent = False
            close_at = None
            while True:
                if (session['stop'].is_set() or time.monotonic() >= session['until']) and not sent:
                    ws.send(json.dumps({'type': 'session.close'}))
                    sent, close_at = True, time.monotonic() + 15
                if close_at and time.monotonic() >= close_at:
                    events.append({'type': 'close_timeout', 'voice': session['voice']})
                    break
                try:
                    event = json.loads(ws.recv(timeout=0.5))
                except TimeoutError:
                    continue
                kind = event.get('type')
                if kind == 'session.closed':
                    events.append({'type': kind, 'voice': session['voice'], 'usage': event.get('usage')})
                    break
                if kind == 'error':
                    events.append({'type': 'error', 'code': event.get('error', {}).get('code')})
    except Exception as exc:
        events.append({'type': 'watchdog_error', 'class': type(exc).__name__})
        session['stop'].set()
    finally:
        with lock:
            if active is session:
                active = None

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def reply(self, code, data, media='application/json'):
        body = data if isinstance(data, bytes) else json.dumps(data).encode()
        self.send_response(code)
        self.send_header('Content-Type', media)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.headers.get('Host') != 'localhost:8767':
            return self.reply(403, {})
        if self.path == '/':
            page = Path(__file__).with_name('index.html').read_text().replace('__TOKEN__', TOKEN)
            return self.reply(200, page.encode(), 'text/html; charset=utf-8')
        static = {
            '/audition.css': 'text/css; charset=utf-8',
            '/assets/special-elite.ttf': 'font/ttf',
            '/creature-scene.mjs': 'text/javascript; charset=utf-8',
            '/motion-core.mjs': 'text/javascript; charset=utf-8',
            '/blender-head.mjs': 'text/javascript; charset=utf-8',
            '/assets/creature-v9.glb': 'model/gltf-binary',
            '/assets/creature-kiri.glb': 'model/gltf-binary',
            '/vendor/GLTFLoader.js': 'text/javascript; charset=utf-8',
            '/vendor/BufferGeometryUtils.js': 'text/javascript; charset=utf-8',
            '/photo-head.mjs': 'text/javascript; charset=utf-8',
            '/assets/head-reference.png': 'image/png',
            '/vendor/three.module.js': 'text/javascript; charset=utf-8',
            '/vendor/three.core.js': 'text/javascript; charset=utf-8',
            '/vendor/OrbitControls.js': 'text/javascript; charset=utf-8',
            '/vendor/THREE-LICENSE.txt': 'text/plain; charset=utf-8',
            '/rig-notes.md': 'text/plain; charset=utf-8',
        }
        if self.path in static:
            return self.reply(200, (Path(__file__).parent / self.path[1:]).read_bytes(), static[self.path])
        if self.path == '/reference.wav':
            return self.reply(200, (ROOT/'analysis/audio/incremental/live-streamed-creature-audition.wav').read_bytes(), 'audio/wav')
        if self.path == '/status':
            return self.reply(200, {'active': active is not None, 'sessions': count,
                                   'events': events, 'stop_requested': bool(active and active['stop'].is_set())})
        return self.reply(404, {})

    def do_POST(self):
        global active, deadline, count, speech_count
        if self.headers.get('Host') != 'localhost:8767' or self.headers.get('Origin') != ORIGIN:
            return self.reply(403, {})
        try:
            size = int(self.headers.get('Content-Length', '0'))
            if not 0 < size <= 65536:
                raise ValueError()
            body = json.loads(self.rfile.read(size))
            if not secrets.compare_digest(body.get('token', ''), TOKEN):
                return self.reply(403, {})
        except (ValueError, TypeError):
            return self.reply(400, {})
        if self.path == '/stop':
            if active:
                active['stop'].set()
            return self.reply(200, {'stopping': True})
        if self.path != '/session':
            return self.reply(404, {})
        voice = body.get('voice')
        if voice not in ('vesper', 'stone') or not isinstance(body.get('sdp'), str) or not body['sdp'].startswith('v=0'):
            return self.reply(400, {'error': 'Invalid voice or SDP'})
        with lock:
            if active is None and deadline and time.monotonic() >= deadline:
                count, deadline = 0, None
            if active or count >= MAX_SESSIONS:
                return self.reply(409, {'error': 'Session active or audition limit reached'})
            active = {'id': None, 'voice': voice, 'stop': threading.Event()}
            session = active
        try:
            result = api('live/sessions', {'session': {'model': 'gpt-live-1',
                'instructions': STYLE + LORE, 'audio': {'output': {'voice': voice}},
                'client': {'data_channel': {'allowed_client_events': ['session.close', 'session.instructions.append']}},
                'store': False, 'delegation': {'type': 'responses', 'responses': {
                    'model': 'gpt-5-mini', 'instructions': STYLE + LORE,
                    'max_output_tokens': 256, 'reasoning': {'effort': 'minimal'},
                    'tools': [], 'tool_choice': 'none'}}},
                'transport': {'type': 'webrtc', 'sdp': body['sdp']}})
            with lock:
                count += 1
                deadline = deadline or time.monotonic() + WINDOW_SECONDS
                speech_count = 0
                session.update(id=result['session']['id'], until=min(deadline, time.monotonic()+SESSION_SECONDS))
            threading.Thread(target=watch, args=(session,), daemon=True).start()
            events.append({'type': 'created', 'voice': voice})
            return self.reply(201, result)
        except urllib.error.HTTPError as exc:
            try:
                error = json.loads(exc.read()).get('error', {})
                message = error.get('message', 'Live session request failed')
                code = error.get('code')
            except ValueError:
                message, code = 'Live session request failed', None
            events.append({'type': 'creation_failed', 'status': exc.code, 'code': code})
            with lock:
                active = None
            return self.reply(exc.code, {'error': message, 'code': code})
        except Exception as exc:
            with lock:
                active = None
            return self.reply(502, {'error': 'Connection failed: '+type(exc).__name__})

if __name__ == '__main__':
    print(ORIGIN, flush=True)
    speech_server = serve(
        speech_socket,
        '127.0.0.1',
        SPEECH_PORT,
        origins=[ORIGIN],
        compression=None,
        max_size=65536,
    )
    speech_thread = threading.Thread(
        target=speech_server.serve_forever,
        name='creature-speech-server',
        daemon=True,
    )
    speech_thread.start()
    server = ThreadingHTTPServer(('127.0.0.1', 8767), Handler)
    try:
        server.serve_forever()
    finally:
        if active:
            active['stop'].set()
            time.sleep(2)
        speech_server.shutdown()
        server.server_close()
