import unittest
try:
    import unittest.mock as mock
except ImportError:
    import mock

from opsdroidaudio import generators


class TestGenerators(unittest.TestCase):
    """Test the opsdroidaudio generators class."""

    def test_prepare_url(self):
        """Test the prepare_url method"""
        response = generators.prepare_url('https://www.youtube.com')
        self.assertEqual('a link to youtube.com', response)
