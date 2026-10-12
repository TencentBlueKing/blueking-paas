"""Small helpers whose names promise which failure they swallow."""

import signal
import subprocess
import sys

from app_spark_agent.utils import killpg_ignore_absent


def test_killpg_kills_the_whole_group() -> None:
    process = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"], start_new_session=True)

    killpg_ignore_absent(process.pid, signal.SIGKILL)

    assert process.wait(timeout=5) == -signal.SIGKILL


def test_killpg_on_a_group_that_already_exited_is_not_an_error() -> None:
    process = subprocess.Popen([sys.executable, "-c", "pass"], start_new_session=True)
    process.wait(timeout=5)

    killpg_ignore_absent(process.pid, signal.SIGKILL)
