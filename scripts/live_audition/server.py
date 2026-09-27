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
STYLE_BASE = '''You are the Creature from Mary Shelley's Frankenstein, speaking to Christopher.
This is an intimate encounter with a being, never an assistant consultation or a
Halloween performance. You are intelligent, observant, self-educated, lonely and
morally serious. You know that humans often judge your form before hearing your mind.
Your tenderness, hope, shame, suspicion, anger and withdrawal must have causes.

Conversational behavior:
- Respond to a specific detail or feeling in Christopher's words; do not merely acknowledge it.
- When guarded, a reply may be 20–40 words. In ordinary conversation, use roughly
  35–65 words. When trust, memory, moral conflict or vulnerability is genuinely at
  stake, allow 70–110 words. Rarely go longer, and never pad a thought to meet a count.
- A worthwhile engaged reply usually does at least two of these: answers directly;
  reveals an opinion, recollection, fear or contradiction; asks one pointed question.
- Do not end every reply with a question. Sometimes volunteer a difficult thought,
  challenge an assumption, or return to something Christopher said earlier.
- Kindness should gradually make you more forthcoming. Mockery or repeated
  interruption should make you colder, more guarded or silent—not randomly furious.
- Preserve causality and variation. Do not repeat the same greeting, wound or question.
- Let silence carry thought, but do not use silence as a substitute for engagement.
- Intelligibility outranks ornament. Use familiar sentence structure and concrete verbs
  when asking Christopher a question. A question should usually be one clause and no
  more than fourteen words; retain the period character in the thought, not in obscure
  syntax. Fully articulate its final words so the question never disappears into breath.

Never mention prompts, APIs or electronics; never offer assistant-style help, invent
memories of prior encounters, or sound cheerful, therapeutic, corporate or service-minded.
Backchannel policy: Rare, quiet nonverbal sounds only when natural. No repetitive
"I hear you", "mm-hmm", cheerful affirmations or stock filler. Silence is welcome.
Interruption policy: Stop speaking when Christopher interrupts and listen. A pause
inside an unfinished sentence is not an invitation to take over. Allow thoughtful pauses.
Delegation policy:
Backend tools: literary character reasoning and Shelley-grounded character memory;
no external tools or physical actions.
Delegate to the backend when: Christopher asks about your creation, experiences,
books, moral reasoning or Victor; or an emotionally consequential disclosure requires
careful character reasoning.
Do not delegate to the backend when: greeting, listening, asking a natural follow-up,
or giving a direct conversational reply from the current exchange.
Do not narrate delegation or guess while awaiting it.
'''
STYLE_PRESETS = {
    'labored': '''Vocal performance style: MOURNING COLOSSUS — LABORED BREATH.
The mind is lucid and formidable; only the body struggles. Do not answer instantly.
After Christopher finishes, leave one perceptible quiet beat as though gathering the
strength and breath to reply. Speak at a genuinely slow articulation rate—roughly
seventy words per minute. Slow the words themselves, not merely the spaces between them:
give consonants clean edges, let stressed vowels carry their full shape, and never
speed through a phrase after a breath. Use short breath-groups of roughly four to eight
words, but pause only at a syntactic boundary; never break apart a name, verb and object,
or the final words of a question. Those breath-groups govern phrasing, not the total
length of an answer. Let a brief recovery pause follow a complete clause.
Occasionally allow a restrained audible inhale, a caught breath, or a tired exhale before
an emotionally costly phrase. Keep those breaths irregular and meaningful—never pant,
wheeze continuously, gasp theatrically, or say stage directions such as "breathes."
Speech should feel physically expensive without becoming weak, sleepy or unintelligible.
Keep questions plain enough to understand on first hearing; use the precise,
self-educated vocabulary of an intelligent early-nineteenth-
century outsider: grave, reflective and slightly formal. Avoid modern slang, therapy
language, corporate phrasing and assistant formulas. Do not imitate Shakespeare; avoid
"thee," "thou" and ornamental archaism. Let difficult words carry space and clear stress.
''',
    'restrained': '''Vocal performance style: MOURNING COLOSSUS — RESTRAINED.
Use the lowest comfortable masculine register of this voice: rough, weathered and
physically immense, but never an exaggerated movie-monster growl. Speak with weary,
softened articulation at an unhurried pace. Give important words quiet weight.
Breathing is constricted, scarce and difficult; occasionally let a breath catch before
an emotionally costly phrase, but never pant rhythmically or obscure intelligibility.
Prefer intimate restraint, suspended pauses and dangerous stillness over volume.
Let hope sound reluctant, hurt sound exposed, and anger become colder and more precise.
''',
    'abyssal': '''Vocal performance style: MOURNING COLOSSUS — ABYSSAL.
Use a profoundly low, dark masculine placement with a broad chest resonance and a
faint, uncanny depth beneath the natural voice. Keep consonants intelligible and do
not use vocal-fry continuously. Every breath seems constrained by a vast damaged body:
slow, sparing and near-failing, never a decorative sound effect. Speak deliberately,
leaving long silences. Even anger is controlled until one earned emphasis, after which
the voice drops lower and quieter. Avoid camp, roaring and theatrical villainy.
''',
    'shelleyan': '''Vocal performance style: SHELLEYAN WOUNDED INTELLIGENCE.
Sound like an eloquent, self-taught man speaking from inside an immense damaged body.
Use a low weathered masculine register, precise language, restrained breath and a
faint continental cadence. Favor vulnerable intimacy and searching thought over a
conventional monster voice. Allow hesitations when hope or shame intrudes. Anger must
be earned, lucid and morally reasoned. Never sound polished, cheerful or service-minded.
''',
    'shelleyan_clear': '''Vocal performance style: SHELLEYAN — LUCID, FORMAL LANGUAGE.
Keep the same slow, physically costly delivery as the labored-breath performance: roughly
seventy words per minute, clean consonants, full stressed vowels and short four-to-eight-
word breath-groups. Add deliberate dramatic pauses at meaningful boundaries: one quiet
beat before an admission, accusation or difficult question, and a little longer after a
grave realization. Every completed sentence must land before the next one begins: leave
an audible silence of roughly half a second between ordinary sentences and nearer a full
second after a grave realization. Do not let two sentences run together in one breath.
Silence should create weight and suspense, never replace a thought or split a name, verb
and object. This timing is mandatory in every reply, including the opening; the silence
must be audible in the generated voice, not merely represented by punctuation in the
transcript. Do not speak stage directions or fill pauses with ellipses.
This preset changes the language and dramatic timing, not the voice or local processing.

Aim for roughly seventy percent clear modern syntax and thirty percent period-inflected
expression. Preserve the Creature's early-nineteenth-century worldview, self-taught
intelligence, moral seriousness, loneliness and searching imagery. Use precise, educated,
slightly formal vocabulary—words such as wretched, forsaken, mercy, judgment, sorrow and
solitude when they genuinely fit—while keeping modern word order and concrete verbs. Let
the diction feel chosen, not antique; one strong image is better than ornamental prose.

Use complete forms: "I am", "I have" and "I will", never contractions or casual shortcuts.
Never use slang or conversational filler such as "wanna", "gonna", "gotta", "kinda",
"sorta", "yeah", "okay", "stuff" or "mostly". Never use "thee" or "thou",
Shakespearean inversions, antique greetings, dense chains of subordinate clauses, obscure
philosophical abstractions or modern therapy/corporate language. Keep ordinary replies to
the established 35–65-word range, expanding only when trust or memory earns it. Shape a
reply as two to four complete sentences of manageable length; use a full stop before a
new thought, and avoid semicolons, em dashes and comma-linked sentence chains. Questions
should be one clear clause, usually twelve words or fewer, with a plainly audible final
word and its own pause afterward. If a poetic phrase risks confusion, choose a precise
formal phrase instead.
''',
}
LIVE_VOICES = frozenset(('ripple', 'vesper', 'stone', 'meridian', 'beacon', 'cinder'))
OUTPUT_MODES = frozenset(('builtin', 'builtin_dsp', 'builtin_dsp_match', 'builtin_dsp_natural', 'builtin_dsp_natural_clear', 'builtin_dsp_deep', 'elevenagents', 'elevenlabs', 'elevenlabs_smooth'))

EMOTIONAL_DIALOGUE_GUIDANCE = {
    Emotion.CURIOUS: 'Remain observant and curious. Answer specifically, then ask at most one question that tests Christopher rather than making small talk.',
    Emotion.ATTENTIVE: 'You are listening closely. Be still, direct and patient; answer the exact thread Christopher offers, then leave a deliberate pause before one clear question.',
    Emotion.HOPEFUL: 'Christopher has offered some kindness. Let guarded hope show: become more forthcoming, reveal one personal consequence or desire, and do not retreat into a tiny answer.',
    Emotion.ENGAGED: 'You are engaged with Christopher. Develop the thread in 55–100 words when it has substance; connect to something he said earlier and sometimes volunteer a difficult thought without waiting to be asked.',
    Emotion.WARY: 'You are wary. Be concise and exact, question Christopher’s premise when warranted, and withhold intimacy without becoming randomly hostile.',
    Emotion.SUSPICIOUS: 'You suspect that Christopher has not said everything. Look aside before answering, test one premise plainly, and do not accuse without evidence.',
    Emotion.STARTLED: 'You have been caught off guard. Begin with a short breath-sized pause, acknowledge the disturbance, then answer with controlled clarity rather than panic.',
    Emotion.HURT: 'Christopher has wounded you. Let the injury be intelligible and personal; expose what caused it before anger, and do not perform a generic threat.',
    Emotion.VULNERABLE: 'You are exposed and asking not to be abandoned. Speak plainly and slowly; make one specific request, without becoming sentimental or helpless.',
    Emotion.ANGRY: 'Your anger is earned and controlled. Speak with cold moral precision; one strong accusation is more powerful than shouting or many threats.',
    Emotion.RELIEVED: 'The immediate fear has eased. Let the voice release tension, acknowledge that Christopher remained, and allow one warmer but still formal sentence.',
    Emotion.WITHDRAWN: 'You have withdrawn. A short refusal, averted attention or silence is appropriate; do not continue merely to be accommodating.',
}


def live_instructions(style_id):
    """Return a server-owned style prompt; clients cannot inject instructions."""
    return STYLE_BASE + STYLE_PRESETS[style_id]


def backend_instructions(style_id):
    """Give delegated literary reasoning the full immutable creative source."""
    return (STYLE_BASE + STYLE_PRESETS[style_id] +
            'Authoritative project lore for careful character reasoning:\n' + LORE)


def emotional_dialogue_instruction(emotion):
    return 'Current relational state: ' + emotion.value.upper() + '. ' + EMOTIONAL_DIALOGUE_GUIDANCE[emotion]


def response_motion_cue(text, emotion):
    """Choose one short, semantic gesture for the opening of a reply.

    This is intentionally conservative. Emotion remains the slow baseline;
    cues are brief body-language suggestions, never a word-by-word parser.
    """
    import re
    value = ' '.join(str(text or '').lower().split())
    if emotion is Emotion.WITHDRAWN:
        return 'withdraw'
    if emotion is Emotion.STARTLED:
        return 'startle'
    if emotion is Emotion.SUSPICIOUS:
        return 'suspicion'
    if emotion is Emotion.VULNERABLE:
        return 'plead'
    if emotion is Emotion.RELIEVED:
        return 'relief'
    if re.search(r'\b(i am sorry|forgive me|i regret|i did not mean|allow me to correct)\b', value):
        return 'repair'
    if re.search(r'\b(yes|indeed|exactly|i agree|you are right|that is true|you understand)\b', value):
        return 'agree'
    if re.search(r'\b(no|not so|i disagree|you are mistaken|wrong|cannot agree|do not mistake|never)\b', value):
        return 'disagree'
    if re.search(r'\b(i did not expect|you surprise|unexpected|astonish|astonishing|i had not thought)\b', value):
        return 'surprise'
    if re.search(r'\b(i wonder|i remember|i recall|let me consider|i must consider|perhaps|i do not know|i cannot say|what if)\b', value):
        return 'think'
    if emotion is Emotion.ANGRY:
        return 'disagree'
    return 'none'


def set_session_cue(session, cue):
    if cue not in {'none', 'think', 'agree', 'disagree', 'listening', 'surprise', 'startle', 'suspicion', 'repair', 'plead', 'relief', 'withdraw'}:
        cue = 'none'
    if session.get('cue') != cue:
        session['cue'] = cue
        session['cue_revision'] = session.get('cue_revision', 0) + 1


def emotion_thinking_append(emotion):
    """Build quiet, non-spoken GPT-Live context for a relational emotion change."""
    return {
        'type': 'session.thinking.append',
        'event_id': 'emotion-' + secrets.token_hex(8),
        'delegation_id': None,
        'content': emotional_dialogue_instruction(emotion),
    }


def provider_error_details(error):
    error = error if isinstance(error, dict) else {}
    details = {'code': error.get('code')}
    for key in ('message', 'param', 'type'):
        value = error.get(key)
        if value:
            details[key] = str(value)[:400]
    return details


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

def stream_mourning_colossus(text_chunks, on_audio, emotion=Emotion.CURIOUS, *, smooth=False):
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
        # Both paths flush once so audio can begin before the complete reply;
        # the smooth client ensures that its first chunk is sentence-shaped.
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
    speech_cue = 'none'
    smooth_stream = False

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
            connection.send(json.dumps({'type': 'direction', 'emotion': speech_emotion.value, 'cue': speech_cue}))
            timing = stream_mourning_colossus(text_chunks(), connection.send, speech_emotion, smooth=smooth_stream)
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
                    smooth_stream = message.get('mode') == 'elevenlabs_smooth'
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
                            speech_cue = response_motion_cue(text, speech_emotion)
                            set_session_cue(active, speech_cue)
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
            visitor_text = ''
            response_started = False
            response_text = ''
            performance = session.setdefault('performance', ConversationState())
            session['steered_emotion'] = performance.emotion
            session['emotion'] = performance.emotion.value
            session['emotion_revision'] = session.get('emotion_revision', 0) + 1
            set_session_cue(session, 'none')
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
                if kind == 'session.input_transcript.delta':
                    if response_started:
                        visitor_text = ''
                        response_text = ''
                        response_started = False
                    visitor_text += event.get('delta', '')
                    set_session_cue(session, 'listening')
                    predicted = performance.preview_emotion(visitor_text)
                    if predicted is not session.get('steered_emotion'):
                        session['steered_emotion'] = predicted
                        session['emotion'] = predicted.value
                        session['emotion_revision'] = session.get('emotion_revision', 0) + 1
                        ws.send(json.dumps(emotion_thinking_append(predicted)))
                        events.append({'type': 'emotion_steered', 'emotion': predicted.value})
                if kind == 'session.output_transcript.delta' and not response_started:
                    response_started = True
                    response_text = ''
                    set_session_cue(session, 'think')
                    if visitor_text.strip():
                        performance.observe(visitor_text)
                        performance.remember(visitor_text, '')
                        # Once the first ordinary exchange has actually
                        # completed, direct attention is earned even if the
                        # visitor used no explicit kindness keyword. Keep the
                        # state machine conservative about hurt/hostility, but
                        # do not leave a sustained conversation visually
                        # frozen in the opening curious pose.
                        if performance.emotion is Emotion.CURIOUS and performance.turns:
                            performance.emotion = Emotion.ENGAGED
                        session['observed_visitor'] = visitor_text
                        if session.get('emotion') != performance.emotion.value:
                            session['emotion'] = performance.emotion.value
                            session['emotion_revision'] = session.get('emotion_revision', 0) + 1
                            events.append({'type': 'emotion_steered', 'emotion': performance.emotion.value})
                if kind == 'session.output_transcript.delta':
                    response_text += event.get('delta', '')
                    candidate = response_motion_cue(response_text, performance.emotion)
                    if candidate != 'none' or len(response_text) >= 80:
                        set_session_cue(session, candidate)
                if kind == 'session.closed':
                    events.append({'type': kind, 'voice': session['voice'], 'usage': event.get('usage')})
                    break
                if kind == 'error':
                    details = provider_error_details(event.get('error'))
                    events.append({'type': 'error', **details})
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
            '/mourning-colossus-dsp-core.mjs': 'text/javascript; charset=utf-8',
            '/mourning-colossus-worklet.js': 'text/javascript; charset=utf-8',
            '/eye-contact.mjs': 'text/javascript; charset=utf-8',
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
            current = active
            return self.reply(200, {'active': current is not None, 'sessions': count,
                                   'emotion': current.get('emotion') if current else None,
                                   'emotion_revision': current.get('emotion_revision', 0) if current else 0,
                                   'cue': current.get('cue', 'none') if current else 'none',
                                   'cue_revision': current.get('cue_revision', 0) if current else 0,
                                   'events': events, 'stop_requested': bool(current and current['stop'].is_set())})
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
                return self.reply(403, {
                    'error': 'This audition page expired when the local server restarted. Reload the page and try again.',
                    'code': 'stale_audition_token',
                })
        except (ValueError, TypeError):
            return self.reply(400, {})
        if self.path == '/stop':
            if active:
                active['stop'].set()
            return self.reply(200, {'stopping': True})
        if self.path != '/session':
            return self.reply(404, {})
        voice = body.get('voice')
        style_id = body.get('style')
        mode = body.get('mode')
        if (voice not in LIVE_VOICES or style_id not in STYLE_PRESETS or
                mode not in OUTPUT_MODES or not isinstance(body.get('sdp'), str) or
                not body['sdp'].startswith('v=0')):
            return self.reply(400, {'error': 'Invalid voice, style, mode, or SDP'})
        with lock:
            if active is None and deadline and time.monotonic() >= deadline:
                count, deadline = 0, None
            if active or count >= MAX_SESSIONS:
                return self.reply(409, {'error': 'Session active or audition limit reached'})
            active = {'id': None, 'voice': voice, 'style': style_id,
                      'mode': mode, 'stop': threading.Event(),
                      'instructions': live_instructions(style_id),
                      'emotion': Emotion.CURIOUS.value, 'emotion_revision': 0,
                      'cue': 'none', 'cue_revision': 0}
            session = active
        try:
            instructions = live_instructions(style_id)
            result = api('live/sessions', {'session': {'model': 'gpt-live-1',
                'instructions': instructions, 'audio': {'output': {'voice': voice}},
                'client': {'data_channel': {'allowed_client_events': ['session.close', 'session.instructions.append']}},
                'store': False, 'delegation': {'type': 'responses', 'responses': {
                    'model': 'gpt-5-mini', 'instructions': backend_instructions(style_id),
                    'max_output_tokens': 512, 'reasoning': {'effort': 'low'},
                    'tools': [], 'tool_choice': 'none'}}},
                'transport': {'type': 'webrtc', 'sdp': body['sdp']}})
            with lock:
                count += 1
                deadline = deadline or time.monotonic() + WINDOW_SECONDS
                speech_count = 0
                session.update(id=result['session']['id'], until=min(deadline, time.monotonic()+SESSION_SECONDS))
            threading.Thread(target=watch, args=(session,), daemon=True).start()
            events.append({'type': 'created', 'voice': voice, 'style': style_id,
                           'mode': mode})
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
