import pytest
from unittest.mock import MagicMock
import sys
from pathlib import Path
from pytest_mock import MockerFixture

# Add the project root to sys.path to import main
sys.path.append(str(Path(__file__).parent.parent))

from main import process_file, TARGET_VIDEO_ENCODER, TARGET_AUDIO_ENCODER


@pytest.fixture
def mock_ffmpeg(
    mocker: MockerFixture,
) -> tuple[MagicMock, MagicMock, MagicMock, MagicMock]:
    """Mocks ffmpeg module to avoid actual execution."""
    mock_probe: MagicMock = mocker.patch("ffmpeg.probe")
    mock_input: MagicMock = mocker.patch("ffmpeg.input")
    mock_output: MagicMock = mocker.patch("ffmpeg.output")

    # Mock the return value of ffmpeg.output to be an object with a .run() method
    mock_stream: MagicMock = MagicMock()
    mock_output.return_value = mock_stream
    mock_stream.run.return_value = None

    return mock_probe, mock_input, mock_output, mock_stream


@pytest.fixture
def mock_fs(mocker: MockerFixture) -> tuple[MagicMock, MagicMock, MagicMock]:
    """Mocks filesystem operations."""
    mock_rename: MagicMock = mocker.patch("os.rename")
    mock_remove: MagicMock = mocker.patch("os.remove")
    mock_exists: MagicMock = mocker.patch("pathlib.Path.exists", return_value=True)
    return mock_rename, mock_remove, mock_exists


def test_compliant_file_skipped(
    mock_ffmpeg: tuple[MagicMock, MagicMock, MagicMock, MagicMock],
    mock_fs: tuple[MagicMock, MagicMock, MagicMock],
) -> None:
    mock_probe, mock_input, mock_output, _ = mock_ffmpeg

    # Setup compliant file probe
    mock_probe.return_value = {
        "streams": [
            {"codec_type": "video", "codec_name": "h264"},
            {"codec_type": "audio", "codec_name": "aac"},
        ]
    }

    process_file(Path("test_video.mp4"))

    # Verify ffmpeg.input/output were NOT called
    mock_input.assert_not_called()
    mock_output.assert_not_called()


def test_video_conversion_needed(
    mock_ffmpeg: tuple[MagicMock, MagicMock, MagicMock, MagicMock],
    mock_fs: tuple[MagicMock, MagicMock, MagicMock],
) -> None:
    mock_probe, mock_input, mock_output, _ = mock_ffmpeg

    # Setup non-compliant video codec (mpeg4)
    mock_probe.return_value = {
        "streams": [
            {"codec_type": "video", "codec_name": "mpeg4", "bit_rate": "1000000"},
            {"codec_type": "audio", "codec_name": "aac", "bit_rate": "128000"},
        ]
    }

    process_file(Path("test_video.mp4"))

    # Verify input was called with correct path
    mock_input.assert_called_with("test_video.mp4")

    # Verify output arguments
    _, kwargs = mock_output.call_args

    # Check stream mappings and codecs
    assert kwargs["map"] == 0
    # Stream 0 (video): mpeg4 -> h264
    assert kwargs[f"c:{0}"] == TARGET_VIDEO_ENCODER
    assert kwargs[f"b:{0}"] == "1000000"
    # Stream 1 (audio): aac -> copy
    assert kwargs[f"c:{1}"] == "copy"


def test_audio_conversion_needed(
    mock_ffmpeg: tuple[MagicMock, MagicMock, MagicMock, MagicMock],
    mock_fs: tuple[MagicMock, MagicMock, MagicMock],
) -> None:
    mock_probe, mock_input, mock_output, _ = mock_ffmpeg

    # Setup non-compliant audio codec (mp3)
    mock_probe.return_value = {
        "streams": [
            {"codec_type": "video", "codec_name": "h264", "bit_rate": "2000000"},
            {"codec_type": "audio", "codec_name": "mp3", "bit_rate": "192000"},
        ]
    }

    process_file(Path("test_video.mkv"))

    mock_input.assert_called_with("test_video.mkv")
    _, kwargs = mock_output.call_args

    # Stream 0 (video): h264 -> copy
    assert kwargs[f"c:{0}"] == "copy"
    # Stream 1 (audio): mp3 -> aac
    assert kwargs[f"c:{1}"] == TARGET_AUDIO_ENCODER
    assert kwargs[f"b:{1}"] == "192000"


def test_subtitle_conversion(
    mock_ffmpeg: tuple[MagicMock, MagicMock, MagicMock, MagicMock],
    mock_fs: tuple[MagicMock, MagicMock, MagicMock],
) -> None:
    mock_probe, mock_input, mock_output, _ = mock_ffmpeg

    # Setup non-compliant subtitle (srt)
    mock_probe.return_value = {
        "streams": [
            {"codec_type": "video", "codec_name": "h264"},
            {"codec_type": "audio", "codec_name": "aac"},
            {"codec_type": "subtitle", "codec_name": "subrip"},
        ]
    }

    process_file(Path("test_video.avi"))

    mock_input.assert_called_with("test_video.avi")
    _, kwargs = mock_output.call_args

    # Stream 2 (subtitle): subrip -> mov_text
    assert kwargs[f"c:{2}"] == "mov_text"


def test_container_conversion_needed(
    mock_ffmpeg: tuple[MagicMock, MagicMock, MagicMock, MagicMock],
    mock_fs: tuple[MagicMock, MagicMock, MagicMock],
) -> None:
    mock_probe, mock_input, mock_output, _ = mock_ffmpeg

    # Setup compliant codecs but wrong container (avi)
    mock_probe.return_value = {
        "streams": [
            {"codec_type": "video", "codec_name": "h264"},
            {"codec_type": "audio", "codec_name": "aac"},
        ]
    }

    process_file(Path("test_video.avi"))

    mock_input.assert_called_with("test_video.avi")
    args, kwargs = mock_output.call_args

    # Output file should be .mp4 (checked via path logic in main)
    assert args[1].endswith(".mp4")

    # Codecs should be copied since they are compliant
    assert kwargs[f"c:{0}"] == "copy"
    assert kwargs[f"c:{1}"] == "copy"


def test_rename_logic(
    mock_ffmpeg: tuple[MagicMock, MagicMock, MagicMock, MagicMock],
    mock_fs: tuple[MagicMock, MagicMock, MagicMock],
) -> None:
    mock_probe, _, _, mock_stream = mock_ffmpeg
    mock_rename, _, _ = mock_fs

    # Force conversion
    mock_probe.return_value = {
        "streams": [{"codec_type": "video", "codec_name": "mpeg4"}]
    }

    process_file(Path("test.avi"))

    # Verify ffmpeg run was called
    mock_stream.run.assert_called_once()

    # Verify renames
    # 1. Original -> Backup
    mock_rename.assert_any_call(Path("test.avi"), Path("test.avi.bak"))
    # 2. Temp -> Target
    mock_rename.assert_any_call(Path("test_temp.mp4"), Path("test.mp4"))


def test_probe_failure_handles_gracefully(
    mock_ffmpeg: tuple[MagicMock, MagicMock, MagicMock, MagicMock],
    mock_fs: tuple[MagicMock, MagicMock, MagicMock],
) -> None:
    mock_probe, mock_input, mock_output, _ = mock_ffmpeg

    # Simulate probe failure
    import ffmpeg

    err = ffmpeg.Error("cmd", "stdout", b"stderr")
    mock_probe.side_effect = err

    process_file(Path("broken.mp4"))

    mock_input.assert_not_called()
    mock_output.assert_not_called()


def test_dry_run(
    mock_ffmpeg: tuple[MagicMock, MagicMock, MagicMock, MagicMock],
    mock_fs: tuple[MagicMock, MagicMock, MagicMock],
) -> None:
    mock_probe, mock_input, mock_output, mock_stream = mock_ffmpeg
    mock_rename, _, _ = mock_fs

    # Force conversion logic
    mock_probe.return_value = {
        "streams": [{"codec_type": "video", "codec_name": "mpeg4"}]
    }

    process_file(Path("test.avi"), dry_run=True)

    # ffmpeg.run should NOT be called
    mock_stream.run.assert_not_called()

    # Renames should NOT be called
    mock_rename.assert_not_called()


def test_hevc_preservation(
    mock_ffmpeg: tuple[MagicMock, MagicMock, MagicMock, MagicMock],
    mock_fs: tuple[MagicMock, MagicMock, MagicMock],
) -> None:
    mock_probe, mock_input, mock_output, _ = mock_ffmpeg

    # Setup HEVC video in non-compliant container to force check
    mock_probe.return_value = {
        "streams": [
            {"codec_type": "video", "codec_name": "hevc"},
            {"codec_type": "audio", "codec_name": "aac"},
        ]
    }

    process_file(Path("test.avi"))

    mock_input.assert_called_with("test.avi")
    _, kwargs = mock_output.call_args

    # HEVC video should be copied
    assert kwargs[f"c:{0}"] == "copy"
    # AAC audio should be copied
    assert kwargs[f"c:{1}"] == "copy"


def test_subtitle_only_does_not_trigger_conversion(
    mock_ffmpeg: tuple[MagicMock, MagicMock, MagicMock, MagicMock],
    mock_fs: tuple[MagicMock, MagicMock, MagicMock],
) -> None:
    mock_probe, mock_input, mock_output, _ = mock_ffmpeg

    # Setup compliant container, video, audio but non-compliant subtitle
    mock_probe.return_value = {
        "streams": [
            {"codec_type": "video", "codec_name": "h264"},
            {"codec_type": "audio", "codec_name": "aac"},
            {"codec_type": "subtitle", "codec_name": "subrip"},
        ]
    }

    process_file(Path("test_video.mp4"))

    # Verify ffmpeg.input/output were NOT called (file skipped)
    mock_input.assert_not_called()
    mock_output.assert_not_called()


def test_h264_preservation(
    mock_ffmpeg: tuple[MagicMock, MagicMock, MagicMock, MagicMock],
    mock_fs: tuple[MagicMock, MagicMock, MagicMock],
) -> None:
    mock_probe, mock_input, mock_output, _ = mock_ffmpeg

    # Setup H.264 video in non-compliant container to force check
    mock_probe.return_value = {
        "streams": [
            {"codec_type": "video", "codec_name": "h264"},
            {"codec_type": "audio", "codec_name": "aac"},
        ]
    }

    process_file(Path("test.avi"))

    mock_input.assert_called_with("test.avi")
    _, kwargs = mock_output.call_args

    # H.264 video should be copied
    assert kwargs[f"c:{0}"] == "copy"
    # AAC audio should be copied
    assert kwargs[f"c:{1}"] == "copy"


def test_attached_pic_preservation(
    mock_ffmpeg: tuple[MagicMock, MagicMock, MagicMock, MagicMock],
    mock_fs: tuple[MagicMock, MagicMock, MagicMock],
) -> None:
    mock_probe, mock_input, mock_output, _ = mock_ffmpeg

    # Setup file with main video (h264) and attached pic (mjpeg)
    mock_probe.return_value = {
        "streams": [
            {
                "codec_type": "video",
                "codec_name": "h264",
                "disposition": {"attached_pic": 0},
            },
            {
                "codec_type": "video",
                "codec_name": "mjpeg",
                "disposition": {"attached_pic": 1},  # This is cover art
            },
            {"codec_type": "audio", "codec_name": "aac"},
        ]
    }

    process_file(Path("test_cover.mp4"))

    # Should be compliant (h264/aac are valid, attached pic mjpeg is copied)
    # So process_file returns early because NO conversion needed for main streams
    # and mjpeg is handled as "copy".
    # Wait, my logic:
    # if attached_pic -> copy.
    # if h264 -> copy.
    # if aac -> copy.
    # So all streams are copy.
    # reason list is empty.
    # So "compliant".

    mock_input.assert_not_called()
    mock_output.assert_not_called()
