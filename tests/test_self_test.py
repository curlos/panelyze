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
