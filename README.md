# YouTube Video Downloader

A Flask web application that allows you to download YouTube videos in various formats and qualities.

## Prerequisites

1. Python 3.6 or higher
2. FFmpeg (required for merging video and audio)

### Installing FFmpeg

#### Windows
1. Download FFmpeg from the official website: https://ffmpeg.org/download.html
2. Extract the downloaded zip file
3. Add FFmpeg to your system PATH:
   - Open System Properties > Advanced > Environment Variables
   - Under System Variables, find and select "Path"
   - Click "Edit" and add the path to FFmpeg's bin folder
   - Click "OK" to save

#### Linux
```bash
sudo apt update
sudo apt install ffmpeg
```

#### macOS
```bash
brew install ffmpeg
```

## Installation

1. Clone this repository
2. Install the required Python packages:
```bash
pip install -r requirements.txt
```

## Usage

1. Run the Flask application:
```bash
python app.py
```

2. Open your web browser and navigate to `http://localhost:5000`
3. Enter a YouTube URL and select your desired format
4. Click download to save the video

## Features

- Download videos in various qualities
- Download audio-only formats
- Merge video and audio streams
- Preview video information before downloading 