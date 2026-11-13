import unittest

from midi_clock_follower import MidiClockFollower


class MidiClockFollowerTests(unittest.TestCase):
    def test_start_and_clock_pulses_advance_beat(self):
        clock = MidiClockFollower(120)
        clock.start(0.0)
        clock.clock_pulse(1 / 48)
        self.assertAlmostEqual(clock.beat_at_time(1 / 48), 1 / 24)

    def test_tempo_estimated_from_clock_intervals(self):
        clock = MidiClockFollower(100)
        clock.start(0.0)
        for i in range(1, 25):
            clock.clock_pulse(i / 48)
        self.assertAlmostEqual(clock.bpm, 120)

    def test_tempo_tracks_changed_pulse_interval(self):
        clock = MidiClockFollower(120)
        clock.start(0.0)
        for i in range(1, 25):
            clock.clock_pulse(i / 48)
        for i in range(25, 50):
            clock.clock_pulse(0.5 + (i - 24) / 24)
        self.assertAlmostEqual(clock.bpm, 60)

    def test_stop_freezes_beat_position(self):
        clock = MidiClockFollower(120)
        clock.start(0.0)
        clock.clock_pulse(1 / 48)
        clock.stop(0.02)
        self.assertFalse(clock.running)
        self.assertAlmostEqual(clock.beat_at_time(10.0), clock.beat_at_time(0.02))

    def test_continue_resumes_from_saved_position(self):
        clock = MidiClockFollower(120)
        clock.start(0.0)
        clock.clock_pulse(1 / 48)
        clock.stop(0.03)
        frozen = clock.beat_at_time(0.03)
        clock.continue_playback(1.0)
        clock.clock_pulse(1.0 + 1 / 48)
        self.assertAlmostEqual(clock.beat_at_time(1.0 + 1 / 48), frozen + 1 / 24)

    def test_song_position_pointer_sets_sixteenth_note_position(self):
        clock = MidiClockFollower(120)
        clock.start(0.0)
        clock.song_position_pointer(16, 1.0)
        self.assertAlmostEqual(clock.beat_at_time(1.0), 4.0)

    def test_quantize_to_sixteenth_grid(self):
        clock = MidiClockFollower(120)
        clock.start(0.0)
        # 12 pulses = half a beat; sixteenth-note grid at beat 0.5.
        for i in range(1, 13):
            clock.clock_pulse(i / 48)
        self.assertAlmostEqual(clock.quantized_time(0.25, 16), 0.25)

    def test_ignores_clock_while_stopped(self):
        clock = MidiClockFollower(120)
        clock.clock_pulse(0.1)
        self.assertEqual(clock.beat_at_time(0.1), 0.0)

    def test_invalid_values_are_rejected(self):
        with self.assertRaises(ValueError):
            MidiClockFollower(0)
        with self.assertRaises(ValueError):
            MidiClockFollower(120, 1)
        clock = MidiClockFollower(120)
        with self.assertRaises(ValueError):
            clock.song_position_pointer(16384, 0.0)
        with self.assertRaises(ValueError):
            clock.quantized_time(0.0, 12)


if __name__ == "__main__":
    unittest.main()
