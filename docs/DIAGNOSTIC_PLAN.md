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
