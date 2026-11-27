"""Small helpers whose names promise which failure they swallow."""

import signal
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from pydantic import BaseModel, ValidationError

from app_spark_agent.utils import first_validation_error, killpg_ignore_absent, write_atomic


def test_killpg_kills_the_whole_group() -> None:
    process = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"], start_new_session=True)

    killpg_ignore_absent(process.pid, signal.SIGKILL)

    assert process.wait(timeout=5) == -signal.SIGKILL


def test_killpg_on_a_group_that_already_exited_is_not_an_error() -> None:
    process = subprocess.Popen([sys.executable, "-c", "pass"], start_new_session=True)
    process.wait(timeout=5)

    killpg_ignore_absent(process.pid, signal.SIGKILL)


def test_concurrent_atomic_writes_of_one_path_do_not_break_each_other(tmp_path: Path) -> None:
    """A shared staging name let one writer unlink the other's file before its replace."""
    target = tmp_path / "app_desc.yaml"

    def write_many(data: bytes) -> None:
        for _ in range(200):
            write_atomic(target, data)

    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(write_many, f"writer {index}\n".encode()) for index in range(4)]
        for future in futures:
            future.result()

    assert target.read_bytes() in {f"writer {index}\n".encode() for index in range(4)}
    assert [path.name for path in tmp_path.iterdir()] == ["app_desc.yaml"]


def test_first_validation_error_formats_field_path_and_message() -> None:
    class Payload(BaseModel):
        count: int

    with pytest.raises(ValidationError) as exc_info:
        Payload.model_validate({"count": "not-an-int"})

    formatted = first_validation_error(exc_info.value)
    assert formatted.startswith("count: ")
