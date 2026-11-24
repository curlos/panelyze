import logging
from contextlib import contextmanager
import sys
import threading
from types import SimpleNamespace

import pytest

from gui_classes import AppOutput as app_output_module
from gui_classes.AppOutput import AppOutput, AppOutputStream


class FakeListView:
    def __init__(self):
        self.controls = []
        self.page = None

    def update(self):
        pass


def show_and_get_lines(output, list_view):
    # What the app's terminal shows after its next update.
    output.update_gui()
    return [control.value for control in list_view.controls]


@pytest.fixture
def app_output(tmp_path, monkeypatch):
    """
    An "AppOutput" with no real terminal behind it (like a packaged app opened from Finder). Inside "with app_output.installed():", it's sys.stdout and sys.stderr.
    """
    list_view = FakeListView()
    log_file_path = tmp_path / "logs" / "panelyze.log"
    output = AppOutput(list_view, str(log_file_path))
    output.original_stdout = None
    monkeypatch.setattr(app_output_module, "current_app_output", output)

    # pytest swaps sys.stdout/sys.stderr for its own capturing at the start of each test, so ours are swapped in inside the test itself.
    @contextmanager
    def installed():
        original_stdout, original_stderr = sys.stdout, sys.stderr
        sys.stdout = AppOutputStream(output, "stdout", None)
        sys.stderr = AppOutputStream(output, "stderr", None)
        try:
            yield
        finally:
            sys.stdout, sys.stderr = original_stdout, original_stderr

    return SimpleNamespace(
        installed=installed,
        lines=lambda: show_and_get_lines(output, list_view),
        log=lambda: log_file_path.read_text(),
    )


def test_prints_errors_and_logging_all_show_up(app_output):
    with app_output.installed():
        print("normal output")
        print("an error", file=sys.stderr)
        # Like the app: Python's own logging and warnings print to whatever sys.stderr is (pytest normally intercepts them).
        logging.StreamHandler(sys.stderr).handle(
            logging.makeLogRecord({"msg": "a logged warning", "levelno": logging.WARNING})
        )

    lines = "\n".join(app_output.lines())
    for text in ["normal output", "an error", "a logged warning"]:
        assert text in lines
        assert text in app_output.log()


def test_progress_bar_redraws_stay_on_one_line(app_output):
    with app_output.installed():
        print("Downloading")
        for percent in [0, 50, 100]:
            sys.stderr.write(f"\r{percent}%|bar|")
        sys.stderr.write("\n")

    assert app_output.lines() == ["Downloading", "100%|bar|"]
    # Only the finished line goes in the log, not every redraw.
    assert "0%|bar|" not in app_output.log().replace("100%|bar|", "")


def test_progress_bar_that_erases_itself_disappears(app_output):
    with app_output.installed():
        print("Building video")
        sys.stderr.write("\r  0%|bar|")
        sys.stderr.write("\r" + " " * 20 + "\r")
        print("Done")

    assert app_output.lines() == ["Building video", "Done"]


def test_unfinished_text_shows_right_away(app_output):
    with app_output.installed():
        sys.stdout.write("Loading model...")

    assert app_output.lines() == ["Loading model..."]

    with app_output.installed():
        sys.stdout.write(" done\n")

    assert app_output.lines() == ["Loading model... done"]


def test_no_lines_are_lost_when_several_threads_print(app_output):
    def print_lines(thread_number):
        for line_number in range(200):
            print(f"thread {thread_number} line {line_number}")

    with app_output.installed():
        threads = [threading.Thread(target=print_lines, args=[n]) for n in range(4)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

    assert len(app_output.lines()) == 800
    assert sorted(app_output.lines()) == sorted(
        f"thread {t} line {n}" for t in range(4) for n in range(200)
    )


def test_app_messages_also_go_to_the_log(app_output):
    from utils import add_line_to_terminal_output_list_view

    add_line_to_terminal_output_list_view(None, "ERROR: something broke", color="red")

    assert app_output.lines() == ["ERROR: something broke"]
    assert "ERROR: something broke" in app_output.log()


def test_tool_output_is_streamed_once_with_progress_as_one_line(app_output):
    from utils import ProcessManager

    command = [
        sys.executable,
        "-c",
        "import sys\nprint('start')\nfor p in (10, 60, 100): sys.stdout.write(f'\\r{p}%')\nprint()\nprint('end')",
    ]
    with app_output.installed():
        ProcessManager().monitor_terminal_output(command)

    assert app_output.lines() == ["start", "100%", "end", "Command executed successfully!"]


def test_the_app_terminal_keeps_only_the_newest_lines(app_output, monkeypatch):
    monkeypatch.setattr(app_output_module, "MAX_LINES_IN_APP", 10)

    with app_output.installed():
        for line_number in range(25):
            print(f"line {line_number}")

    assert app_output.lines() == [f"line {n}" for n in range(15, 25)]
    assert "line 0" in app_output.log()


def test_each_start_rotates_the_logs_so_panelyze_log_is_only_this_run(tmp_path):
    from gui_classes.AppOutput import open_log_file

    log_file_path = tmp_path / "panelyze.log"
    for run in range(1, 13):
        log_file = open_log_file(str(log_file_path))
        log_file.write(f"run {run}\n")
        log_file.close()

    # 12 runs: this run, then the 9 before it; the 2 oldest are gone.
    assert "run 12" in log_file_path.read_text() and "run 11" not in log_file_path.read_text()
    assert "run 11" in (tmp_path / "panelyze.1.log").read_text()
    assert "run 3" in (tmp_path / "panelyze.9.log").read_text()
    assert {path.name for path in tmp_path.iterdir()} == {"panelyze.log"} | {f"panelyze.{number}.log" for number in range(1, 10)}


@pytest.mark.parametrize("locked_file", ["panelyze.log", "panelyze.2.log"])
def test_a_log_that_can_t_be_moved_leaves_every_log_as_it_was_and_this_run_is_added(tmp_path, monkeypatch, locked_file):
    import os

    from gui_classes import AppOutput

    logs = {"panelyze.log": "the run before\n", "panelyze.1.log": "two runs ago\n", "panelyze.2.log": "three runs ago\n"}
    for name, text in logs.items():
        (tmp_path / name).write_text(text)
    real_replace = os.replace

    def replace(source, destination):
        # Windows can't move a file another program has open (another Panelyze, or a viewer).
        if os.path.basename(source) == locked_file:
            raise PermissionError(32, "The process cannot access the file because it is being used by another process")
        real_replace(source, destination)

    monkeypatch.setattr(AppOutput.os, "replace", replace)

    log_file = AppOutput.open_log_file(str(tmp_path / "panelyze.log"))
    log_file.write("this run\n")
    log_file.close()

    # No old run is lost, and none moved: this run is added to the last one.
    assert {path.name for path in tmp_path.iterdir()} == set(logs)
    assert (tmp_path / "panelyze.log").read_text().startswith("the run before") and "this run" in (tmp_path / "panelyze.log").read_text()
    assert (tmp_path / "panelyze.1.log").read_text() == "two runs ago\n"
    assert (tmp_path / "panelyze.2.log").read_text() == "three runs ago\n"
