# LOCKSTEP quantiser engine — first test specification

**Scope:** define and test the timing engine independently of MPC hardware, MIDI connection type, and the eventual MPC integration method.

The engine must be connection-neutral. A controller connected through either 5-pin DIN or USB should be treated as a source of MIDI events; the engine should not care which connector carried them. The MPC Live III exposes DIN inputs as MPC 1 / MPC 2 and direct USB MIDI inputs as USB MIDI Port 1 / USB MIDI Port 2. Akai documents selecting a specific input port and channel for a track.

References:
- https://support.akaipro.com/en/support/solutions/articles/69000873948-akai-pro-mpc-series-understanding-the-midi-ports-on-your-mpc
- https://support.akaipro.com/en/support/solutions/articles/69000804431-akai-pro-mpc-series-configuring-midi-ports-for-multi-midi-control

## Design boundary

The quantiser core receives timestamped MIDI events and emits scheduled MIDI events. It does not open MIDI ports, hook ALSA, communicate with MPC, or write files. Those are separate adapters to be implemented only after their safety and feasibility are established.

Use a monotonic high-resolution clock for event arrival times. Use a separately supplied beat-clock model to map time to grid positions. Do not assume the Windows PC clock, wall clock, or an arbitrary fixed BPM is the MPC clock.

## Initial user-facing behaviour

- Grid choices: 1/4, 1/8, 1/16, 1/32.
- Strength: 100% initially; later allow partial strength if it can be implemented predictably.
- Quantisation direction: nearest grid line, with deterministic tie handling.
- Preserve pitch, velocity, channel and other note attributes.
- Chords: notes arriving within a configurable short chord-capture window should be assigned to the same grid target. The window must be measured/tested, not chosen by guesswork.
- Note-offs: schedule relative to the corresponding note-on so note length is preserved. Do not independently snap note-off to the grid in the first version.
- Repeated same-pitch notes: maintain separate note instances/FIFO pairing per source port, channel and pitch so an earlier note-off cannot prematurely stop a later note.
- Bypass: forward the event stream unchanged, with no timing changes.
- Non-note messages: initially pass through unchanged; document any message types that cannot safely be delayed or transformed.

## Event model

Each input event should carry:
- source-port identity;
- monotonic arrival timestamp;
- MIDI status/type;
- channel (when applicable);
- data bytes (including pitch and velocity for notes);
- stable sequence number to preserve ordering for events with identical timestamps.

Scheduled output events should carry:
- original event data;
- target monotonic output time;
- stable sequence number;
- pairing identity for note-on/note-off bookkeeping.

## Timing model

For a beat period T and grid division N (4, 8, 16 or 32 subdivisions per whole note), grid spacing is G = 4T/N. Given a note-on arrival time t, choose the nearest grid point q according to the selected tie rule. At 100% strength, the note-on target is q. At partial strength s in [0,1], target is t + s(q-t).

The engine must not emit an event earlier than the current time. If the nearest grid point is already in the past by the time the event can be scheduled, the adapter must apply a defined late-event policy (for example, use the next grid point or emit immediately); this policy must be explicit and tested. It must never silently drop a note.

Note-off target = paired note-on target + original measured note duration. If an input note-off arrives before its note-on has been emitted, retain it until the paired note-on has been emitted and then schedule it at the calculated target. Enforce a maximum safe pending-event capacity and define overflow recovery that sends note-offs/all-notes-off as appropriate rather than leaving stuck notes.

## Test cases before any live MIDI integration

1. Single note just before, exactly on, and just after a grid line.
2. Nearest-grid boundary and tie behaviour.
3. Each grid division at multiple tempos.
4. Chord notes arriving inside and outside the chord-capture window.
5. Same pitch repeated before the first note-off.
6. Overlapping notes of same pitch on different MIDI channels.
7. Note-off before scheduled note-on emission.
8. Very short and very long note durations.
9. MIDI velocity 1, typical midrange velocity, and 127.
10. Running status / real-time MIDI bytes if the chosen adapter handles raw byte streams.
11. Tempo change while events are pending.
12. Start/stop/clock discontinuity and loss of clock.
13. Queue saturation and recovery without stuck notes.
14. Bypass toggled with notes currently held.
15. Non-note messages pass-through policy.

## Acceptance criteria

- No missing, duplicated, or stuck notes in deterministic tests.
- Chords remain together within the specified capture window.
- Pitch, velocity and channel remain unchanged for note messages except timing.
- Note duration is preserved within scheduler resolution.
- Event ordering is stable and deterministic.
- Bypass reproduces original event bytes and ordering.
- Tests cover boundary conditions and simulated scheduling delays.
- No dependency on DIN versus USB, MPC pad events, or an installed MPC add-in.

## Explicit non-goals for this first stage

- No MPC installation.
- No MIDI injection into a live MPC.
- No ALSA hook or port interception.
- No audio processing or transport control.
- No assumption that internal pad events are accessible.
- No promise that external MIDI can yet be intercepted/reinjected safely.

## First reference implementation (2026-11-13)

A small Python reference model and deterministic unit-test suite have now been added:

- [engine/reference_quantizer.py](../engine/reference_quantizer.py)
- [engine/test_reference_quantizer.py](../engine/test_reference_quantizer.py)
- [engine/clock_timeline.py](../engine/clock_timeline.py)
- [engine/test_clock_timeline.py](../engine/test_clock_timeline.py)
- [engine/midi_clock_follower.py](../engine/midi_clock_follower.py)
- [engine/test_midi_clock_follower.py](../engine/test_midi_clock_follower.py)
- [GitHub Actions test workflow](../.github/workflows/reference-engine-tests.yml)

The reference model covers grid spacing and nearest-line snapping, strength, chord grouping within a configurable window, note-on/note-off duration pairing, FIFO handling of repeated same-pitch notes, independent source/channel pairing, velocity preservation (including note-off velocity), and stable output ordering. Chord windows are tracked independently per source/channel, so activity from another MIDI source does not break a chord being played on the first source.

A separate [tempo timeline model](../engine/clock_timeline.py) represents piecewise-constant tempo changes while keeping beat position continuous. It tests two explicit late-event policies: move a late note to the next grid line, or schedule it immediately at the current time. A third [MIDI Clock follower model](../engine/midi_clock_follower.py) now models the 24-pulses-per-quarter MIDI Clock stream, tempo estimation, Start/Continue/Stop and Song Position Pointer. All these models receive already-decoded timestamps or tempo changes from their caller; they do not discover or follow the MPC clock themselves. The MIDI Clock model uses a simple median of recent pulse intervals and is not yet a production jitter-rejection algorithm.

The grid arithmetic and 12 focused behavioural checks were independently exercised during development. The committed unit-test suite has not yet been confirmed by a completed GitHub Actions run.

**Important limits:** these are offline reference models, not production real-time code. They do not open DIN/USB ports, discover or follow the MPC clock or transport, schedule against a live operating clock, parse raw MIDI byte streams, provide a live bypass, or guarantee queue-overflow recovery. The late-event policy is modelled but not integrated into a live scheduler. Chord-window behaviour is a first deterministic rule to test, not a final musical decision. These missing pieces must be resolved before connecting to hardware or an MPC.

## Current status

Reference quantiser, tempo-timeline and MIDI Clock follower models, their unit tests, and the automated test workflow are now in the repository. No MIDI hardware has been connected, no MPC add-in or live MIDI processor has been built, and nothing has been installed on the MPC.
