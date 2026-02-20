# Video Converter for Jellyfin

This application scans a directory and its subdirectories for video files and ensures they are in a Jellyfin-friendly format.

## Features

- **Container:** Converts non-mp4/mkv files to `.mp4`.
- **Video Codec:** Re-encodes video to H.264 (x264) if not already H.264 or H.265 (HEVC).
- **Audio Codec:** Re-encodes audio to AAC if not already AAC.
- **Backup:** Original files are renamed with a `.bak` extension.
- **Output:** New files are always `.mp4` if conversion is required.

## Requirements

- Python 3.12+
- `uv` package manager
- `ffmpeg` installed on your system and available in PATH.

## Usage

1.  **Install dependencies:**
    Navigate to this directory and run:
    ```bash
    uv sync
    ```

2.  **Run the converter:**
    ```bash
    uv run main.py /path/to/your/video/library
    ```
    
    Or if you are in the root of the repo:
    ```bash
    uv run video_converter/main.py /path/to/your/video/library
    ```

## Logic Details

- Allowed input extensions: mp4, mkv, avi, mov, flv, wmv, webm, m4v, mpg, mpeg, 3gp.
- Target format:
    - Container: `.mp4`
    - Video: `libx264` (H.264)
    - Audio: `aac`
- If a file is already compliant (e.g., an `.mkv` with H.264 and AAC), it is skipped.
