"""Offline MIDI Clock follower model for LOCKSTEP.

Consumes already-decoded MIDI realtime messages and timestamps. It does not
open MIDI ports or communicate with an MPC. MIDI Clock is 24 pulses/quarter.
"""
from __future__ import annotations

from collections import deque
from statistics import median


class MidiClockFollower:
    """Small deterministic model of MIDI Clock tempo and beat position."""

    def __init__(self, fallback_bpm: float = 120.0, history_size: int = 24) -> None:
        if fallback_bpm <= 0:
            raise ValueError("fallback_bpm must be positive")
        if history_size < 2:
            raise ValueError("history_size must be at least 2")
        self.fallback_bpm = float(fallback_bpm)
        self._intervals = deque(maxlen=history_size)
        self._running = False
        self._beat = 0.0
        self._last_pulse_time = None
        self._anchor_time = None
        self._last_event_time = 0.0

    @property
    def running(self) -> bool:
        return self._running

    @property
    def bpm(self) -> float:
        if self._intervals:
            return 60.0 / (24.0 * median(self._intervals))
        return self.fallback_bpm

    def start(self, timestamp: float) -> None:
        self._check_time(timestamp)
        self._running = True
        self._beat = 0.0
        self._intervals.clear()
        self._last_pulse_time = None
        self._anchor_time = float(timestamp)
        self._last_event_time = float(timestamp)

    def continue_playback(self, timestamp: float) -> None:
        self._check_time(timestamp)
        self._require_non_decreasing(timestamp)
        self._running = True
        self._anchor_time = float(timestamp)
        self._last_pulse_time = None
        self._last_event_time = float(timestamp)

    def stop(self, timestamp: float) -> None:
        self._check_time(timestamp)
        self._require_non_decreasing(timestamp)
        if self._running:
            self._beat = self.beat_at_time(timestamp)
        self._running = False
        self._last_event_time = float(timestamp)

    def song_position_pointer(self, sixteenth_notes: int, timestamp: float) -> None:
        """Apply MIDI Song Position Pointer; its units are sixteenth notes."""
        self._check_time(timestamp)
        self._require_non_decreasing(timestamp)
        if not 0 <= sixteenth_notes <= 16383:
            raise ValueError("song position pointer must be 0..16383")
        self._beat = sixteenth_notes / 4.0
        self._intervals.clear()
        self._last_pulse_time = None
        self._anchor_time = float(timestamp)
        self._last_event_time = float(timestamp)

    def clock_pulse(self, timestamp: float) -> None:
        self._check_time(timestamp)
        if not self._running:
            return
        if timestamp < self._last_event_time:
            raise ValueError("MIDI Clock timestamps must be non-decreasing")
        if self._last_pulse_time is not None:
            interval = timestamp - self._last_pulse_time
            if interval > 0:
                self._intervals.append(interval)
        self._beat += 1.0 / 24.0
        self._last_pulse_time = float(timestamp)
        self._anchor_time = float(timestamp)
        self._last_event_time = float(timestamp)

    def beat_at_time(self, timestamp: float) -> float:
        self._check_time(timestamp)
        if not self._running:
            return self._beat
        if self._anchor_time is None:
            return self._beat
        pulse_period = 60.0 / (self.bpm * 24.0)
        return self._beat + (timestamp - self._anchor_time) / (24.0 * pulse_period)

    def quantized_time(self, timestamp: float, division: int = 16) -> float:
        if division not in (4, 8, 16, 32):
            raise ValueError("division must be 4, 8, 16, or 32")
        if not self._running:
            raise RuntimeError("MIDI Clock is not running")
        beat = self.beat_at_time(timestamp)
        spacing = 4.0 / division
        grid_index = int(beat / spacing + 0.5)
        target_beat = grid_index * spacing
        delta_beats = target_beat - beat
        return timestamp + delta_beats * 60.0 / self.bpm

    def _require_non_decreasing(self, timestamp: float) -> None:
        if timestamp < self._last_event_time:
            raise ValueError("MIDI Clock timestamps must be non-decreasing")

    @staticmethod
    def _check_time(timestamp: float) -> None:
        if timestamp < 0:
            raise ValueError("timestamp cannot be negative")
