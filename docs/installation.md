# Gamdl Installation Guide

## Table of Contents
- [Prerequisites](#prerequisites)
- [Installation Methods](#installation-methods)
  - [Pip Installation](#pip-installation)
  - [Source Installation](#source-installation)
  - [Docker Installation](#docker-installation)
- [Platform-Specific Instructions](#platform-specific-instructions)
- [Post-Installation Configuration](#post-installation-configuration)
- [Troubleshooting](#troubleshooting)

## Prerequisites

Before installing Gamdl, ensure your system meets the following requirements:

### Minimum System Requirements
- Python 3.8+
- pip (Python package manager)
- Git (optional, for source installation)

### Required Dependencies
- requests
- spotipy
- youtube-dl
- python-telegram-bot
- mutagen

### Optional Dependencies
- FFmpeg
- Docker (for containerized installation)

## Installation Methods

### Pip Installation

The recommended method for installing Gamdl is via pip:

```bash
# Install latest stable version
pip install gamdl

# Install with additional dependencies
pip install gamdl[full]


# Create virtual environment
python3 -m venv gamdl_env

# Activate virtual environment
# On Unix/macOS
source gamdl_env/bin/activate

# On Windows
gamdl_env\Scripts\activate

# Install Gamdl
pip install gamdl


# Clone repository
git clone https://github.com/your-username/gamdl.git
cd gamdl

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install package in editable mode
pip install -e .


# Pull official Docker image
docker pull gamdl/gamdl:latest

# Run Gamdl container
docker run -v /path/to/downloads:/downloads gamdl/gamdl



# docker-compose.yml
version: '3'
services:
  gamdl:
    image: gamdl/gamdl:latest
    volumes:
      - ./downloads:/downloads
    environment:
      - SPOTIFY_CLIENT_ID=your_client_id
      - SPOTIFY_CLIENT_SECRET=your_client_secret


