"""Collection rules shared by the whole agent test suite."""

from __future__ import annotations

import os

# Live Git-host tests need a running Forgejo, so they are opt-in for a developer. They are *not*
# opt-in for CI: the job that sets this variable must fail when Forgejo will not start, rather
# than skipping the only coverage the persistence feature has end to end.
if os.environ.get("APP_SPARK_FORGEJO_LIVE") != "1":
    collect_ignore = ["live_forgejo"]
