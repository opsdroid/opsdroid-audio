import os
import sys
import signal
import logging
from datetime import datetime

import yaml

import opsdroidaudio.audio as audio
from opsdroidaudio import recognizers, generators, speakers


logging.basicConfig()
_LOGGER = logging.getLogger()
_LOGGER.setLevel(logging.DEBUG)

interrupted = False


def signal_handler(signal, frame):
    global interrupted
    interrupted = True

def interrupt_callback():
    global interrupted
    return interrupted

def detected_callback(data, detector):
    audio.play_audio_file(audio.DETECT_DING)

def recording_callback(data, detector):
    start_time = datetime.now()
    audio.play_audio_file(audio.DETECT_DONG)

    user_text = recognize_text(data, detector.detector.SampleRate())
    _LOGGER.info("User said '%s'" ,user_text)

    # TODO: Send user_text to opsdroid and get back bot response
    bot_response = user_text  # For testing
    _LOGGER.info("Bot says '%s'" ,bot_response)

    speech = generate_text(bot_response)
    end_time = datetime.now()
    _LOGGER.info("Response took %f seconds.", (end_time - start_time).total_seconds())

    speak(speech)

def recognize_text(data, sample_rate):
    _LOGGER.debug("Recognizing speech...")
    return recognizers.google_cloud(data, sample_rate)

def generate_text(text):
    _LOGGER.debug("Generating speech...")
    return generators.google(text)

def speak(speech):
    _LOGGER.debug("Speaking...")
    return speakers.google(speech)

def load_config_file(config_paths):
    """Load a yaml config file from path."""
    config_path = ""
    for possible_path in config_paths:
        if not os.path.isfile(possible_path):
            _LOGGER.debug("Config file " + possible_path +
                          " not found")
        else:
            config_path = possible_path
            break

    if not config_path:
        critical("No configuration files found", 1)

    try:
        with open(config_path, 'r') as stream:
            _LOGGER.info("Loaded config from %s", config_path)
            return yaml.load(stream)
    except yaml.YAMLError as error:
        critical(error, 1)
    except FileNotFoundError as error:
        critical(str(error), 1)

def critical(message, code):
    _LOGGER.critical(message)
    sys.exit(1)

def main():
    config = load_config_file([
            "./configuration.yaml",
            os.path.join(os.path.expanduser("~"),
                         ".opsdroidaudio/configuration.yaml"),
            "/etc/opsdroidaudio/configuration.yaml"
            ])

    if os.path.exists(config.get("model")):
        model = config.get("model")
    else:
        pwd, _ = os.path.split(os.path.realpath(__file__))
        model = "{}/models/{}.pmdl".format(pwd, config.get("model"))
        if not os.path.exists(model):
            critical("Unable to find model {}".format(model), 1)

    _LOGGER.info("Loaded model %s", config.get("model"))

    # capture SIGINT signal, e.g., Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)

    detector = audio.HotwordDetector(model, sensitivity=0.4)
    print('Listening... Press Ctrl+C to exit')

    # main loop
    detector.start(detected_callback=detected_callback,
                   recording_callback=recording_callback,
                   interrupt_check=interrupt_callback,
                   sleep_time=0.03)

    detector.terminate()

if __name__ == "__main__":
    main()
