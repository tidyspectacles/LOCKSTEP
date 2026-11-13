"""Offline tempo-map and late-event policy for LOCKSTEP.

This module models a supplied monotonic timeline. It does NOT read MPC tempo,
MIDI Clock, transport, or any hardware clock.
"""
from __future__ import annotations

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class TempoSegment:
    start_time: float
    start_beat: float
    bpm: float


class TempoTimeline:
    """Piecewise-constant tempo timeline, anchored at time zero / beat zero."""

    def __init__(self, bpm: float) -> None:
        if bpm <= 0:
            raise ValueError("bpm must be positive")
        self._segments = [TempoSegment(0.0, 0.0, float(bpm))]

    @property
    def segments(self) -> tuple[TempoSegment, ...]:
        return tuple(self._segments)

    def beat_at_time(self, timestamp: float) -> float:
        if timestamp < 0:
            raise ValueError("timestamp cannot be negative")
        segment = self._segment_for_time(timestamp)
        return segment.start_beat + (timestamp - segment.start_time) * segment.bpm / 60.0

    def time_at_beat(self, beat: float) -> float:
        if beat < 0:
            raise ValueError("beat cannot be negative")
        segment = self._segment_for_beat(beat)
        return segment.start_time + (beat - segment.start_beat) * 60.0 / segment.bpm

    def set_tempo(self, timestamp: float, bpm: float) -> None:
        """Change tempo at timestamp without moving the musical beat position."""
        if timestamp < 0 or bpm <= 0:
            raise ValueError("timestamp must be non-negative and bpm positive")
        beat = self.beat_at_time(timestamp)
        self._segments = [s for s in self._segments if s.start_time < timestamp]
        self._segments.append(TempoSegment(float(timestamp), beat, float(bpm)))

    def quantized_time(self, timestamp: float, division: int = 16, strength: float = 1.0) -> float:
        if division not in (4, 8, 16, 32):
            raise ValueError("division must be 4, 8, 16, or 32")
        if not 0.0 <= strength <= 1.0:
            raise ValueError("strength must be between 0 and 1")
        beat_spacing = 4.0 / division
        beat = self.beat_at_time(timestamp)
        grid_index = math.floor(beat / beat_spacing + 0.5)
        grid_time = self.time_at_beat(grid_index * beat_spacing)
        return timestamp + strength * (grid_time - timestamp)

    def target_with_late_policy(
        self, event_time: float, now: float, division: int = 16, policy: str = "next_grid"
    ) -> float:
        """Return a target not earlier than now; never silently discard an event."""
        if now < 0:
            raise ValueError("now cannot be negative")
        target = self.quantized_time(event_time, division, strength=1.0)
        if target >= now:
            return target
        if policy == "immediate":
            return now
        if policy != "next_grid":
            raise ValueError("policy must be 'next_grid' or 'immediate'")
        spacing = 4.0 / division
        now_beat = self.beat_at_time(now)
        next_index = math.floor(now_beat / spacing) + 1
        return self.time_at_beat(next_index * spacing)

    def _segment_for_time(self, timestamp: float) -> TempoSegment:
        for segment in reversed(self._segments):
            if timestamp >= segment.start_time:
                return segment
        return self._segments[0]

    def _segment_for_beat(self, beat: float) -> TempoSegment:
        for segment in reversed(self._segments):
            if beat >= segment.start_beat:
                return segment
        return self._segments[0]
