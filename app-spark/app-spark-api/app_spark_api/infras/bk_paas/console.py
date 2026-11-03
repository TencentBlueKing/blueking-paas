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

"""开发者中心前端页面的链接。站点地址各环境不同，由调用方传入（即 BKPAAS_URL），为空时一律返回 None。"""

from urllib.parse import quote, urlencode

import attrs


@attrs.frozen
class ConsoleLinks:
    """Where an application's logs, deployments, environment variables and members are managed."""

    logs: str
    deployments: str
    env_vars: str
    members: str


def build_console_links(console_url: str, app_code: str, module: str) -> ConsoleLinks | None:
    """Build the console pages of one application module."""
    app = _build_app_url(console_url, app_code)
    if app is None:
        return None

    mod = quote(module, safe="")
    return ConsoleLinks(
        logs=f"{app}/{mod}/logging",
        deployments=f"{app}/deployments/prod",
        # 云原生应用的环境变量在模块配置里。
        env_vars=f"{app}/{mod}/settings/modules/env",
        members=f"{app}/settings/application/member",
    )


def build_deployment_detail_url(console_url: str, app_code: str, deployment_id: str) -> str | None:
    """Build the page showing one deployment's log."""
    app = _build_app_url(console_url, app_code)
    if app is None:
        return None

    # 部署历史页按 logId 打开对应那次部署的日志侧栏，logId 就是部署接口返回的 deployment_id。
    return f"{app}/deployments/history?{urlencode({'logId': deployment_id})}"


def _build_app_url(console_url: str, app_code: str) -> str | None:
    root = console_url.rstrip("/")
    if not root:
        return None

    return f"{root}/developer-center/apps/{quote(app_code, safe='')}"
