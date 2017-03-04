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

    def __init__(self):
        self.interrupted = False

    def signal_handler(self, signal, frame):
        self.interrupted = True

    def interrupt_callback(self):
        return self.interrupted

    def detected_callback(self, data, detector):
        audio.play_audio_file(audio.DETECT_DING)

    def recording_callback(self, data, detector):
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
        _LOGGER.debug("Recognizing speech...")
        return recognizers.google_cloud(data, sample_rate)

    def generate_text(self, text):
        _LOGGER.debug("Generating speech...")
        return generators.google(text)

    def speak(self, speech):
        _LOGGER.debug("Speaking...")
        return speakers.google(speech)

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

    def critical(self, message, code):
        _LOGGER.critical(message)
        sys.exit(1)

    def main(self):
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

        # capture SIGINT signal, e.g., Ctrl+C
        signal.signal(signal.SIGINT, self.signal_handler)

        self.detector = audio.HotwordDetector(self.model, sensitivity=0.4)
        print('Listening... Press Ctrl+C to exit')

        # main loop
        self.detector.start(detected_callback=self.detected_callback,
                       recording_callback=self.recording_callback,
                       interrupt_check=self.interrupt_callback,
                       sleep_time=0.03)

        self.detector.terminate()

if __name__ == "__main__":
    opsdroid_audio = OpsdroidAudio()
    opsdroid_audio.main()
