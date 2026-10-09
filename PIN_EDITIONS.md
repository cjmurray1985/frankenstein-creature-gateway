# PIN-scoped public editions

The unchanged legacy `scripts/live_audition/` and `creature_runtime/` trees serve the existing family login. The upgraded edition is a separate snapshot under `upgraded/`, with its own loopback HTTP and speech engine (8807/8808). Gateway cookies select the edition from a server-side SQLite record; URL parameters cannot select it. Existing cookies default to legacy.

## Activation

Set `UPGRADED_PASSWORD_HASH` in Render to the PBKDF2-SHA256 hash generated in the owner's private configuration. Keep `FAMILY_PASSWORD_HASH` unchanged. No PIN or hash is included in this repository. If the upgraded secret is absent, the existing family experience continues and the new login remains unavailable.

The new edition includes calibrated virtual servo motion, coordinated gaze and head attention, revised emotional cues, silent performance studies, synthetic visitor scenarios, and isolated rehearsal memory. Rehearsal memory is process-local and can be cleared; it does not identify real visitors, connect Archive, or call a Decisions service. Physical Pi, Shelly, microphone-device routing and camera observation remain local and are not exposed by this deployment.

## Release checklist

- Owner reviews this feature PR before merge, as required by the existing release policy.
- Required Tests and container build check passes.
- Set only the new secret; preserve legacy credentials, budgets and persistent disk.
- Confirm the Render deployed SHA and health after merge.
- Confirm both login editions and access restrictions before claiming availability.

## Rollback

Remove `UPGRADED_PASSWORD_HASH` to disable new logins without changing legacy access, or redeploy the prior main SHA. Existing upgraded cookies fail closed if their edition is unavailable. The additive SQLite edition table does not change the existing login table.
