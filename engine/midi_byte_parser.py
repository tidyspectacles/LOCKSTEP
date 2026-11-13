"""Incremental MIDI 1.0 byte-stream decoder for LOCKSTEP.

This is an offline parser only. It does not open ports, timestamp bytes, or
communicate with an MPC. Realtime bytes may appear between any message bytes.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MidiEvent:
    kind: str
    status: int
    channel: int | None
    data: tuple[int, ...]


class MidiByteParser:
    """Decode MIDI 1.0 messages across arbitrary input chunk boundaries."""

    _REALTIME = {
        0xF8: "clock",
        0xFA: "start",
        0xFB: "continue",
        0xFC: "stop",
        0xFE: "active_sensing",
        0xFF: "reset",
        0xF9: "undefined_realtime",
        0xFD: "undefined_realtime",
    }

    _SYSTEM_LENGTHS = {
        0xF1: 1,  # MTC quarter frame
        0xF2: 2,  # Song Position Pointer
        0xF3: 1,  # Song Select
        0xF6: 0,  # Tune request
    }

    def __init__(self) -> None:
        self._running_status: int | None = None
        self._pending_status: int | None = None
        self._pending_data: list[int] = []
        self._needed = 0
        self._in_sysex = False

    @staticmethod
    def _message_length(status: int) -> int:
        high = status & 0xF0
        if high in (0xC0, 0xD0):
            return 1
        if high in (0x80, 0x90, 0xA0, 0xB0, 0xE0):
            return 2
        return 0

    @staticmethod
    def _channel_kind(status: int, data: tuple[int, ...]) -> str:
        high = status & 0xF0
        if high == 0x80 or (high == 0x90 and data[1] == 0):
            return "note_off"
        if high == 0x90:
            return "note_on"
        if high == 0xA0:
            return "poly_pressure"
        if high == 0xB0:
            return "control_change"
        if high == 0xC0:
            return "program_change"
        if high == 0xD0:
            return "channel_pressure"
        if high == 0xE0:
            return "pitch_bend"
        return "unknown"

    def feed(self, chunk: bytes | bytearray | memoryview) -> list[MidiEvent]:
        """Consume bytes and return all complete events in arrival order."""
        events: list[MidiEvent] = []

        for byte in bytes(chunk):
            if byte >= 0xF8:
                events.append(MidiEvent(
                    self._REALTIME.get(byte, "undefined_realtime"),
                    byte, None, (),
                ))
                continue

            if self._in_sysex:
                if byte == 0xF7:
                    self._in_sysex = False
                    events.append(MidiEvent("sysex_end", 0xF7, None, ()))
                continue

            if byte & 0x80:
                self._pending_data.clear()
                self._pending_status = None
                self._needed = 0

                if byte == 0xF0:
                    self._running_status = None
                    self._in_sysex = True
                    events.append(MidiEvent("sysex_start", byte, None, ()))
                    continue

                if byte == 0xF7:
                    self._running_status = None
                    events.append(MidiEvent("sysex_end", byte, None, ()))
                    continue

                if byte >= 0xF0:
                    self._running_status = None
                    if byte in self._SYSTEM_LENGTHS:
                        self._pending_status = byte
                        self._needed = self._SYSTEM_LENGTHS[byte]
                        if self._needed == 0:
                            events.append(MidiEvent("tune_request", byte, None, ()))
                            self._pending_status = None
                    else:
                        events.append(MidiEvent("system_common", byte, None, ()))
                    continue

                self._running_status = byte
                self._pending_status = byte
                self._needed = self._message_length(byte)
                continue

            if self._pending_status is None:
                if self._running_status is None:
                    continue
                self._pending_status = self._running_status
                self._needed = self._message_length(self._running_status)

            self._pending_data.append(byte)
            if len(self._pending_data) == self._needed:
                status = self._pending_status
                data = tuple(self._pending_data)
                if status < 0xF0:
                    events.append(MidiEvent(
                        self._channel_kind(status, data),
                        status,
                        (status & 0x0F) + 1,
                        data,
                    ))
                    # Channel running status remains active.
                    self._pending_status = None
                    self._pending_data.clear()
                    self._needed = 0
                else:
                    kind = "song_position" if status == 0xF2 else "system_common"
                    events.append(MidiEvent(kind, status, None, data))
                    self._pending_status = None
                    self._pending_data.clear()
                    self._needed = 0

        return events

    def reset(self) -> None:
        """Clear parser state after a port disconnect or explicit stream reset."""
        self._running_status = None
        self._pending_status = None
        self._pending_data.clear()
        self._needed = 0
        self._in_sysex = False
