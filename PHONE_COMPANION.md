# Public phone companion relay

Adds trusted-HTTPS profile routes to the existing encounter origin. The encounter login, voice engines, existing secrets and persistent disk are unchanged. Visitors scan existing high-entropy QR links and use the local profile password flow; a QR is not identity proof and an unclaimed profile still has first-claim setup.

The laptop initiates WSS `/companion-relay`. An Ed25519 challenge authenticates against `scripts/family_encounter/phone-relay-public-key.txt`. Only this public verification key is deployed. The signing key, encrypted profile database, passwords, recognition vectors and admin tools remain local. Relay payloads pass through Render in memory; application access logging is disabled and no relay payloads are persisted. Render terminates public TLS.

Only GET `/p/TOKEN` and `/companion/app.js`, `style.css`, `me`, `portrait`, `duplicates`, plus POST `claim`, `auth`, `lock`, `save`, `merge-request` are forwarded. No public `/people`, camera, encounter review/reset, local-certificate download, arbitrary URL or provider endpoints. Exact Origin applies to phone POSTs; backend cookies/CSRF/password gates remain authoritative. Eight in-flight requests, 3MB request/5MB response limits and bounded timeouts prevent unbounded buffering. Agent loss fails closed with503 and pending requests are cleared. The agent independently validates paths/methods and always uses fixed loopback8792.

The local connector requires a trusted WSS origin and retries with bounded exponential backoff. After deployment, switch the companion public base and QR payloads to the Render origin. Do not move the existing database or ship the local application tree wholesale. The local certificate can remain inactive for fallback; visitors must not install it for public links.

Validation: relay route/Origin rejection, bad signature, replay-resistant challenge, duplicate connector rejection, allowed request/cookie forwarding, large body limit, disconnect recovery and unchanged browser-side encounter suite. Local gateway compilation and required deployment CI must pass before release.

Rollback: deploy the prior main commit, stop the local public relay and restore the local companion public base. This introduces no destructive data migration.
