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
- NECK_SIDE drives coupled yaw/lean (0.25 / -0.17 rad at full normalized travel).
  NECK_FB drives pitch (0.16 rad). The complete assembly shares the neck pivot.
  Native Blender custom properties provide degree-based yaw and pitch controls.
- CH8 now drives linked curved upper/lower eyelid surfaces in the browser.
  Upper lids supply most of the travel; lower lids rise slightly to meet them.
  The material color is sampled from nearby scanned skin. Automatic blinks,
  emotional narrowing and full closure are active. This is a visual approximation
  of the linked mechanism, not calibrated servo travel. CH1–CH3 remain unresolved.

The browser levels the bilateral eye-center vector to remove residual capture
yaw/roll and applies an additional -8-degree pitch correction. This is a rigid
presentation adjustment, not a change to scanned anatomy or the preserved Blender
authoring file. Curious rest now targets exactly zero gaze and neck offsets.
The movement study lasts 20 seconds and checks horizontal/vertical gaze, followed
by a slow eyelid close, a one-second closed hold, and reopening.
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

Ambient thunder loop (2026-09-21): the synthetic entrance crack/rumble is replaced by `assets/mixkit-thunderstorm-and-rain-loop-2402.wav`, a user-supplied 44.1 kHz stereo loop. It starts as soon as the authenticated laboratory page initializes, retries after the first user gesture if autoplay is blocked, fades to a 0.035 HTML-audio gain and loops under the encounter. The old one-shot synthesized cue remains disabled; voice playback still uses its own audio path and is not mixed through this bed.

### Invitation transition polish (2026-09-20)
Eye opening now spans 4.9–6.0s, before full light at 6.8s. Only after full entrance completion does the CTA fade in over 1.1s. Its worn border fades over 400ms on hover in/out. Replay resets visibility; reduced-motion skips CSS transitions.

Eyelid timing adjustment (2026-09-20): opening now spans 3.9–5.0s, exactly one second earlier. Light/CTA timing remains unchanged.

Framing refinement (2026-09-20): resting vertical half-span 1.66, aim target Y=−0.03; width constraint remains 1.10×height/width. Visitor position unchanged. This yields a larger portrait with ~30px crown clearance in the inspected 645×817 viewport.

Silhouette hold (2026-09-20): reveal reaches 0.16 at 4.0s and holds through the 5.05s seated arrival until 5.7s. Full lighting eases in over 5.7–8.5s, then laboratory flicker blends in through 9.7s. CTA waits for completion at 8.5s. Eyelids retain their 3.9–5.0s opening; reduced-motion skips the sequence. This supersedes the earlier 6.8s full-light timing.

Dimmer laboratory preset (2026-09-20): key 1.58, ambient 0.028, rim 0.14, frontal fill 0.44. Directions and timing unchanged; fill is reduced less to preserve eye readability.

Eye texture correction (2026-09-21): both iris/pupil fields now sample the clean right-eye photograph so the cloudy left-eye capture no longer appears. The sclera is lifted modestly for visibility, with three thin, low-contrast red vessel strokes at each outer corner. Generated eyelid shells are multiplied darker and shifted toward a muted brown-violet, while their geometry, closure travel and eye-contact projection remain unchanged.
