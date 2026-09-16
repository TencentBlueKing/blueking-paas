# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) Tencent. All rights reserved.
# Licensed under the MIT License (the "License"); you may not use this file except
# in compliance with the License. You may obtain a copy of the License at
#
#     http://opensource.org/licenses/MIT
#
# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied. See the License for the specific language governing permissions and
# limitations under the License.
#
# We undertake not to change the open source license (MIT license) applicable
# to the current version of the project delivered to anyone in the future.

"""Drive a real Forgejo the way ``tests/api/test_conversations.py`` drives a real Agent.

These tests are not collected unless ``APP_SPARK_FORGEJO_LIVE=1``. When they are,
this fixture starts the sibling ``repo-server/forgejo`` test instance
(``just test-up``) and loads its credentials. A missing Git host fails the job;
it does not skip. Set ``APP_SPARK_FORGEJO_BASE_URL`` and
``APP_SPARK_FORGEJO_SERVICE_ACCOUNT_PASSWORD`` to point at an already-running
instance instead of starting Compose.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

FORGEJO_DIR = Path(__file__).resolve().parents[4] / "repo-server" / "forgejo"


def _parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        values[key] = value
    return values


@pytest.fixture(scope="session")
def forgejo_live_env() -> dict[str, str]:
    """Ensure a Forgejo is reachable and return the settings the tests need."""
    existing_url = os.environ.get("APP_SPARK_FORGEJO_BASE_URL", "").strip()
    existing_password = os.environ.get("APP_SPARK_FORGEJO_SERVICE_ACCOUNT_PASSWORD", "").strip()
    if existing_url and existing_password:
        return {
            "base_url": existing_url,
            "password": existing_password,
            "org": os.environ.get("APP_SPARK_FORGEJO_ORG", "app-spark"),
            "account": os.environ.get("APP_SPARK_FORGEJO_SERVICE_ACCOUNT", "app-spark-bot"),
        }

    just = shutil.which("just")
    if just is None:
        pytest.fail("`just` is required to start repo-server/forgejo")
    justfile = FORGEJO_DIR / "justfile"
    if not justfile.is_file():
        pytest.fail(f"Forgejo justfile missing at {justfile}")

    result = subprocess.run(
        [just, "test-up"],
        cwd=FORGEJO_DIR,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        pytest.fail(f"just test-up failed in {FORGEJO_DIR}:\n{result.stderr or result.stdout}")

    creds_path = FORGEJO_DIR / "secrets" / "test" / "credentials.env"
    if not creds_path.is_file():
        pytest.fail(f"Forgejo test credentials missing: {creds_path}")
    creds = _parse_env_file(creds_path)
    password = creds.get("SERVICE_ACCOUNT_PASSWORD", "").strip()
    if not password:
        pytest.fail(f"SERVICE_ACCOUNT_PASSWORD missing in {creds_path}")

    port = os.environ.get("TEST_HTTP_PORT", "3001")
    base_url = f"http://127.0.0.1:{port}"
    account = creds.get("SERVICE_ACCOUNT_USERNAME", "app-spark-bot")
    org = creds.get("ORG_NAME", "app-spark")
    os.environ["APP_SPARK_FORGEJO_BASE_URL"] = base_url
    os.environ["APP_SPARK_FORGEJO_SERVICE_ACCOUNT_PASSWORD"] = password
    os.environ["APP_SPARK_FORGEJO_SERVICE_ACCOUNT"] = account
    os.environ["APP_SPARK_FORGEJO_ORG"] = org
    return {"base_url": base_url, "password": password, "org": org, "account": account}
