"""Text to speech generator functions."""
import logging

from gtts import gTTS


_LOGGER = logging.getLogger(__name__)

def google(config, text):
    """Generate speech with Google."""
    try:
        return gTTS(text=text, lang='en')
    except Exception:
        return None

def apple_say(config, text):
    """Generate speech for the `say` command on MacOS."""
    return text  # `say` can read text
