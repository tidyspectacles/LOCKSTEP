# LOCKSTEP feasibility research

**Status: promising interception lead found; internal pad-note path not yet proven.**

Last reviewed: 2026-11-13.

## What the public research establishes

1. Open MPC documents a separate add-in mechanism: a shared library loaded into the MPC process with `LD_PRELOAD`. This is distinct from a normal VST2 instrument or effect.
2. Open MPC's add-in documentation describes hooks around ALSA functions, including `snd_rawmidi_read` and `snd_rawmidi_write`.
3. The public MPC Skipback add-in provides a concrete example. Its README describes hooks around the controller's ALSA raw-MIDI port identified by its “Private” name, and observes hardware-button messages while passing normal MPC button presses through. The documented messages are hardware-button note events, not performance-pad events.
4. Skipback's README reports that its aarch64 build loads on a Gen2 MPC Live III. That is useful evidence that this add-in technique can run on the target hardware, but it is not evidence that pad notes are available through the same port.
5. Historical MPC controller research describes the internal controller as a USB-connected device with ALSA raw-MIDI ports. This supports investigating the controller MIDI path, but the exact Live III pad-note messages and port routing still need direct verification.

## The key unanswered question

Do physical pad presses arrive at MPC as MIDI data on the same ALSA raw-MIDI handle/port that the controller add-ins can observe, or are pad events delivered through a different interface or internal software path?

Even if the messages are visible, we must still establish whether an add-in can safely prevent the original note from reaching the instrument and schedule a replacement note without duplicate triggers, timing glitches or damage to normal MPC operation.

## Proposed safe proof-of-concept sequence

1. **Observe only.** Build a Gen2/aarch64 diagnostic add-in that logs raw-MIDI input from candidate controller ports. It must pass every read through unchanged and must not write MIDI, alter pad events, or change audio.
2. **Identify messages.** With a saved test project and no live performance, compare logs for idle, button presses, single pad taps, pad releases, velocity changes and MPCe gestures. Determine whether pad events are present, which port carries them, and their message format.
3. **Check timing and completeness.** Establish whether note-on and note-off (or equivalent events) are both visible, whether chords and repeated hits are distinguishable, and whether timestamps can be obtained accurately enough.
4. **Only then consider interception.** Design a separate prototype with a bypass switch and a reliable pass-through path. Test on a non-critical setup, with a recovery/uninstall route, before attempting any live note rescheduling.
5. **Prove reinjection.** Determine whether corrected events can reach the intended track/instrument through a supported route without triggering the original event as well.

## Important limitations and safety

- No LOCKSTEP code or installable build exists yet.
- No one has demonstrated internal pad-note interception or safe reinjection on the MPC Live III as part of this project.
- A VST2 MIDI generator or effect must not be assumed to transparently process the MPC's own internal pad events.
- Add-ins run inside MPC. A faulty hook can crash or prevent MPC from starting. The Gen2 add-in setup also has firmware-specific persistence details; this must be handled by the packaging and recovery plan.
- Do not install a diagnostic or experimental add-in on a primary production MPC until its code has been reviewed, tested offline, and a safe recovery procedure is ready.

## Research references

- Open MPC add-in design and installation rules (including Gen2 and 3.10.1 persistence notes): https://github.com/open-mpc/mpc-vst-plugins/blob/main/docs/ADDINS.md
- Open MPC plugin/add-in toolchain: https://github.com/open-mpc/mpc-vst-plugins
- MPC Skipback add-in (README and source demonstrate raw-MIDI controller-port observation): https://github.com/sd88me/mpc-addin-skipback
- MPC internal controller MIDI background research: https://github.com/TheKikGen/MPC-LiveXplore-libs

This note records a research lead, not a claim that the core LOCKSTEP feature is feasible or implemented.
