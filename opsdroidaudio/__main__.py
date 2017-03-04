"""The main class for opsdroid audio."""
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


class OpsdroidAudio:
    """The opsdroid audio class."""

    def __init__(self):
        """Initialize variables and load config."""
        self.interrupted = False
        self.config = self.load_config_file([
                "./configuration.yaml",
                os.path.join(os.path.expanduser("~"),
                             ".opsdroidaudio/configuration.yaml"),
                "/etc/opsdroidaudio/configuration.yaml"
                ])

        if os.path.exists(self.config.get("hotword")):
            self.model = self.config.get("hotword")
        else:
            pwd, _ = os.path.split(os.path.realpath(__file__))
            self.model = "{}/models/{}.pmdl".format(pwd, self.config.get("hotword"))
            if not os.path.exists(self.model):
                critical("Unable to find model for hotword {}".format(self.model), 1)

        _LOGGER.info("Loaded model %s", self.config.get("hotword"))

    def start(self):
        """Start listening and processing audio."""
        self.detector = audio.HotwordDetector(self.model, sensitivity=0.4,
                                              recording_threshold=3000)
        print('Listening... Press Ctrl+C to exit')

        # main loop
        self.detector.start(detected_callback=self.detected_callback,
                            recording_callback=self.recording_callback,
                            interrupt_check=self.interrupt_callback,
                            sleep_time=0.03)

        self.detector.terminate()

    def signal_handler(self, signal, frame):
        """Handle SIGINT."""
        self.interrupted = True

    def critical(self, message, code):
        """Exit with critical error."""
        _LOGGER.critical(message)
        sys.exit(1)

    def load_config_file(self, config_paths):
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

    def interrupt_callback(self):
        """Callback to notify the hotword detector of an interrupt."""
        return self.interrupted

    def detected_callback(self, data, detector):
        """Callback for when the hotword has been detected."""
        audio.play_audio_file(audio.DETECT_DING)

    def recording_callback(self, data, detector):
        """Callback for handling a recording."""
        start_time = datetime.now()
        audio.play_audio_file(audio.DETECT_DONG)

        user_text = self.recognize_text(data, detector.detector.SampleRate())
        _LOGGER.info("User said '%s'" ,user_text)

        # TODO: Send user_text to opsdroid and get back bot response
        bot_response = user_text  # For testing
        _LOGGER.info("Bot says '%s'", bot_response)

        speech = self.generate_text(bot_response)
        end_time = datetime.now()
        _LOGGER.info("Response took %f seconds.", (end_time - start_time).total_seconds())

        self.speak(speech)

    def recognize_text(self, data, sample_rate):
        """Convert raw user audio into text."""
        _LOGGER.debug("Recognizing speech...")
        try:
            config = self.config["speech"]["recognizer"]
            if config["name"] == "google_cloud":
                return recognizers.google_cloud(config, data, sample_rate)
            else:
                raise KeyError
        except KeyError:
            self.critical("No speech recognizer configured!", 1)

    def generate_text(self, text):
        """Generate speech audio from bot response text."""
        _LOGGER.debug("Generating speech...")
        try:
            config = self.config["speech"]["generator"]
            if config["name"] == "google":
                return generators.google(config, text)
            elif config["name"] == "apple_say":
                return generators.apple_say(config, text)
            else:
                raise KeyError
        except KeyError:
            self.critical("No speech generator configured!", 1)

    def speak(self, speech):
        """Play generated speech audio to the user."""
        _LOGGER.debug("Speaking...")
        try:
            config = self.config["speech"]["generator"]
            if config["name"] == "google":
                return speakers.google(config, speech)
            elif config["name"] == "apple_say":
                return speakers.apple_say(config, speech)
            else:
                raise KeyError
        except KeyError:
            self.critical("No speech generator configured!", 1)

if __name__ == "__main__":
    opsdroid_audio = OpsdroidAudio()

    # capture SIGINT signal, e.g., Ctrl+C
    signal.signal(signal.SIGINT, opsdroid_audio.signal_handler)

    opsdroid_audio.start()
