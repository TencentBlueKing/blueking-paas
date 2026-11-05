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

"""A stand-in for the developer center client in publication tests."""

from collections import defaultdict
from typing import Any, Self

from app_spark_api.infras.bk_paas import CreatedApp, Deployment, DeploymentResult


class FakeBkPaaSClient:
    """Answers like a healthy developer center; queue an exception or a result per method to steer a test."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self._queued: dict[str, list[Any]] = defaultdict(list)

    def queue(self, method: str, answer: Any) -> None:
        """Make the next call to method raise answer if it is an exception, else return it."""
        self._queued[method].append(answer)

    def called(self, method: str) -> list[dict[str, Any]]:
        """Return the keyword arguments of every call to method."""
        return [kwargs for name, kwargs in self.calls if name == method]

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *exc: object) -> None:
        return None

    async def create_app(self, **kwargs: Any) -> CreatedApp:
        return self._answer("create_app", kwargs, CreatedApp(kwargs["code"], kwargs["name"], "default"))

    async def upload_package_via_link(self, **kwargs: Any) -> None:
        return self._answer("upload_package_via_link", kwargs, None)

    async def deploy(self, **kwargs: Any) -> Deployment:
        return self._answer("deploy", kwargs, Deployment("d-1"))

    async def get_deployment_result(self, **kwargs: Any) -> DeploymentResult:
        url = f"https://apps.example.com/{kwargs['code']}/"
        return self._answer("get_deployment_result", kwargs, DeploymentResult("successful", access_url=url))

    def _answer(self, method: str, kwargs: dict[str, Any], default: Any) -> Any:
        self.calls.append((method, kwargs))
        answer = self._queued[method].pop(0) if self._queued[method] else default
        if isinstance(answer, BaseException):
            raise answer

        return answer
