# Creature family deployment workflow

The service is deployed from this private Git repository. Follow the release policy in `docs/render-deployment-strategy.md` in the project workspace. Do not place provider credentials, family password hashes, visitor transcripts, Archive records, screenshots, camera frames, or `.env` files in Git.

## Release path

- Feature branch and pull request to `main`; GitHub requires the `Tests and container build` check and resolved conversations. The owner reviews the PR checklist before merging. Independent approval is not enforced while this repository has only one collaborator with write access.
- Render PR previews are manual (`[render preview]` in the PR title), short-lived, and use an independent preview store plus test-only credentials. Production disk data and `sync: false` secrets are not copied. Close previews after review; idle environments expire after three days.
- A reviewed merge to `main` deploys through Render only after CI passes (`autoDeployTrigger: checksPass`). Never use the production family site as the preview environment.
- Schedule production deploys between encounters. This service has a persistent disk and a single instance; expect possible interruption. After deploy, check `/healthz`, login, mobile page, DSP, emotion updates, a complete test encounter, and session shutdown.
- Roll back to the last known-good Render deploy if health or smoke checks fail. Record the deployed SHA and result in the project context.

The CI workflow exercises existing JavaScript unit tests, Python compilation, and a Docker build. It does not contact OpenAI or ElevenLabs and does not publish an image. Render Preview environments must receive only test credentials; the production `sync: false` secrets are intentionally not copied into previews. `PUBLIC_ORIGIN` may be omitted in a preview because the gateway uses Render's `RENDER_EXTERNAL_URL` fallback.
