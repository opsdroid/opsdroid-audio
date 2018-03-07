"""Text to speech generator functions."""
import logging
import tempfile
from subprocess import call
import re

from playsound import playsound
from gtts import gTTS  # pylint: disable=import-error

_LOGGER = logging.getLogger(__name__)


def prepare_url(text):
    """Transform url found in text for better voice understanding."""
    text = text.replace("/www.", "/")
    url = re.search(r'(https?:\/\/(\w+.\w+).*)', text)
    text = text.split(" ")
    text[text.index(url.group(1))] = "a link to {}".format(url.group(2))

    return " ".join(text)


def google(config, text):
    """Generate speech with Google."""
    # pylint: disable=broad-except
    # gTTS is a poorly written library and only throws broad Exceptions which
    # we need to catch.
    try:
        speech = gTTS(text=prepare_url(text), lang='en')
    except Exception:
        speech = None
    with tempfile.NamedTemporaryFile() as temp:
        try:
            speech.write_to_fp(temp)
            playsound(temp.name)
        except AttributeError:
            _LOGGER.error("No sound to play")


def apple_say(config, text):
    """Generate speech for the `say` command on MacOS."""
    text = prepare_url(text)
    try:
        call(["say", "-v", config["voice"], text])
    except KeyError:
        call(["say", text])
