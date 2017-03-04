
import logging

from speech_recognition import Recognizer, AudioData


_LOGGER = logging.getLogger(__name__)


def google_cloud(data, sample_rate):
    audio_data = AudioData(data, sample_rate, 2)
    return Recognizer().recognize_google_cloud(audio_data,
                                               credentials_json = None,
                                               language = "en-GB",
                                               preferred_phrases = None,
                                               show_all = False)
