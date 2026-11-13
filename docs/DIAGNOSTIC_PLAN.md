# LOCKSTEP diagnostic prototype plan

**Purpose:** determine whether MPC Live III pad events are visible to an add-in, without changing playback.

**Current state:** design only. No diagnostic source code, binary or installer has been created. Nothing should be installed on the MPC yet.

**Confirmed target:** Akai MPC Live III running MPC OS 3.10.1 (confirmed by the user on 2026-11-13). Treat this as the baseline for compatibility research; re-check the version before any future device test.

## Safety rules

- Read-only observation: no MIDI writes, note suppression, note injection, audio processing, transport control or filesystem changes on the MPC beyond an explicitly selected diagnostic log.
- Every intercepted API call must call the original function with the original arguments and return its original result unchanged.
- If a hook cannot resolve the original function, initialization fails safely and the hook must not interfere with MPC.
- Diagnostic logging must be bounded, rate-limited and performed away from real-time audio callbacks.
- The add-in must be disabled by default unless an explicit diagnostic enable flag is present.
- Include a documented uninstall/recovery path before any device test.
- Do not test during a performance or on a device containing the only copy of important projects.

## Questions the prototype must answer

1. Which ALSA raw-MIDI input handles does MPC open for its internal controller?
2. Do pad presses produce data on any of those handles?
3. Can we distinguish pad note-on, pad note-off, velocity, channel, repeated hits and simultaneous pads?
4. Are events timestamped at the input boundary, or can sufficiently accurate monotonic timestamps be captured in the read hook?
5. Does observing the port leave normal pad playing completely unchanged?

## Test matrix

| Test | Action | Evidence sought |
|---|---|---|
| Idle baseline | Launch MPC and wait without touching controls | Port opens, background traffic |
| Hardware controls | Press a few non-performance buttons | Identify controller messages |
| Single pad | Tap one pad at several strengths | Candidate pad event and velocity |
| Release behaviour | Hold then release a pad, if the pad mode supports it | Note-off or equivalent release event |
| Repeated hits | Tap one pad rapidly | Distinct events and ordering |
| Chords | Tap two or more pads together | Event separation and timing |
| MPCe gestures | Test only if safe and relevant | Whether gesture data is separate |
| Bypass comparison | Compare normal operation with diagnostic disabled/enabled | No changed playback behaviour |

Record the exact MPC model, OS version, selected track/program, port identity and test conditions with each log. Do not publish logs containing personal device identifiers or unrelated MIDI controller data.

## Go/no-go criteria

**Go to a separate interception feasibility prototype only if:**
- pad events are positively identified;
- note-on and release semantics are understood;
- velocity and simultaneous events are preserved;
- observation has no audible or operational side effects;
- a safe way to suppress the original event and reinject one corrected event has a credible technical basis.

**No-go / revise scope if:** pad events are not visible through the observed path, events cannot be distinguished reliably, or reinjection cannot be achieved without duplicate notes or unstable MPC behaviour. In that case, investigate another internal event interface or narrow LOCKSTEP to a supported external-MIDI workflow rather than claiming internal-pad support.

## Build and device-testing constraints

The Open MPC build guide documents a Linux-style shell, Git, Python 3 and Docker; on Windows it specifically describes Ubuntu under WSL 2. The user has chosen not to install Linux, so do not ask them to set up WSL. **A suitable upstream remote-build workflow has now been found.** Open MPC provides a reusable GitHub Actions workflow (`.github/workflows/addin-release.yml`) that runs on `ubuntu-latest`, checks out the add-in and toolchain, sets up QEMU for ARM/ARM64 builds, packages Gen2/aarch64 output with `release_addin.py`, and runs `catalog_check.py`. It can upload a ZIP as a run artifact in `dry_run` mode without creating a release. This is a much better fit than asking the user to install WSL or Linux. See https://github.com/open-mpc/mpc-vst-plugins/blob/main/.github/workflows/addin-release.yml.

This establishes a practical remote-build mechanism, but **not yet a working LOCKSTEP build**: no LOCKSTEP source tree or build command exists, and the reusable workflow has not been called from this repository. Once a minimal diagnostic source exists, add a manually triggered workflow that pins the upstream toolchain revision, builds only Gen2/aarch64, runs upstream package validation, and uploads only a diagnostic artifact. Do not add device deployment or auto-install steps.

Open MPC's add-in guide describes a Gen2 Live III case where the loader drop-in falls back to `/run` (temporary storage) and must be recreated after reboot. The same guide has a separate, later note for MPC OS 3.10.1 with Akai user access enabled on a Key 37, where a writable `/etc` overlay can persist the drop-in. That 3.10.1 note is specifically evidenced on a Key 37, not on the user's Live III, so we must not assume it resolves Live III persistence. A community restore patch is reported tested on a Live III running MPC OS 3.10, but its applicability to this user's 3.10.1 setup must be checked. This is additional system-level complexity, not a reason to install anything now. Any future package must follow the current catalog's supported installer/uninstaller and recovery requirements.

The Skipback example is useful but narrower than LOCKSTEP needs: it hooks the controller's `Private` ALSA raw-MIDI port and logs hardware-button presses (documented as note-on messages). It does **not** demonstrate that performance-pad hits appear on that port. Pad-event visibility remains unproven.

## Decision

Do not write the actual note-quantising hook until the read-only diagnostic establishes where pad events travel and a safe reinjection path is understood.


## Newly identified hook-interaction risk (2026-11-13)

Two existing add-ins now provide relevant evidence and a compatibility warning:

- MPC Skipback hooks ALSA raw-MIDI functions including `snd_rawmidi_close`, `snd_rawmidi_open` and `snd_rawmidi_read` to observe controller messages.
- MPC Remote also hooks `snd_rawmidi_open`, `snd_rawmidi_read` and `poll` for controller-button input. Its catalog entry explicitly warns that it may not work alongside Skipback because the first add-in to replace a function receives the call; another add-in sees it only if the first forwards the call.

Therefore a LOCKSTEP diagnostic that interposes on the same functions could conflict with either add-in unless its hook chain is designed and tested carefully. For the first device experiment, the safest plan is to avoid having either of those add-ins installed/running, and test only the observer (after a recovery plan and explicit user approval). We must not ask the user to remove existing add-ins without first checking what is installed and explaining the consequences.

The diagnostic's hook should resolve and call the next implementation exactly once, preserve return values and errors, avoid blocking/allocating/logging synchronously on MPC's MIDI read path, and write bounded diagnostic records from a separate worker or similarly safe mechanism. A read-only observer is still executable code inside MPC and can still crash or stall it; "read-only" does not mean risk-free.

## Immediate engineering sequence

1. Inspect current upstream Skipback and MPC Remote hook implementations and document their chaining behavior.
2. Decide whether a safe, compatible ALSA hook can be written without assuming pad events use the controller port.
3. Create a minimal source skeleton with no MIDI injection, no event suppression, and a disabled-by-default activation gate.
4. Add a manually triggered GitHub Actions dry-run build using the upstream reusable Gen2/aarch64 workflow, pinned to a specific upstream commit.
5. Run host-side tests and package validation. No device installation until the source review, recovery procedure, and user approval are complete.


## Upstream source review (2026-11-13)

A closer review of the existing MPC Remote and Skipback projects makes the current boundary clearer:

- MPC Remote explicitly lists **pressing pads and Q-Links as not included**. Its documented midi_listen feature collects what MPC sends back to its ALSA sequencer input port; that is not evidence that internal pad hits are exposed there.
- MPC Remote's documented MIDI output port is for sending notes/messages into MPC after a user enables that port for a track. This is an external MIDI input route, not proof of transparent interception of the built-in pads.
- Skipback's controller observer is specifically a passive reader of the controller's Private raw-MIDI port. Its documented messages are hardware-button note-ons/releases. It does not establish that performance pads use that same port.
- Both projects are useful engineering references for add-in loading and bounded background work, but neither supplies the missing pad-event path.

**Implementation decision:** do not create a snd_rawmidi_read observer on the assumption that it will see pads. It might only record hardware-button traffic, producing a misleading diagnostic. Before writing that hook, we need reliable evidence identifying the actual pad event interface on MPC Live III OS 3.10.1, or a safe way to inspect candidate MIDI/ALSA interfaces without changing the running system. The first prototype remains unbuilt.

This is a meaningful narrowing of the hypothesis, not a failure of the project: external MIDI quantisation may still be a separate feasible route, but it does not satisfy the original requirement to quantise built-in pad hits transparently.
