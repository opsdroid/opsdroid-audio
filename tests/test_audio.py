import unittest
try:
    import unittest.mock as mock
except ImportError:
    import mock

from opsdroidaudio import audio

class TestCore(unittest.TestCase):
    """Test the opsdroid core class."""

    def test_ring_buffer(self):
        ring_buffer = audio.RingBuffer()
        ring_buffer.extend([True])
        self.assertEqual(ring_buffer.length, 1)
