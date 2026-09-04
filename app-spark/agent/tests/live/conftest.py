"""The shared live-Runtime fixtures, with no API key gate.

A ``fake:`` scenario never reaches a provider, so unlike :mod:`tests.e2e` this suite has
nothing to skip on and runs as part of the default test command.
"""

from __future__ import annotations

from tests.support.live_fixtures import StartRuntime, conversation_id, start_runtime, workspace

# pytest only discovers fixtures that are bound in a conftest's own namespace, so importing
# them is the point rather than an accident.
__all__ = ["StartRuntime", "conversation_id", "start_runtime", "workspace"]
