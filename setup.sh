#!/bin/bash

# Install system dependencies
apt-get update
apt-get install -y tesseract-ocr tesseract-ocr-ara tesseract-ocr-eng

# Install Python dependencies
pip install -r requirements.txt 