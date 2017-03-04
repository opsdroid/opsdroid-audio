
import tempfile
import logging

from playsound import playsound


_LOGGER = logging.getLogger(__name__)


def google(speech):
    with tempfile.NamedTemporaryFile() as temp:
        speech.write_to_fp(temp)
        try:
            playsound(temp.name)
        except AttributeError:
            _LOGGER.error("No sound to play")
