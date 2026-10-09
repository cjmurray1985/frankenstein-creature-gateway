# KIRI Creature in the voice audition

The audition loads `assets/creature-kiri.glb`, derived from
`assets/creature-kiri/Frankenstein-KIRI-rigged.blend` at the project root.
The previous v9 GLB and authoring files remain available for rollback.

## Appearance

The actual KIRI surface and original 4096×4096 photographed color map supply
facial shape and appearance. The source OBJ, MTL and JPEG remain byte-identical
under `assets/creature-kiri/source/`. The intact Blender import is also preserved.
Derived cleanup removes disconnected islands, trims underside fragments and some
wire geometry, and compresses/smooths obvious posterior wig fins. Rigid alignment
levels the scan; it does not reshape the face into the previous authored model.
Some attached wire remnants, rough hair reconstruction and baked lighting remain.
This is a scan-derived preview, not a metrically calibrated mechanical twin.

The browser asset contains 167,695 triangles and is 9,016,544 bytes, versus
376,096 triangles and 12,670,624 bytes for v9. Three embedded images comprise the
4K scan map and two 256-pixel eye maps sampled from its existing photographed eyes.
No new AI texture or source-photo retouching was used.

## Motion

- M1 drives a localized Mouth_Open morph around the scanned lip aperture. The
  lower chin remains fixed; there is no detached chin or rotating puppet jaw.
  A recessed dark interior lies behind the opening. Neutral retains the small
  opening present in the scan.
- Two stationary eye surfaces sit behind the scanned lid rims. A browser material
  moves only the sampled iris/pupil appearance, excluding photographed eyelid
  edges; eye shell geometry, whites and lid outlines stay fixed. CH4/CH5 drive
  vertical gaze and CH6/CH7 horizontal gaze. Travel remains approximate.
- CH1/PWM5 drives neck flexion/extension and maps to pitch (0.16 rad at full
  normalized travel). CH2/PWM6 drives neck rotation/yaw (0.25 rad). CH3/PWM7
  drives neck lateral flexion/roll (-0.17 rad). The complete assembly shares
  the neck pivot; native Blender custom properties provide degree-based controls.
- CH8 now drives linked curved upper/lower eyelid surfaces in the browser.
  Upper lids supply most of the travel; lower lids rise slightly to meet them.
  The material color is sampled from nearby scanned skin. Automatic blinks,
  emotional narrowing and full closure are active. This is a visual approximation
  of the linked mechanism, not calibrated servo travel. CH1–CH3 now map to the
  confirmed neck flexion, rotation and lateral-flexion mechanisms; their visual
  travel remains uncalibrated.

The browser levels the bilateral eye-center vector to remove residual capture
yaw/roll and applies an additional -8-degree pitch correction. This is a rigid
presentation adjustment, not a change to scanned anatomy or the preserved Blender
authoring file. Curious rest now targets exactly zero gaze and CH1–CH3 neck offsets.
The movement study lasts 20 seconds and checks mouth, neck rotation/flexion/lateral
flexion, horizontal/vertical gaze, then linked-eyelid closure and reopening.
The eye material, rest correction and new eyelid surfaces are browser-specific;
they are not baked into the GLB or Blender asset.

The existing post-DSP PCM envelope and Web Audio timestamps drive the mouth.
Reference playback follows its media clock. Existing emotional direction shapes
supported gaze/neck posture; this is not phoneme recognition or measured acoustic
emotion extraction. Silence/stop returns the mouth morph to zero.

## Verification

Evidence is under `analysis/kiri-rig/`, with reproducible scripts under
`scripts/blender_creature/`: `prepare_kiri.py`, `rig_kiri.py`,
`check_kiri_poses.py` and `validate_kiri_glb.py`.

Front, both profiles, oblique, back and mouth-extreme renders were reviewed.
Earlier rejected fitting passes are preserved. Native eye extremes and neck
12-degree yaw / 8-degree pitch checks pass. Binary GLB checks establish finite
base/morph data, localized mouth movement, zero lower-chin/neck displacement,
four assembly children beneath the common neck and three embedded textures.

Fourteen JS audio/motion tests and eleven Python streaming/bridge tests pass.
Browser checks confirmed the loaded scan, both eye pivots, visible neck movement,
saved ElevenLabs reference playback with nonzero mouth influence, zero influence
after stop, and no browser errors. No fresh microphone/provider session was needed.
Renderer remains locally vendored Three.js r180; audio transport and voice settings
are unchanged. No physical device is controlled by this preview.

Eyelid verification (2026-09-20): browser full-closure review shows covered pupils,
reopening to curious rest (0.22), fixed eye-shell transforms and independent gaze.
Automatic blink peak reaches exactly 1.0; no browser errors. Sixteen JS tests pass.
Evidence: `analysis/kiri-eyelids/verification.json`.

Eye depth fitting (2026-09-20): both eye shells move forward by 0.0045 in
uncalibrated scan units along their local +Z axes before lid construction.
Their child lids follow the same placement. Bilateral oblique and steep-angle
browser review checked the rim fit; full closure still covers the pupils.
Gaze remains texture-only and the resting head correction is unchanged.

### Continuous mouth lining (2026-09-20)
The browser replaces the small recessed mouth insert with an unlit near-black cavity built from the actual 42-edge aperture boundary. UV seam vertices are welded only for boundary lookup; source topology is untouched. The cavity rim follows the same Mouth_Open morph as the lips and meets a recessed center, closing oblique sightlines into the head. The original insert is hidden in the browser. Original GLB/Blender files are unchanged.

### Resting lids and atmosphere (2026-09-20)
Curious lid closure is now 0.36 (previously 0.22), hopeful 0.27, engaged 0.32. Full blinks and more closed expressions retain their travel. The movement study uses the same resting lid value. Moody lighting defaults to reduced ambient fill, a warm upper-side key and cool rear edge; Moonlight and the original Studio setup are selectable, with 50–150% brightness. Lighting preferences persist locally. Scan texture retains its captured illumination, so relighting remains an approximation.

### Laboratory atmosphere and throat fade (2026-09-20)
The stage/page background is black. A shader dims the scan smoothly between rest-space heights −0.68 (visible throat) and −1.55 (black), in normalized scene units. It remains attached to the skin while orbiting or articulating the neck. The display stand is removed. Laboratory lighting uses cyan-green side illumination, a dim amber opposing lamp and a cool rear edge; independently smoothed fluctuations and occasional dropouts are optional. Reduced-motion preferences disable fluctuation. Brightness and Flicker controls persist under a new laboratory preference version. These effects do not alter audio or physical hardware.

### Occasional lightning (2026-09-20)
Laboratory lighting includes an independently switchable cool-white directional flash: one 80–120 ms pulse every 18–40 seconds, with randomized side/intensity and fast decay. Timing uses performance wall time so low frame rates cannot prolong a pulse. The black background and throat fade remain unchanged. Test lightning previews a pulse and reschedules the next automatic strike. Hidden pages and reduced-motion preferences suppress flashes; no thunder/audio is added.

### Visitor viewpoint and entrance (2026-09-20)
The camera is perspective, with a five-foot horizontal separation, an eight-foot creature and a five-foot-eleven visitor whose assumed eye line is four inches below their height. The normalized 3.7-unit head/neck is staged as two feet tall; its center is at seven feet and its virtual waist is at 4.2 feet. This yields a ~16.39° upward viewing angle. A presentation head mount tilts forward 0.28 radians and vertical pupil direction is biased −0.70 within the existing bounds. These are scenic assumptions, not scan measurements or new hardware commands.

On load, a virtual waist pivots from 85° forward to upright after a 0.45-second pause and 4.6-second eased rise. A shared material reveal and temporary wider framing prevent a brightly clipped head during approach. The original throat fade remains attached. Start audition skips to the settled view; reduced-motion skips the rise. Replay entrance is in the menu and unavailable during active audition.

### Reference-inspired underlighting and hooded eyes (2026-09-20)
The laboratory key is now muted green from below/front-left at (−1.8, −3.6, 3.2), power 1.4; ambient 0.07, rim 0.50 and amber fill 0.17 deepen the shadows. Existing independent flicker, lightning timing, reduced-motion handling and saved controls remain. Curious closure is 0.68, hopeful 0.58, engaged 0.63, wary 0.73, hurt 0.70, angry 0.77, withdrawn 0.80 and dormant 0.82. Full blinks still reach 1.0. Linear sclera color is (0.12, 0.13, 0.10), preserving photographed iris/pupil sampling and fixed shells. The source scan contains baked illumination, so this browser relighting remains approximate. Evidence: `analysis/kiri-underlight/verification.json`.

### Supine-to-seated entrance correction (2026-09-20)
The entrance now rotates from −90° at the virtual waist (head behind the hips, face upward) to 0°. The head rises and advances toward the visitor on that arc. Lens framing stays fixed throughout; the 0.28-radian downward head tilt eases in only over the final 35% of hinge progress. Reveal runs from progress 0.08 to 0.70, retaining darkness at the start. Duration, replay, audition skip, reduced-motion and settled viewpoint remain. This supersedes the earlier forward-bend/temporary-zoom description above.

### Entrance lightning cue and encounter controls (2026-09-20)
Menu is a labeled 44px hamburger icon. The transparent outlined CTA reads “Speak to the Creature”; connection/error/reset visibility behavior is preserved. A single existing lightning pulse is cued at 4.406 seconds (~0.64 seconds before the 5.05-second settled entrance). Random strikes wait until the entrance ends. Replay rearms the cue; Start/Reset skip it; Lightning off, non-laboratory lighting, hidden pages and reduced-motion suppress it.

### Weathered CTA visibility (2026-09-20)
Special Elite is served locally and preloaded. The transparent CTA uses dim gray-green lettering and a worn gradient border. HTML starts hidden; actual entrance completion releases the UI gate, replay closes it, and active-session hiding takes precedence. Reduced-motion and explicit skip complete the gate; model initialization failure allows voice-only access.

### Slow reveal and hard low light (2026-09-20)
The entrance-specific lightning cue is removed. Reveal now starts at 1.2s and eases over 5.6s, finishing at 6.8s after the existing 5.05s sit-up; CTA waits for full reveal. Laboratory flicker blends in over 6.8–8s. All lightning is suppressed during the entrance, with occasional ambient strikes rescheduled afterward. The laboratory directional key is at (−1.2, −5.5, 2), power 2.5; ambient 0.018, rim 0.20 and amber fill 0.035. A 2048px PCF shadow map adds harder cast shadows from the scan and eyelids. This supersedes the prior entrance cue.

### Eye readability and awakening (2026-09-20)
Key power 2.25/ambient 0.04 plus frontal fill (0, 0.2, 4), power 0.55 with a 60% flicker floor, soften the orbital darkness while retaining the low source and cast shadows. Intro overrides lid closure to 1 through full illumination at 6.8s, holds 0.2s, then eases open over 1.1s to the emotional pose. Completion/CTA is now 8.1s, followed by gradual flicker and later blink; reduced-motion skips the sequence. CTA border is hover-only, retaining a separate keyboard focus outline.

### Sculpted lids and earlier awakening (2026-09-20)
Browser lid meshes gain convex padding, a recessed fold and three rows of rounded edge thickness. Surface sampling is 48×18; roughness 0.74. Motion and eye placement are unchanged. Opening now starts at 5.8s, ends at 6.9s, overlapping the final illumination; CTA then appears and flicker blends in through 8.1s. This supersedes the 7.0–8.1s opening interval above.

### Camera-directed pupils (2026-09-20)
The previous −0.70 vertical gaze bias is removed. Each pupil is projected toward the camera in its own transformed eye space using the fixed ellipsoid and export UV mapping, with bounded emotional offsets retained. Eye shells/lids remain stationary relative to the head. Resting/curious lid closure is 0.58, hopeful 0.50 and engaged 0.55; entrance closure and full blinks remain.

Ambient thunder loop (2026-09-21): the synthetic entrance crack/rumble is replaced by `assets/mixkit-thunderstorm-and-rain-loop-2402.wav`, a user-supplied 44.1 kHz stereo loop. It starts as soon as the authenticated laboratory page initializes, retries after the first user gesture if autoplay is blocked, fades to a 0.001 HTML-audio gain on coarse/mobile pointers and 0.012 on desktop, and loops under the encounter. The old one-shot synthesized cue remains disabled; voice playback still uses its own audio path and is not mixed through this bed.

### Invitation transition polish (2026-09-20)
Eye opening now spans 4.9–6.0s, before full light at 6.8s. Only after full entrance completion does the CTA fade in over 1.1s. Its worn border fades over 400ms on hover in/out. Replay resets visibility; reduced-motion skips CSS transitions.

Eyelid timing adjustment (2026-09-20): opening now spans 3.9–5.0s, exactly one second earlier. Light/CTA timing remains unchanged.

Framing refinement (2026-09-20): resting vertical half-span 1.66, aim target Y=−0.03; width constraint remains 1.10×height/width. Visitor position unchanged. This yields a larger portrait with ~30px crown clearance in the inspected 645×817 viewport.

Silhouette hold (2026-09-20): reveal reaches 0.16 at 4.0s and holds through the 5.05s seated arrival until 5.7s. Full lighting eases in over 5.7–8.5s, then laboratory flicker blends in through 9.7s. CTA waits for completion at 8.5s. Eyelids retain their 3.9–5.0s opening; reduced-motion skips the sequence. This supersedes the earlier 6.8s full-light timing.

Dimmer laboratory preset (2026-09-20): key 1.58, ambient 0.028, rim 0.14, frontal fill 0.44. Directions and timing unchanged; fill is reduced less to preserve eye readability.

Eye texture correction (2026-09-21): both iris/pupil fields now sample the clean right-eye photograph so the cloudy left-eye capture no longer appears. The sclera is lifted modestly for visibility, with three thin, low-contrast red vessel strokes at each outer corner. Generated eyelid shells are multiplied darker and shifted toward a muted brown-violet, while their geometry, closure travel and eye-contact projection remain unchanged.

Mobile audio/menu correction (2026-09-23): the ambient thunder loop now starts and remains at 0.001 volume on coarse/mobile pointers (0.012 on desktop), keeping it effectively muted beneath the voice without a gesture-triggered fade-in. During connecting, connected, and rendering phases it is hard-muted so the live Creature voice cannot be masked by the storm bed. All encounter errors now remain on the stage warning and close any open dialog; the menu is user-controlled and never opens just to report an error. This prevents mobile conversation failures from interrupting the visitor with a menu popup.

Ambient thunder removal (2026-09-23): Christopher requested that the storm bed be removed entirely after device playback remained too loud during conversation. The WAV asset, HTML audio element, autoplay/retry listeners, entrance hook, and static serving entries were deleted; the Creature voice remains on its independent ElevenLabs/OpenAI audio path.

### Emotion-directed virtual body language (2026-09-27)
The browser motion core now treats the eight conversation emotions as coordinated body-language profiles rather than a single gaze offset. Each profile supplies resting gaze, linked-lid closure, neck flexion/rotation/lateral targets, jaw emphasis, and a normalized shared `LED_BOLTS` signal. Curiosity acquires with the eyes before the neck follows; hope opens and gently advances; engagement holds direct contact; wariness narrows and turns aside; hurt lowers and averts; anger advances with a firmer stare and brighter visual LED proxies; withdrawal looks away and becomes unusually still. Live speech can add one restrained phrase-level neck emphasis on an audio-envelope rising edge, with a refractory interval so syllables do not drive a mechanical chatter. The two laboratory point lights are visual stand-ins for the shared bolt signal only and are not calibrated PWM outputs. Native GPT-Live sessions now expose the server's current relational emotion through the local status poll at 350 ms, while ElevenLabs streams retain their pre-audio direction message. Added a deterministic `Run emotional arc` browser preview for dormant → curious → hopeful → engaged → wary → hurt → angry → withdrawn → curious. No physical signal, actuator, Pi, GPIO, wiring or power operation occurred; all normalized values remain virtual and bounded.

### Semantic conversational cues (2026-09-27)
The sustained emotion profiles now have a separate short-lived cue layer for readable social gestures. `think` lifts gaze and slightly turns the head as if searching for a thought; `agree` gives a small nod; `disagree` gives a bounded side-to-side motion; `listening` leans in; `surprise` briefly opens the lids and raises the gaze; `repair` acknowledges a correction; and `withdraw` turns away. Cues use only the confirmed eye, eyelid, CH1/PWM5, CH2/PWM6, CH3/PWM7 and shared `LED_BOLTS` virtual channels, are envelope-shaped and auto-expire. Conservative server phrase matching selects a cue from the Creature's response, while visitor transcript input creates a listening cue and the first response token creates a thinking cue. The browser status includes the active cue for inspection. No hardware values are calibrated or emitted.

### GPT-Live credit exhaustion diagnosis (2026-09-27)
The localhost page remained healthy but conversation start returned the provider's `429 credit_balance_exhausted` response from the OpenAI API project. The server event log recorded three creation failures; this is distinct from stale audition tokens, microphone permission, invalid voice/style/SDP and local WebRTC setup. The browser now preserves the provider error code and displays an actionable billing message. Add credits or point the server at a funded Live-enabled API project/key before attempting another conversation. No hardware or actuator path is involved.

### GPT-Live access verification after credit reload (2026-09-27)
After Christopher replenished the OpenAI API project, the local bridge was restarted and localhost refreshed. Cinder with labored breath and naturalized-clear DSP created a GPT-Live session successfully, reached `Listening`, produced Creature output, and ended cleanly after 15 seconds. The server status recorded `created` followed by `session.closed`; the page is ready for the next user-started encounter. No hardware or actuator path was involved.

### Supported in-session emotion context (2026-09-27)
The first replacement attempt used `session.update`, but the current GPT-Live model rejected `session.instructions` as an unknown parameter. The subsequent `conversation.item.create` experiment was rejected by the GPT-Live event allowlist. Emotion changes now use the supported quiet `session.thinking.append` event with `delegation_id: null` and the current relational guidance; the original `live_instructions(style)` remains untouched in the session. The status/cue layer continues to drive the virtual eyes, lids, neck and shared LED proxy. Provider errors retain bounded code, message, parameter and type fields. A deterministic watch test confirms that a friendly transcript emits a HOPEFUL thinking append. No hardware or actuator path was involved.

### Quiet emotion-context path (2026-09-27)
After the GPT-Live `session.update` and `conversation.item.create` rejections, the bridge now uses `session.thinking.append` for quiet emotion context. This avoids spoken interruption while preserving the session's original Creature prompt. The virtual emotion/cue path remains independent and inspectable.

### Emotion cue observability and mapping correction (2026-09-27)
The latest live session did trigger `engaged`, but its body-language profile is deliberately restrained; short cues such as `think` and `listening` can expire before the menu is opened. The deterministic emotion arc visibly reports its active state and non-neutral normalized mechanism values. Corrected a stale PCA label regression back to the confirmed virtual map: CH1/PWM5, CH2/PWM6, CH3/PWM7, CH4/PWM0, CH5/PWM1, CH6/PWM2, CH7/PWM3 and CH8/PWM4. No hardware or actuator path was involved.
# Expressive emotion presentation toggle (2026-09-27)

The browser audition now exposes a checked-by-default `More expressive emotion` toggle. It is a presentation-layer comparison: enabled mode amplifies the semantic eye, linked-lid, neck and shared LED-bolt proxy changes, plus brief think/agree/disagree/listening/surprise/repair/withdraw cues, while leaving voice synthesis, local DSP, mouth audio envelope and latency untouched. Off returns to the restrained profiles. The normalized virtual channels remain clamped and the scene diagnostics report `expressive`; the control persists across a stop/reset and is applied to reference playback and all live output paths. This remains a virtual simulation only; no PWM, hardware, GPIO, Pi, wiring or power operation occurred.
# Live emotion observability correction (2026-09-27)

The first expressive-toggle pass still allowed a real encounter to look neutral. The cause was twofold: the engaged profile was too close to curious, and a queued ElevenLabs segment could overwrite a newer server-poll direction with its stale start-state emotion. Engaged now has clearly narrower linked lids, a slight lean/turn toward Christopher and a slow side-to-side attention scan; wary and hopeful are more distinct as well. The browser no longer lets segment metadata override the live status bridge. Kindness vocabulary was broadened conservatively, and completion of a first ordinary exchange now earns visible direct engagement, so a neutral conversation does not remain in the opening curious pose. The PCA map and virtual-only normalized bounds are unchanged.

# Readable emotional body language pass (2026-09-27)

The virtual presentation now includes five additional readable states: attentive,
suspicious, startled, vulnerable and relieved. Attentive holds a direct, quiet
gaze; suspicious leads with a side-eye and small bilateral eye offset; startled
opens the gaze, recoils and briefly accents the shared LED proxy; vulnerable
looks upward with a slight tilt; and relieved releases tension toward center.
Normal attention remains bilaterally paired. New high-confidence transcript
phrases, dialogue guidance and semantic cues (`startle`, `suspicion`, `plead`,
`relief`) feed these states without claiming acoustic emotion recognition.

Semantic cue envelopes now last approximately 1.0–1.45 seconds, long enough to
register at five feet while still expiring automatically. The deterministic arc
exercises all new states. Browser-only neck presentation multipliers are now
0.28 rad flexion, 0.42 rad rotation and 0.30 rad lateral flexion at normalized
full scale; these are visibility multipliers, not servo/PWM calibration. All
channels remain normalized and clamped, M1 remains audio-driven, and no physical
signal or actuator command is emitted.


### Local hardware twin first fit (2026-10-07)

The local hardware-enabled page now defaults to the iPhone-observed first fit. CH4/CH7 affect the viewer-right eye; CH5/CH6 the viewer-left. Horizontal pupil direction and yaw are reversed relative to the earlier presentation, neck travel is reduced, and eyelid closure uses a nonlinear curve. The earlier presentation is available with the fit toggle. Held-position controls are under Mechanisms & fidelity. Amplitudes and neck angles remain visual estimates from a single camera; smoothing mirrors nominal Pi settings, not measured feedback. See `docs/workstreams/hardware-lab/experiments/virtual-twin-calibration.md` for raw recordings, derived sheets and live connection failures. Mouth and emotional profiles are unchanged.


### Straight-on three-pass refinement (2026-10-07)

Three additional recorded gauntlets began from CH1–CH7=1492 µs and CH8=1897 µs. PCA register readback confirmed the programmed resting widths (approximately 1494/1899 µs at nominal 50 Hz, not measured waveform feedback). Fitted mode removes fixed scan skin only inside the moving exposed orbital aperture, slightly increases eye height and reduces horizontal pupil span. The nonlinear lid curve retains visually closed 1600/1748, partly open 1897 and fully open 2100 µs. A straight-on comparison checkbox removes visitor-camera/presentation-tilt bias while comparing. Lighting, skin detail and exact 3-D motion remain approximate. Evidence and all three critiques are in the linked virtual-twin experiment record; no physical rest or pulse bound changed.
