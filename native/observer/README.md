# LOCKSTEP RawMIDI observer (experimental source)

This is the first native add-in **prototype**, not a quantiser and not an installable MPC package.

## What it does

- Exports interposers for `snd_rawmidi_open`, `snd_rawmidi_read`, and `snd_rawmidi_close`.
- Calls the next implementation exactly once and returns its result.
- Is inactive unless the process executable is exactly `/usr/bin/MPC` and `LOCKSTEP_DIAGNOSTIC_ENABLE=1`.
- When enabled with no target name, records the ALSA RawMIDI names opened by MPC but captures no MIDI bytes.
- Captures read bytes only when `LOCKSTEP_TARGET_ALSA_NAME` exactly matches the name passed to `snd_rawmidi_open`.
- Sends bounded records to a background logger at `/tmp/lockstep-observer.log`; the read hook does not perform file I/O.
- Never writes MIDI, suppresses notes, injects notes, changes audio, or changes transport.

## Two-stage investigation

1. **Name discovery:** enable the observer but leave `LOCKSTEP_TARGET_ALSA_NAME` unset. Review the OPEN records to identify candidate RawMIDI names. No MIDI payload bytes are captured in this mode.
2. **Targeted observation:** only after the MPC Pads port has been positively identified, set `LOCKSTEP_TARGET_ALSA_NAME` to that exact ALSA name. The observer then copies bytes returned by MPC's own read call for that handle.

The name shown in the MPC UI may not be the ALSA name. Do not guess it. If the port is implemented through ALSA Sequencer or an Akai-specific route, this RawMIDI observer will not see it.

## Important limitations

- This source has not been tested inside MPC OS or against the Live III's actual ALSA library.
- It is not yet integrated with the Open MPC add-in loader or its package/install/uninstall format.
- Hook coexistence with Skipback, MPC Remote, and other `LD_PRELOAD` add-ins is untested.
- Handle lifetime/concurrent close behaviour, event completeness, timing overhead, and log reliability require further host and device testing.
- A read result larger than the capture buffer is explicitly marked truncated; queue overflow is counted in the log.
- The log is written to temporary storage at `/tmp/lockstep-observer.log`; persistence is not promised.
- This hook observes only ALSA RawMIDI. It does not hook ALSA Sequencer.

## Build

The manually triggered workflow `.github/workflows/native-observer-build.yml` cross-compiles a Gen2/aarch64 shared library and uploads it as a GitHub Actions artifact. The artifact is a raw `.so`, **not an MPC add-in package**. Do not install it on the MPC.

The source uses an opaque ALSA handle declaration and does not require ALSA development headers to compile. Runtime ABI compatibility still must be verified on the target.

