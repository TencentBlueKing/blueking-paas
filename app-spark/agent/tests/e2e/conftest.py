"""The API key gate, on top of the shared live-Runtime fixtures.

Everything about starting and stopping processes is in :mod:`tests.support.live_fixtures`, which
:mod:`tests.live` uses too. All this suite adds is the refusal to run without a real key.
"""

import pytest

from app_spark_agent import settings
from tests.support.live_fixtures import StartRuntime, conversation_id, start_runtime, workspace

# pytest only discovers fixtures that are bound in a conftest's own namespace, so importing
# them is the point rather than an accident.
__all__ = ["StartRuntime", "conversation_id", "require_api_key", "start_runtime", "workspace"]


@pytest.fixture(autouse=True)
def require_api_key() -> None:
    """Skip rather than fail when there is no key: these tests spend real money and time."""
    if settings.MODEL.startswith("fake:") or not settings.is_model_ready():
        pytest.skip("e2e needs BK_AIDEV_ACCESS_TOKEN or MODEL_API_KEY, plus MODEL_NAME and MODEL_BASE_URL")
