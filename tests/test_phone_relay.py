import asyncio,base64,json,tempfile,unittest
from pathlib import Path
from aiohttp import ClientSession,WSMsgType,web
from aiohttp.test_utils import TestServer
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization
from scripts.family_encounter.phone_relay import PhoneRelay,allowed,LIMIT

class RelayTest(unittest.IsolatedAsyncioTestCase):
 async def asyncSetUp(self):
  self.key=Ed25519PrivateKey.generate();public=self.key.public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw)
  self.relay=PhoneRelay('https://exhibit.test',public)
  async def route(request):
   return await self.relay.handle(request) if self.relay.handles(request.path) else web.Response(status=404)
  app=web.Application();app.router.add_route('*','/{path:.*}',route)
  self.server=TestServer(app);await self.server.start_server();self.client=ClientSession();self.sockets=[]
 async def asyncTearDown(self):
  await self.relay.close()
  for ws in self.sockets:await ws.close()
  await self.client.close();await self.server.close()
 async def agent(self,key=None):
  ws=await self.client.ws_connect(self.server.make_url('/companion-relay'));self.sockets.append(ws)
  challenge=base64.b64decode((await ws.receive_json())['challenge']);signature=(key or self.key).sign(b'frankenstein-phone-relay:v1:'+challenge)
  await ws.send_json({'signature':base64.b64encode(signature).decode()});return ws
 async def test_offline_and_private_boundaries(self):
  for path in ('/people','/vision/frame.jpg','/companion/local-ca.cer','/live-memory/password-reset'):
   async with self.client.get(self.server.make_url(path)) as r:self.assertEqual(r.status,404)
  async with self.client.get(self.server.make_url('/companion/me')) as r:self.assertEqual(r.status,503)
  async with self.client.post(self.server.make_url('/companion/save'),headers={'Origin':'https://evil.test'},json={}) as r:self.assertEqual(r.status,403)
  async with self.client.get(self.server.make_url('/companion/me?url=http://evil.test')) as r:self.assertEqual(r.status,404)
 async def test_invalid_signature_does_not_connect(self):
  ws=await self.agent(Ed25519PrivateKey.generate());message=await ws.receive();self.assertEqual(message.type,WSMsgType.CLOSE);self.assertIsNone(self.relay.agent)
 async def test_authenticated_forwarding_body_and_cookie(self):
  ws=await self.agent();self.assertTrue((await ws.receive_json())['ready'])
  async def browser():
   async with self.client.post(self.server.make_url('/companion/save'),data=b'x'*100000,headers={'Origin':'https://exhibit.test','Cookie':'creature_companion=test','X-CSRF-Token':'test','X-Companion-Transport':'spoofed','X-Other':'discard'}) as r:return r.status,await r.read(),r.headers.get('Set-Cookie')
  task=asyncio.create_task(browser());request=await ws.receive_json()
  self.assertEqual(len(base64.b64decode(request['body'])),100000);self.assertEqual(request['path'],'/companion/save');self.assertNotIn('X-Companion-Transport',request['headers']);self.assertNotIn('X-Other',request['headers'])
  await ws.send_json({'id':request['id'],'status':200,'body':base64.b64encode(b'{"saved":true}').decode(),'headers':{'Content-Type':'application/json','Set-Cookie':'creature_companion=rotated; Secure; HttpOnly; SameSite=Strict','X-Other':'discard'}})
  status,body,cookie=await task;self.assertEqual(status,200);self.assertEqual(json.loads(body),{'saved':True});self.assertIn('Secure',cookie)
 async def test_duplicate_agent_cannot_replace_existing(self):
  first=await self.agent();await first.receive_json();second=await self.agent();message=await second.receive();self.assertEqual(message.type,WSMsgType.CLOSE);self.assertFalse(first.closed)
 async def test_disconnect_fails_pending_and_oversize_rejected(self):
  ws=await self.agent();await ws.receive_json()
  task=asyncio.create_task(self.client.get(self.server.make_url('/companion/me')));await ws.receive_json();await ws.close()
  response=await task;self.assertEqual(response.status,503);await response.read();response.release()
  ws=await self.agent();await ws.receive_json()
  async with self.client.post(self.server.make_url('/companion/save'),data=b'x'*(LIMIT+1),headers={'Origin':'https://exhibit.test'}) as r:self.assertEqual(r.status,413)
 def test_local_allowlist_rejects_arbitrary_targets(self):
  for path in ('http://evil.test/companion/me','//evil.test','/companion/../live-memory/review','/companion/me?x=1','/people'):
   self.assertFalse(allowed('GET',path))
  self.assertFalse(allowed('DELETE','/companion/save'));self.assertTrue(allowed('GET','/p/'+'a'*32))

if __name__=='__main__':unittest.main()
