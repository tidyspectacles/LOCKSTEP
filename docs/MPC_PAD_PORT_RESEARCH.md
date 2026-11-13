# MPC pad ports and clock: research update

**Date:** 2026-11-13  
**Target:** MPC Live III, MPC OS 3.10.1 (user-confirmed)

## New finding: dedicated pad and keyboard MIDI ports

Akai's official article *Understanding the MIDI Ports On Your MPC* lists two dedicated ports for all MPC standalone models:

- **MPC Pads**
- **MPC Keyboard**

Akai describes these as the ports "for controlling the MPC's Pads and Keyboard". They are listed separately from physical 5-pin MIDI inputs (MPC 1 / MPC 2 on Live III), direct USB MIDI inputs (USB MIDI Port 1 / USB MIDI Port 2), and the Remote port.

Reference: https://support.akaipro.com/en/support/solutions/articles/69000873948-akai-pro-mpc-series-understanding-the-midi-ports-on-your-mpc

This is a more promising and more specific research target for LOCKSTEP's original built-in-pad goal than assuming that performance-pad messages share the controller-button "Private" raw-MIDI port used by some add-ins.

### What this does and does not prove

It proves that Akai exposes named MPC Pads and MPC Keyboard MIDI ports in its documented MIDI port model. It does **not** yet prove:

- whether every physical performance-pad strike is represented as ordinary MIDI note-on/note-off on that port;
- whether pad velocity, releases, repeated strikes, chords and MPCe gestures are all represented;
- which ALSA device/handle corresponds to the named port on OS 3.10.1;
- whether an add-in can observe the port without interfering with MPC;
- whether the original event can be suppressed and a corrected event safely delivered to the selected internal instrument.

Akai's multi-MIDI guide adds a useful routing detail: the MPC Pads input is an example of a port with **Global** enabled. Global means MIDI data from that port always goes to the currently selected program. Track mode instead makes a port selectable as a track input. This explains why the built-in pad path is not necessarily the same as an ordinary external MIDI track input.

Reference: https://support.akaipro.com/en/support/solutions/articles/69000804431-akai-pro-mpc-series-configuring-midi-ports-for-multi-midi-control

## New finding: MPC can send MIDI Clock

Akai's official multi-MIDI guide says that each output port can have **Sync** enabled. When enabled, it sends the sync messages selected under MIDI / Sync > Sync Send. The guide lists MIDI Clock, MIDI Time Code (MTC), and Ableton Link as sync choices, and separately describes transport synchronisation.

On the Live III, Akai lists physical 5-pin MIDI outputs as **MPC A** and **MPC B**. Therefore a DIN MIDI Clock output is a documented way for an external clock-aware processor to follow the MPC's tempo. The actual output must be configured and tested; do not assume it is enabled by default.

Reference: https://support.akaipro.com/en/support/solutions/articles/69000804431-akai-pro-mpc-series-configuring-midi-ports-for-multi-midi-control

## MIDI Clock follower reference model

An offline [MIDI Clock follower model](../engine/midi_clock_follower.py) and unit tests have also been added. It models the standard 24 clock pulses per quarter note, estimates tempo from recent pulse intervals, tracks Start/Continue/Stop and Song Position Pointer state, and calculates grid targets. It consumes already-decoded messages with timestamps; it is not a raw MIDI parser, does not read the MPC's clock, and has not been connected to hardware. Its simple median-interval estimate is a test baseline, not a finished jitter-resistant clock-recovery algorithm.

## Revised investigation order

1. First identify the documented **MPC Pads** port in the MPC's MIDI/Sync input-port list. Do not change its Global/Control/Track settings during the first inspection.
2. Determine whether the OS exposes this named port as an ALSA raw-MIDI device and whether the event stream can be observed read-only. Do not assume the controller Private port is the same thing.
3. If accessible, compare idle, one pad tap, held pad/release, different velocities, repeated hits, and simultaneous pads. Record only the necessary event bytes and monotonic timestamps.
4. Separately verify that MPC A or B can send MIDI Clock when Sync is enabled. This can support an external processor, but it is not a substitute for understanding the internal pad event path.
5. Keep the external DIN/USB input route separate. Akai documents those inputs as MPC 1 / MPC 2 and USB MIDI Port 1 / USB MIDI Port 2 on Live III.

## Safety and status

This remains research only. No settings have been changed, no test MIDI has been sent, no code has been installed, and no MPC filesystem has been touched. Do not change the MPC Pads port from Global during normal use as an experiment: that could alter how the pads control the currently selected program.

The key next technical task is to map Akai's named MPC Pads port to the actual OS-level MIDI device and prove read-only observation. A named port in the user interface is not, by itself, proof of a safe interception point.
