"""Connect decoded MIDI realtime events to the offline clock follower.

The caller supplies one timestamp for a decoded batch. This is a batch/read
boundary timestamp, not a hardware timestamp for each individual MIDI byte.
No ports or hardware are accessed.
"""
from __future__ import annotations

from midi_byte_parser import MidiEvent, MidiByteParser
from midi_clock_follower import MidiClockFollower


class MidiClockBridge:
    """Parse MIDI bytes and apply clock/transport messages to a follower."""

    def __init__(self, follower: MidiClockFollower | None = None) -> None:
        self.parser = MidiByteParser()
        self.follower = follower or MidiClockFollower()

    def feed(self, data: bytes, batch_timestamp: float) -> list[MidiEvent]:
        """Decode bytes, update clock state, and return every decoded event."""
        events = self.parser.feed(data)
        for event in events:
            if event.kind == "clock":
                self.follower.clock_pulse(batch_timestamp)
            elif event.kind == "start":
                self.follower.start(batch_timestamp)
            elif event.kind == "continue":
                self.follower.continue_playback(batch_timestamp)
            elif event.kind == "stop":
                self.follower.stop(batch_timestamp)
            elif event.kind == "song_position":
                position = event.data[0] | (event.data[1] << 7)
                self.follower.song_position_pointer(position, batch_timestamp)
        return events

    def reset_parser(self) -> None:
        """Reset partial byte-stream parsing after a disconnect."""
        self.parser.reset()
