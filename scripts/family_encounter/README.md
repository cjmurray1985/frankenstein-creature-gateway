# Family encounter deployment

Status: implemented and locally security-tested; NOT published. The existing local audition remains on localhost:8767. Protected local preview: localhost:8772. No new paid conversation was opened during testing.

## Hosting

Deploy one always-on Docker web service with a persistent disk. The prepared Render blueprint uses a paid Starter service and 1GB disk. An owner-created hosting account/billing setup and a private source repository (or container registry) are still required. No account was created or charged.

1. Generate the clean bundle with `python scripts/family_encounter/package.py`. Use only `analysis/family-encounter/deploy/` as the private repository/build context. Do not upload the whole electronics project, local home directory, Keychain, or credentials.
2. On Render, deploy the blueprint from that private repository. Set runtime secrets `OPENAI_API_KEY`, `ELEVENLABS_API_KEY`, `FAMILY_PASSWORD_HASH`; set `PUBLIC_ORIGIN` to the assigned HTTPS origin without a path. The selected family password has already been hashed into the private local file `~/.config/frankenstein-family/password.hash`. Transfer its contents through the provider secret UI; do not commit it.
3. Keep exactly one instance and mount a persistent, writable directory at `/var/lib/creature` owned by UID 10001. The sqlite counters must survive restarts; do not use ephemeral storage or multiple instances. Only the gateway port 10000 is exposed. The voice engine ports 8767/8768 bind loopback and must never be independently exposed.
4. Check the HTTPS login, microphone permission, a complete conversation, interruption, full five-minute server cutoff and logout on the actual host before sharing. Provider networking/voice behavior and Docker image build have not been verified here (no Docker daemon is installed).
5. Set the journal's server environment `FAMILY_ENCOUNTER_ORIGIN` to the verified HTTPS origin, then publish the journal's prepared header link. Its `/encounter` route returns a closed-laboratory page until configured; it never points public visitors at localhost. Current Sites connector reports `Sites is not yet enabled for this workspace`; publishing remains blocked until that access is restored.

Provider setup references: https://render.com/docs/web-services, https://render.com/docs/disks, https://render.com/docs/configure-environment-variables, https://render.com/docs/websocket.

## Access and usage limits

- Password verified only by the gateway with salted PBKDF2-SHA256 (600,000 iterations). No plaintext password or hash is shipped in client assets or deployment bundle.
- Opaque eight-hour login cookies: HttpOnly, SameSite=Strict, Secure for HTTPS. CSRF checks and exact Origin/Host checks cover mutations and speech sockets. Auth precedes assets, status, session creation, stop and WebSocket upgrade. Lock the laboratory revokes the login.
- Five login attempts per connecting IP per 15 minutes; twenty attempts globally per 24 hours. Behind a reverse proxy, connections may share the per-IP bucket; forwarded headers are intentionally not trusted. Attempts include successful logins, so persist the eight-hour cookie instead of repeated signing in. A short shared password is not a guarantee against disclosure or eventual guessing.
- One active family encounter at a time; only its owner can send speech, stop it or read its state. Four starts per hour and twenty per 24 hours globally, stored on disk. Failed provider attempts also consume a start reservation. Existing server watchdog closes sessions after five minutes. Twelve text streams per session; 1,200 characters per stream; bounded frame size and stream lifetime. These bound usage rather than guarantee a dollar bill.
- Provider keys stay in the internal voice engine. The browser receives only the WebRTC SDP answer, never provider session secrets. No open-ended provider proxy, model selection, tool choice, URL fetch, or arbitrary asset path is exposed. OpenAI frontend data-channel permissions allow only closing and instruction append; session/delegation updates and explicit response creation are denied at provider startup. This uses the official Live create-session client.data_channel allowlist (https://developers.openai.com/api/reference/resources/live/methods/create).
- The OpenAI media connection itself is WebRTC; after authenticated creation it is controlled by the existing trusted sideband watchdog. Production verification of cutoff is a release gate, including provider/network failure behavior. Set provider-level project spend limits as a separate ceiling.
- Existing local audition remains loopback-only. Gateway development HTTP is accepted only for localhost/127.0.0.1; public configuration must use HTTPS.

## Tests

`uv pip install --python .venv/bin/python -r scripts/family_encounter/requirements.txt`

`.venv/bin/python -m unittest tests.test_family_encounter tests.test_live_audition -q`

Tests use a fake upstream, exercise anonymous access rejection, invalid/expired/revoked sessions, cookie/CSRF behavior, ownership, persistent quotas and an actual local WebSocket audio bridge. No paid provider calls are made.

## iPhone / mobile web

Open the hosted HTTPS link directly in Safari, sign in, wait for the entrance and tap **Speak to the Creature**, then allow microphone access. `localhost:8772` is only the Mac preview; it does not reach the Mac from an iPhone. A plain HTTP LAN address cannot provide the required secure microphone context. The page remains password protected on phones, with the same server-side limits.

The layout accommodates portrait/landscape, safe-area insets and dynamic browser toolbars. Touch devices use 1.5× maximum render resolution and 1024px shadows. Audio unlock begins in the start tap; permission/audio failure restores retry. Active encounters end on app switching/screen locking, and navigating away releases even a microphone permission result that arrives late. Returning requires a fresh tap. The reference button starts media directly from its tap for Safari playback policy.

Verified with Playwright WebKit 26.5 in iPhone emulation at 320×568, 390×844, 430×932 and 844×390: authenticated page, textured 3D rendering, dialog fit/touch controls, portrait/landscape resize, reference media playback, normal entrance/CTA timing, and simulated permission-denial recovery; no browser exceptions. This is desktop WebKit emulation, not physical iOS or a live provider conversation. Physical iPhone microphone, speaker/Bluetooth routing, background interruption and production HTTPS/network behavior remain release checks. Evidence: `analysis/mobile-web/` in the source project.
