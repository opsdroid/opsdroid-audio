#!/bin/bash
#
# Script to get the snowboy repository and create a working python module from it.

# Set variables
INSTALL_DIR=${1:-${PWD}}
CURRENT_DIR=${PWD}
TMP_DIR="/tmp/snowboy"
SNOWBOY_VERSION="v1.1.0"
SNOWBOY_REPOSITORY="https://github.com/Kitt-AI/snowboy.git"

# Get the snowboy code
if [ $(which git) ]
then
  echo "Downloading snowboy."
  git clone --branch $SNOWBOY_VERSION $SNOWBOY_REPOSITORY $TMP_DIR
  if [ ! $? -eq 0 ]; then
    echo "Error: Failed to clone the snowboy repository."; exit 1
  fi
else
  echo "Error: Installing snowboy requires git."
  exit 1
fi

# Check for swig and if swig3.0 installed update the Makefile
if [ ! $(which swig) ]; then
  if [ $(which swig3.0) ]; then
    echo "Detected swig3.0."
    sed -i '' 's/SWIG := swig/SWIG := swig3.0/g' $TMP_DIR/swig/Python/Makefile
  else
    echo "Error: Installing snowboy requires swig3.0."
    exit 1
  fi
fi

# Check if python3 and if so update the Makefile
if [[ $(python --version 2>&1) =~ ^.*3\.[0-9]+\.[0-9]+$ ]]; then
  echo "Setting build for python 3"
  sed -i '' 's/python-config/python3-config/g' $TMP_DIR/swig/Python/Makefile
else
  echo "Setting build for python 2"
fi

# Make the module
echo "Building..."
cd $TMP_DIR/swig/Python
make
if [ ! $? -eq 0 ]; then
  echo "Error: Build failed."
  exit 1
fi
cd $CURRENT_DIR

# Create an init file for the module
touch $TMP_DIR/swig/Python/__init__.py

# Move the module to the install directory
echo "Installing module to $INSTALL_DIR/snowboydetect."
mv $TMP_DIR/swig/Python $INSTALL_DIR/snowboydetect
if [ ! $? -eq 0 ]; then
  echo "Error: Failed to install module to $INSTALL_DIR/snowboydetect."
  exit 1
fi

# Clean up
rm -r $TMP_DIR

echo "Done"
