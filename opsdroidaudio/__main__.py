"""The main class for opsdroid audio."""
import os
import sys
import signal
import logging
import threading
import time
from Queue import Queue
from datetime import datetime

import yaml
import websocket
import requests

import opsdroidaudio.audio as audio
from opsdroidaudio import recognizers, generators


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
        self.websocket_open = False
        self.config = self.load_config_file()
        self.opsdroid_host = self.config.get(
            "opsdroid", {"host": "localhost"}).get("host", "localhost")
        self.opsdroid_port = self.config.get(
            "opsdroid", {"port": "8080"}).get("port", "8080")
        self.model = self.load_model()

    def start(self):
        """Start listening and processing audio."""
        self.detector = audio.HotwordDetector(self.model, sensitivity=0.4,
                                              recording_threshold=3000)
        print('Listening... Press Ctrl+C to exit')

        # main loop
        self.threads.append(
            threading.Thread(target=self.detector.start, kwargs={
                "detected_callback": self.detected_callback,
                "recording_callback": self.recording_callback,
                "interrupt_check": self.interrupt_callback,
                "sleep_time": 0.03}))
        self.threads.append(threading.Thread(target=self.await_speech))
        self.threads.append(threading.Thread(target=self.start_socket))

        for thread in self.threads:
            thread.start()
        for thread in self.threads:
            thread.join()

        self.detector.terminate()

    def signal_handler(self, signalcode, frame):
        """Handle SIGINT."""
        _LOGGER.info("User pressed ^C, exiting...")
        self.websocket.close()
        self.interrupted.put(True)

    @staticmethod
    def critical(message, code):
        """Exit with critical error."""
        _LOGGER.critical(message)
        sys.exit(1)

    def load_model(self):
        """Locate the model file to use."""
        try:
            if os.path.exists(self.config.get("hotword")):
                return self.config.get("hotword")
            else:
                pwd, _ = os.path.split(os.path.realpath(__file__))
                model = "{}/models/{}.pmdl".format(
                    pwd, self.config.get("hotword"))
                if os.path.exists(model):
                    return model
                else:
                    self.critical(
                        "Unable to find hotword {}".format(self.model), 1)
        finally:
            _LOGGER.info("Loaded model %s", self.config.get("hotword"))

    def load_config_file(self):
        """Load a yaml config file from path."""
        config_paths = ["./configuration.yaml",
                        os.path.join(os.path.expanduser("~"),
                                     ".opsdroidaudio/configuration.yaml"),
                        "/etc/opsdroidaudio/configuration.yaml"]
        config_path = ""
        for possible_path in config_paths:
            if not os.path.isfile(possible_path):
                _LOGGER.debug("Config file " + possible_path +
                              " not found")
            else:
                config_path = possible_path
                break

        if not config_path:
            self.critical("No configuration files found", 1)

        try:
            with open(config_path, 'r') as stream:
                _LOGGER.info("Loaded config from %s", config_path)
                return yaml.load(stream)
        except yaml.YAMLError as error:
            self.critical(error, 1)
        except FileNotFoundError as error:
            self.critical(str(error), 1)

    def get_websocket(self):
        """Request a new websocket from opsdroid."""
        response = requests.post("http://{}:{}/connector/websocket".format(
            self.opsdroid_host, self.opsdroid_port), data={})
        output = response.json()
        _LOGGER.debug(output)
        return output["socket"]

    def start_socket(self):
        """Connect to opsdroid with a websocket."""
        try:
            self.websocket_url = self.get_websocket()
        except requests.ConnectionError as error:
            self.socket_error(None, error)
            return
        self.websocket = websocket.WebSocketApp(
            "ws://{}:{}/connector/websocket/{}".format(
                self.opsdroid_host, self.opsdroid_port, self.websocket_url),
            on_message=self.socket_message,
            on_close=self.socket_close,
            on_error=self.socket_error)
        self.websocket_open = True
        self.websocket.run_forever()

    def socket_message(self, ws, message):
        """Process a new message form the socket."""
        _LOGGER.info("Bot says '%s'", message)
        self.speak_queue.put(message)

    def socket_close(self, ws=None):
        """Handle the socket closing."""
        _LOGGER.info("Websocket closed, attempting reconnect in 5 seconds")
        if self.interrupted.empty():
            self.websocket_open = False
            time.sleep(5)
            self.start_socket()
        else:
            return

    def socket_error(self, ws, error):
        """Handle an error on the socket."""
        _LOGGER.error("Unable to connect to opsdroid.")
        if self.websocket_open:
            self.websocket.close()
        else:
            self.socket_close()

    def interrupt_callback(self):
        """Callback to notify the hotword detector of an interrupt."""
        return not self.interrupted.empty()

    @staticmethod
    def detected_callback(data, detector):
        """Callback for when the hotword has been detected."""
        audio.play_audio_file(audio.DETECT_DING)

    def recording_callback(self, data, detector):
        """Callback for handling a recording."""
        audio.play_audio_file(audio.DETECT_DONG)

        start_time = datetime.now()
        user_text = self.recognize_text(data, detector.detector.SampleRate())
        end_time = datetime.now()
        _LOGGER.info("Speech recognition took %f seconds.",
                     (end_time - start_time).total_seconds())

        self.websocket.send(user_text)
        _LOGGER.info("User said '%s'", user_text)

    def await_speech(self):
        """Thread to play speech when received."""
        while self.interrupted.empty():
            if not self.speak_queue.empty():
                self.generate_speech(self.speak_queue.get())

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

    def generate_speech(self, text):
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
        finally:
            _LOGGER.debug("Done.")


if __name__ == "__main__":
    oaudio = OpsdroidAudio()

    # capture SIGINT signal, e.g., Ctrl+C
    signal.signal(signal.SIGINT, oaudio.signal_handler)

    oaudio.start()
