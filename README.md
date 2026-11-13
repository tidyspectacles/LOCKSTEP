# LOCKSTEP

**A real-time MIDI quantiser concept for the Akai MPC Live III.**

LOCKSTEP aims to make live pad playing land on the MPC's musical grid by quantising incoming note events in real time.

> **Status: Early research / experimental.** The key technical challenge—reliably observing and rescheduling notes from the MPC's internal pads while preserving normal instrument playback—has not yet been demonstrated. LOCKSTEP is not currently a working MPC plugin, and no installable build is available.

## Project goal

Explore whether a standalone extension for the MPC Live III can:

- Quantise live pad notes and supported external MIDI input to the MPC clock.
- Offer selectable grid divisions such as 1/4, 1/8, 1/16 and 1/32.
- Preserve note pitch, velocity, MIDI channel and note duration.
- Keep chords together on the same quantise point.
- Work with the MPC's existing instruments and Drum Programs, rather than replacing their sounds.

The intended feel is simple: play freely, and have notes snap to the selected beat grid.

## Technical approach

The first task is to investigate the MPC's internal note-event path and the supported extension mechanisms available on MPC OS 3.x.

A normal VST2 effect's MIDI output cannot be assumed to feed notes back into the MPC host. The internal-pad interception and safe note reinjection required by LOCKSTEP are therefore an open research question. An experimental native add-in or another supported mechanism may be needed; feasibility must be proven on suitable test equipment before implementation is presented as working.

See the [feasibility research note](docs/FEASIBILITY.md), the [read-only diagnostic plan](docs/DIAGNOSTIC_PLAN.md), the [MPC pad-port research update](docs/MPC_PAD_PORT_RESEARCH.md), and the [external MIDI fallback plan](docs/EXTERNAL_MIDI_FALLBACK.md). The built-in-pad route and external MIDI route are being investigated separately.

## Initial development milestones

1. **Feasibility research** — identify where internal pad events are generated, how timing and transport are represented, and whether notes can be safely observed and rescheduled.
2. **Read-only diagnostic** — establish whether pad messages are visible without altering normal playback.
3. **Minimal prototype** — prove note-on/note-off handling and clock synchronisation without disrupting normal MPC operation.
4. **Offline quantiser model** — test grid calculations, chord grouping, note-on/note-off pairing and repeated notes independently of MPC hardware. The initial reference model and unit tests are in [engine/](engine/) and are not a live MIDI processor.
5. **MIDI integration feasibility** — investigate external DIN and USB input paths, then prove safe pass-through and reinjection before any live processing.
6. **Testing and packaging** — test carefully on a separate/test setup before considering any public release.

## Safety and compatibility

- Target device: Akai MPC Live III (ARM64 / Gen 2).
- Target software: MPC OS 3.10.1 or later, subject to verification.
- No installable release is available yet.
- Experimental system-level extensions can affect device stability. Do not install development builds on a primary production setup.

## Contributing

Research, documentation, testing ideas and technical contributions are welcome. Please open an issue before proposing device-level hooks or patches so the approach can be reviewed for safety and compatibility.

## Project status

This repository is a public work in progress. Features listed above are goals, not claims that they are implemented. The current Python reference models cover note timing, a simulated tempo timeline, late-event policies, an offline MIDI Clock follower, an incremental MIDI 1.0 byte-stream decoder, and a parser-to-clock bridge. They are test aids only: they do not connect to MIDI hardware, identify the MPC Pads port, provide hardware-accurate event timestamps, or read the MPC clock. The four offline engine test modules currently define 55 test methods. A GitHub Actions workflow is configured to run them; do not treat the method count or a pushed commit as evidence that the latest workflow passed.
