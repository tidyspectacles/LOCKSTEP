"""Connection-neutral reference model for LOCKSTEP's quantiser timing rules.

This is an offline test/reference implementation, NOT an MPC add-in and NOT
a live MIDI router. Times are seconds on a monotonic timeline supplied by the
caller. No MIDI ports, clocks, files, or hardware are accessed.
"""
from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
import math
from typing import Deque, Dict, List, Tuple


@dataclass(frozen=True)
class ScheduledEvent:
    kind: str
    source: str
    channel: int
    pitch: int
    velocity: int
    input_time: float
    target_time: float
    sequence: int


class ReferenceQuantizer:
    """Deterministic timing model used to test LOCKSTEP's core behaviour."""

    def __init__(
        self,
        beat_period: float,
        grid_division: int = 16,
        chord_window: float = 0.0,
        strength: float = 1.0,
    ) -> None:
        if beat_period <= 0:
            raise ValueError("beat_period must be positive")
        if grid_division not in (4, 8, 16, 32):
            raise ValueError("grid_division must be 4, 8, 16, or 32")
        if chord_window < 0:
            raise ValueError("chord_window cannot be negative")
        if not 0.0 <= strength <= 1.0:
            raise ValueError("strength must be between 0 and 1")
        self.beat_period = float(beat_period)
        self.grid_division = grid_division
        self.chord_window = float(chord_window)
        self.strength = float(strength)
        self._sequence = 0
        self._active_chord_start = None
        self._active_chord_target = None
        self._active_chord_key = None
        self._held: Dict[Tuple[str, int, int], Deque[ScheduledEvent]] = defaultdict(deque)
        self._events: List[ScheduledEvent] = []

    @property
    def grid_spacing(self) -> float:
        # A quarter note is one beat. Eighths are half a beat, etc.
        return self.beat_period * 4.0 / self.grid_division

    def quantized_time(self, event_time: float) -> float:
        spacing = self.grid_spacing
        # Deterministic half-up tie handling: exact midpoint goes to later line.
        grid_index = math.floor(event_time / spacing + 0.5)
        nearest = grid_index * spacing
        return event_time + self.strength * (nearest - event_time)

    def note_on(
        self, source: str, channel: int, pitch: int, velocity: int, event_time: float
    ) -> ScheduledEvent:
        self._validate_note(channel, pitch, velocity)
        if velocity == 0:
            return self.note_off(source, channel, pitch, event_time, velocity=0)

        if (
            self._active_chord_start is None
            or event_time - self._active_chord_start > self.chord_window
            or self._active_chord_key != (source, channel)
        ):
            self._active_chord_start = event_time
            self._active_chord_target = self.quantized_time(event_time)
            self._active_chord_key = (source, channel)

        target = self._active_chord_target
        self._sequence += 1
        event = ScheduledEvent(
            "note_on", source, channel, pitch, velocity,
            event_time, target, self._sequence
        )
        self._held[(source, channel, pitch)].append(event)
        self._events.append(event)
        return event

    def note_off(
        self, source: str, channel: int, pitch: int, event_time: float, velocity: int = 0
    ) -> ScheduledEvent:
        if not 1 <= channel <= 16 or not 0 <= pitch <= 127 or not 0 <= velocity <= 127:
            raise ValueError("invalid MIDI channel, pitch, or note-off velocity")
        key = (source, channel, pitch)
        if not self._held[key]:
            raise ValueError("note_off has no matching note_on")
        paired_on = self._held[key].popleft()
        duration = max(0.0, event_time - paired_on.input_time)
        target = paired_on.target_time + duration
        self._sequence += 1
        event = ScheduledEvent(
            "note_off", source, channel, pitch, velocity,
            event_time, target, self._sequence
        )
        self._events.append(event)
        return event

    def scheduled_events(self) -> List[ScheduledEvent]:
        """Return events in output-time order, stable for equal target times."""
        return sorted(self._events, key=lambda item: (item.target_time, item.sequence))

    @staticmethod
    def _validate_note(channel: int, pitch: int, velocity: int) -> None:
        if not 1 <= channel <= 16:
            raise ValueError("MIDI channel must be 1..16")
        if not 0 <= pitch <= 127 or not 0 <= velocity <= 127:
            raise ValueError("MIDI pitch and velocity must be 0..127")
