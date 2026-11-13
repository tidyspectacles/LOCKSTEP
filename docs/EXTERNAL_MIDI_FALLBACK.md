# LOCKSTEP external MIDI fallback

**Purpose:** define a separate route for quantising notes from an external MIDI controller into an MPC Live III track, if transparent quantisation of the built-in MPC pads proves unavailable.

**Target:** Akai MPC Live III, MPC OS 3.10.1 (user-confirmed 2026-11-13).

## Why this route is worth testing

The MPC supports external MIDI input ports and lets a track select a specific input port and MIDI channel. Akai's documentation lists the Live III physical MIDI inputs as **MPC 1** and **MPC 2**, and its direct USB MIDI ports as **USB MIDI Port 1** and **USB MIDI Port 2**. A track can be configured to receive from a selected port, or from all ports. This gives us a documented normal track-input path for external controllers.

References:
- Akai, *Understanding the MIDI Ports On Your MPC*: https://inmusicsupport.freshdesk.com/en/support/solutions/articles/69000873948-akai-pro-mpc-series-understanding-the-midi-ports-on-your-mpc
- Akai, *Configuring MIDI Ports for Multi-MIDI Control*: https://support.akaipro.com/en/support/solutions/articles/69000804431-akai-pro-mpc-series-configuring-midi-ports-for-multi-midi-control
- Akai, *Connecting the MPC to External Gear*: https://support.akaipro.com/en/support/solutions/articles/69000868287-akai-pro-mpc%E4%B8%96%E4%BB%A3%EF%BD%9Cmpc%E3%81%A8%E5%A4%96%E9%83%A8%E6%A9%9F%E5%99%A8%E3%81%AE%E6%8E%A5%E7%B6%9A

## Clock synchronisation lead

Akai documents per-output-port **Sync** enablement. With Sync enabled, the selected output sends the sync type configured in MIDI / Sync > Sync Send. The Live III's physical 5-pin MIDI outputs are named **MPC A** and **MPC B**. This creates a documented possibility for an external processor to receive MIDI Clock from the MPC over a DIN connection and use it as its timing reference.

This is only a routing capability documented by Akai. It does not prove that a particular external processor can receive and recover the clock accurately, nor that clock is enabled by default. See [MPC_PAD_PORT_RESEARCH.md](MPC_PAD_PORT_RESEARCH.md) for the source and the offline clock-follower model.

## Two possible implementation routes

### Route A — inside the MPC (preferred fallback to investigate)

An add-in could potentially observe and process data arriving on a selected external ALSA MIDI input handle before MPC's track receives it, then deliver the quantised stream into a normal MPC track input. This is **not yet proven**. We must identify the exact ALSA interface MPC uses for the physical DIN and USB MIDI ports, establish whether interception can be limited to the selected external port, and prove a safe output/reinjection path that does not duplicate or bypass track input.

The controller-port hook used by MPC Skipback is not evidence for this route: it observes the MPC's own controller hardware-button port, not necessarily external DIN/USB inputs.

### Route B — external MIDI processor (fallback if an MPC add-in cannot do it)

A separate MIDI processor between the controller and MPC could quantise the note stream before the MPC receives it. This might be a small standalone MIDI processor or a Windows-based MIDI routing setup. The exact hardware/software and connection arrangement must be chosen only after checking the user's controller, available MIDI connections, and whether the MPC Live III can receive the processed stream on a suitable input. This route would not require changing MPC system files, but may add a computer or extra device to the playing setup.

## Required behaviour

- Quantise note-on timing to the MPC clock/grid (initial target: 1/4, 1/8, 1/16, 1/32; 100% strength).
- Preserve pitch, velocity, MIDI channel and note-off/note duration.
- Keep simultaneous notes/chords together.
- Handle repeated hits on the same pitch without stuck or prematurely released notes.
- Pass unrelated MIDI messages through unchanged unless explicitly documented otherwise.
- Provide a true bypass that restores unmodified input immediately.
- Do not alter audio, transport, projects or existing instruments/programs.

## Safe proof sequence

1. **No device changes:** inspect the documented MPC MIDI port model and design a host-side MIDI test harness.
2. **Read-only input check:** establish which ALSA input handle corresponds to the selected physical DIN or USB MIDI port. Observe only; do not suppress, delay or rewrite messages.
3. **Pass-through check:** demonstrate that the selected external input can be observed while the MPC still receives the original notes unchanged.
4. **Offline scheduler tests:** test grid calculations, note-on/note-off pairing, chords, repeated same-pitch notes, velocity and channel using recorded/test MIDI data.
5. **Controlled processing prototype:** only after the above, test a separate opt-in build that processes one explicitly selected external input. Keep the original route recoverable and include a bypass.
6. **MPC integration test:** verify that processed notes reach a normal MPC track/instrument and record correctly. Confirm no doubled notes, stuck notes, timing drift or interference with other MIDI ports.

No installation or live processing test should happen until source, package, recovery steps and risks have been reviewed and the user explicitly approves.

## Important limitations

- A normal MIDI track input setting does not itself quantise incoming notes; it only routes them to the track.
- The ability to read external MIDI does not prove that an add-in can transparently replace it before the MPC track receives it.
- A documented MIDI Clock output provides a potential timing reference, but the processor still needs a reliable clock input and tested handling of clock jitter, start/stop and tempo changes.
- ALSA interposition can conflict with other add-ins that hook the same functions. MPC Remote and Skipback already have documented hook overlap. Do not assume they can coexist with LOCKSTEP.
- A Windows external processor may be possible, but its routing depends on the actual controller and connection setup. Do not prescribe a cable or app before confirming those details.
- The internal-pad route remains a separate, unproven goal. External-MIDI support would be a useful first release, but must be labelled accurately.

## Current status

**Research/design only.** No source code, diagnostic add-in, MIDI processor, build workflow, binary or installer exists yet. No changes have been made to the MPC.
