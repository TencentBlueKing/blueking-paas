"""Keep the production image unable to start local Agent processes."""

import json
import shlex
from pathlib import Path, PurePosixPath

API_ROOT = Path(__file__).resolve().parents[1]

AGENT_SOURCE_DIR = "agent/app_spark_agent"


def read_build_file(name: str) -> str:
    """Read one API image build definition."""
    return (API_ROOT / name).read_text()


def parse_instructions(dockerfile: str) -> list[tuple[str, str]]:
    """Split a Dockerfile into (keyword, arguments) pairs with continuation lines joined."""
    instructions = []
    pending = ""
    for raw_line in dockerfile.splitlines():
        line = raw_line.strip()

        # Docker drops comment and blank lines even in the middle of a continued instruction.
        if not line or line.startswith("#"):
            continue

        if line.endswith("\\"):
            pending += line[:-1] + " "
            continue

        keyword, _, arguments = (pending + line).partition(" ")
        instructions.append((keyword.upper(), arguments.strip()))
        pending = ""

    return instructions


def split_copy_arguments(arguments: str) -> tuple[list[str], str]:
    """Return the sources and destination of a COPY or ADD instruction, ignoring its flags."""
    if arguments.startswith("["):
        paths = json.loads(arguments)
    else:
        paths = [token for token in shlex.split(arguments) if not token.startswith("--")]

    return paths[:-1], paths[-1]


def collect_copy_sources(instructions: list[tuple[str, str]]) -> list[str]:
    """Collect every path a COPY or ADD instruction pulls from the build context."""
    sources = []
    for keyword, arguments in instructions:
        if keyword in {"COPY", "ADD"}:
            sources.extend(split_copy_arguments(arguments)[0])

    return sources


def collect_ignore_patterns(dockerignore: str) -> list[str]:
    """Collect the non-comment patterns of a dockerignore file in order."""
    return [line.strip() for line in dockerignore.splitlines() if line.strip() and not line.startswith("#")]


def collect_directory_exceptions(patterns: list[str], context: Path) -> list[str]:
    """Collect "!" patterns that re-include a whole directory by naming it bare."""
    exceptions = []
    for pattern in patterns:
        if not pattern.startswith("!") or pattern.endswith("/**"):
            continue

        # Re-including a directory admits everything under it, so the file-level rules that follow
        # never apply. The trailing slash form is caught even where the directory is absent.
        if pattern.endswith("/") or (context / pattern[1:]).is_dir():
            exceptions.append(pattern)

    return exceptions


def is_full_uv_sync(arguments: str) -> bool:
    """Tell whether a RUN command installs the project in the working directory, not just its deps."""
    tokens = shlex.split(arguments)
    return tokens[:2] == ["uv", "sync"] and "--no-install-project" not in tokens and "--project" not in tokens


def test_production_image_builds_from_the_api_project_only():
    instructions = parse_instructions(read_build_file("Dockerfile"))
    patterns = collect_ignore_patterns(read_build_file("Dockerfile.dockerignore"))

    # The context is app-spark-api/. A path prefixed with the project name, or one climbing out of
    # it, means someone switched back to the parent context that can see the sibling Agent.
    for source in collect_copy_sources(instructions):
        first_part = PurePosixPath(source).parts[0]
        assert first_part not in {"agent", "app-spark-api", ".."}, source

    destinations = [split_copy_arguments(args)[1] for keyword, args in instructions if keyword in {"COPY", "ADD"}]
    assert not any(PurePosixPath(dest).is_relative_to("/app/agent") for dest in destinations)

    # Starting from "**" keeps new files out of the context until they are admitted on purpose.
    assert patterns[0] == "**"
    assert not any(pattern.startswith(("!agent", "!app-spark-api")) for pattern in patterns)
    assert collect_directory_exceptions(patterns, API_ROOT) == []


def test_dev_image_installs_the_agent_project():
    instructions = parse_instructions(read_build_file("Dockerfile.dev"))
    patterns = collect_ignore_patterns(read_build_file("Dockerfile.dev.dockerignore"))

    assert patterns[0] == "**"
    assert f"!{AGENT_SOURCE_DIR}/**" in patterns
    assert collect_directory_exceptions(patterns, API_ROOT.parent) == []

    # local_process runs the Agent with --no-sync, so the image must install the Agent project
    # itself after its sources land, in the same directory, not only its dependencies.
    workdir = ""
    agent_workdir = None
    synced_after_copy = False
    for keyword, arguments in instructions:
        if keyword == "WORKDIR":
            workdir = arguments
        elif keyword == "COPY" and AGENT_SOURCE_DIR in split_copy_arguments(arguments)[0]:
            agent_workdir = workdir
        elif keyword == "RUN" and agent_workdir is not None and workdir == agent_workdir:
            synced_after_copy = synced_after_copy or is_full_uv_sync(arguments)

    # The Chart's default agent_project_dir points at this directory.
    assert agent_workdir == "/app/agent"
    assert synced_after_copy
