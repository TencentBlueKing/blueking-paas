# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) Tencent. All rights reserved.
# Licensed under the MIT License (the "License"); you may not use this file except
# in compliance with the License. You may obtain a copy of the License at
#
#     http://opensource.org/licenses/MIT
#
# Unless required by applicable law or agreed to in writing, the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations under the License.
#
# We undertake not to change the open source license (MIT license) applicable
# to the current version of the project delivered to anyone in the future.

"""Developer Center deployment manifest for an Agent-built application."""

from pathlib import Path

from app_spark_agent.app_arch.files import FileSyncResult, sync_text_files
from app_spark_agent.app_arch.python import build_proc_command

# Format references:
# https://github.com/TencentBlueKing/blueking-paas/blob/main/apiserver/paasng/paasng/platform/bkapp_model/serializers/v1alpha2.py
# https://github.com/TencentBlueKing/blueking-paas/blob/main/apiserver/paasng/tests/paasng/platform/smart_app/assets/cnb-image/app_desc.yaml
APP_DESC_FILENAME = "app_desc.yaml"


def render_app_desc(port: int) -> str:
    """Return the complete platform-owned app_desc.yaml document."""
    command = build_proc_command(port)
    return f"""specVersion: 3
module:
  language: Python
  spec:
    processes:
      - name: web
        procCommand: {command}
        services:
          - name: web
            exposedType:
              name: bk/http
            targetPort: {port}
            port: 80
"""


def sync_app_desc(workspace: Path, port: int) -> FileSyncResult:
    """Create or repair the Developer Center application description."""
    return sync_text_files(workspace, {APP_DESC_FILENAME: render_app_desc(port)})
