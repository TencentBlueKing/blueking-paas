"""A new app, started the way the instructions describe: three turns, and the project they leave.

A question alone leaves the workspace empty. The first code is preceded by exactly one
init_project call, which writes the template under the app's name. A later change keeps those
files as they are. The tool itself is covered in tests/tools/test_init_project.py; what only a
real model can show is whether it reaches for the tool at the right moment, and only then.
"""

import tomllib
from pathlib import Path
from typing import Any

import pytest

from app_spark_agent import settings
from app_spark_agent.tools.init_project import PROJECT_FILES
from tests.support import console
from tests.support.live import LiveRuntime, model_messages

pytestmark = pytest.mark.live

# The question names the app on purpose: a model that creates the project as soon as it hears
# what the app is called is exactly what the instructions forbid for a question-only turn.
ASK = "I'm going to build an app called Todo Board. Which web framework will you use? One sentence."
START = 'Now start it: main.py with a FastAPI app whose GET / returns {"ok": true}. Do not launch it. Reply DONE.'
CHANGE = 'Add GET /health returning {"status": "ok"} to main.py. Do not launch it. Reply DONE.'
# "Todo Board" normalized the way uv records it in uv.lock.
PROJECT_NAME = "todo-board"
WRITE_TOOLS = {"write_file", "edit_file", "create_directory"}


def test_a_new_app_starts_from_the_project_template(
    runtime: LiveRuntime,
    workspace: Path,
    conversation_id: str,
) -> None:
    console.banner("turn 1: a question alone creates no project")
    asked = runtime.turn(conversation_id=conversation_id, prompt=ASK)

    assert "init_project" not in asked.tool_calls
    assert not any((workspace / name).exists() for name in PROJECT_FILES)

    console.banner("turn 2: the first code is preceded by init_project")
    started = runtime.turn(conversation_id=conversation_id, prompt=START)

    assert started.tool_calls.count("init_project") == 1, started.tool_calls
    writes = [index for index, name in enumerate(started.tool_calls) if name in WRITE_TOOLS]
    assert writes, "the model never wrote main.py with the file tools"
    assert started.tool_calls.index("init_project") < writes[0], started.tool_calls
    missing = [name for name in PROJECT_FILES if not (workspace / name).is_file()]
    assert not missing, f"init_project ran but left no {missing} in the workspace"
    # Compared with app-template/ itself rather than with what the tool renders, so a rendering
    # bug cannot vouch for its own output. Nothing but the name may differ: anything else makes uv
    # treat the lock as stale and re-resolve over the network on the first launch. A uv.lock this
    # exact is also something no model writes by hand, so it can only have come from the tool.
    assert changes_from_template(workspace) == renamed_only(PROJECT_NAME)
    written = {name: (workspace / name).read_bytes() for name in PROJECT_FILES}
    assert "FastAPI" in (workspace / "main.py").read_text()

    console.banner("turn 3: a change to an existing project leaves its files alone")
    changed = runtime.turn(conversation_id=conversation_id, prompt=CHANGE)

    assert "init_project" not in changed.tool_calls
    assert {name: (workspace / name).read_bytes() for name in PROJECT_FILES} == written
    assert "/health" in (workspace / "main.py").read_text()

    console.banner("what the model was told")
    returns = init_project_returns(model_messages(runtime.drain("log")))
    assert returns == [{"status": "created", "name": PROJECT_NAME, "detail": ""}]


def changes_from_template(workspace: Path) -> dict[str, list[tuple[str, str]]]:
    """Return, for each project file, the (template, workspace) line pairs that differ."""
    changes = {}
    for name in PROJECT_FILES:
        template = (settings.APP_TEMPLATE_DIR / name).read_text().splitlines()
        written = (workspace / name).read_text().splitlines()
        assert len(written) == len(template), f"{name} has {len(written)} lines, the template {len(template)}"
        changes[name] = [(old, new) for old, new in zip(template, written, strict=True) if old != new]
    return changes


def renamed_only(name: str) -> dict[str, list[tuple[str, str]]]:
    """Return what changes_from_template reports when the project was renamed and nothing else."""
    template_pyproject = (settings.APP_TEMPLATE_DIR / "pyproject.toml").read_text()
    template_name = tomllib.loads(template_pyproject)["project"]["name"]
    return {filename: [(f'name = "{template_name}"', f'name = "{name}"')] for filename in PROJECT_FILES}


def init_project_returns(messages: list[dict[str, Any]]) -> list[Any]:
    """Return what every init_project call in the transcript handed back to the model."""
    return [
        part["content"]
        for message in messages
        for part in message["parts"]
        if part["part_kind"] == "tool-return" and part["tool_name"] == "init_project"
    ]
