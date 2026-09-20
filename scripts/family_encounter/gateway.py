"""Single-instance authenticated gateway. Only this port may face the internet.

The existing voice/DSP process stays on loopback. Secrets never reach the page.
Run behind a TLS-terminating host with a persistent private STATE_DIR.
"""
import asyncio
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import secrets
import sqlite3
import time
from urllib.parse import urlsplit
from aiohttp import ClientSession, ClientTimeout, WSMsgType, web

COOKIE = 'creature_family'
STATIC = {'/audition.css', '/creature-scene.mjs', '/motion-core.mjs',
          '/blender-head.mjs', '/assets/creature-kiri.glb',
          '/assets/special-elite.ttf', '/vendor/three.module.js',
          '/vendor/three.core.js', '/vendor/GLTFLoader.js',
          '/vendor/BufferGeometryUtils.js', '/vendor/OrbitControls.js',
          '/assets/head-reference.png', '/rig-notes.md', '/reference.wav'}
SECURITY = {'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff',
            'Referrer-Policy': 'no-referrer', 'X-Frame-Options': 'DENY',
            'Permissions-Policy': 'microphone=(self), camera=(), geolocation=()',
            'Content-Security-Policy': "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; font-src 'self'; media-src 'self' blob:; connect-src 'self' blob:; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"}


def password_hash(password):
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 600_000).hex()
    return f'pbkdf2_sha256$600000${salt}${digest}'


def password_matches(password, encoded):
    try:
        algorithm, iterations, salt, expected = encoded.split('$')
        if algorithm != 'pbkdf2_sha256' or int(iterations) != 600_000:
            return False
        actual = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), int(iterations)).hex()
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


class Store:
    def __init__(self, path):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.db = sqlite3.connect(path)
        os.chmod(path, 0o600)
        self.db.executescript('''
            CREATE TABLE IF NOT EXISTS counters (key TEXT PRIMARY KEY, n INTEGER, expiry REAL);
            CREATE TABLE IF NOT EXISTS logins (id TEXT PRIMARY KEY, csrf TEXT, expiry REAL);
        ''')

    def reserve(self, limits):
        now = time.time()
        with self.db:
            self.db.execute('DELETE FROM counters WHERE expiry <= ?', (now,))
            self.db.execute('DELETE FROM logins WHERE expiry <= ?', (now,))
            for key, limit, seconds in limits:
                row = self.db.execute('SELECT n FROM counters WHERE key=?', (key,)).fetchone()
                if row and row[0] >= limit:
                    return False
            for key, limit, seconds in limits:
                self.db.execute('INSERT INTO counters VALUES (?,?,?) ON CONFLICT(key) DO UPDATE SET n=n+1', (key, 1, now + seconds))
        return True

    def login(self):
        token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
        with self.db:
            self.db.execute('INSERT INTO logins VALUES (?,?,?)', (self.digest(token), csrf, time.time()+8*3600))
        return token

    @staticmethod
    def digest(token):
        return hashlib.sha256(token.encode()).hexdigest()

    def session(self, token):
        if not token or len(token) > 100:
            return None
        sid = self.digest(token)
        row = self.db.execute('SELECT csrf,expiry FROM logins WHERE id=?', (sid,)).fetchone()
        return (sid, row[0]) if row and row[1] > time.time() else None

    def revoke(self, sid):
        with self.db:
            self.db.execute('DELETE FROM logins WHERE id=?', (sid,))


def login_page(message='A private encounter. Enter the family password.'):
    return f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><title>Enter the laboratory</title>
<style>html{{color-scheme:dark;background:#050605;color:#b3b7a3;font-family:Georgia,serif}}body{{min-height:100vh;min-height:100dvh;display:grid;place-items:center;margin:0;padding:env(safe-area-inset-top) env(safe-area-inset-right) env(safe-area-inset-bottom) env(safe-area-inset-left);box-sizing:border-box}}main{{box-sizing:border-box;width:100%;max-width:28rem;padding:2rem}}h1{{font-weight:normal;font-size:2.2rem}}input,button{{box-sizing:border-box;width:100%;padding:1rem;margin-top:1rem;background:transparent;color:inherit;border:1px solid #474a3e;font:16px Georgia,serif}}a{{color:inherit}}p{{line-height:1.6}}button{{cursor:pointer}}</style>
<main><h1>Enter the laboratory</h1><p role="status">{message}</p><p>Turn your volume up. When you enter, the Creature will ask to use your microphone so it can hear you.</p><form method="post" action="/login"><label for="password">Family password</label><input id="password" name="password" type="password" autocomplete="current-password" required maxlength="128"><button>Enter the laboratory</button></form></main><script>
document.querySelector('form').addEventListener('submit', async event => {{
  event.preventDefault();
  const form=event.currentTarget, button=form.querySelector('button');button.disabled=true;
  try {{
    const response=await fetch('/login',{{method:'POST',body:new URLSearchParams(new FormData(form))}});
    if(response.ok && response.redirected){{location.replace('/');return;}}
    document.querySelector('[role=status]').textContent=response.status===429?'Access attempts are temporarily limited. Please try later.':'Password not recognized.';
  }} catch {{ document.querySelector('[role=status]').textContent='The laboratory is temporarily unavailable.'; }}
  button.disabled=false;
}});
</script></html>''' 


class Gateway:
    def __init__(self, origin, encoded_password, store, upstream='http://localhost:8767', speech='ws://localhost:8768'):
        url = urlsplit(origin)
        if url.scheme != 'https' and not (url.scheme == 'http' and url.hostname in ('localhost', '127.0.0.1')):
            raise ValueError('PUBLIC_ORIGIN must use HTTPS (except local previews)')
        if url.path or url.query or url.fragment or url.username or not url.netloc:
            raise ValueError('PUBLIC_ORIGIN must be a bare origin')
        if not re.fullmatch(r'pbkdf2_sha256\$600000\$[a-f0-9]{32}\$[a-f0-9]{64}', encoded_password):
            raise ValueError('A valid server-side password hash is required')
        self.origin, self.host, self.secure = origin, url.netloc, url.scheme == 'https'
        self.encoded_password, self.store = encoded_password, store
        self.upstream, self.speech = upstream, speech
        self.client = None
        self.owner = None
        self.until = 0
        self.token = None
        self.lock = asyncio.Lock()
        self.speech_lock = asyncio.Lock()
        self.replies = 0
        self.app = web.Application(client_max_size=65536, middlewares=[self.guard])
        self.app.router.add_route('*', '/{path:.*}', self.handle)
        self.app.cleanup_ctx.append(self.lifecycle)

    async def lifecycle(self, app):
        self.client = ClientSession(timeout=ClientTimeout(total=40))
        yield
        await self.client.close()
        self.store.db.close()

    @web.middleware
    async def guard(self, request, handler):
        # The only unauthenticated machine route: no configuration/provider data.
        if request.path == '/healthz' and request.method == 'GET':
            return web.json_response({'ok': True}, headers=SECURITY)
        if request.host != self.host:
            return web.Response(status=403, headers=SECURITY)
        if request.method not in ('GET', 'POST') or request.query_string and request.path != '/speech':
            return web.Response(status=404, headers=SECURITY)
        if request.method == 'POST' or request.path == '/speech':
            if request.headers.get('Origin') != self.origin:
                return web.Response(status=403, headers=SECURITY)
        auth = self.store.session(request.cookies.get(COOKIE))
        request['auth'] = auth
        if request.path != '/login' and not auth:
            if request.path == '/' and request.method == 'GET':
                return web.Response(text=login_page(), content_type='text/html', headers=SECURITY)
            return web.json_response({'error': 'Please sign in.'}, status=401, headers=SECURITY)
        try:
            response = await handler(request)
        except (ValueError, json.JSONDecodeError):
            response = web.json_response({'error': 'Invalid request.'}, status=400)
        except web.HTTPException as exc:
            response = exc
        except Exception:
            # Never return upstream exceptions, credentials, SDP or transcripts.
            response = web.json_response({'error': 'The encounter is temporarily unavailable.'}, status=503)
        if not response.prepared:
            response.headers.update(SECURITY)
            if self.secure:
                response.headers['Strict-Transport-Security'] = 'max-age=31536000'
        return response

    async def upstream_request(self, method, path, body=None):
        async with self.client.request(method, self.upstream+path,
                headers={'Host': 'localhost:8767', 'Origin': 'http://localhost:8767'}, json=body) as response:
            return response.status, await response.read(), response.headers.get('Content-Type', 'application/octet-stream')

    async def backend_token(self):
        status, body, _ = await self.upstream_request('GET', '/')
        match = re.search(rb"const token='([A-Za-z0-9_-]+)'", body)
        if status != 200 or not match:
            raise RuntimeError('Upstream unavailable')
        self.token = match.group(1).decode()
        return body.decode()

    async def handle(self, request):
        if request.path == '/login':
            if request.method == 'GET':
                return web.Response(text=login_page(), content_type='text/html')
            # Do not trust forwarded IP headers. Global throttling also prevents
            # distributed guessing of the intentionally short family password.
            peer = hashlib.sha256((request.remote or 'unknown').encode()).hexdigest()
            if not self.store.reserve([('login:'+peer, 5, 900), ('login:global', 20, 86400)]):
                return web.Response(text=login_page('Access attempts are temporarily limited. Please try later.'), content_type='text/html', status=429, headers={'Retry-After':'900'})
            body = await request.post()
            password = body.get('password', '')
            if not isinstance(password, str) or len(password) > 128 or not await asyncio.to_thread(password_matches, password, self.encoded_password):
                return web.Response(text=login_page('Password not recognized.'), content_type='text/html', status=401)
            token = self.store.login()
            response = web.Response(status=303, headers={'Location':'/'})
            response.set_cookie(COOKIE, token, max_age=8*3600, httponly=True, secure=self.secure, samesite='Strict', path='/')
            return response
        sid, csrf = request['auth']
        if request.path == '/speech':
            if request.method != 'GET' or not hmac.compare_digest(request.query.get('token', ''), csrf):
                return web.Response(status=403)
            return await self.bridge(request, sid)
        if request.method == 'GET':
            if request.path == '/':
                page = await self.backend_token()
                page = page.replace("const token='"+self.token+"'", "const token='"+csrf+"'")
                page = page.replace('ws://localhost:8768/speech?token=', "${location.protocol==='https:'?'wss:':'ws:'}//${location.host}/speech?token=")
                page = page.replace('Five minutes per audition; twenty minutes total.', 'Five minutes per encounter. One visitor at a time; family usage limits apply.')
                page = page.replace('const result=await r.json();if(!r.ok)throw Error(', 'const result=await r.json();if(r.status===401){location.href=\'/login\';return;}if(!r.ok)throw Error(')
                page = page.replace('</dialog>', '<form method="post" action="/logout"><input type="hidden" name="token" value="'+csrf+'"><button class="secondary">Lock the laboratory</button></form></dialog>')
                return web.Response(text=page, content_type='text/html')
            if request.path == '/status':
                if sid != self.owner or time.monotonic() >= self.until:
                    return web.json_response({'active': False, 'stop_requested': True})
                code, data, _ = await self.upstream_request('GET', '/status')
                status = json.loads(data)
                if not status.get('active'):
                    self.until = 0
                return web.json_response({'active': bool(status.get('active')), 'stop_requested': bool(status.get('stop_requested'))})
            if request.path in STATIC:
                code, body, media = await self.upstream_request('GET', request.path)
                return web.Response(status=code, body=body, headers={'Content-Type':media})
            return web.Response(status=404)
        body = dict(await request.post()) if request.path == '/logout' else await request.json()
        if not isinstance(body, dict) or not isinstance(body.get('token'), str) or not hmac.compare_digest(body['token'], csrf):
            return web.Response(status=403)
        async with self.lock:
            if request.path in ('/logout', '/stop'):
                if sid == self.owner:
                    await self.upstream_request('POST', '/stop', {'token':self.token})
                    self.until = 0
                if request.path == '/logout':
                    self.store.revoke(sid)
                    response = web.Response(status=303, headers={'Location':'/login'})
                    response.del_cookie(COOKIE, path='/')
                    return response
                return web.json_response({'stopping':True})
            if request.path != '/session':
                return web.Response(status=404)
            if self.owner and time.monotonic() < self.until:
                return web.json_response({'error':'The Creature is speaking with another visitor. Try again shortly.'}, status=409)
            if body.get('voice') != 'vesper' or not isinstance(body.get('sdp'), str) or not body['sdp'].startswith('v=0'):
                return web.Response(status=400)
            if not self.store.reserve([('sessions:hour',4,3600), ('sessions:day',20,86400)]):
                return web.json_response({'error':'The family encounter limit has been reached. Please return later.'}, status=429)
            await self.backend_token()
            code, data, _ = await self.upstream_request('POST', '/session', {'token':self.token,'voice':'vesper','sdp':body['sdp']})
            if code != 201:
                return web.json_response({'error':'The Creature is unavailable. Please try again shortly.'}, status=503)
            answer = json.loads(data)['transport']['sdp']
            self.owner, self.until, self.replies = sid, time.monotonic()+300, 0
            # Only SDP is needed. Never expose a provider session credential.
            return web.json_response({'transport':{'sdp':answer}}, status=201)

    async def bridge(self, request, sid):
        if sid != self.owner or time.monotonic() >= self.until or self.replies >= 12:
            return web.Response(status=403)
        async with self.speech_lock:
            if sid != self.owner or time.monotonic() >= self.until or self.replies >= 12:
                return web.Response(status=403)
            self.replies += 1
            socket = web.WebSocketResponse(max_msg_size=65536, heartbeat=15)
            socket.headers.update(SECURITY)
            async with self.client.ws_connect(self.speech+'/speech?token='+self.token, origin='http://localhost:8767', max_msg_size=1_000_000) as upstream:
                await socket.prepare(request)
                async def send():
                    characters = 0
                    async for frame in socket:
                        if frame.type != WSMsgType.TEXT or time.monotonic() >= self.until or not self.store.session(request.cookies.get(COOKIE)):
                            break
                        message = json.loads(frame.data)
                        if not isinstance(message, dict) or message.get('type') not in ('start','text','end','cancel'):
                            break
                        if message['type'] in ('start','text'):
                            text = message.get('text')
                            if not isinstance(text, str) or not text:
                                break
                            characters += len(text)
                            if characters > 1200:
                                break
                        await upstream.send_str(frame.data)
                async def receive():
                    async for frame in upstream:
                        if frame.type == WSMsgType.BINARY:
                            await socket.send_bytes(frame.data)
                        elif frame.type == WSMsgType.TEXT:
                            message = json.loads(frame.data)
                            if message.get('type') == 'error':
                                message = {'type':'error','message':'The voice is temporarily unavailable.'}
                            await socket.send_json(message)
                        else:
                            break
                async def expired():
                    while sid == self.owner and time.monotonic() < self.until and self.store.session(request.cookies.get(COOKIE)):
                        await asyncio.sleep(.25)
                tasks = [asyncio.create_task(send()), asyncio.create_task(receive()), asyncio.create_task(expired())]
                try:
                    await asyncio.wait(tasks, timeout=max(0,min(45,self.until-time.monotonic())), return_when=asyncio.FIRST_COMPLETED)
                finally:
                    for task in tasks:
                        task.cancel()
                    await asyncio.gather(*tasks, return_exceptions=True)
                    await socket.close()
            return socket


def main():
    state = Path(os.environ.get('STATE_DIR', '/var/lib/creature'))
    origin = os.environ['PUBLIC_ORIGIN'].rstrip('/')
    encoded = os.environ.get('FAMILY_PASSWORD_HASH')
    if not encoded:
        encoded = Path(os.environ['FAMILY_PASSWORD_HASH_FILE']).read_text().strip()
    gateway = Gateway(origin, encoded, Store(state/'access.sqlite3'))
    # Loopback for local previews; hosting explicitly opts into 0.0.0.0.
    web.run_app(gateway.app, host=os.environ.get('GATEWAY_BIND','127.0.0.1'), port=int(os.environ.get('PORT','8772')), access_log=None)

if __name__ == '__main__':
    main()
