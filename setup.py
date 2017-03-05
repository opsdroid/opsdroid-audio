#!/usr/bin/env python3
import os
from setuptools import setup, find_packages
from opsdroidaudio.const import __version__

PACKAGE_NAME = 'opsdroidaudio'
HERE = os.path.abspath(os.path.dirname(__file__))

PACKAGES = find_packages(exclude=['tests', 'tests.*', 'modules',
                                  'modules.*', 'docs', 'docs.*'])

REQUIRES = [
    'google-api-python-client==1.6.2',
    'playsound==1.2.1',
    'PyAudio==0.2.9',
    'PyYAML==3.11',
    'requests==2.13.0',
    'SpeechRecognition==3.6.0',
    'websocket-client==0.40.0',
]

setup(
    name=PACKAGE_NAME,
    version=__version__,
    license='GNU GENERAL PUBLIC LICENSE V3',
    url='',
    download_url='',
    author='Jacob Tomlinson',
    author_email='jacob@tom.linson.uk',
    description='Speech recognition and audio responses for opsdroid.',
    packages=PACKAGES,
    include_package_data=True,
    zip_safe=False,
    platforms='any',
    install_requires=REQUIRES,
    test_suite='tests',
    keywords=['bot', 'chatops'],
    entry_points={
        'console_scripts': [
            'opsdroidaudio = opsdroidaudio.__main__:main'
        ]
    },
)
