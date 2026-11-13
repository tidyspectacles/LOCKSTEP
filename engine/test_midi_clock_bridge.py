import unittest

from midi_clock_bridge import MidiClockBridge
from midi_clock_follower import MidiClockFollower


class MidiClockBridgeTests(unittest.TestCase):
    def test_start_and_clock_batch_update_follower(self):
        follower = MidiClockFollower(120)
        bridge = MidiClockBridge(follower)
        bridge.feed(bytes([0xFA]), 0.0)
        bridge.feed(bytes([0xF8]), 1 / 48)
        self.assertTrue(follower.running)
        self.assertAlmostEqual(follower.beat_at_time(1 / 48), 1 / 24)

    def test_transport_messages_control_running_state(self):
        follower = MidiClockFollower(120)
        bridge = MidiClockBridge(follower)
        bridge.feed(bytes([0xFA]), 0.0)
        bridge.feed(bytes([0xFC]), 0.1)
        self.assertFalse(follower.running)
        bridge.feed(bytes([0xFB]), 0.2)
        self.assertTrue(follower.running)

    def test_song_position_is_decoded_lsb_first(self):
        follower = MidiClockFollower(120)
        bridge = MidiClockBridge(follower)
        bridge.feed(bytes([0xFA]), 0.0)
        bridge.feed(bytes([0xF2, 0x01, 0x02]), 0.1)
        self.assertAlmostEqual(follower.beat_at_time(0.1), 257 / 4)

    def test_note_events_are_returned_but_not_changed(self):
        bridge = MidiClockBridge()
        events = bridge.feed(bytes([0x90, 60, 100]), 0.0)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].kind, "note_on")
        self.assertEqual(events[0].data, (60, 100))

    def test_clock_in_same_batch_as_start_uses_batch_timestamp(self):
        follower = MidiClockFollower(120)
        bridge = MidiClockBridge(follower)
        events = bridge.feed(bytes([0xFA, 0xF8]), 0.0)
        self.assertEqual([event.kind for event in events], ["start", "clock"])
        self.assertAlmostEqual(follower.beat_at_time(0.0), 1 / 24)

    def test_parser_can_continue_across_batches(self):
        follower = MidiClockFollower(120)
        bridge = MidiClockBridge(follower)
        bridge.feed(bytes([0xFA]), 0.0)
        bridge.feed(bytes([0xF2, 0x05]), 0.1)
        events = bridge.feed(bytes([0x01]), 0.2)
        self.assertEqual(events, [])
        self.assertAlmostEqual(follower.beat_at_time(0.2), 133 / 4)

    def test_parser_reset_discards_partial_message(self):
        bridge = MidiClockBridge()
        bridge.feed(bytes([0x90, 60]), 0.0)
        bridge.reset_parser()
        self.assertEqual(bridge.feed(bytes([100]), 0.1), [])


if __name__ == "__main__":
    unittest.main()
