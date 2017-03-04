"""The main class for opsdroid audio."""
import os
import sys
import signal
import logging
import threading
from Queue import Queue
from datetime import datetime

import yaml
import websocket
import requests

import opsdroidaudio.audio as audio
from opsdroidaudio import recognizers, generators, speakers


logging.basicConfig()
_LOGGER = logging.getLogger()
_LOGGER.setLevel(logging.DEBUG)


class OpsdroidAudio:
    """The opsdroid audio class."""

    def __init__(self):
        """Initialize variables and load config."""
        self.threads = []
        self.interrupted = Queue()
        self.speak_queue = Queue()
        self.lock = threading.Lock()
        self.config = self.load_config_file([
                "./configuration.yaml",
                os.path.join(os.path.expanduser("~"),
                             ".opsdroidaudio/configuration.yaml"),
                "/etc/opsdroidaudio/configuration.yaml"
                ])
        self.opsdroid_host = self.config.get("opsdroid", {"host": "localhost"}).get("host", "localhost")
        self.opsdroid_port = self.config.get("opsdroid", {"port": "8080"}).get("port", "8080")
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
        self.threads.append(threading.Thread(target=self.detector.start,kwargs={
                                        "detected_callback": self.detected_callback,
                                        "recording_callback": self.recording_callback,
                                        "interrupt_check": self.interrupt_callback,
                                        "sleep_time": 0.03}))
        self.threads.append(threading.Thread(target=self.await_speech))
        self.start_socket()

        for thread in self.threads:
            thread.start()
        for thread in self.threads:
            thread.join()

        self.detector.terminate()

    def signal_handler(self, signal, frame):
        """Handle SIGINT."""
        self.interrupted.put(True)

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

    def get_websocket(self):
        r = requests.post("http://{}:{}/connector/websocket".format(self.opsdroid_host, self.opsdroid_port), data = {})
        response = r.json()
        _LOGGER.debug(response)
        return response["socket"]

    def start_socket(self):
        try:
            self.websocket = self.get_websocket()
        except ConnectionError as e:
            self.socket_error(None, e)
            return
        self.ws = websocket.WebSocketApp(
                "ws://{}:{}/connector/websocket/{}".format(self.opsdroid_host, self.opsdroid_port, self.websocket),
                on_message = self.socket_message,
                on_close = self.socket_close,
                on_error = self.socket_error)
        self.threads.append(threading.Thread(target=self.ws.run_forever))

    def socket_message(self, ws, message):
        _LOGGER.info("Bot says '%s'", message)
        self.speak_queue.put(message)

    def socket_close(self, ws):
        self.start_socket()
        time.sleep(5)

    def socket_error(self, ws, error):
        self.start_socket()
        time.sleep(5)

    def interrupt_callback(self):
        """Callback to notify the hotword detector of an interrupt."""
        return not self.interrupted.empty()

    def detected_callback(self, data, detector):
        """Callback for when the hotword has been detected."""
        audio.play_audio_file(audio.DETECT_DING)

    def recording_callback(self, data, detector):
        """Callback for handling a recording."""
        # start_time = datetime.now()
        audio.play_audio_file(audio.DETECT_DONG)

        try:
            self.lock.acquire()
            user_text = self.recognize_text(data, detector.detector.SampleRate())
        finally:
            self.lock.release()

        self.ws.send(user_text)
        _LOGGER.info("User said '%s'" ,user_text)

        # end_time = datetime.now()

        # _LOGGER.info("Response took %f seconds.", (end_time - start_time).total_seconds())

    def await_speech(self):
        while True:
            if not self.speak_queue.empty():
                speech = self.generate_text(self.speak_queue.get())
                try:
                    self.lock.acquire()
                    self.speak(speech)
                finally:
                    self.lock.release()

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
    signal.signal(signal.SIGINT, sys.exit)

    opsdroid_audio.start()
