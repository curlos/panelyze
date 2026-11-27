import pytest

import janai
import self_test


@pytest.mark.skipif(
    not janai.can_use_coreml(), reason="Core ML is only used on Apple Silicon Macs"
)
def test_the_best_upscaler_check_runs_core_ml_on_this_computer(tmp_path):
    assert (
        self_test.check_best_upscaler_libraries(str(tmp_path))
        == "spandrel loads, and Core ML converts and runs a model"
    )


def test_the_best_upscaler_check_works_without_core_ml(tmp_path, monkeypatch):
    monkeypatch.setattr(janai, "can_use_coreml", lambda: False)

    assert (
        self_test.check_best_upscaler_libraries(str(tmp_path))
        == "spandrel loads (Core ML isn't used on this computer)"
    )


def test_the_best_upscaler_check_is_part_of_the_self_test():
    assert self_test.check_best_upscaler_libraries in self_test.CHECKS


def test_the_video_check_fails_when_ffmpeg_is_not_the_one_that_comes_with_the_app(
    monkeypatch, tmp_path
):
    import moviepy.config

    # Like imageio-ffmpeg 0.5.1 on an Apple Silicon Mac: no ffmpeg of its own, so MoviePy ran the computer's ("ffmpeg" on the PATH, e.g. Homebrew's), which users don't have.
    monkeypatch.setattr(moviepy.config, "FFMPEG_BINARY", "ffmpeg")

    with pytest.raises(
        AssertionError, match="isn't the one that comes with imageio-ffmpeg"
    ):
        self_test.check_video(str(tmp_path))
