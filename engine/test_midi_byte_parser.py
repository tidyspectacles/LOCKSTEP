import unittest

from midi_byte_parser import MidiByteParser


class MidiByteParserTests(unittest.TestCase):
    def test_note_on_and_note_off(self):
        parser = MidiByteParser()
        events = parser.feed(bytes([0x90, 60, 100, 0x80, 60, 45]))
        self.assertEqual([e.kind for e in events], ["note_on", "note_off"])
        self.assertEqual(events[0].channel, 1)
        self.assertEqual(events[0].data, (60, 100))
        self.assertEqual(events[1].data, (60, 45))

    def test_velocity_zero_note_on_is_note_off(self):
        events = MidiByteParser().feed(bytes([0x91, 64, 0]))
        self.assertEqual(events[0].kind, "note_off")
        self.assertEqual(events[0].channel, 2)

    def test_running_status_decodes_repeated_notes(self):
        events = MidiByteParser().feed(bytes([0x90, 60, 90, 62, 80]))
        self.assertEqual([e.data for e in events], [(60, 90), (62, 80)])

    def test_message_can_be_split_across_chunks(self):
        parser = MidiByteParser()
        self.assertEqual(parser.feed(bytes([0x90, 60])), [])
        events = parser.feed(bytes([100]))
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].kind, "note_on")

    def test_realtime_clock_can_be_interleaved_in_note(self):
        parser = MidiByteParser()
        events = parser.feed(bytes([0x90, 60, 0xF8, 100]))
        self.assertEqual([e.kind for e in events], ["clock", "note_on"])
        self.assertEqual(events[1].data, (60, 100))

    def test_transport_realtime_messages(self):
        events = MidiByteParser().feed(bytes([0xFA, 0xFB, 0xFC, 0xF8]))
        self.assertEqual([e.kind for e in events],
                         ["start", "continue", "stop", "clock"])

    def test_song_position_pointer(self):
        events = MidiByteParser().feed(bytes([0xF2, 0x01, 0x02]))
        self.assertEqual(events[0].kind, "song_position")
        self.assertEqual(events[0].data, (1, 2))

    def test_realtime_does_not_break_system_common_message(self):
        parser = MidiByteParser()
        events = parser.feed(bytes([0xF2, 0xF8, 0x01, 0x02]))
        self.assertEqual([e.kind for e in events], ["clock", "song_position"])
        self.assertEqual(events[1].data, (1, 2))

    def test_sysex_is_skipped_but_realtime_is_seen(self):
        events = MidiByteParser().feed(
            bytes([0xF0, 0x01, 0x02, 0xF8, 0x03, 0xF7, 0x90, 60, 90])
        )
        self.assertEqual(
            [e.kind for e in events],
            ["sysex_start", "clock", "sysex_end", "note_on"],
        )

    def test_system_common_clears_running_status(self):
        parser = MidiByteParser()
        parser.feed(bytes([0x90, 60, 90]))
        events = parser.feed(bytes([0xF6, 61, 80]))
        self.assertEqual([e.kind for e in events], ["tune_request"])

    def test_program_change_single_data_byte(self):
        events = MidiByteParser().feed(bytes([0xC2, 10]))
        self.assertEqual(events[0].kind, "program_change")
        self.assertEqual(events[0].channel, 3)
        self.assertEqual(events[0].data, (10,))

    def test_reset_discards_partial_message(self):
        parser = MidiByteParser()
        parser.feed(bytes([0x90, 60]))
        parser.reset()
        self.assertEqual(parser.feed(bytes([100])), [])

    def test_ignores_data_without_status(self):
        self.assertEqual(MidiByteParser().feed(bytes([60, 100])), [])


if __name__ == "__main__":
    unittest.main()
