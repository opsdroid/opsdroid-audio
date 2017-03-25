"""Speech to text recognizer functions."""
import logging

from speech_recognition import Recognizer, AudioData, UnknownValueError


_LOGGER = logging.getLogger(__name__)


def google_cloud(config, data, sample_rate):
    """Perform speech recognition using Google Cloud."""
    audio_data = AudioData(data, sample_rate, 2)
    try:
        text = Recognizer().recognize_google_cloud(audio_data,
                                                   credentials_json=None,
                                                   language="en-GB",
                                                   preferred_phrases=None,
                                                   show_all=False)
    except UnknownValueError:
        text = ""
        _LOGGER.warning("No speech found in audio.")
    return text


def sphinx(config, data, sample_rate):
    """Perform speech recognition using sphinx."""
    audio_data = AudioData(data, sample_rate, 2)
    try:
        text = Recognizer().recognize_sphinx(audio_data,
                                             language="en-US",
                                             keyword_entries=None,
                                             show_all=False)
    except UnknownValueError:
        text = ""
        _LOGGER.warning("No speech found in audio.")
    return text
