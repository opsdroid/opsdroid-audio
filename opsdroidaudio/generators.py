
import logging

from gtts import gTTS


_LOGGER = logging.getLogger(__name__)

def google(text):
    return gTTS(text=text, lang='en')
