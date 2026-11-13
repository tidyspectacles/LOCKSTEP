import unittest

from reference_quantizer import ReferenceQuantizer


class ReferenceQuantizerTests(unittest.TestCase):
    def test_grid_spacing_for_all_divisions(self):
        expected = {4: 1.0, 8: 0.5, 16: 0.25, 32: 0.125}
        for division, spacing in expected.items():
            q = ReferenceQuantizer(1.0, division)
            self.assertAlmostEqual(q.grid_spacing, spacing)

    def test_nearest_grid_and_half_up_tie(self):
        q = ReferenceQuantizer(0.5, 16)
        self.assertAlmostEqual(q.quantized_time(0.04), 0.0)
        self.assertAlmostEqual(q.quantized_time(0.09), 0.125)
        self.assertAlmostEqual(q.quantized_time(0.0625), 0.125)

    def test_strength_zero_is_bypass_timing(self):
        q = ReferenceQuantizer(0.5, 16, strength=0.0)
        self.assertAlmostEqual(q.quantized_time(0.137), 0.137)

    def test_strength_one_snaps_fully(self):
        q = ReferenceQuantizer(0.5, 16, strength=1.0)
        self.assertAlmostEqual(q.quantized_time(0.137), 0.125)

    def test_chord_notes_share_target_within_window(self):
        q = ReferenceQuantizer(0.5, 16, chord_window=0.03)
        a = q.note_on("usb-a", 1, 60, 100, 0.180)
        b = q.note_on("usb-a", 1, 64, 90, 0.190)
        self.assertAlmostEqual(a.target_time, b.target_time)


    def test_chord_window_survives_interleaved_other_source(self):
        q = ReferenceQuantizer(0.5, 16, chord_window=0.03)
        first = q.note_on("usb-a", 1, 60, 100, 0.050)
        q.note_on("usb-b", 1, 70, 100, 0.300)
        second = q.note_on("usb-a", 1, 64, 100, 0.070)
        self.assertAlmostEqual(first.target_time, second.target_time)

    def test_note_outside_chord_window_starts_new_group(self):
        q = ReferenceQuantizer(0.5, 16, chord_window=0.02)
        a = q.note_on("din-1", 1, 60, 100, 0.110)
        b = q.note_on("din-1", 1, 64, 90, 0.190)
        self.assertNotEqual(a.target_time, b.target_time)

    def test_note_duration_is_preserved(self):
        q = ReferenceQuantizer(0.5, 16)
        on = q.note_on("usb-a", 2, 60, 111, 0.137)
        off = q.note_off("usb-a", 2, 60, 0.337)
        self.assertAlmostEqual(off.target_time - on.target_time, 0.200)
        self.assertEqual(on.velocity, 111)
        self.assertEqual(off.velocity, 0)

    def test_repeated_same_pitch_pairs_fifo(self):
        q = ReferenceQuantizer(0.5, 16, chord_window=0.0)
        first = q.note_on("din-1", 1, 60, 80, 0.100)
        second = q.note_on("din-1", 1, 60, 110, 0.300)
        first_off = q.note_off("din-1", 1, 60, 0.200)
        second_off = q.note_off("din-1", 1, 60, 0.500)
        self.assertAlmostEqual(first_off.target_time - first.target_time, 0.100)
        self.assertAlmostEqual(second_off.target_time - second.target_time, 0.200)
        self.assertEqual([first.velocity, second.velocity], [80, 110])

    def test_channels_and_sources_are_independent(self):
        q = ReferenceQuantizer(0.5, 16)
        q.note_on("usb-a", 1, 60, 100, 0.100)
        q.note_on("usb-a", 2, 60, 100, 0.100)
        q.note_on("din-1", 1, 60, 100, 0.100)
        self.assertAlmostEqual(q.note_off("usb-a", 1, 60, 0.200).target_time, 0.225)
        self.assertAlmostEqual(q.note_off("usb-a", 2, 60, 0.250).target_time, 0.275)
        self.assertAlmostEqual(q.note_off("din-1", 1, 60, 0.300).target_time, 0.325)

    def test_chord_grouping_does_not_cross_source_or_channel(self):
        q = ReferenceQuantizer(0.5, 16, chord_window=0.03)
        a = q.note_on("usb-a", 1, 60, 100, 0.180)
        b = q.note_on("usb-b", 1, 64, 100, 0.190)
        c = q.note_on("usb-a", 2, 67, 100, 0.195)
        self.assertNotEqual(a.target_time, b.target_time)
        self.assertNotEqual(a.target_time, c.target_time)

    def test_note_off_velocity_is_preserved(self):
        q = ReferenceQuantizer(0.5, 16)
        q.note_on("usb-a", 1, 60, 100, 0.1)
        off = q.note_off("usb-a", 1, 60, 0.2, velocity=37)
        self.assertEqual(off.velocity, 37)

    def test_note_off_without_note_on_is_rejected(self):
        q = ReferenceQuantizer(0.5, 16)
        with self.assertRaises(ValueError):
            q.note_off("usb-a", 1, 60, 0.2)

    def test_velocity_zero_note_on_is_note_off(self):
        q = ReferenceQuantizer(0.5, 16)
        q.note_on("usb-a", 1, 60, 100, 0.1)
        off = q.note_on("usb-a", 1, 60, 0, 0.2)
        self.assertEqual(off.kind, "note_off")

    def test_output_order_is_stable(self):
        q = ReferenceQuantizer(0.5, 16, chord_window=0.02)
        q.note_on("usb-a", 1, 60, 100, 0.100)
        q.note_on("usb-a", 1, 64, 100, 0.110)
        ordered = q.scheduled_events()
        self.assertEqual([e.sequence for e in ordered], sorted(e.sequence for e in ordered))

    def test_invalid_parameters_are_rejected(self):
        for kwargs in (
            {"beat_period": 0},
            {"beat_period": 1, "grid_division": 12},
            {"beat_period": 1, "strength": 1.1},
            {"beat_period": 1, "chord_window": -0.1},
        ):
            with self.assertRaises(ValueError):
                ReferenceQuantizer(**kwargs)


if __name__ == "__main__":
    unittest.main()
