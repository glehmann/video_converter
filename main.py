import os
import sys
import argparse
import ffmpeg
from pathlib import Path
from typing import Any

# Constants
ALLOWED_EXTENSIONS: set[str] = {
    ".mp4",
    ".mkv",
    ".avi",
    ".mov",
    ".flv",
    ".wmv",
    ".webm",
    ".m4v",
    ".mpg",
    ".mpeg",
    ".3gp",
}
TARGET_EXT: str = ".mp4"
TARGET_VIDEO_CODEC_CHECK: set[str] = {"h264", "hevc", "h265"}
TARGET_AUDIO_CODEC_CHECK: set[str] = {"aac"}
TARGET_VIDEO_ENCODER: str = "libx264"
TARGET_AUDIO_ENCODER: str = "aac"


def get_streams(file_path: str) -> list[dict[str, Any]] | None:
    """Probes the file to get stream information."""
    try:
        probe = ffmpeg.probe(file_path)
        return probe.get("streams", [])
    except ffmpeg.Error as e:
        print(
            f"Error probing {file_path}: {e.stderr.decode() if e.stderr else str(e)}",
            file=sys.stderr,
        )
        return None


def process_file(file_path: Path, dry_run: bool = False) -> None:
    """Checks and converts the video file if necessary."""
    path = Path(file_path)

    # Check if it's a video file based on extension
    if path.suffix.lower() not in ALLOWED_EXTENSIONS:
        return

    streams = get_streams(str(path))
    if not streams:
        print(f"  Skipping {file_path}: Could not probe streams.")
        return

    # Analyze streams to determine if conversion is needed
    reasons: list[str] = []
    if path.suffix.lower() not in [".mp4", ".mkv"]:
        reasons.append(f"container {path.suffix}")

    output_kwargs: dict[str, Any] = {"map": 0}

    # Iterate through all streams to configure output
    for i, stream in enumerate(streams):
        codec_type = stream.get("codec_type")
        codec_name = stream.get("codec_name", "unknown").lower()
        bit_rate = stream.get("bit_rate")

        if codec_type == "video":
            # Check if it's an attached picture (cover art)
            disposition = stream.get("disposition", {})
            is_attached_pic = disposition.get("attached_pic") == 1

            if is_attached_pic:
                output_kwargs[f"c:{i}"] = "copy"
            elif codec_name not in TARGET_VIDEO_CODEC_CHECK:
                reasons.append(f"video codec {codec_name}")
                output_kwargs[f"c:{i}"] = TARGET_VIDEO_ENCODER
                if bit_rate:
                    output_kwargs[f"b:{i}"] = bit_rate
            else:
                output_kwargs[f"c:{i}"] = "copy"

        elif codec_type == "audio":
            if codec_name not in TARGET_AUDIO_CODEC_CHECK:
                reasons.append(f"audio codec {codec_name}")
                output_kwargs[f"c:{i}"] = TARGET_AUDIO_ENCODER
                if bit_rate:
                    output_kwargs[f"b:{i}"] = bit_rate
            else:
                output_kwargs[f"c:{i}"] = "copy"

        elif codec_type == "subtitle":
            if codec_name in {"subrip", "ass", "ssa", "webvtt", "mov_text"}:
                # Note: We don't add to reasons here (subtitles alone don't trigger conversion)
                output_kwargs[f"c:{i}"] = "mov_text"
            else:
                output_kwargs[f"c:{i}"] = "copy"

        else:
            output_kwargs[f"c:{i}"] = "copy"

    if not reasons:
        print(f"  [OK] {file_path} is already compliant.")
        return

    # Conversion needed
    output_path = path.with_suffix(TARGET_EXT)
    temp_output_path = path.with_name(f"{path.stem}_temp{TARGET_EXT}")
    backup_path = path.with_name(f"{path.name}.bak")

    if dry_run:
        print(f"  [DRY RUN] Would convert {path} (Reason: {', '.join(reasons)})")
        return

    print(f"  [CONVERTING] {file_path} (Reason: {', '.join(reasons)})")
    input_node = ffmpeg.input(str(path))

    # Run FFMPEG
    try:
        # Run conversion to temporary file
        (
            ffmpeg.output(input_node, str(temp_output_path), **output_kwargs).run(
                cmd="ffmpeg", overwrite_output=True
            )
        )

        # Backup original
        os.rename(path, backup_path)

        # Rename temp to target
        os.rename(temp_output_path, output_path)
        print(f"  [SUCCESS] Created {output_path}")
        print(f"  [BACKUP] Original renamed to {backup_path.name}")

    except ffmpeg.Error as e:
        print(f"  [ERROR] FFMPEG failed for {file_path}", file=sys.stderr)
        # Try to print stderr from ffmpeg
        if e.stderr:
            print(e.stderr.decode(), file=sys.stderr)

        # Cleanup temp file if it exists
        if temp_output_path.exists():
            os.remove(temp_output_path)
    except Exception as e:
        print(f"  [ERROR] Unexpected error: {e}", file=sys.stderr)
        if temp_output_path.exists():
            os.remove(temp_output_path)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scan and normalize video files to mp4/h264/aac."
    )
    parser.add_argument("directory", help="The root directory to scan.")
    parser.add_argument(
        "-n",
        "--dry-run",
        action="store_true",
        help="Show what would be done without actually doing it.",
    )
    args = parser.parse_args()

    root_dir = Path(args.directory)
    if not root_dir.exists() or not root_dir.is_dir():
        print(f"Error: {root_dir} is not a valid directory.")
        sys.exit(1)

    for root, dirs, files in os.walk(root_dir):
        for file in files:
            file_path = Path(root) / file
            # Check for backup files to avoid processing them
            if file_path.suffix == ".bak":
                continue

            # Simple check before calling process (optimization)
            if file_path.suffix.lower() in ALLOWED_EXTENSIONS:
                process_file(file_path, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
