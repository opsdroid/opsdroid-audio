"""Audio handling submodule."""
import collections
import time
import os
import logging
from array import array

import wave
import pyaudio

from snowboydetect import snowboydetect

logging.basicConfig()
_LOGGER = logging.getLogger("snowboy")
_LOGGER.setLevel(logging.INFO)
TOP_DIR = os.path.dirname(os.path.abspath(__file__))

RESOURCE_FILE = os.path.join(TOP_DIR, "resources/common.res")
DETECT_DING = os.path.join(TOP_DIR, "resources/ding.wav")
DETECT_DONG = os.path.join(TOP_DIR, "resources/dong.wav")
BUFFER_LENGTH = 5  # Seconds

RECORDING_SILENCE_START = 3
RECORDING_SILENCE = 4
RECORDING_THRESHOLD = 3000


class RingBuffer:
    """Ring buffer to hold audio from PortAudio."""

    def __init__(self, size=4096):
        """Set buffer max size on init."""
        self._buf = collections.deque(maxlen=size)

    def extend(self, data):
        """Add data to the end of buffer."""
        self._buf.extend(data)

    def get(self):
        """Retrieve data from the beginning of buffer and clears it."""
        tmp = bytes(bytearray(self._buf))
        self._buf.clear()
        return tmp

    @property
    def length(self):
        """Get the length of the buffer."""
        return len(self._buf)


def play_audio_file(fname=DETECT_DING):
    """Play a wave file.

    By default it plays a Ding sound.

    :param str fname: wave file name
    :return: None
    """
    ding_wav = wave.open(fname, 'rb')
    ding_data = ding_wav.readframes(ding_wav.getnframes())
    audio = pyaudio.PyAudio()
    stream_out = audio.open(
        format=audio.get_format_from_width(ding_wav.getsampwidth()),
        channels=ding_wav.getnchannels(),
        rate=ding_wav.getframerate(), input=False, output=True)
    stream_out.start_stream()
    stream_out.write(ding_data)
    time.sleep(0.2)
    stream_out.stop_stream()
    stream_out.close()
    audio.terminate()


class HotwordDetector:
    """
    Detect whether a keyword exists in a microphone input stream.

    :param decoder_model: decoder model file path, a string or list of strings
    :param resource: resource file path.
    :param sensitivity: decoder sensitivity, a float of a list of floats.
                              The bigger the value, the more senstive the
                              decoder. If an empty list is provided, then the
                              default sensitivity in the model will be used.
    :param audio_gain: multiply input volume by this factor.
    """

    # pylint: disable=too-many-instance-attributes
    # Needs refactoring as port of opsdroid/opsdroid-audio#12

    def __init__(self, decoder_model,
                 resource=RESOURCE_FILE,
                 sensitivity=None,
                 audio_gain=1):
        """Initialise the HotwordDetector object."""
        def audio_callback(in_data, frame_count, time_info, status):
            """Extend buffer with data from pyaudio."""
            self.ring_buffer.extend(in_data)
            play_data = chr(0) * len(in_data)
            return play_data, pyaudio.paContinue

        self.recording = False
        self.recording_silence = 0
        self.recording_time = 0
        self.last_chunk_silent = False

        if not isinstance(decoder_model, list):
            decoder_model = [decoder_model]
        if sensitivity is None:
            sensitivity = []
        elif not isinstance(sensitivity, list):
            sensitivity = [sensitivity]
        model_str = ",".join(decoder_model)

        # pylint: disable=unexpected-keyword-arg
        self.detector = snowboydetect.SnowboyDetect(
            resource_filename=str(resource.encode()),
            model_str=str(model_str.encode()))
        self.detector.SetAudioGain(audio_gain)
        self.num_hotwords = self.detector.NumHotwords()

        if len(decoder_model) > 1 and len(sensitivity) == 1:
            sensitivity = sensitivity*self.num_hotwords
        if sensitivity:
            assert self.num_hotwords == len(sensitivity), \
                "number of hotwords in decoder_model (%d) and sensitivity " \
                "(%d) does not match" % (self.num_hotwords, len(sensitivity))
        sensitivity_str = ",".join([str(t) for t in sensitivity])
        if sensitivity:
            self.detector.SetSensitivity(sensitivity_str.encode())

        self.ring_buffer = RingBuffer(
            self.detector.NumChannels() *
            self.detector.SampleRate() * BUFFER_LENGTH)
        self.record_buffer = RingBuffer(None)
        self.audio = pyaudio.PyAudio()
        self.stream_in = self.audio.open(
            input=True, output=False,
            format=self.audio.get_format_from_width(
                self.detector.BitsPerSample() / 8),
            channels=self.detector.NumChannels(),
            rate=self.detector.SampleRate(),
            frames_per_buffer=2048,
            stream_callback=audio_callback)

    def start(self, detected_callback=play_audio_file,
              recording_callback=None,
              interrupt_check=lambda: False,
              sleep_time=0.03):
        """
        Start the voice detector.

        For every `sleep_time` second it checks the
        audio buffer for triggering keywords. If detected, then call
        corresponding function in `detected_callback`, which can be a single
        function (single model) or a list of callback functions (multiple
        models). Every loop it also calls `interrupt_check` -- if it returns
        True, then breaks from the loop and return.

        :param detected_callback: a function or list of functions. The number
                                  of items must match the number of models in
                                  `decoder_model`.
        :param interrupt_check: a function that returns True if the main loop
                                needs to stop.
        :param float sleep_time: how much time in second every loop waits.
        :return: None
        """
        # pylint: disable=too-many-branches
        # Needs refactoring as port of opsdroid/opsdroid-audio#12
        if interrupt_check():
            _LOGGER.debug("detect voice return")
            return

        if not isinstance(detected_callback, list):
            detected_callback = [detected_callback]
        if len(detected_callback) == 1 and self.num_hotwords > 1:
            detected_callback *= self.num_hotwords

        assert self.num_hotwords == len(detected_callback), \
            "Error: hotwords in your models (%d) do not match the number " \
            "of callbacks (%d)" % (self.num_hotwords, len(detected_callback))

        _LOGGER.debug("detecting...")

        while True:
            if interrupt_check():
                _LOGGER.debug("detect voice break")
                break
            data = self.ring_buffer.get()
            if not data:
                time.sleep(sleep_time)
                continue

            data_as_ints = array('h', data)

            if self.recording:
                self.record_buffer.extend(data)
                self.recording_time += 1
                if self.recording_time > RECORDING_SILENCE_START and \
                        max(data_as_ints) < RECORDING_THRESHOLD and \
                        self.last_chunk_silent:
                    self.recording_silence += 1
                else:
                    self.recording_silence = 0
                if self.recording_silence >= RECORDING_SILENCE:
                    _LOGGER.info("Stopping recording")
                    if recording_callback is not None:
                        recording_callback(self.record_buffer.get(), self)
                    self.recording = False
                    self.recording_silence = 0
                    self.recording_time = 0

                self.last_chunk_silent = max(data_as_ints) <= RECORDING_THRESHOLD
            else:
                ans = self.detector.RunDetection(data)
                if ans == -1:
                    _LOGGER.warning(
                        "Error initializing streams or reading audio data")
                elif ans > 0:
                    _LOGGER.info("Keyword detected, starting recording")
                    self.recording = True
                    self.record_buffer.extend(data)
                    callback = detected_callback[ans-1]
                    if callback is not None:
                        callback(data, self)

        _LOGGER.debug("finished.")

    def terminate(self):
        """
        Terminate audio stream. Users cannot call start() again to detect.

        :return: None
        """
        self.stream_in.stop_stream()
        self.stream_in.close()
        self.audio.terminate()
