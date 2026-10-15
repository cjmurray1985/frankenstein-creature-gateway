# Automatic browser encounter memory

Scope: upgraded edition only. The legacy frontend/runtime trees are unchanged.

## Behavior

- A separate opaque 256-bit HttpOnly/Secure/SameSite=Strict cookie identifies a browser history across family logins. It is not visual or person verification.
- Memory is automatic; no opt-in or required name field. The menu explains browser scope and includes Forget me.
- New sessions hydrate only the visitor relationship and explicit facts, apply existing inactivity decay, and provide bounded quoted prior visitor statements to both Live and delegated character reasoning.
- The visitor name is no longer hard-coded to Christopher in this edition. Introductions and corrections remain optional.
- Checkpoints persist only server-observed visitor statements when the Creature starts replying. No audio or incomplete Creature output is stored. This is bounded visitor-statement continuity, not a complete transcript/archive of both sides.
- Repeated checkpoints in one session count as one encounter. Later sessions start from relationship residue rather than the last transient pose.
- Up to 24 explicit name/promise facts (latest name retained), eight recent visitor statements and 32 retrieval audit entries are retained per browser; maximum 4,096 browser profiles, with 365-day inactivity expiry. Empty/failed starts do not count as visits.
- Synthetic rehearsal profiles never enter real encounter memory.

## Storage and operations

Encrypted AES-256-GCM payloads live at `$STATE_DIR/visitor-memory/profiles.sqlite3`; a random encryption key is created once at `$STATE_DIR/visitor-memory/memory.key`. Directory is 0700, DB/key files 0600. The key and ciphertext share the existing persistent disk; this protects payload plaintext at rest but is not external key-management or protection from a host administrator. Back up/recover them together. Never regenerate/delete the key to repair a decryption error.

No new Render secret is required. Existing PIN hashes, voice credentials and state disk stay unchanged. A failed key/load preserves existing memory and blocks the upgraded voice start rather than silently overwriting it; legacy voice remains on its original process. Saving errors are reported in the memory inspector.

Forget me clears the encrypted payload, revokes the old profile generation, rotates the browser cookie and stops that profile's active conversation. Checkpoints cannot resurrect the revoked data. Shared-browser tabs use the same history; other browsers have separate histories. Logout locks access without deleting history. Clearing browser cookies starts a different history; forgotten tokens cannot retrieve old facts.

## Release status

Implementation and static syntax review are complete. Live provider return/name/forget acceptance has not been run. Review the PR and required CI before release. A deployed smoke check must confirm both PIN editions, memory endpoints and session behavior before claiming the full milestone accepted.
