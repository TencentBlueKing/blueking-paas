"""Keep the production image unable to start local Agent processes."""

from pathlib import Path

API_ROOT = Path(__file__).resolve().parents[1]


def read_build_file(name: str) -> str:
    """Read one API image build definition."""
    return (API_ROOT / name).read_text()


def test_production_image_builds_from_the_api_project_only():
    dockerfile = read_build_file("Dockerfile")
    dockerignore = read_build_file("Dockerfile.dockerignore")

    # Production builds from app-spark-api/, so paths stay relative to this project and the
    # sibling Agent never enters the context.
    assert "COPY app-spark-api/" not in dockerfile
    assert "COPY agent/" not in dockerfile
    assert "ADD agent/" not in dockerfile
    assert "!agent/" not in dockerignore
    assert "!app-spark-api/" not in dockerignore
    assert "COPY pyproject.toml uv.lock ./" in dockerfile
    assert "COPY app_spark_api ./app_spark_api" in dockerfile


def test_local_image_explicitly_includes_the_agent_project():
    dockerfile = read_build_file("Dockerfile.local")
    dockerignore = read_build_file("Dockerfile.local.dockerignore")

    # local_process uses --no-sync, so both source and the prebuilt virtualenv must come from
    # this explicit development image instead of leaking back into the production image.
    assert "COPY agent/app_spark_agent ./app_spark_agent" in dockerfile
    assert "RUN uv sync --frozen --no-dev" in dockerfile
    assert "!agent/app_spark_agent/**" in dockerignore
