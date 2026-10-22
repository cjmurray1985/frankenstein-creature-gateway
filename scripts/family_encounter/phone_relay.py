"""Public HTTPS phone routes over an outbound, signed local-agent channel.

Visitor profile and separately authenticated owner app use explicit routes only.
No arbitrary local URL or unauthenticated private data route is exposed.
"""
import asyncio,base64,json,re,secrets,time
from pathlib import Path
from http.cookies import SimpleCookie
from aiohttp import web,WSMsgType
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

OPERATOR_GET=frozenset(('/operator/','/operator/app.js','/operator/style.css','/operator/manifest.webmanifest','/operator/sw.js','/operator/icon-192.png','/operator/icon-512.png','/operator/api/status','/operator/api/camera','/operator/api/session'))
OPERATOR_POST=frozenset(('/operator/api/login','/operator/api/logout','/operator/api/power','/operator/api/memory','/operator/api/merges'))
GET_PATH=re.compile(r'/p/[A-Za-z0-9_-]{32}|/companion/(?:app\.js|style\.css|me|portrait|duplicates)')
POST_PATH=frozenset(('/companion/claim','/companion/auth','/companion/lock','/companion/save','/companion/merge-request'))
LIMIT=3_000_000
RESPONSE_LIMIT=5_000_000

def allowed(method,path):
    return bool(method=='GET' and (GET_PATH.fullmatch(path) or path in OPERATOR_GET) or method=='POST' and (path in POST_PATH or path in OPERATOR_POST))

class PhoneRelay:
    def __init__(self,origin,public_key=None):
        self.origin=origin;self.agent=None;self.pending={};self.attempts={}
        file=Path(__file__).with_name('phone-relay-public-key.txt')
        self.key=public_key if public_key is not None else bytes.fromhex(file.read_text().strip()) if file.exists() else None
    def handles(self,path):return path=='/companion-relay' or bool(GET_PATH.fullmatch(path)) or path in POST_PATH or path in OPERATOR_GET or path in OPERATOR_POST
    def rate(self,request):
        now=time.monotonic();self.attempts={k:v for k,v in self.attempts.items() if v[1]>now}
        owner=request.path.startswith('/operator/')
        key=(request.remote or 'unknown', 'operator' if owner else 'visitor');count,until=self.attempts.get(key,(0,now+60))
        if count>=(360 if owner else 120) or len(self.attempts)>4096:return False
        self.attempts[key]=(count+1,until);return True
    async def handle(self,request):
        if request.query_string:return web.Response(status=404)
        if request.path=='/companion-relay':return await self.connect(request)
        if not allowed(request.method,request.path):return web.Response(status=404)
        if request.method=='POST' and request.headers.get('Origin')!=self.origin:return web.Response(status=403)
        if not self.rate(request):return web.Response(status=429,headers={'Retry-After':'60'})
        if self.agent is None or self.agent.closed:return self.unavailable()
        if len(self.pending)>=8:return self.unavailable()
        if request.content_length is not None and request.content_length>LIMIT:return web.Response(status=413)
        body=bytearray()
        async for chunk in request.content.iter_chunked(65536):
            body.extend(chunk)
            if len(body)>LIMIT:return web.Response(status=413)
        identifier=secrets.token_hex(16);future=asyncio.get_running_loop().create_future();self.pending[identifier]=future
        headers={key:request.headers[key] for key in ('Cookie','Origin','Content-Type','X-CSRF-Token') if key in request.headers}
        if any(len(v)>8192 for v in headers.values()):self.pending.pop(identifier,None);return web.Response(status=400)
        if 'Cookie' in headers:
            cookies=SimpleCookie()
            try:cookies.load(headers['Cookie'])
            except Exception:cookies=SimpleCookie()
            cookie_name='creature_operator' if request.path.startswith('/operator/') else 'creature_companion'
            headers['Cookie']=cookie_name+'='+cookies[cookie_name].value if cookie_name in cookies else ''
        try:
            await self.agent.send_json({'id':identifier,'method':request.method,'path':request.path,'headers':headers,'body':base64.b64encode(body).decode()})
            result=await asyncio.wait_for(future,20)
            raw=base64.b64decode(result['body'],validate=True)
            if len(raw)>RESPONSE_LIMIT:raise ValueError()
            response=web.Response(status=int(result['status']),body=raw)
            for key,value in result.get('headers',{}).items():
                if key.lower() in ('content-type','content-security-policy','referrer-policy','x-content-type-options') and isinstance(value,str) and '\r' not in value and '\n' not in value:response.headers[key]=value
                if key.lower()=='set-cookie' and isinstance(value,str) and value.startswith(('creature_companion=','creature_operator=')) and '\r' not in value and '\n' not in value:response.headers['Set-Cookie']=value
            response.headers['Cache-Control']='no-store'
            return response
        except (asyncio.TimeoutError,ConnectionError,ValueError,KeyError):return self.unavailable()
        finally:self.pending.pop(identifier,None)
    @staticmethod
    def unavailable():return web.json_response({'error':'The exhibit profile service is offline. Please try again shortly.'},status=503,headers={'Cache-Control':'no-store'})
    async def connect(self,request):
        if request.method!='GET' or self.key is None:return web.Response(status=404)
        if request.headers.get('Origin'):return web.Response(status=403) # Machine agent, never a browser.
        if not self.rate(request):return web.Response(status=429)
        ws=web.WebSocketResponse(heartbeat=20,max_msg_size=7_000_000);await ws.prepare(request)
        challenge=secrets.token_bytes(32);await ws.send_json({'challenge':base64.b64encode(challenge).decode()})
        authenticated=False
        try:
            msg=await asyncio.wait_for(ws.receive(),10)
            if msg.type!=WSMsgType.TEXT:raise ValueError()
            signature=base64.b64decode(json.loads(msg.data)['signature'],validate=True)
            Ed25519PublicKey.from_public_bytes(self.key).verify(signature,b'frankenstein-phone-relay:v1:'+challenge)
            if self.agent and not self.agent.closed:await ws.close(code=1008,message=b'Agent already connected');return ws
            self.agent=ws;authenticated=True;await ws.send_json({'ready':True})
            async for msg in ws:
                if msg.type!=WSMsgType.TEXT:break
                value=json.loads(msg.data);future=self.pending.get(value.get('id'))
                if future and not future.done():future.set_result(value)
        except Exception:
            await ws.close(code=1008,message=b'Relay connection rejected')
        finally:
            if authenticated and self.agent is ws:
                self.agent=None
                for future in self.pending.values():
                    if not future.done():future.set_exception(ConnectionError('Agent disconnected'))
            if not ws.closed:await ws.close()
        return ws
    async def close(self):
        if self.agent:await self.agent.close()
