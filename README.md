# opsdroid audio

[![Build Status](https://travis-ci.org/opsdroid/opsdroid-audio.svg?branch=master)](https://travis-ci.org/opsdroid/opsdroid-audio) [![Updates](https://pyup.io/repos/github/opsdroid/opsdroid-audio/shield.svg)](https://pyup.io/repos/github/opsdroid/opsdroid-audio/)


**This application is an early alpha and should not be used yet.**

A companion python application for [opsdroid][opsdroid] which adds hotwords, speech recognition and audio responses.

This application uses [snowboy hotword detection][snowboy] to allow you to activate opsdroid by saying a hotword followed by your message. Unlike other voice assistants you can train your own hotword or choose from the vast catalogue provided by [kitt.ai][snowboy].

Once awoken opsdroid audio will record your voice until you stop speaking and then analyse what you said using your choice of service from a range of speech-to-text services.

When the text has been generated it will be sent off to opsdroid for analysis by the skills you have configured.

Finally when opsdroid responds this application will run the response through your choice of text-to-speech engines and will then play back the audio response.

## Privacy

If you have privacy concerns when using voice assistant applications then you will be happy to hear that opsdroid audio supports both local and cloud based services.

When opsdroid audio listens for your hotword it only retains the last few seconds of sound and processes it locally. This means nothing leaves your device until you say the hotword, and even then maybe not.

When you trigger the hotword and opsdroid audio begins recording your voice it is only sent to the services you configure. If you choose to use a local speech recognition service then no sound will ever leave the application. Any sound sent to cloud based services will be encrypted in transit and it is your decision whether to trust that provider with your data or not.

## Installation
TODO

## Configuration
TODO

## Recognizers
List of currently available speech recognition services:

 * Google Cloud (cloud)
 * Sphinx (local) **Coming soon!**

## Generators
List of test-to-speech engines.

 * Google (cloud)
 * Apple Say (local) *- Apple macOS only*


## Contributing
Pull requests are welcome!

## License
GPLv3

Hotword components from [snowboy][snowboy-github] redistributed here are [Apache 2.0][apache20] licensed and are [compatible][apache-gpl-compatible] for use in a GPLv3 project.

[apache20]: http://www.apache.org/licenses/LICENSE-2.0
[apache-gpl-compatible]: https://www.apache.org/licenses/GPL-compatibility.html
[opsdroid]: https://opsdroid.github.io/
[snowboy]: https://snowboy.kitt.ai/
[snowboy-github]: https://github.com/Kitt-AI/snowboy#introduction
