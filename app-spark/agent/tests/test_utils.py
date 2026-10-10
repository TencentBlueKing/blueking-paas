"""Small helpers whose names promise which failure they swallow."""

import signal
import subprocess
import sys
from pathlib import Path

from app_spark_agent.utils import append_text_ignore_unwritable, killpg_ignore_absent


def test_killpg_kills_the_whole_group() -> None:
    process = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"], start_new_session=True)

    killpg_ignore_absent(process.pid, signal.SIGKILL)

    assert process.wait(timeout=5) == -signal.SIGKILL


def test_killpg_on_a_group_that_already_exited_is_not_an_error() -> None:
    process = subprocess.Popen([sys.executable, "-c", "pass"], start_new_session=True)
    process.wait(timeout=5)

    killpg_ignore_absent(process.pid, signal.SIGKILL)


def test_append_creates_the_file_and_then_appends(tmp_path: Path) -> None:
    path = tmp_path / "app.log"

    append_text_ignore_unwritable(path, "first\n")
    append_text_ignore_unwritable(path, "second\n")

    assert path.read_text() == "first\nsecond\n"


def test_append_to_an_unwritable_path_drops_the_text(tmp_path: Path) -> None:
    append_text_ignore_unwritable(tmp_path / "missing-dir" / "app.log", "lost\n")

    assert not (tmp_path / "missing-dir").exists()
