import unittest

from clock_timeline import TempoTimeline


class TempoTimelineTests(unittest.TestCase):
    def test_constant_tempo_maps_seconds_to_beats(self):
        clock = TempoTimeline(120)
        self.assertAlmostEqual(clock.beat_at_time(1.0), 2.0)
        self.assertAlmostEqual(clock.time_at_beat(2.0), 1.0)

    def test_tempo_change_keeps_beat_position_continuous(self):
        clock = TempoTimeline(120)
        clock.set_tempo(1.0, 60)
        self.assertAlmostEqual(clock.beat_at_time(1.0), 2.0)
        self.assertAlmostEqual(clock.beat_at_time(2.0), 3.0)
        self.assertAlmostEqual(clock.time_at_beat(3.0), 2.0)

    def test_multiple_tempo_changes(self):
        clock = TempoTimeline(120)
        clock.set_tempo(1.0, 60)
        clock.set_tempo(3.0, 90)
        self.assertAlmostEqual(clock.beat_at_time(4.0), 4.5)
        self.assertAlmostEqual(clock.time_at_beat(4.5), 4.0)

    def test_replacing_future_tempo_change(self):
        clock = TempoTimeline(120)
        clock.set_tempo(1.0, 60)
        clock.set_tempo(2.0, 90)
        clock.set_tempo(1.5, 120)
        self.assertEqual(len(clock.segments), 2)
        self.assertAlmostEqual(clock.beat_at_time(2.0), 3.0)

    def test_quantize_at_multiple_divisions(self):
        clock = TempoTimeline(120)
        expected = {4: 1.0, 8: 0.5, 16: 0.25, 32: 0.125}
        for division, spacing in expected.items():
            self.assertAlmostEqual(clock.time_at_beat(4.0 / division), spacing / 2)

    def test_quantize_uses_tempo_at_target_grid_line(self):
        clock = TempoTimeline(120)
        clock.set_tempo(1.0, 60)
        # At 1.1s, beat 2.1; nearest sixteenth beat line is beat 2.0 at 1.0s.
        self.assertAlmostEqual(clock.quantized_time(1.1, 16), 1.0)

    def test_late_event_moves_to_next_grid(self):
        clock = TempoTimeline(120)
        self.assertAlmostEqual(clock.target_with_late_policy(0.10, 0.20), 0.25)

    def test_late_event_can_be_emitted_immediately(self):
        clock = TempoTimeline(120)
        self.assertAlmostEqual(
            clock.target_with_late_policy(0.10, 0.20, policy="immediate"), 0.20
        )

    def test_event_on_current_grid_is_not_considered_late(self):
        clock = TempoTimeline(120)
        self.assertAlmostEqual(clock.target_with_late_policy(0.25, 0.25), 0.25)

    def test_invalid_values_are_rejected(self):
        with self.assertRaises(ValueError):
            TempoTimeline(0)
        clock = TempoTimeline(120)
        with self.assertRaises(ValueError):
            clock.set_tempo(1.0, 0)
        with self.assertRaises(ValueError):
            clock.quantized_time(1.0, 12)
        with self.assertRaises(ValueError):
            clock.target_with_late_policy(0.1, 0.2, policy="drop")


if __name__ == "__main__":
    unittest.main()
